"""Apply reviewed historical unit rates as explicitly dated estimating allowances."""
import copy
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from estimating_price_review import accept_estimating_price


def checked_file(root, reference):
    path=(root/reference['source_file']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Allowance evidence must be inside the price evidence folder')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=reference['source_sha256']:
        raise ValueError('Allowance evidence hash does not match saved source')
    return path


def allowance_purchase_tax(row, rate, cost, as_of, root, plan_sha256):
    """Apply the same sourced purchase-tax treatment to unit and component allowances."""
    for key in ('supplier_cost','purchase_tax','purchase_tax_percent'):
        row.pop(key,None)
    tax=rate.get('purchase_tax')
    if tax is None:
        if rate.get('tax_included') is False or (row.get('cost_type')=='MATERIAL' and rate.get('tax_included') is not True):
            raise ValueError('Material allowance requires explicit purchase tax treatment')
        return cost,True,''
    tax_record=json.loads(checked_file(root,tax).read_text(encoding='utf-8'))
    if (tax_record.get('plan_sha256')!=plan_sha256
            or any(tax_record.get(k)!=tax.get(k) for k in ('percent','effective_from','effective_through'))
            or not tax_record.get('jurisdiction') or not tax_record.get('source')):
        raise ValueError('Purchase tax must match the project and source record')
    if isinstance(tax['percent'],bool):raise ValueError('Invalid purchase tax percent')
    percent=Decimal(str(tax['percent']))
    if not percent.is_finite() or not 0<=percent<=100 or rate.get('tax_included') is not False:
        raise ValueError('Purchase tax needs a valid rate and an explicitly pretax allowance')
    start=date.fromisoformat(tax['effective_from']);end=date.fromisoformat(tax['effective_through'])
    if end<start:raise ValueError('Purchase tax effective dates are reversed')
    current=start<=date.fromisoformat(as_of)<=end
    row.update(supplier_cost=cost if current else None,purchase_tax=None,purchase_tax_percent=tax['percent'])
    if not current:return None,False,'; withheld: purchase tax evidence is not effective for the pricing date'
    if cost is not None:
        money=lambda n:float(n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
        row['purchase_tax']=money(Decimal(str(cost))*percent/100)
        cost=money(Decimal(str(cost))+Decimal(str(row['purchase_tax'])))
    return cost,True,f'; estimated {percent}% purchase tax included once'


def apply_dated_allowances(draft, pricing, as_of, evidence_root):
    candidates=pricing.get('dated_allowances',[])
    if not candidates:return draft
    root=Path(evidence_root).resolve()
    authority=json.loads(checked_file(root,pricing['allowance_authorization']).read_text(encoding='utf-8'))
    if authority.get('answer')!='Use saved rates as dated allowances':
        raise ValueError('Dated allowance owner authorization is missing')
    rows={r['row_id']:r for r in draft['rows']+draft.get('additional_cost_rows',[])}
    latest={}
    for candidate in candidates:
        record=json.loads(checked_file(root,candidate).read_text(encoding='utf-8'))
        checked_file(root,record['original_document'])
        rate=record['rate']
        identity=rate['row_id']
        if identity not in rows and draft.get('saved_trade_review_required') and identity in draft.get('withheld_supplemental_cost_ids',[]):
            draft.setdefault('unapplied_prices',[]).append({'row_id':identity,
                'reason':'Saved trade quantities withheld after geometry change; dated allowance not applied'})
            continue
        if identity not in rows:raise ValueError('Unknown dated allowance cost row: '+identity)
        row=rows[identity]
        kits=[q for q in row.get('quantity_sources',[]) if q.get('kind') in ('reviewed_kit_purchase','reviewed_item_purchase')]
        if any(q['product_id']!=rate.get('product_id') or q['model']!=rate.get('model') for q in kits):
            raise ValueError('Purchase allowance must match the identified product and model')
        if (row.get('cost_type') not in ('MATERIAL','LABOR','SUBCONTRACTOR','ALLOWANCE','EQUIPMENT','FEE')
                or row.get('completion_status','').startswith('not_applicable')
                or row.get('covered_by_package') or row.get('cost_owner_row_id')
                or row.get('pricing_role')=='input_only' or row.get('parent','').strip().upper()=='INPUTS'):
            raise ValueError('Dated allowance needs a separate eligible cost owner')
        if (record.get('plan_sha256')!=draft['plan_sha256'] or rate.get('scope_reviewed') is not True
                or rate.get('pricing_basis')!='unit_rate' or rate.get('unit')!=row['unit']
                or rate.get('currency')!='USD' or not rate.get('source')
                or not rate.get('scope_match') or not rate.get('tax_delivery_basis')
                or rate.get('evidence_kind') not in ('dated_supplier_allowance','dated_company_template_allowance')):
            raise ValueError('Dated allowance needs reviewed matching scope, unit and project')
        values=[rate[k] for k in ('unit_price','source_unit_price','units_per_source_unit')]
        if any(isinstance(v,bool) for v in values):raise ValueError('Invalid allowance rate')
        amount,source_amount,divisor=map(lambda v:Decimal(str(v)),values)
        if (any(not v.is_finite() for v in (amount,source_amount,divisor))
                or amount<0 or source_amount<0 or divisor<=0 or amount!=source_amount/divisor):
            raise ValueError('Allowance rate conversion does not match the saved source')
        source_date=date.fromisoformat(rate['date'])
        if source_date>date.fromisoformat(as_of):raise ValueError('Allowance source is future dated')
        if identity in latest and latest[identity][0]['date']==rate['date']:
            raise ValueError('Same-date allowance sources need an explicit selection')
        if identity not in latest or source_date>date.fromisoformat(latest[identity][0]['date']):
            latest[identity]=(rate,candidate)
    money=lambda v:float(v.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    for identity,(rate,reference) in latest.items():
        row=rows[identity]
        if row.get('unit_cost') is not None and row.get('pricing_basis')!='dated_allowance':
            continue
        cost=None if row['draft_quantity'] is None else money(Decimal(str(row['draft_quantity']))*Decimal(str(rate['unit_price'])))
        cost,tax_current,tax_status=allowance_purchase_tax(row,rate,cost,as_of,root,draft['plan_sha256'])
        sell=None if cost is None else money(Decimal(str(cost))*(1+Decimal(str(row['markup_pct']))/100))
        label='Company-template estimating allowance' if rate['evidence_kind']=='dated_company_template_allowance' else 'Dated estimating allowance'
        status=f"{label}: {rate['source']}, {rate['date']}; current supplier price unverified. {rate['tax_delivery_basis']}"
        status+=tax_status
        row.update(unit_cost=float(rate['unit_price']) if tax_current else None,line_cost=cost,line_price=sell,
            pricing_basis='dated_allowance',current_price_certified=False,
            price_status=status,
            price_evidence={**copy.deepcopy(rate),**reference,
                'authorization':copy.deepcopy(pricing['allowance_authorization'])})
        accept_estimating_price(row, as_of, 'authorized_dated_allowance')
    return draft
