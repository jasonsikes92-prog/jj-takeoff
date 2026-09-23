"""Select dated, pretax material rates by exact supplier SKU and sales unit."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal


def build_catalog(lines, *, as_of):
    cutoff = date.fromisoformat(as_of)
    eligible, excluded = defaultdict(list), []
    for number, line in enumerate(lines, 1):
        if any(not isinstance(line.get(k), str) or not line[k].strip()
               for k in ('sku', 'unit', 'description', 'invoice', 'source_file')):
            raise ValueError('Material rate needs product, unit and invoice evidence')
        when = datetime.strptime(line['invoice_date'], '%m-%d-%y').date()
        quantity = line['shipped_quantity']
        price, extension = (Decimal(str(line[k])) for k in
                            ('historical_unit_price', 'historical_extension'))
        if (type(quantity) is not int or quantity < 0
                or not price.is_finite() or not extension.is_finite()
                or price < 0 or extension < 0
                or abs(quantity*price-extension) > Decimal('.01')):
            raise ValueError('Invalid shipped quantity or invoice extension')
        reason = None
        if when > cutoff:
            reason = 'Invoice is later than pricing date'
        elif line['unit'] == 'PKG':
            reason = 'Package total is not an individual material unit rate'
        elif line.get('package_component_no_separate_charge'):
            reason = 'Package component has no separate unit price'
        elif not quantity:
            reason = 'No shipped quantity; quoted unshipped stock is not a purchase rate'
        elif not price:
            reason = 'Zero charge does not establish a reusable free material rate'
        if reason:
            excluded.append({'ledger_line': number, 'sku': line['sku'], 'reason': reason})
            continue
        eligible[(line['sku'], line['unit'])].append({
            'ledger_line': number, 'date': when.isoformat(), 'unit_price': str(price),
            'description': line['description'], 'invoice': line['invoice'],
            'source_file': line['source_file'], 'pdf_page': line['pdf_page']})
    rates = []
    for (sku, unit), history in sorted(eligible.items()):
        newest = max(r['date'] for r in history)
        candidates = [r for r in history if r['date'] == newest]
        prices = {Decimal(r['unit_price']) for r in candidates}
        descriptions = {' '.join(r['description'].split()) for r in candidates}
        conflict = len(prices) != 1 or len(descriptions) != 1
        rates.append({'sku': sku, 'unit': unit, 'date': newest,
                      'unit_price': None if conflict else str(next(iter(prices))),
                      'status': 'conflicting_latest_sources' if conflict else 'dated_allowance_candidate',
                      'selected_sources': candidates, 'history': history,
                      'currency': 'USD', 'tax_included': False, 'delivery_included': False,
                      'current_price_certified': False, 'job_scope_match_required': True})
    return {'as_of': as_of, 'rates': rates, 'excluded_lines': excluded,
            'basis': 'Historical purchases only. Match exact SKU and sales unit; apply project tax, delivery and markup separately after scope review.'}


def checked_catalog(ledger_path, pdf_dir, *, as_of):
    import hashlib
    import json
    from pathlib import Path
    path, root = Path(ledger_path), Path(pdf_dir).resolve()
    raw = path.read_bytes()
    ledger = json.loads(raw)
    for name, digest in ledger['source_pdf_hashes'].items():
        pdf = (root/name).resolve()
        if (not pdf.is_relative_to(root) or not pdf.is_file()
                or hashlib.sha256(pdf.read_bytes()).hexdigest() != digest):
            raise ValueError('Original invoice source changed or missing')
    if any(r['source_file'] not in ledger['source_pdf_hashes'] for r in ledger['lines']):
        raise ValueError('Invoice line has no original source hash')
    result = build_catalog(ledger['lines'], as_of=as_of)
    result.update(ledger_sha256=hashlib.sha256(raw).hexdigest(),
                  source_pdf_hashes=ledger['source_pdf_hashes'])
    return result


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--pdf-dir', required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = checked_catalog(args.ledger, args.pdf_dir, as_of=args.as_of)
    with Path(args.output).open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'products': len(result['rates']), 'excluded_lines': len(result['excluded_lines'])}))


if __name__ == '__main__':
    main()
