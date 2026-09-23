"""Register unchanged, reviewed retail observations as authorized dated fallbacks."""
import copy
import hashlib
import json
from pathlib import Path
from dated_price_allowances import checked_file


def register_retail_fallbacks(pricing, evidence_root):
    root=Path(evidence_root).resolve()
    authority=json.loads(checked_file(root,pricing['allowance_authorization']).read_text(encoding='utf-8'))
    if authority.get('answer')!='Use saved rates as dated allowances':
        raise ValueError('Retail fallback requires owner authorization')
    result=copy.deepcopy(pricing);existing={}
    for ref in result.get('dated_allowances',[]):
        record=json.loads(checked_file(root,ref).read_text(encoding='utf-8'))
        key=(record['rate']['row_id'],record['rate']['date'])
        if key in existing:raise ValueError('Duplicate dated allowance selection')
        existing[key]=record
    prepared=[]
    for price in pricing['rates']:
        if price.get('evidence_kind')!='retail_listing':continue
        original=json.loads(checked_file(root,price).read_text(encoding='utf-8'))
        if (price.get('scope_reviewed') is not True or price.get('validity_policy')!='observation_date_only'
                or price.get('valid_through')!=price.get('date') or price.get('pricing_basis')!='unit_rate'
                or not original.get('unit_basis') or not original.get('product_id')
                or any(original.get(k)!=price.get(k) for k in ('date','unit_price','unit','source','product_id','currency','tax_included','unit_basis'))
                or (original.get('model') is not None and original['model']!=price.get('model'))):
            raise ValueError('Retail fallback must match the reviewed original observation')
        rate={k:copy.deepcopy(price[k]) for k in ['row_id','unit','unit_price','date','source','currency','product_id']}
        for key in ['model','purchase_tax','tax_included']:
            if key in price:rate[key]=copy.deepcopy(price[key])
        rate.update(source_unit_price=price['unit_price'],source_unit=price['unit'],units_per_source_unit=1,
            pricing_basis='unit_rate',evidence_kind='dated_supplier_allowance',scope_reviewed=True,
            source_observation_kind='retail_listing',scope_match=price.get('basis') or original['unit_basis'],
            basis=price.get('basis') or original['unit_basis'],
            tax_delivery_basis='Saved retail observation, not a current quote. Preserve separately sourced purchase-tax treatment; job delivery/checkout and current stock are unverified.',
            limitation=price.get('limitation','')+' Current price and availability have not been reverified; original observation date is unchanged.')
        record={'plan_sha256':pricing['plan_sha256'],
                'original_document':{k:price[k] for k in ['source_file','source_sha256']},'rate':rate}
        key=(rate['row_id'],rate['date'])
        if key in existing:
            if existing[key]!=record:raise ValueError('Same-date allowance needs explicit source selection')
            continue
        raw=(json.dumps(record,sort_keys=True,indent=2)+'\n').encode('utf-8')
        digest=hashlib.sha256(raw).hexdigest();name=f'retail_allowance_{digest}.json'
        prepared.append((name,digest,raw));existing[key]=record
    for name,digest,raw in prepared:
        target=root/name
        if target.exists():
            if target.read_bytes()!=raw:raise ValueError('Existing fallback evidence changed')
        else:
            with target.open('xb') as f:f.write(raw)
        result.setdefault('dated_allowances',[]).append({'source_file':name,'source_sha256':digest})
    return result
