#!/usr/bin/env python3
"""Normalize per-unit prices for items where |diff_pct|>50 so the comparison is honest.

For each outlier:
- Parse our pack size (count, grams, ml) from `size` field + product_name hints
- Parse iHerb pack size from iherb_name
- Convert both to canonical unit (count / gram / ml)
- Recompute diff% on per-unit basis
- Update verdict
"""

import json
import re
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_THRESHOLD = 50.0  # |diff_pct| above which we re-normalize

# unit conversions
LB_TO_G = 453.592
OZ_MASS_TO_G = 28.3495
KG_TO_G = 1000.0
FL_OZ_TO_ML = 29.5735

COUNT_CORE = r'(?:tablets?|tabs?|capsules?|caps?|softgels?|soft\s*gels?|vcaps?|vegcaps?|vegtabs?|gummies|caplets?|licaps?|liqcaps?|packets?|servings)'
# Allow 0-3 descriptor words like "Vegetarian", "Liquid", "Mini" between number and core
COUNT_PATTERN = re.compile(
    rf'(\d[\d,]*)\s+(?:[A-Za-z-]+\s+){{0,3}}{COUNT_CORE}',
    re.IGNORECASE,
)

def parse_iherb_size(name):
    """Return dict with 'count', 'mass_g', 'volume_ml' if found."""
    if not name:
        return {}
    out = {}
    # mass (prefer parenthesized g if present)
    m = re.search(r'\(\s*([\d.,]+)\s*g\s*\)', name)
    if m:
        out['mass_g'] = float(m.group(1).replace(',', ''))
    else:
        m = re.search(r'([\d.,]+)\s*kg', name, re.I)
        if m:
            out['mass_g'] = float(m.group(1).replace(',', '')) * KG_TO_G
        else:
            m = re.search(r'([\d.,]+)\s*lbs?\b', name, re.I)
            if m:
                out['mass_g'] = float(m.group(1).replace(',', '')) * LB_TO_G
            else:
                # "10 oz" mass (only if NOT fl oz)
                m = re.search(r'([\d.,]+)\s*oz(?!\s*\(\s*\d*\s*ml)', name)
                if m and 'fl oz' not in name.lower()[max(0, m.start()-5):m.end()+5]:
                    # heuristic: if "fl oz" appears nearby don't take
                    out['mass_g'] = float(m.group(1).replace(',', '')) * OZ_MASS_TO_G

    # volume (prefer parenthesized ml)
    m = re.search(r'\(\s*([\d.,]+)\s*ml\s*\)', name)
    if m:
        out['volume_ml'] = float(m.group(1).replace(',', ''))
    else:
        m = re.search(r'([\d.,]+)\s*fl\s*oz', name, re.I)
        if m:
            out['volume_ml'] = float(m.group(1).replace(',', '')) * FL_OZ_TO_ML

    # count (allow descriptors between number and core word)
    m = COUNT_PATTERN.search(name)
    if m:
        out['count'] = int(m.group(1).replace(',', ''))

    return out


def parse_our_size(size_str, product_name):
    """Heuristically map our size string to a normalized dict."""
    if not size_str:
        size_str = ''
    s = str(size_str).strip()
    name = product_name or ''
    out = {}

    # Pure number?
    m = re.fullmatch(r'(\d+(?:\.\d+)?)', s)
    if m:
        num = float(m.group(1))
        powder_liquid = re.search(r'\b(protein|powder|whey|oil|liquid|drops|tincture|extract|syrup|gainer|isolate|mre|mass\s*tech|nitro\s*tech)\b', name, re.I)
        # If product name contains weight/volume hint, treat number accordingly
        if re.search(r'\b(oz|fl\s*oz|lb|lbs|gram|ml)\b', name, re.I):
            if re.search(r'fl\s*oz', name, re.I):
                out['volume_ml'] = num * FL_OZ_TO_ML
            elif re.search(r'\boz\b', name, re.I):
                out['mass_g'] = num * OZ_MASS_TO_G
            elif re.search(r'\blbs?\b', name, re.I):
                out['mass_g'] = num * LB_TO_G
            elif re.search(r'\bml\b', name, re.I):
                out['volume_ml'] = num
            else:
                out['count'] = int(num) if num.is_integer() else num
        elif powder_liquid and not num.is_integer():
            # decimal number on a powder/liquid product → assume oz weight
            out['mass_g'] = num * OZ_MASS_TO_G
        else:
            out['count'] = int(num) if num.is_integer() else num
        return out

    # Patterns like "10 LB", "5lb", "10LB", "1000g", "16 oz", "5 oz", "16 fl oz", "30 ml"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(lbs?|LB)', s, re.I)
    if m:
        out['mass_g'] = float(m.group(1)) * LB_TO_G
        return out
    m = re.search(r'(\d+(?:\.\d+)?)\s*kg', s, re.I)
    if m:
        out['mass_g'] = float(m.group(1)) * KG_TO_G
        return out
    m = re.search(r'(\d+(?:\.\d+)?)\s*g(?:rams?)?\b', s, re.I)
    if m:
        out['mass_g'] = float(m.group(1))
        return out
    m = re.search(r'(\d+(?:\.\d+)?)\s*fl\s*oz', s, re.I)
    if m:
        out['volume_ml'] = float(m.group(1)) * FL_OZ_TO_ML
        return out
    m = re.search(r'(\d+(?:\.\d+)?)\s*ml\b', s, re.I)
    if m:
        out['volume_ml'] = float(m.group(1))
        return out
    m = re.search(r'(\d+(?:\.\d+)?)\s*oz\b', s, re.I)
    if m:
        # oz: liquid or mass? check product_name
        if re.search(r'\b(liquid|liposomal|drops|oil|tincture|extract|syrup|fl\s*oz)\b', name, re.I):
            out['volume_ml'] = float(m.group(1)) * FL_OZ_TO_ML
        else:
            out['mass_g'] = float(m.group(1)) * OZ_MASS_TO_G
        return out

    # Patterns like "60ct", "180 CT", "60ct 400mg", "120 ct 5 mg"
    m = re.search(r'(\d+)\s*ct\b', s, re.I)
    if m:
        out['count'] = int(m.group(1))
        return out
    # Patterns like "120 Tablets", "5 oz Pwd"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:tablets?|caps?|capsules?|softgels?)', s, re.I)
    if m:
        out['count'] = int(float(m.group(1)))
        return out

    # Just "LB" with no number → assume product_name has size
    if re.search(r'\b(LB|lb|lbs)\b', s) and not re.search(r'\d', s):
        # extract count from product_name
        m = re.search(r'(\d+(?:\.\d+)?)\s*LB', name, re.I)
        if m:
            out['mass_g'] = float(m.group(1)) * LB_TO_G
            return out
        m = re.search(r'(\d+(?:\.\d+)?)\s*lbs?', name, re.I)
        if m:
            out['mass_g'] = float(m.group(1)) * LB_TO_G
            return out

    return out


def common_unit(ours, theirs):
    """Pick a unit both share. Priority: count > mass > volume."""
    if 'count' in ours and 'count' in theirs:
        return 'count', ours['count'], theirs['count']
    if 'mass_g' in ours and 'mass_g' in theirs:
        return 'mass_g', ours['mass_g'], theirs['mass_g']
    if 'volume_ml' in ours and 'volume_ml' in theirs:
        return 'volume_ml', ours['volume_ml'], theirs['volume_ml']
    return None, None, None


THORNE_KIT_NAMES = {
    'fertility', 'menopause', 'weight management', 'gut health test',
    'sleep', 'stress', 'thyroid', 'vitamin d',
    'biological age', 'heavy metals',
}

def is_different_product_class(brand, our_pn, iherb_pn, size_str):
    """Detect things like Thorne test kit vs supplement, CADDY vs single stick, etc."""
    if not our_pn or not iherb_pn:
        return False
    ours = our_pn.lower().strip()
    theirs = iherb_pn.lower()
    # Thorne test kits: brand=Thorne, size="1", name is a generic body-system word
    if brand == 'Thorne' and str(size_str).strip() == '1' and ours in THORNE_KIT_NAMES:
        return True
    # CADDY hints (multi-pack vs single stick)
    if 'caddy' in ours:
        return True
    # Multi-supplement "Essential Packets" / "Detox Program" vs single supplement
    if ('essential packets' in ours or 'detox program' in ours or 'support packets' in ours) and \
       'packets' not in theirs:
        return True
    return False


def main():
    with open(os.path.join(ROOT, 'comparison.json')) as f:
        data = json.load(f)

    items = data['items']
    fix_count = 0
    detail = []

    for it in items:
        if it.get('iherb_price') is None or it.get('diff_pct') is None:
            continue
        if abs(it['diff_pct']) <= OUT_THRESHOLD:
            continue
        # outlier — try normalize
        ours = parse_our_size(it.get('size', ''), it.get('product_name', ''))
        theirs = parse_iherb_size(it.get('iherb_name', ''))

        # Different product class detection (e.g., Thorne test kit vs supplement)
        if is_different_product_class(it.get('brand'), it.get('product_name'), it.get('iherb_name'), it.get('size', '')):
            it['original_diff_pct'] = it['diff_pct']
            it['original_verdict'] = it['verdict']
            it['diff_pct'] = None
            it['diff_abs'] = None
            it['verdict'] = 'not_comparable'
            it['normalize_note'] = 'Different product class — our SKU is a test kit / multi-pack; iHerb match is a single supplement / single stick. Per-unit comparison not meaningful.'
            it['per_unit'] = None
            fix_count += 1
            detail.append((it['brand'], it['product_name'], 'NOT_COMPARABLE'))
            continue

        unit, ours_q, theirs_q = common_unit(ours, theirs)
        if not unit:
            it['original_diff_pct'] = it['diff_pct']
            it['original_verdict'] = it['verdict']
            it['normalize_note'] = (
                f"Could not determine common unit (ours={ours}, theirs={theirs}). "
                "Pack sizes differ but cannot be normalized — keeping original pack-vs-pack diff."
            )
            it['per_unit'] = None
            detail.append((it['brand'], it['product_name'], f'NO_UNIT ours={ours} theirs={theirs}'))
            continue

        # compute per-unit prices
        ours_per = it['our_price'] / ours_q
        theirs_per = it['iherb_price'] / theirs_q
        new_diff_abs = ours_per - theirs_per
        new_diff_pct = (new_diff_abs / theirs_per) * 100

        it['original_diff_pct'] = it['diff_pct']
        it['original_verdict'] = it['verdict']

        unit_label = {'count': 'unit', 'mass_g': 'g', 'volume_ml': 'ml'}[unit]
        it['per_unit'] = {
            'unit': unit_label,
            'our_size': round(ours_q, 2),
            'iherb_size': round(theirs_q, 2),
            'our_per_unit': round(ours_per, 4),
            'iherb_per_unit': round(theirs_per, 4),
        }
        it['diff_pct'] = round(new_diff_pct, 1)
        it['diff_abs'] = round(new_diff_abs, 4)
        if new_diff_pct < -1:
            it['verdict'] = 'cheaper'
        elif new_diff_pct > 1:
            it['verdict'] = 'more_expensive'
        else:
            it['verdict'] = 'same'
        it['normalize_note'] = (
            f"Normalized to price per {unit_label}: ours ${ours_per:.4f}/{unit_label} "
            f"(pack: {ours_q} {unit_label}, ${it['our_price']:.2f}) vs iHerb ${theirs_per:.4f}/{unit_label} "
            f"(pack: {theirs_q} {unit_label}, ${it['iherb_price']:.2f})."
        )
        fix_count += 1
        detail.append((it['brand'], it['product_name'][:60],
                       f"{it['original_verdict']}({it['original_diff_pct']:+.0f}%) → {it['verdict']}({new_diff_pct:+.1f}%)  per-{unit_label}"))

    print(f"\nNormalized {fix_count} of {len(items)} outliers (threshold ±{OUT_THRESHOLD}%)")
    for b, n, d in detail:
        print(f"  {b:<22} | {n:<60} | {d}")

    # Recompute summary stats
    matched = [i for i in items if i['iherb_price'] is not None and i['verdict'] != 'not_comparable']
    cheaper = [i for i in matched if i['verdict'] == 'cheaper']
    expensive = [i for i in matched if i['verdict'] == 'more_expensive']
    same = [i for i in matched if i['verdict'] == 'same']
    not_comp = [i for i in items if i['verdict'] == 'not_comparable']
    no_data = [i for i in items if i['verdict'] == 'no_data']

    stats = {
        'total': len(items),
        'matched': len(matched),
        'not_comparable': len(not_comp),
        'no_match': len(no_data),
        'we_cheaper': len(cheaper),
        'we_expensive': len(expensive),
        'we_same': len(same),
        'avg_diff_pct': round(sum(i['diff_pct'] for i in matched)/len(matched), 1) if matched else 0,
        'avg_cheaper_pct': round(sum(i['diff_pct'] for i in cheaper)/len(cheaper), 1) if cheaper else 0,
        'avg_expensive_pct': round(sum(i['diff_pct'] for i in expensive)/len(expensive), 1) if expensive else 0,
    }
    data['stats'] = stats
    data['fixed'] = True
    data['outliers_normalized'] = fix_count

    with open(os.path.join(ROOT, 'comparison_fixed.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nWrote comparison_fixed.json. Stats: {stats}")


if __name__ == '__main__':
    main()
