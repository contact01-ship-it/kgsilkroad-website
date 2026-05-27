# SPECIFICATION — KG Silkroad Inc. Website

**Version:** 1.0  
**Date:** 2026-05-27  
**Status:** Current (covers deployed state of main branch)

---

## 1. Problem Statement

CIS-country wholesalers (Kazakhstan, Kyrgyzstan, Uzbekistan, Russia) have no efficient direct channel to purchase US-sourced vitamins, peptides, and sports nutrition at true wholesale prices. Existing routes require local middlemen who add 30–60% markup and offer no volume price transparency.

KG Silkroad provides a direct B2B ordering channel: browse products, see tiered wholesale pricing, and place an inquiry via WhatsApp or an on-site request form.

**Target buyer:** Gym owners, pharmacy chains, supplement retailers, B2B buyers in CIS. Minimum order: 20 units total / 5 per SKU.

---

## 2. Goals and Non-Goals

### Goals
- Present ~60+ peptides and 200+ vitamin/sports nutrition brands with wholesale pricing
- Allow buyers to estimate order cost before contacting (bulk calculator, shipping calculator)
- Drive WhatsApp/email contact for order placement
- Build trust with a premium design matching the product quality positioning
- Bilingual: Russian (primary), English (secondary), Kyrgyz (AI assistant only)

### Non-Goals
- No online payment or checkout (orders fulfilled via WhatsApp/email)
- No user accounts or login
- No CMS or admin interface
- No inventory management

---

## 3. User Stories

| As a... | I want to... | So that... |
|---------|-------------|-----------|
| B2B buyer | Browse peptides with pricing tiers | I can plan my order volume |
| B2B buyer | Calculate total cost for a bulk order | I know my COGS before committing |
| B2B buyer | Calculate shipping to my country | I can include landed cost in pricing |
| B2B buyer | See MOQ conditions clearly | I understand minimum commitment before browsing |
| B2B buyer | Ask questions in my language | I can get answers without a sales call |
| Site owner | Show product catalog without a backend | Maintenance is simple; no DB to manage |

---

## 4. Architecture

```
Static HTML/CSS/JS (GitHub Pages / Cloudflare Pages)
│
├── index.html          — Homepage: hero, categories, how it works,
│                         bulk calculator, shipping calculator, CTA
├── peptides.html       — Peptide catalog with search/filter + MOQ strip
├── vitamins.html       — Vitamin & supplement brand directory
├── brand.html          — Individual brand product page (URL param: ?brand=)
│
├── products.json       — (legacy / unused in prod)
├── dsn_brands.json     — Brand list + product data (inline in vitamins.html)
├── dsn_products.json   — Full product detail data
│
└── Cloudflare Worker   — anthropic-proxy.kgsilkroad.workers.dev
                          Proxies AI chat requests; holds Anthropic API key
```

**No build step. No framework. No npm.** All JS is vanilla, all CSS is hand-written using CSS variables. Deployed as static files.

---

## 5. Pages and Modules

### 5.1 index.html — Homepage

**Sections (top to bottom):**

1. **Nav** — Logo, category links (Vitamins, Peptides, Sports), Calculator, Shipping anchors; WhatsApp button; language switcher (RU/EN); cart icon with count badge
2. **Hero** — Full-viewport background, headline, stats (60+ peptides, 200+ brands, 4 CIS countries), CTA buttons
3. **Category Cards** — Vitamins, Peptides, Sports Nutrition; each links to respective page
4. **Brand Ticker** — Animated horizontal scroll of brand names
5. **How It Works** — 4-step process: Browse → Calculator → Send Request → Receive Shipment
6. **Logistics Strip** — 4 origin-to-destination lanes with transit times and packaging types
7. **Bulk Order Calculator** — (Peptides only) Select product + qty → see tier price, unit cost, total, savings vs. list; highlights active pricing tier in table; "Add to Cart" integration
8. **Shipping Calculator** — Enter weight in kg → auto-calculates estimated shipping cost to KG, KZ, UZ, RU at fixed per-kg rates
9. **CTA Section** — WhatsApp contact + email
10. **Footer** — Contact info, navigation, copyright

**Cart System:**
- `cart[]` array stores `{name, price, qty}`
- `addToCart(item)` — adds with qty=1
- `addBulkToCart()` — adds from calculator with selected tier price and specified qty
- `updateCart()` — re-renders cart drawer, calculates total
- `submitRequest()` — opens WhatsApp with cart contents as pre-filled message
- Cart drawer slides in from right; persists in-session only (no localStorage)

**AI Assistant:**
- Floating chat button (bottom-right)
- Sends user messages to Cloudflare Worker proxy → Anthropic Claude claude-sonnet-4-20250514
- System prompt: KG Silkroad product knowledge, pricing context, WhatsApp contact
- Language auto-detection (RU/EN/KG); `SHOW_WHATSAPP` trigger in AI response adds contact link
- Chat history maintained per session in `chatHistory[]`

**Language System:**
- `setLang(lang)` function toggles `data-ru` / `data-en` span visibility
- Default: Russian; URL param `?lang=en` or user click switches language
- Language stored in `window.currentLang`

### 5.2 peptides.html — Peptide Catalog

- Full searchable/filterable product grid loaded from inline `PEP_DATA[]` array (~110 peptides)
- Search by name; filter tabs: All / Lyophilized Powder / Capsules
- Each product card: image, name, CAS number, pricing table, "Add to Cart" button
- **MOQ Strip** (below page header): 4 metric tiles (20 units total, 5/SKU, ships 1-2 days USA, CIS 2-3 weeks) + packaging options (Naked / Generic Label / Private Label highlighted)
- Product modal: full attribute table (form, CAS, formula, molecular weight) + full pricing tier table
- Bilingual RU/EN

### 5.3 vitamins.html — Vitamin & Brand Directory

- Filter tabs: All / Vitamins / Sports Nutrition
- Brand search by name
- Each card links to `brand.html?brand=<encoded-name>`
- Data: `BRANDS_DATA` object (inline, ~200+ brands)

### 5.4 brand.html — Brand Detail Page

- Reads `?brand=` URL parameter
- Displays paginated product table for selected brand
- Product columns: name, SKU count, price, category
- Cart integration: "Add" button on each row

---

## 6. Data Structures

### Peptide product (`pepData[]` in index.html, `PEP_DATA[]` in peptides.html)
```js
{
  name: "GHRP-2",
  tag: "Порошок",
  form: "Lyophilized Powder",
  cas: "158861-67-7",
  formula: "C45H55N9O6",
  weight: "817.0 g/mol",
  img: "https://...",
  imgs: ["https://...", ...],          // peptides.html only
  desc: "Research use only...",
  pricing: [
    { q: "5 - 29", p: "$39.49" },
    { q: "30 - 99", p: "$36.86" },
    ...
    { q: "1000+", p: "$26.33" }
  ],
  price: 39.49,                        // numeric, lowest tier fallback
  purity: "≥98%"
}
```

### Pricing tier parsing (`parsePricingTier(q)`)
```js
// "5 - 29"  → { min: 5, max: 29 }
// "1000+"   → { min: 1000, max: Infinity }
```

### Cart item
```js
{ name: "GHRP-2", price: 36.86, qty: 30 }
```

### Shipping rates (per kg in USD)
| Country | Code | Rate |
|---------|------|------|
| Kyrgyzstan | KG | $12 |
| Kazakhstan | KZ | $12 |
| Uzbekistan | UZ | $13 |
| Russia | RU | $20 |

---

## 7. Cloudflare Worker Proxy

**URL:** `https://anthropic-proxy.kgsilkroad.workers.dev`  
**Method:** POST  
**Body:** `{ model, max_tokens, system, messages }` — proxied directly to Anthropic Messages API  
**Auth:** Anthropic API key stored as Cloudflare Worker environment secret (never exposed client-side)  
**CORS:** Permissive (allows requests from site origin)

---

## 8. Theme and Design System

```css
--deep:     #0f1f16   /* darkest background */
--forest:   #182d20   /* section background */
--forest2:  #1e3628   /* alternate section */
--gold:     #C4973A   /* primary accent */
--gold-l:   #d4a84a   /* hover gold */
--parchment:#F3EDE0   /* body text */
```

**Typography:**
- Display: Cormorant Garamond (serif) — headings, prices
- Body: Jost (sans-serif) — navigation, labels, body copy

**Shared patterns:**
- Section labels: `0.62rem`, `letter-spacing: 0.26em`, uppercase, gold
- Buttons: `.btn-gold` (gold fill), `.btn-outline` (white border)
- Reveal animations: `.reveal` + IntersectionObserver → `.visible` class
- Mobile breakpoints: 720px (single-column), 480px (nav collapse)

---

## 9. Security Posture

### Findings (reviewed 2026-05-27)

| Severity | Area | Finding | Status |
|----------|------|---------|--------|
| HIGH | XSS — AI chat | Bot responses injected via `innerHTML` without escaping — prompt injection could execute arbitrary HTML | **FIXED** in this review |
| HIGH | Rate limiting | Cloudflare Worker has no rate limiting — open endpoint burns API credits | **OPEN** — add Cloudflare Rate Limiting rule (free tier) |
| LOW | XSS — product names | `item.name` rendered via `innerHTML` in cart, modal, brand table — data is static/hardcoded so no active path, but would be a vector if data ever comes from an API | Note for future |
| LOW | Security headers | No `Content-Security-Policy`, `X-Frame-Options`, or `X-Content-Type-Options` headers set | Note for future |
| PASS | Secrets | No API keys in client-side code; Anthropic key is in Worker env secret | OK |
| PASS | Auth/IDOR | No user accounts; no protected resources | N/A |
| PASS | HTTPS | Enforced by Cloudflare | OK |
| PASS | Dependencies | No external JS scripts (fonts only via Google Fonts CDN) | OK |

### Fix applied
`escapeHtml()` helper added to `index.html`. All `addMsg('bot', reply)` calls now go through HTML entity encoding before `innerHTML` injection, preventing prompt-injection XSS.

### Recommended next actions
1. **Worker rate limiting:** In Cloudflare dashboard → Security → WAF → Rate Limiting, add rule: max 20 req/min per IP to `anthropic-proxy.kgsilkroad.workers.dev`
2. **CSP header:** Add via Cloudflare Transform Rules or `_headers` file:
   ```
   Content-Security-Policy: default-src 'self'; script-src 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; connect-src https://anthropic-proxy.kgsilkroad.workers.dev; img-src 'self' https: data:
   ```

---

## 10. Launch Checklist

- [x] Peptide catalog (110+ SKUs with pricing tiers)
- [x] Vitamin/sports brand directory (200+ brands)
- [x] Bulk Order Calculator (peptides)
- [x] Shipping Calculator (KG, KZ, UZ, RU)
- [x] AI assistant (Cloudflare Worker proxy)
- [x] MOQ conditions strip (peptides page)
- [x] Bilingual RU/EN throughout
- [x] Cart + WhatsApp request flow
- [x] Mobile responsive
- [ ] Rate limiting on AI proxy endpoint
- [ ] CSP / security headers
- [ ] `robots.txt` and `sitemap.xml`
- [ ] Google Analytics or Cloudflare Web Analytics
