"""Combine reviewed dated rates under one template or explicitly owned purchase row."""
import copy
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from dated_price_allowances import checked_file,allowance_purchase_tax
from estimating_price_review import accept_estimating_price
from invoice_allocations import validate_allocations


def quantity_binding(row):
    value={k:row.get(k) for k in ('draft_quantity','quantity_sources','assembly_inputs')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def apply_component_allowances(draft, pricing, as_of, evidence_root):
    references=pricing.get('dated_component_allowances',[])
    if not references:return draft
    from pathlib import Path
    root=Path(evidence_root).resolve()
    authority=json.loads(checked_file(root,pricing['allowance_authorization']).read_text(encoding='utf-8'))
    if authority.get('answer')!='Use saved rates as dated allowances':
        raise ValueError('Component allowances need owner authorization')
    all_rows=draft['rows']+draft.get('additional_cost_rows',[])
    rows={r['row_id']:r for r in all_rows};seen=set()
    if len(rows)!=len(all_rows):raise ValueError('Duplicate component cost row identity')
    records=[json.loads(checked_file(root,r).read_text(encoding='utf-8')) for r in references]
    partitioned={r['original_document']['source_sha256'] for r in records if r.get('invoice_allocations')}
    used_allocations={}
    for row in all_rows:
        quote=row.get('price_evidence',{}).get('quote',{})
        if row.get('line_cost') is not None and quote.get('source_sha256') in partitioned:
            raise ValueError('Component invoice is already charged by a package')
    money=lambda n:n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    for reference,record in zip(references,records):
        checked_file(root,record['original_document']);checked_file(root,record['scope_confirmation'])
        for evidence in record.get('quantity_evidence',[]):checked_file(root,evidence)
        identity=record['row_id']
        if identity not in rows or identity in seen:raise ValueError('Unique component cost owner required')
        seen.add(identity);row=rows[identity]
        if row in draft.get('additional_cost_rows',[]):
            source=rows.get(row.get('source_row_id'),{})
            if (source.get('assembly_input_cost_owners',{}).get(row.get('source_assembly_input_id'))!=identity
                    or source.get('pricing_role')!='input_only'):
                raise ValueError('Supplemental component allowance needs an explicit assembly input owner')
        if (record.get('plan_sha256')!=draft['plan_sha256'] or record.get('unit')!=row['unit']
                or record.get('scope_reviewed') is not True or record.get('currency')!='USD'
                or not record.get('source') or not record.get('tax_delivery_basis')
                or row.get('cost_type') not in ('SUBCONTRACTOR','ALLOWANCE','MATERIAL')
                or row.get('completion_status','').startswith('not_applicable')
                or row.get('covered_by_package') or row.get('cost_owner_row_id')
                or row.get('pricing_role')=='input_only'):
            raise ValueError('Component allowance needs matching reviewed scope and cost ownership')
        if date.fromisoformat(record['date'])>date.fromisoformat(as_of):
            raise ValueError('Component rate is future dated')
        components=record['components'];ids=set();cost=Decimal(0);resolved=[]
        if not components:raise ValueError('Component allowance is empty')
        for component in components:
            if (not component.get('id') or component['id'] in ids or not component.get('source_ref')
                    or not component.get('unit') or not component.get('quantity_basis')):
                raise ValueError('Component needs unique identity, source and quantity basis')
            ids.add(component['id'])
            values=[component[k] for k in ('quantity_numerator','quantity_denominator','unit_price')]
            if any(isinstance(v,bool) for v in values):raise ValueError('Invalid component amount')
            numerator,denominator,rate=map(lambda v:Decimal(str(v)),values)
            if (any(not v.is_finite() for v in (numerator,denominator,rate))
                    or numerator<0 or denominator<=0 or rate<0):raise ValueError('Invalid component amount')
            amount=money(numerator*rate/denominator);cost+=amount
            resolved.append({**component,'cost':float(amount)})
        document=record['original_document']['source_sha256']
        if document in partitioned:
            if not record.get('invoice_allocations'):
                raise ValueError('Shared component invoice needs an explicit allocation')
            allocations=validate_allocations(record['invoice_allocations'],
                {'quoted_total':str(cost),'source_sha256':document},root)
            for claim in allocations['claims']:
                source=claim['source_sha256'];part=claim['allocation_id'];prior=used_allocations.get(source)
                if prior and (prior['ledger']!=allocations['source_sha256'] or part in prior['parts']):
                    raise ValueError('Component invoice allocation already charged or partition changed')
                used_allocations.setdefault(source,{'ledger':allocations['source_sha256'],'parts':set()})['parts'].add(part)
        # Current independent rates win; historical components cannot add another charge.
        if row.get('unit_cost') is not None and row.get('pricing_basis')!='dated_component_allowance':continue
        if row.get('pricing_basis')=='dated_component_allowance':
            row.update(unit_cost=None,line_cost=None,line_price=None)
            for key in ('pricing_basis','price_evidence','supplier_cost','purchase_tax','purchase_tax_percent','estimating_price_review'):
                row.pop(key,None)
        if record.get('reviewed_quantity_binding')!=quantity_binding(row) or row.get('draft_quantity') is None:
            row['price_status']='Component allowance withheld: quantity or source changed; recalculate and review'
            continue
        quantity=Decimal(str(row['draft_quantity']));markup=Decimal(str(row['markup_pct']))
        if not quantity.is_finite() or quantity<=0 or not markup.is_finite() or markup<0:
            raise ValueError('Positive template quantity and nonnegative markup required')
        taxed,tax_current,tax_status=allowance_purchase_tax(row,record,float(cost),as_of,root,draft['plan_sha256'])
        cost=Decimal(str(taxed)) if tax_current else None
        row.update(unit_cost=float(cost/quantity) if tax_current else None,line_cost=float(cost) if tax_current else None,
            line_price=float(money(cost*(1+markup/100))) if tax_current else None,
            pricing_basis='dated_component_allowance',current_price_certified=False,
            price_status=f"Dated component estimating allowance: {record['source']}, {record['date']}; current quote unverified. {record.get('limitation','')}"+tax_status,
            price_evidence={**copy.deepcopy(record),**reference,'components':resolved,
                'reviewed_template_quantity':row['draft_quantity'],
                'authorization':copy.deepcopy(pricing['allowance_authorization'])})
        accept_estimating_price(row, as_of, 'authorized_dated_allowance')
    return draft
