"""Join live draft measurements to preserved template rows without inventing prices."""
import copy
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from slab_outputs import apply_price

from measurement_quantities import rollup
from dated_price_allowances import apply_dated_allowances
from component_allowances import apply_component_allowances
from estimating_price_review import accept_estimating_price
from estimate_summary import summary_layout


def template_draft(state, rules, template):
    quantities = rollup(state, rules)
    rows = copy.deepcopy(template['rows'])
    by_row = {str(r['excel_row']): r for r in rows}
    if len(by_row) != len(rows) or len({r['row_id'] for r in rows}) != len(rows):
        raise ValueError('Template row identities must be unique')
    units = {'ft2': 'SF', 'sq ft': 'SF', 'SF': 'SF', 'LF': 'LF', 'lf': 'LF', 'feet': 'LF', 'each': 'EA', 'EA': 'EA'}
    assigned = set()
    summary=summary_layout(template)
    for pending in quantities.get('pending_quantities',[]):
        targets=list(map(str,pending['template_rows']))
        if not targets or len(targets)!=len(set(targets)):
            raise ValueError('Pending quantity needs unique template targets')
        for target in targets:
            if target not in by_row or by_row[target]['cost_type']=='GROUP' or by_row[target]['row_id'] in summary or by_row[target]['completion_status'].startswith('not_applicable'):
                raise ValueError('Pending quantity has an invalid template target: '+target)
    for row in rows:
        row.update(draft_quantity=None, quantity_sources=[], assembly_inputs=[],
                   unit_cost=None, line_cost=None, line_price=None, certified=False)
        row['pricing_role']='input_only' if row.get('parent','').strip().upper()=='INPUTS' else 'cost_line'
    for quantity in quantities['quantities']:
        targets = quantity['template_rows']
        if not targets or len(set(map(str, targets))) != len(targets):
            raise ValueError('Quantity needs unique template targets')
        for target in targets:
            target = str(target)
            if target not in by_row:
                raise ValueError('Unknown template row: '+target)
            row = by_row[target]
            if row['row_id'] in summary:raise ValueError('Cannot assign construction quantities to a summary row')
            if row['cost_type'] == 'GROUP' or row['completion_status'].startswith('not_applicable'):
                raise ValueError('Cannot assign quantity to a group or excluded row')
            if quantity['use'] == 'assembly_input':
                row['assembly_inputs'].append(copy.deepcopy(quantity))
                continue
            if target in assigned:
                raise ValueError('Multiple quantities claim template row: '+target)
            if units.get(row['unit']) != quantity['unit']:
                raise ValueError('Quantity unit does not match template row: '+target)
            assigned.add(target)
            row['draft_quantity'] = quantity['quantity']
            row['quantity_sources'].append(copy.deepcopy(quantity))
    return {'measurement_version': state['version'], 'plan_sha256': state['plan_sha256'],
            'rows': rows, 'mapped_quantity_rows': len(assigned),
            'pending_quantities':quantities.get('pending_quantities',[]),
            'unmapped_measurements':[{'id':identity,'label':m.get('label',identity),'page':m.get('page'),
                'reason':m.get('scope_mapping_reason','Measurement has no template scope mapping')} for identity,m in state['measurements'].items()
                if not any(identity in rule['measurement_ids'] for rule in rules['rules'])],
            'whole_house_total': None, 'estimate_released': False,
            'status': 'Draft measured quantities only; assembly checks and current pricing remain required'}


def price_draft(draft, pricing, as_of, evidence_root):
    """Apply reviewed rates with source, drawing and applicable revision checks.

    Historical allowances require separately reviewed, owner-authorized evidence;
    package quotes cannot enter this unit-rate path. Standing owner and dated retail rates
    recalculate changed quantities; quotes retain their revision checks.
    Priced draft lines are not certification.
    """
    reusable_rates=all(p.get('validity_policy') in ('owner_rate_until_changed','observation_date_only') for p in pricing['rates'])
    if (pricing['plan_sha256'] != draft['plan_sha256'] or
            (pricing['measurement_version'] != draft['measurement_version'] and not reusable_rates)):
        raise ValueError('Pricing belongs to a different drawing or measurement version')
    result = copy.deepcopy(draft)
    result.pop('unapplied_prices',None)
    root = Path(evidence_root).resolve()
    cost_rows=result['rows']+result.get('additional_cost_rows',[])
    rows = {r['row_id']: r for r in cost_rows}
    if len(rows)!=len(cost_rows):raise ValueError('Duplicate cost ownership across template and supplemental rows')
    claimed = set()
    for price in pricing['rates']:
        identity = price['row_id']
        if identity in claimed:raise ValueError('Duplicate priced cost row')
        claimed.add(identity)
        if identity not in rows and draft.get('saved_trade_review_required') and identity in draft.get('withheld_supplemental_cost_ids',[]):
            result.setdefault('unapplied_prices',[]).append({'row_id':identity,
                'reason':'Saved trade quantities withheld after geometry change; price not applied'})
            continue
        if identity not in rows:
            raise ValueError('Unknown or duplicate priced template row')
        row = rows[identity]
        if row.get('completion_status','').startswith('not_applicable'):
            raise ValueError('Excluded template options cannot receive a price')
        if row.get('cost_type') in ('GROUP','ASSEMBLY'):
            raise ValueError('Template groups and assemblies cannot receive a separate unit price')
        if row.get('cost_type') not in ('MATERIAL','LABOR','SUBCONTRACTOR','ALLOWANCE','EQUIPMENT','FEE'):
            raise ValueError('Summary or unknown template roles cannot receive a unit price')
        if row.get('covered_by_package'):
            raise ValueError('Template row is already covered by a package quote')
        if row.get('cost_owner_row_id'):
            raise ValueError('Template cost is assigned to another purchase row')
        if row.get('pricing_role')=='input_only' or row.get('parent','').strip().upper()=='INPUTS':
            raise ValueError('Template input quantities are not billable cost lines')
        if (price.get('evidence_kind') not in ('current_supplier_quote', 'current_purchase', 'jason_approved_rate', 'retail_listing')
                or price.get('scope_reviewed') is not True or price.get('pricing_basis') != 'unit_rate'):
            raise ValueError('Current reviewed unit-rate evidence required')
        if row['draft_quantity'] is None and price.get('validity_policy') not in ('owner_rate_until_changed','observation_date_only'):
            raise ValueError('Cannot price a row without a mapped quantity')
        evidence = (root / price['source_file']).resolve()
        if not evidence.is_relative_to(root) or not evidence.is_file():
            raise ValueError('Price evidence must be a file within the evidence folder')
        if hashlib.sha256(evidence.read_bytes()).hexdigest() != price.get('source_sha256'):
            raise ValueError('Price evidence hash does not match saved source')
        retail=price.get('evidence_kind')=='retail_listing'
        kit_sources=[q for q in row.get('quantity_sources',[]) if q.get('kind') in ('reviewed_kit_purchase','reviewed_item_purchase')]
        if kit_sources and any(q['product_id']!=price.get('product_id') or q['model']!=price.get('model') for q in kit_sources):
            raise ValueError('Purchase price must match the identified product and model')
        if price.get('validity_policy')=='observation_date_only' and not retail:
            raise ValueError('Observation-date pricing requires retail listing evidence')
        for key in ('supplier_cost','purchase_tax','purchase_tax_percent'):
            row.pop(key,None)
        tax=price.get('purchase_tax')
        if retail:
            record=json.loads(evidence.read_text(encoding='utf-8'))
            if (price.get('validity_policy')!='observation_date_only' or price.get('valid_through')!=price['date']
                    or any(record.get(k)!=price.get(k) for k in ('date','unit_price','unit','source','product_id'))
                    or not record.get('product_id') or not record.get('unit_basis')):
                raise ValueError('Retail price must match its dated product and purchase-unit observation')
            tax=price['purchase_tax']
            if not isinstance(tax,dict):raise ValueError('Retail purchase tax treatment is required')
        if tax is not None:
            tax_path=(root/tax['source_file']).resolve()
            if (not tax_path.is_relative_to(root) or not tax_path.is_file()
                    or hashlib.sha256(tax_path.read_bytes()).hexdigest()!=tax['source_sha256']):
                raise ValueError('Purchase tax evidence missing or changed')
            tax_record=json.loads(tax_path.read_text(encoding='utf-8'))
            if (tax_record.get('plan_sha256')!=draft['plan_sha256']
                    or any(tax_record.get(k)!=tax.get(k) for k in ('percent','effective_from','effective_through'))
                    or not tax_record.get('jurisdiction') or not tax_record.get('source')):
                raise ValueError('Purchase tax must match the project and source record')
            percent=Decimal(str(tax['percent']))
            if not percent.is_finite() or not 0<=percent<=100 or price.get('tax_included') is not False:
                raise ValueError('Retail tax needs a valid rate and an explicitly pretax listing')
        if price.get('validity_policy')=='owner_rate_until_changed':
            record=json.loads(evidence.read_text(encoding='utf-8'))
            recorded_rate=record
            source_field=price.get('source_rate_field')
            if not isinstance(source_field,str) or not source_field:
                raise ValueError('Standing owner rate must match its original dated answer: invalid source field')
            for part in source_field.split('.'):
                recorded_rate=recorded_rate.get(part) if isinstance(recorded_rate,dict) else None
            if (record.get('source')!='Jason, current conversation'
                    or record.get('recorded_at','')[:10]!=price['date']
                    or recorded_rate!=price['unit_price']):
                raise ValueError('Standing owner rate must match its original dated answer')
        priced = {'unit':row['unit'], 'quantity':row['draft_quantity'],
                  'markup_percent':row['markup_pct'], 'unit_price':None, 'cost':None, 'sell_amount':None}
        apply_price(priced, price, as_of)
        if tax is not None:
            row['supplier_cost']=priced['cost'];row['purchase_tax']=None
            row['purchase_tax_percent']=tax['percent'];row['current_price_certified']=False
            if not date.fromisoformat(tax['effective_from'])<=date.fromisoformat(as_of)<=date.fromisoformat(tax['effective_through']):
                priced.update(unit_price=None,cost=None,sell_amount=None,price_status='Purchase tax evidence is not effective for the pricing date')
                row['supplier_cost']=None
            elif priced['cost'] is not None:
                money=lambda n:n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                purchase_tax=money(Decimal(str(priced['cost']))*percent/100)
                cost=Decimal(str(priced['cost']))+purchase_tax
                priced.update(cost=float(cost),sell_amount=float(money(cost*(1+Decimal(str(row['markup_pct']))/100))))
                row['purchase_tax']=float(purchase_tax)
                priced['price_status']+=f"; estimated {percent}% purchase tax included once"
        if retail:
            priced['price_status']+='; delivery separate; dated public retail listing, local availability and checkout price unverified'
        row.update(unit_cost=priced['unit_price'], line_cost=priced['cost'], line_price=priced['sell_amount'],
                   price_status=priced['price_status'], price_evidence=copy.deepcopy(price))
        row.pop('pricing_basis',None)
        if price.get('validity_policy')=='owner_rate_until_changed':
            row['current_price_certified']=False
            row['price_status']+=f"; owner estimating rate recorded {price['date']}; supplier pricing not revalidated"
            if any(q.get('kind')=='porch_labor_allowance' for q in row.get('quantity_sources',[])):
                row['price_status']+='; porch SF uses the garage rate as an estimating allowance, not a confirmed porch quote'
            accept_estimating_price(row, as_of, 'owner_estimating_rate')
    result=apply_dated_allowances(result,pricing,as_of,evidence_root)
    result=apply_component_allowances(result,pricing,as_of,evidence_root)
    result['pricing_as_of'] = as_of
    result['pricing_sha256'] = hashlib.sha256(json.dumps(pricing,sort_keys=True,allow_nan=False).encode()).hexdigest()
    result['status'] = 'Draft line pricing only; whole-house completeness and quantity certification remain required'
    return result
