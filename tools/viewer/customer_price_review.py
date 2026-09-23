"""Keep an explicit customer charge separate from unknown internal cost."""
import copy
import hashlib
import json
import math
from pathlib import Path


def apply_customer_prices(draft, folder):
    root=Path(folder).resolve();path=root/'customer_price_review.json'
    if not path.exists():return draft
    raw=path.read_bytes();config=json.loads(raw)
    if config['plan_sha256']!=draft['plan_sha256']:raise ValueError('Customer price belongs to another plan')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']};seen=set()
    for item in config['items']:
        identity=item['row_id'];source=item['source'];amount=item['customer_price']
        evidence=(root/source['file']).resolve()
        if (identity in seen or not evidence.is_relative_to(root)
                or hashlib.sha256(evidence.read_bytes()).hexdigest()!=source['sha256']):
            raise ValueError('Customer price evidence is duplicate or changed')
        seen.add(identity)
        record=json.loads(evidence.read_bytes())
        if (record.get('source_kind')!='owner_confirmation' or record.get('plan_sha256')!=draft['plan_sha256']
                or record.get('customer_price')!=amount or not record.get('scope')
                or type(amount) not in (int,float) or not math.isfinite(amount) or amount<0):
            raise ValueError('Customer charge needs a matching owner confirmation')
        row=rows[identity]
        if (row['cost_type'] not in ('LABOR','FEE','ALLOWANCE') or row.get('covered_by_package')
                or row.get('cost_owner_row_id') or row.get('completion_status','').startswith('not_applicable')
                or any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
            raise ValueError('Customer charge conflicts with another price or cost owner')
        row.update(line_price=amount,pricing_basis='owner_customer_charge',
            customer_price_source=copy.deepcopy(source),customer_price_scope=record['scope'],
            price_status='Customer charge confirmed; direct cost unknown; no additional markup',
            current_price_certified=False)
    if path.read_bytes()!=raw:raise ValueError('Customer price changed during calculation')
    return result
