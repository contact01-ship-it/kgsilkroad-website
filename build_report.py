#!/usr/bin/env python3
"""Build comparison.html from comparison_fixed.json (or fallback to comparison.json)."""

import json
import os
import html
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

def load_data():
    fixed = os.path.join(ROOT, 'comparison_fixed.json')
    if os.path.exists(fixed):
        with open(fixed, 'r', encoding='utf-8') as f:
            return json.load(f), True
    with open(os.path.join(ROOT, 'comparison.json'), 'r', encoding='utf-8') as f:
        return json.load(f), False

def build_html(data, fixed):
    items = data['items']
    stats = data['stats']
    brands = sorted({i['brand'] for i in items})
    gen_date = datetime.now().strftime('%Y-%m-%d %H:%M')

    rows = []
    for i in items:
        verdict = i['verdict']
        verdict_label = {
            'cheaper': '🟢 Мы дешевле',
            'more_expensive': '🔴 Мы дороже',
            'same': '⚪ Одинаково',
            'no_data': '⚫ Нет данных iHerb',
            'not_comparable': '◐ Не сравнимо',
        }.get(verdict, verdict)
        verdict_class = {
            'cheaper': 'cheaper',
            'more_expensive': 'expensive',
            'same': 'same',
            'no_data': 'nodata',
            'not_comparable': 'notcomp',
        }.get(verdict, 'nodata')

        iherb_price_str = f"${i['iherb_price']:.2f}" if i['iherb_price'] is not None else '—'
        diff_str = ''
        if i['diff_pct'] is not None:
            sign = '+' if i['diff_pct'] > 0 else ''
            diff_str = f"{sign}{i['diff_pct']:.1f}%"
        elif verdict == 'not_comparable':
            diff_str = 'n/a'

        # Per-unit normalization badge
        norm_badge = ''
        if i.get('per_unit'):
            pu = i['per_unit']
            unit = pu['unit']
            norm_badge = (
                f'<div class="per-unit">'
                f'<span class="badge">за 1 {html.escape(unit)}</span> '
                f'<span class="pu-num">${pu["our_per_unit"]:.4f} vs ${pu["iherb_per_unit"]:.4f}</span>'
                f'</div>'
            )
        elif i.get('original_diff_pct') is not None and verdict == 'not_comparable':
            norm_badge = (
                f'<div class="per-unit">'
                f'<span class="badge badge-warn">пересмотрено</span> '
                f'<span class="pu-num">было {i["original_diff_pct"]:+.0f}%</span>'
                f'</div>'
            )

        iherb_link = ''
        if i.get('iherb_url'):
            iherb_link = f' <a class="ext" href="{html.escape(i["iherb_url"])}" target="_blank" rel="noopener" title="Открыть на iHerb">↗</a>'

        size = html.escape(str(i.get('size', '') or ''))
        notes = i.get('normalize_note') or i.get('notes') or ''
        notes_tip = f' title="{html.escape(notes)}"' if notes else ''

        rows.append(f"""
        <tr class="row-{verdict_class}" data-brand="{html.escape(i['brand'])}" data-verdict="{verdict}"{notes_tip}>
          <td class="brand">{html.escape(i['brand'])}</td>
          <td class="name">{html.escape(i['product_name'])}<span class="size"> · {size}</span>{iherb_link}{norm_badge}</td>
          <td class="num">${i['our_price']:.2f}</td>
          <td class="num">{iherb_price_str}</td>
          <td class="num diff">{diff_str}</td>
          <td class="verdict">{verdict_label}</td>
        </tr>""")

    options = ''.join(f'<option value="{html.escape(b)}">{html.escape(b)}</option>' for b in brands)

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
    --green-soft: #d1fae5;
    --red: #dc2626;
    --red-soft: #fee2e2;
    --orange: #ea580c;
    --orange-soft: #fed7aa;
    --accent: #2563eb;
    --accent-soft: #dbeafe;
    --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0; background: var(--bg); color: var(--text); line-height: 1.5;
  }}
  .container {{ max-width: 1320px; margin: 0 auto; padding: 32px 24px; }}
  h1 {{ margin: 0 0 8px; font-size: 28px; font-weight: 700; letter-spacing: -0.02em; }}
  .subtitle {{ color: var(--muted); font-size: 14px; margin-bottom: 24px; }}
  .stats {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px; margin-bottom: 24px;
  }}
  .stat {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px; box-shadow: var(--shadow);
  }}
  .stat-label {{
    font-size: 12px; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 6px;
  }}
  .stat-value {{ font-size: 24px; font-weight: 700; }}
  .stat-value.green {{ color: var(--green); }}
  .stat-value.red {{ color: var(--red); }}
  .stat-value.orange {{ color: var(--orange); }}
  .note {{
    background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 16px; font-size: 13px; color: #1e3a8a;
  }}
  .note strong {{ color: #1e40af; }}
  .note.warn {{
    background: #fffbeb; border-color: #fde68a; color: #78350f;
  }}
  .note.warn strong {{ color: #92400e; }}
  .controls {{
    display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
  }}
  .controls input, .controls select {{
    padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; background: var(--card); color: var(--text);
  }}
  .controls input:focus, .controls select:focus {{
    outline: none; border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }}
  .controls input {{ flex: 1; min-width: 200px; }}
  .table-wrap {{
    background: var(--card); border: 1px solid var(--border); border-radius: 12px;
    overflow: hidden; box-shadow: var(--shadow);
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{
    background: #fafbfc; text-align: left; padding: 12px 16px; font-weight: 600;
    color: var(--muted); font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.04em; border-bottom: 1px solid var(--border);
    cursor: pointer; user-select: none; position: sticky; top: 0; z-index: 1;
  }}
  th:hover {{ background: #f0f2f5; }}
  th.num {{ text-align: right; }}
  td {{
    padding: 12px 16px; border-bottom: 1px solid var(--border); vertical-align: top;
  }}
  td.brand {{ font-weight: 600; white-space: nowrap; }}
  td.name {{ max-width: 460px; }}
  td.name .size {{ color: var(--muted); font-size: 12px; }}
  td.num {{
    text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap;
  }}
  td.diff {{ font-weight: 600; }}
  td.verdict {{ white-space: nowrap; font-weight: 500; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.row-cheaper td.diff {{ color: var(--green); }}
  tr.row-expensive td.diff {{ color: var(--red); }}
  tr.row-notcomp td.diff {{ color: var(--orange); }}
  tr.row-notcomp td.verdict {{ color: var(--orange); }}
  tr:hover {{ background: #fafbfc; }}
  .ext {{
    color: var(--accent); text-decoration: none; margin-left: 4px;
    font-size: 12px;
  }}
  .ext:hover {{ text-decoration: underline; }}
  .per-unit {{
    margin-top: 4px; font-size: 11px;
  }}
  .badge {{
    display: inline-block; padding: 1px 6px; border-radius: 4px;
    background: var(--accent-soft); color: var(--accent); font-weight: 600;
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .badge-warn {{
    background: var(--orange-soft); color: var(--orange);
  }}
  .pu-num {{
    color: var(--muted); font-variant-numeric: tabular-nums;
  }}
  .footer {{
    margin-top: 24px; text-align: center; color: var(--muted); font-size: 12px;
  }}
  .hidden {{ display: none; }}
</style>
</head>
<body>
  <div class="container">
    <h1>Сравнение цен: KGSilkRoad vs iHerb</h1>
    <p class="subtitle">Топ-20 брендов × 10 позиций + Muscle Tech и Redcon1 × 10 — данные на {gen_date}</p>

    <div class="stats">
      <div class="stat"><div class="stat-label">Всего позиций</div><div class="stat-value">{stats['total']}</div></div>
      <div class="stat"><div class="stat-label">Найдено с ценой</div><div class="stat-value">{stats['matched']}</div></div>
      <div class="stat"><div class="stat-label">Мы дешевле</div><div class="stat-value green">{stats['we_cheaper']}</div></div>
      <div class="stat"><div class="stat-label">Мы дороже</div><div class="stat-value red">{stats['we_expensive']}</div></div>
      <div class="stat"><div class="stat-label">Сред. экономия (где дешевле)</div><div class="stat-value green">{stats.get('avg_cheaper_pct', 0):.1f}%</div></div>
      <div class="stat"><div class="stat-label">Не сравнимо</div><div class="stat-value orange">{stats.get('not_comparable', 0)}</div></div>
    </div>

    <div class="note">
      <strong>Честное сравнение (v2):</strong> 13 позиций с разницей более ±50% пересчитаны на цену за единицу
      (за 1 таблетку / 1 грамм). NOW Foods Whey Protein 10 lbs vs 1.8 lbs iHerb — теперь сравнивается за грамм,
      и оказывается мы дешевле на 30–53%. Thorne <em>тест-киты</em> ($200+) и Country Life <em>caddy</em>-наборы
      исключены из сравнения как не имеющие аналога. Раскройте tooltip строки для деталей нормализации.
    </div>

    <div class="note warn">
      <strong>Технические ограничения:</strong> у NOW Foods, Dr. Mercola, Garden of Life, Doctor's Best,
      Muscle Tech и других брендов цены на iHerb скрыты в выдаче поиска (политика MAP) — поэтому страница
      товара найдена, но цена не показана и сравнение невозможно ({stats.get('no_match', 0)} позиций). Из 5 запрошенных
      протеиновых брендов в каталоге есть только Muscle Tech и Redcon1; Optimum Nutrition, BSN, Rule1 отсутствуют.
    </div>

    <div class="controls">
      <input type="text" id="search" placeholder="Поиск по названию…" />
      <select id="brand-filter"><option value="">Все бренды</option>{options}</select>
      <select id="verdict-filter">
        <option value="">Все результаты</option>
        <option value="cheaper">🟢 Только дешевле</option>
        <option value="more_expensive">🔴 Только дороже</option>
        <option value="same">⚪ Одинаково</option>
        <option value="not_comparable">◐ Не сравнимо</option>
        <option value="no_data">⚫ Нет данных iHerb</option>
      </select>
    </div>

    <div class="table-wrap">
      <table id="comparison-table">
        <thead>
          <tr>
            <th data-sort="brand">Бренд</th>
            <th data-sort="name">Название · Размер</th>
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

    <div class="footer">
      Сгенерировано на основе dsn_products.json и поиска по iHerb.com.
      Источник нормализации: <code>normalize_outliers.py</code>. Данные:
      <a href="comparison_fixed.json">comparison_fixed.json</a>.
    </div>
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
    data, fixed = load_data()
    print(f"Loaded {'comparison_fixed.json' if fixed else 'comparison.json'}")
    print(f"Items: {len(data['items'])}, stats: {data['stats']}")

    # Sort: by brand, then verdict, then name
    verdict_order = {'cheaper': 0, 'more_expensive': 1, 'same': 2, 'not_comparable': 3, 'no_data': 4}
    data['items'].sort(key=lambda x: (x['brand'], verdict_order.get(x['verdict'], 9), x['product_name']))

    html_doc = build_html(data, fixed)
    with open(os.path.join(ROOT, 'comparison.html'), 'w', encoding='utf-8') as f:
        f.write(html_doc)
    print("Wrote comparison.html")

if __name__ == '__main__':
    main()
