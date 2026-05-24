import asyncio
import json
import os
import re
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "https://simplepeptidewholesale.com"
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)


async def login(page):
    print("→ Logging in...")
    await page.goto(f"{BASE_URL}/my-account/", wait_until="networkidle")
    await page.fill("#username", "Contact01")
    await page.fill("#password", "Kgsilkroad2026_")
    await page.click('button[name="login"]')
    await page.wait_for_load_state("networkidle")
    print("✓ Logged in")


async def collect_product_links(page):
    print("→ Collecting product links from all pages...")
    all_links = []
    page_num = 1

    while True:
        url = f"{BASE_URL}/shop/page/{page_num}/" if page_num > 1 else f"{BASE_URL}/shop/"
        print(f"  Scraping shop page {page_num}: {url}")
        await page.goto(url, wait_until="networkidle")

        # Check if page exists (404 or no products)
        if page.url != url and "page" in url:
            print(f"  → Redirected, no more pages")
            break

        links = await page.eval_on_selector_all(
            "ul.products li.product a.woocommerce-LoopProduct-link",
            "els => els.map(e => e.href)"
        )

        if not links:
            # Try alternative selector
            links = await page.eval_on_selector_all(
                ".products .product a:first-child",
                "els => els.map(e => e.href)"
            )

        # Deduplicate
        new_links = [l for l in links if l not in all_links and BASE_URL in l]
        if not new_links:
            print(f"  → No new products found, stopping pagination")
            break

        all_links.extend(new_links)
        print(f"  ✓ Found {len(new_links)} products on page {page_num} (total: {len(all_links)})")

        # Check if there's a next page
        next_btn = await page.query_selector("a.next.page-numbers")
        if not next_btn:
            break
        page_num += 1

    # Deduplicate final list
    all_links = list(dict.fromkeys(all_links))
    print(f"✓ Total unique product links: {len(all_links)}")
    return all_links


async def download_image(url: str, filename: str) -> str:
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                filepath = IMAGES_DIR / filename
                filepath.write_bytes(resp.content)
                return str(filepath)
    except Exception as e:
        print(f"    ! Image download failed: {e}")
    return ""


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[^\w\-_.]', '_', name)
    return name[:100]


async def scrape_product(page, url: str, index: int, total: int) -> dict:
    print(f"\n[{index}/{total}] Scraping: {url}")
    await page.goto(url, wait_until="networkidle")

    product = {"url": url}

    # Title
    try:
        product["name"] = await page.inner_text("h1.product_title")
        product["name"] = product["name"].strip()
    except:
        product["name"] = ""
    print(f"  Name: {product['name']}")

    # Main image
    img_url = ""
    try:
        img_el = await page.query_selector(".woocommerce-product-gallery__image img")
        if img_el:
            img_url = await img_el.get_attribute("data-large_image") or \
                      await img_el.get_attribute("src") or ""
    except:
        pass

    if img_url:
        ext = img_url.split("?")[0].rsplit(".", 1)[-1] if "." in img_url else "jpg"
        safe_name = sanitize_filename(product["name"]) or f"product_{index}"
        filename = f"{safe_name}.{ext}"
        product["image_local"] = await download_image(img_url, filename)
        product["image_url"] = img_url
        print(f"  Image: {product['image_local']}")
    else:
        product["image_local"] = ""
        product["image_url"] = ""

    # Description text
    try:
        desc = await page.inner_text(".woocommerce-product-details__short-description")
        product["short_description"] = desc.strip()
    except:
        product["short_description"] = ""

    try:
        full_desc = await page.inner_text("#tab-description")
        product["full_description"] = full_desc.strip()
    except:
        product["full_description"] = ""

    # Product meta / attributes (CAS Number, Molecular Formula, etc.)
    meta_fields = {}
    target_fields = [
        "cas number", "cas", "molecular formula", "molecular weight",
        "form", "quantity", "purity", "sequence", "molecular mass"
    ]

    # Try table rows in description or product attributes
    try:
        rows = await page.query_selector_all("table tr, .shop_attributes tr, .woocommerce-product-attributes tr")
        for row in rows:
            cells = await row.query_selector_all("td, th")
            if len(cells) >= 2:
                key = (await cells[0].inner_text()).strip().lower().rstrip(":")
                val = (await cells[1].inner_text()).strip()
                if any(f in key for f in target_fields):
                    meta_fields[key] = val
    except:
        pass

    # Also try definition lists
    try:
        dts = await page.query_selector_all(".woocommerce-product-attributes dt, .product_meta dt, dl dt")
        dds = await page.query_selector_all(".woocommerce-product-attributes dd, .product_meta dd, dl dd")
        for dt, dd in zip(dts, dds):
            key = (await dt.inner_text()).strip().lower().rstrip(":")
            val = (await dd.inner_text()).strip()
            if any(f in key for f in target_fields) or True:
                meta_fields[key] = val
    except:
        pass

    # Try parsing from description text with regex
    desc_text = product.get("full_description", "") + " " + product.get("short_description", "")
    patterns = {
        "cas_number": r"CAS(?:\s+Number)?[:\s]+([A-Z0-9\-]+)",
        "molecular_formula": r"Molecular\s+Formula[:\s]+([A-Z0-9]+)",
        "molecular_weight": r"Molecular\s+Weight[:\s]+([\d.,]+(?:\s*g/mol)?)",
        "purity": r"Purity[:\s]+([\d.]+\s*%[^,\n]*)",
        "form": r"\bForm[:\s]+([^\n,]+)",
    }
    for field, pattern in patterns.items():
        m = re.search(pattern, desc_text, re.IGNORECASE)
        if m and field not in meta_fields:
            meta_fields[field] = m.group(1).strip()

    product["attributes"] = meta_fields

    # Wholesale pricing table
    wholesale_pricing = []
    try:
        # Look for pricing tables - common selectors for WooCommerce
        table_selectors = [
            ".wholesale_price_container table",
            ".wholesale-price-table table",
            "table.wholesale",
            ".wc-pao-addon-container table",
            ".entry-content table",
            "table",
        ]
        for sel in table_selectors:
            tables = await page.query_selector_all(sel)
            for table in tables:
                headers = []
                header_els = await table.query_selector_all("thead th, thead td, tr:first-child th, tr:first-child td")
                for h in header_els:
                    headers.append((await h.inner_text()).strip())

                # Check if this looks like a pricing table
                header_text = " ".join(headers).lower()
                if not any(w in header_text for w in ["qty", "quantity", "price", "wholesale", "unit", "amount"]):
                    continue

                rows = await table.query_selector_all("tbody tr, tr:not(:first-child)")
                for row in rows:
                    cells = await row.query_selector_all("td, th")
                    row_data = {}
                    for i, cell in enumerate(cells):
                        key = headers[i] if i < len(headers) else f"col_{i}"
                        row_data[key] = (await cell.inner_text()).strip()
                    if row_data:
                        wholesale_pricing.append(row_data)

                if wholesale_pricing:
                    break
            if wholesale_pricing:
                break
    except Exception as e:
        print(f"  ! Pricing table error: {e}")

    product["wholesale_pricing"] = wholesale_pricing
    if wholesale_pricing:
        print(f"  Pricing rows: {len(wholesale_pricing)}")

    # Extract specific named fields from attributes for convenience
    for key, val in meta_fields.items():
        if "cas" in key:
            product["cas_number"] = val
        elif "molecular formula" in key or "formula" in key:
            product["molecular_formula"] = val
        elif "molecular weight" in key or "weight" in key or "mass" in key:
            product["molecular_weight"] = val
        elif "form" == key or "form " in key:
            product["form"] = val
        elif "quantity" in key:
            product["quantity"] = val
        elif "purity" in key:
            product["purity"] = val

    # Also check for these fields in a structured product info section
    info_selectors = [
        (".product-info-table", "tr"),
        (".product_meta", "span"),
        (".product-details", "li"),
    ]
    for container_sel, item_sel in info_selectors:
        try:
            container = await page.query_selector(container_sel)
            if container:
                items = await container.query_selector_all(item_sel)
                for item in items:
                    text = (await item.inner_text()).strip()
                    for label in ["CAS Number", "CAS", "Molecular Formula", "Molecular Weight", "Form", "Quantity", "Purity"]:
                        if text.lower().startswith(label.lower()):
                            val = text[len(label):].lstrip(":").strip()
                            key = label.lower().replace(" ", "_")
                            if key not in product:
                                product[key] = val
        except:
            pass

    print(f"  ✓ Done: {product.get('cas_number', 'N/A CAS')}")
    return product


async def main():
    products_file = Path("products.json")
    existing = {}
    if products_file.exists():
        try:
            with open(products_file) as f:
                data = json.load(f)
            existing = {p["url"]: p for p in data}
            print(f"→ Loaded {len(existing)} existing products")
        except:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        await login(page)

        links = await collect_product_links(page)

        all_products = list(existing.values())
        done_urls = set(existing.keys())
        total = len(links)

        for i, link in enumerate(links, 1):
            if link in done_urls:
                print(f"[{i}/{total}] Skipping (already scraped): {link}")
                continue
            try:
                product = await scrape_product(page, link, i, total)
                all_products.append(product)
                done_urls.add(link)

                # Save after each product
                with open(products_file, "w", encoding="utf-8") as f:
                    json.dump(all_products, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  ! Error scraping {link}: {e}")

        await browser.close()

    print(f"\n✓ Scraping complete. {len(all_products)} products saved to products.json")


if __name__ == "__main__":
    asyncio.run(main())
