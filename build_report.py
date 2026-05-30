#!/usr/bin/env python3
"""Merge iHerb lookup parts and build comparison.json + comparison.html."""

import json
import os
import html
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

def load_parts():
    out = []
    for i in range(1, 5):
        path = os.path.join(ROOT, f'iherb_results_part{i}.json')
        if not os.path.exists(path):
            print(f"  WARN: missing {path}")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            part = json.load(f)
        print(f"  Part {i}: {len(part)} items")
        out.extend(part)
    return out

def enrich(items, selection):
    """Add brand group and our_price as float; compute diff%, conclusion."""
    # Build lookup from selection by (brand, product_name, size) -> group
    sel_lookup = {}
    for s in selection:
        key = (s.get('brand',''), s.get('product_name',''), str(s.get('size','')))
        sel_lookup[key] = s.get('group', 'top20')

    enriched = []
    for it in items:
        rec = dict(it)
        key = (rec.get('brand',''), rec.get('product_name',''), str(rec.get('size','')))
        rec['group'] = sel_lookup.get(key, 'top20')

        try:
            ours = float(rec.get('our_price') or 0)
        except (ValueError, TypeError):
            ours = 0.0
        try:
            iherb = float(rec.get('iherb_price') or 0) if rec.get('iherb_price') is not None else None
        except (ValueError, TypeError):
            iherb = None

        rec['our_price'] = ours
        rec['iherb_price'] = iherb

        if iherb and ours:
            diff_abs = ours - iherb
            diff_pct = (diff_abs / iherb) * 100
            rec['diff_pct'] = round(diff_pct, 1)
            rec['diff_abs'] = round(diff_abs, 2)
            if diff_pct < -1:
                rec['verdict'] = 'cheaper'
            elif diff_pct > 1:
                rec['verdict'] = 'more_expensive'
            else:
                rec['verdict'] = 'same'
        else:
            rec['diff_pct'] = None
            rec['diff_abs'] = None
            rec['verdict'] = 'no_data'
        enriched.append(rec)
    return enriched

def summary(items):
    matched = [i for i in items if i['iherb_price'] is not None]
    cheaper = [i for i in matched if i['verdict'] == 'cheaper']
    expensive = [i for i in matched if i['verdict'] == 'more_expensive']
    same = [i for i in matched if i['verdict'] == 'same']
    no_data = [i for i in items if i['verdict'] == 'no_data']

    s = {
        'total': len(items),
        'matched': len(matched),
        'no_match': len(no_data),
        'we_cheaper': len(cheaper),
        'we_expensive': len(expensive),
        'we_same': len(same),
    }
    if matched:
        avg_diff = sum(i['diff_pct'] for i in matched) / len(matched)
        s['avg_diff_pct'] = round(avg_diff, 1)
        if cheaper:
            s['avg_cheaper_pct'] = round(sum(i['diff_pct'] for i in cheaper) / len(cheaper), 1)
        else:
            s['avg_cheaper_pct'] = 0
        if expensive:
            s['avg_expensive_pct'] = round(sum(i['diff_pct'] for i in expensive) / len(expensive), 1)
        else:
            s['avg_expensive_pct'] = 0
    return s

def build_html(items, stats):
    brands = sorted({i['brand'] for i in items})
    rows = []
    for i in items:
        verdict = i['verdict']
        verdict_label = {
            'cheaper': '🟢 Мы дешевле',
            'more_expensive': '🔴 Мы дороже',
            'same': '⚪ Одинаково',
            'no_data': '⚫ Нет данных'
        }[verdict]
        verdict_class = {
            'cheaper': 'cheaper',
            'more_expensive': 'expensive',
            'same': 'same',
            'no_data': 'nodata'
        }[verdict]
        iherb_price_str = f"${i['iherb_price']:.2f}" if i['iherb_price'] is not None else '—'
        diff_str = ''
        if i['diff_pct'] is not None:
            sign = '+' if i['diff_pct'] > 0 else ''
            diff_str = f"{sign}{i['diff_pct']:.1f}%"
        iherb_link = ''
        if i.get('iherb_url'):
            iherb_link = f' <a class="ext" href="{html.escape(i["iherb_url"])}" target="_blank" rel="noopener">↗</a>'
        size = html.escape(str(i.get('size','')))
        rows.append(f"""
        <tr class="row-{verdict_class}" data-brand="{html.escape(i['brand'])}" data-group="{i.get('group','top20')}" data-verdict="{verdict}">
          <td class="brand">{html.escape(i['brand'])}</td>
          <td class="name">{html.escape(i['product_name'])}<span class="size"> · {size}</span>{iherb_link}</td>
          <td class="num">${i['our_price']:.2f}</td>
          <td class="num">{iherb_price_str}</td>
          <td class="num diff">{diff_str}</td>
          <td class="verdict">{verdict_label}</td>
        </tr>""")

    options = ''.join(f'<option value="{html.escape(b)}">{html.escape(b)}</option>' for b in brands)

    gen_date = datetime.now().strftime('%Y-%m-%d %H:%M')

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Сравнение цен: KGSilkRoad vs iHerb</title>
<style>
  :root {{
    --bg: #f6f7f9;
    --card: #ffffff;
    --text: #1a1d23;
    --muted: #6b7280;
    --border: #e5e7eb;
    --green: #16a34a;
    --green-bg: #ecfdf5;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --gray: #9ca3af;
    --accent: #2563eb;
    --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  .container {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 32px 24px;
  }}
  h1 {{
    margin: 0 0 8px;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 24px;
  }}
  .stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
  }}
  .stat {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    box-shadow: var(--shadow);
  }}
  .stat-label {{
    font-size: 12px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }}
  .stat-value {{
    font-size: 24px;
    font-weight: 700;
  }}
  .stat-value.green {{ color: var(--green); }}
  .stat-value.red {{ color: var(--red); }}
  .note {{
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 13px;
    color: #78350f;
  }}
  .note strong {{ color: #92400e; }}
  .controls {{
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }}
  .controls input, .controls select {{
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: var(--card);
    color: var(--text);
  }}
  .controls input:focus, .controls select:focus {{
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }}
  .controls input {{ flex: 1; min-width: 200px; }}
  .table-wrap {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: var(--shadow);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }}
  th {{
    background: #fafbfc;
    text-align: left;
    padding: 12px 16px;
    font-weight: 600;
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 1;
  }}
  th:hover {{ background: #f0f2f5; }}
  th.num {{ text-align: right; }}
  td {{
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}
  td.brand {{ font-weight: 600; white-space: nowrap; }}
  td.name {{ max-width: 480px; }}
  td.name .size {{ color: var(--muted); font-size: 12px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
  td.diff {{ font-weight: 600; }}
  td.verdict {{ white-space: nowrap; font-weight: 500; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.row-cheaper td.diff {{ color: var(--green); }}
  tr.row-expensive td.diff {{ color: var(--red); }}
  tr:hover {{ background: #fafbfc; }}
  .ext {{
    color: var(--accent);
    text-decoration: none;
    margin-left: 4px;
    font-size: 12px;
  }}
  .ext:hover {{ text-decoration: underline; }}
  .footer {{
    margin-top: 24px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
  }}
  .hidden {{ display: none; }}
</style>
</head>
<body>
  <div class="container">
    <h1>Сравнение цен: KGSilkRoad vs iHerb</h1>
    <p class="subtitle">Топ-20 брендов × 10 позиций + 2 протеиновых бренда × 10 — данные на {gen_date}</p>

    <div class="stats">
      <div class="stat"><div class="stat-label">Всего позиций</div><div class="stat-value">{stats['total']}</div></div>
      <div class="stat"><div class="stat-label">Найдено на iHerb</div><div class="stat-value">{stats['matched']}</div></div>
      <div class="stat"><div class="stat-label">Мы дешевле</div><div class="stat-value green">{stats['we_cheaper']}</div></div>
      <div class="stat"><div class="stat-label">Мы дороже</div><div class="stat-value red">{stats['we_expensive']}</div></div>
      <div class="stat"><div class="stat-label">Сред. разница</div><div class="stat-value">{stats.get('avg_diff_pct', 0):+.1f}%</div></div>
    </div>

    <div class="note">
      <strong>Примечание:</strong> Из запрошенных 5 протеиновых брендов в каталоге найдены только <strong>Muscle Tech</strong> и <strong>Redcon1</strong>. Бренды Optimum Nutrition, BSN и Rule1 в dsn_products.json отсутствуют. Также 4 бренда из исходного топ-20 (Source Naturals, Swanson, Nutricost, Nature's Plus) содержат только SKU-коды вместо названий товаров и были заменены следующими в рейтинге.
    </div>

    <div class="controls">
      <input type="text" id="search" placeholder="Поиск по названию…" />
      <select id="brand-filter"><option value="">Все бренды</option>{options}</select>
      <select id="verdict-filter">
        <option value="">Все результаты</option>
        <option value="cheaper">Только дешевле</option>
        <option value="more_expensive">Только дороже</option>
        <option value="same">Одинаково</option>
        <option value="no_data">Нет данных iHerb</option>
      </select>
    </div>

    <div class="table-wrap">
      <table id="comparison-table">
        <thead>
          <tr>
            <th data-sort="brand">Бренд</th>
            <th data-sort="name">Название</th>
            <th class="num" data-sort="our">Наша $</th>
            <th class="num" data-sort="iherb">iHerb $</th>
            <th class="num" data-sort="diff">Разница</th>
            <th data-sort="verdict">Вывод</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}
        </tbody>
      </table>
    </div>

    <div class="footer">Сгенерировано автоматически на основе dsn_products.json и поиска по iHerb.com</div>
  </div>

<script>
  const search = document.getElementById('search');
  const brandFilter = document.getElementById('brand-filter');
  const verdictFilter = document.getElementById('verdict-filter');
  const rows = Array.from(document.querySelectorAll('#comparison-table tbody tr'));

  function applyFilters() {{
    const q = search.value.toLowerCase().trim();
    const b = brandFilter.value;
    const v = verdictFilter.value;
    rows.forEach(r => {{
      const name = r.querySelector('.name').textContent.toLowerCase();
      const brand = r.dataset.brand;
      const verdict = r.dataset.verdict;
      const matchQ = !q || name.includes(q) || brand.toLowerCase().includes(q);
      const matchB = !b || brand === b;
      const matchV = !v || verdict === v;
      r.classList.toggle('hidden', !(matchQ && matchB && matchV));
    }});
  }}
  search.addEventListener('input', applyFilters);
  brandFilter.addEventListener('change', applyFilters);
  verdictFilter.addEventListener('change', applyFilters);

  // Sort
  const tbody = document.querySelector('#comparison-table tbody');
  document.querySelectorAll('th[data-sort]').forEach((th, idx) => {{
    let asc = true;
    th.addEventListener('click', () => {{
      const sorted = rows.slice().sort((a, b) => {{
        const ka = a.children[idx].textContent.trim();
        const kb = b.children[idx].textContent.trim();
        const na = parseFloat(ka.replace(/[^0-9.\-]/g, ''));
        const nb = parseFloat(kb.replace(/[^0-9.\-]/g, ''));
        if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
        return asc ? ka.localeCompare(kb) : kb.localeCompare(ka);
      }});
      sorted.forEach(r => tbody.appendChild(r));
      asc = !asc;
    }});
  }});
</script>
</body>
</html>
"""

def main():
    print("Loading parts...")
    items = load_parts()
    print(f"Total items: {len(items)}")

    with open(os.path.join(ROOT, 'selection.json'), 'r', encoding='utf-8') as f:
        selection = json.load(f)

    enriched = enrich(items, selection)
    stats = summary(enriched)
    print(f"\nStats: {stats}")

    # Sort: by brand, then verdict (cheaper first), then name
    verdict_order = {'cheaper': 0, 'more_expensive': 1, 'same': 2, 'no_data': 3}
    enriched.sort(key=lambda x: (x['brand'], verdict_order.get(x['verdict'], 9), x['product_name']))

    out = {
        'generated_at': datetime.now().isoformat(),
        'stats': stats,
        'items': enriched,
    }
    with open(os.path.join(ROOT, 'comparison.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Wrote comparison.json")

    html_doc = build_html(enriched, stats)
    with open(os.path.join(ROOT, 'comparison.html'), 'w', encoding='utf-8') as f:
        f.write(html_doc)
    print("Wrote comparison.html")

if __name__ == '__main__':
    main()
