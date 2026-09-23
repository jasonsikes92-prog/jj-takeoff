"""Read quantity columns from the supported BFS invoice form, never SKU tokens."""
from decimal import Decimal
import re


# PDF points on the verified 612-point-wide form. Other layouts require review.
EDGES = (31, 69, 106, 142, 240, 411, 439, 496, 576)
HEADERS = {'ORDERED': 36.59, 'SHIPPED': 72.86, 'B/O': 118.30,
           'ITEM': 174.59, 'DESCRIPTION': 309.78, 'U/M': 419.17}


def parse_page(words, page_width):
    if abs(page_width - 612) > .1:
        raise ValueError('Unsupported BFS page width')
    anchors = {}
    for name, x in HEADERS.items():
        matches = [w for w in words if w[4] == name and abs(w[0] - x) < 1
                   and 190 < w[1] < 205]
        if len(matches) != 1:
            raise ValueError('Unsupported BFS column header: ' + name)
        anchors[name] = matches[0][1]
    if max(anchors.values()) - min(anchors.values()) > .5:
        raise ValueError('BFS column headers are not aligned')
    rows = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        if not 210 < word[1] < 620:
            continue
        if not rows or abs(rows[-1][0][1] - word[1]) > .5:
            rows.append([])
        rows[-1].append(word)
    result = []
    for row in rows:
        cells = [' '.join(w[4] for w in sorted(row, key=lambda w: w[0])
                          if left <= w[0] < right)
                 for left, right in zip(EDGES, EDGES[1:])]
        ordered, shipped, backorder, sku, description, unit, price, extension = cells
        if not any(re.fullmatch(r'\d+', q) for q in cells[:3]) and not (price or extension):
            continue  # Section titles and continuation descriptions.
        if (not sku or not description or unit not in {'EA', 'BOX', 'BOM', 'PKG'}
                or not shipped or any(q and not q.isdigit() for q in cells[:3])):
            raise ValueError('Incomplete or unsupported BFS item row: ' + repr(cells))
        if not re.fullmatch(r'[\d,]*\.\d{2}', price) or not re.fullmatch(r'[\d,]*\.\d{2} T', extension):
            raise ValueError('Invalid BFS price/extension: ' + repr(cells))
        price_value = Decimal(price.replace(',', ''))
        extension_value = Decimal(extension[:-2].replace(',', ''))
        if abs(int(shipped) * price_value - extension_value) > Decimal('.01'):
            raise ValueError('BFS shipped quantity does not match extension: ' + sku)
        result.append({'sku': sku, 'description': description.replace('\ufffd', "'"),
                       'ordered_quantity': int(ordered) if ordered else None,
                       'shipped_quantity': int(shipped),
                       'backorder_quantity': int(backorder) if backorder else None,
                       'unit': unit, 'historical_unit_price': str(price_value),
                       'historical_extension': str(extension_value),
                       'source_row_y': round(row[0][1], 3)})
    if not result:
        raise ValueError('No BFS item rows found; source review required')
    return result
