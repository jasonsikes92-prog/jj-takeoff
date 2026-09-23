"""Apply reviewed, complete package quotes without duplicate template charges."""
import copy
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from bid_comparison import compare_quotes,scope_digest
from invoice_allocations import validate_allocations
from estimating_price_review import accept_estimating_price
from package_quantity_review import record_package_quantity_review


def price_packages(draft, packages, as_of, evidence_root, withhold_stale=False):
    original_digest=scope_digest(draft)
    result=copy.deepcopy(draft)
    all_rows=result['rows']+result.get('additional_cost_rows',[])
    rows={r['row_id']:r for r in all_rows}
    if len(rows)!=len(all_rows):raise ValueError('Duplicate template or supplemental rows')
    claimed=set();used_quotes=set();used_allocations={}
    # Component allowances are priced before packages; reserve their invoice claims.
    for existing in all_rows:
        if existing.get('line_cost') is None or existing.get('pricing_basis')!='dated_component_allowance':
            continue
        evidence=existing['price_evidence'];document=evidence['original_document']['source_sha256']
        if not evidence.get('invoice_allocations'):
            if document in used_allocations:raise ValueError('Component invoice already charged')
            used_quotes.add(document)
            continue
        pretax=sum((Decimal(str(c['cost'])) for c in evidence['components']),Decimal(0))
        allocations=validate_allocations(evidence['invoice_allocations'],
            {'quoted_total':str(pretax),'source_sha256':document},evidence_root)
        for claim in allocations['claims']:
            source=claim['source_sha256'];part=claim['allocation_id'];prior=used_allocations.get(source)
            if source in used_quotes or (prior and (prior['ledger']!=allocations['source_sha256'] or part in prior['parts'])):
                raise ValueError('Component invoice allocation already charged or review partition changed')
            used_allocations.setdefault(source,{'ledger':allocations['source_sha256'],'parts':set()})['parts'].add(part)
    for package in packages:
        scope=package['scope']
        supplemental=package.get('supplemental_cost')
        if supplemental is not None:
            identity=package['row_id'];parent=rows.get(supplemental['parent_row_id'],{})
            markup_source=rows.get(supplemental['markup_source_row_id'],{})
            installed_allowance=(markup_source.get('cost_type')=='ALLOWANCE'
                                 and isinstance(supplemental.get('installed_scope'),str)
                                 and bool(supplemental['installed_scope'].strip()))
            extras=result.setdefault('additional_cost_rows',[])
            if identity in rows or any(r['row_id']==identity for r in extras):
                raise ValueError('Duplicate supplemental package cost owner')
            if (package.get('billing_basis')!='fixed_package' or package['covered_row_ids']!=[identity]
                    or not supplemental.get('name') or not supplemental.get('scope_id')
                    or not package.get('scope_note')):
                raise ValueError('Supplemental package needs its own fixed cost and reviewed scope')
            if (parent.get('cost_type') not in ('GROUP','ASSEMBLY') or parent.get('parent','').strip().upper()=='INPUTS'
                    or parent.get('completion_status','').startswith('not_applicable')
                    or parent.get('line_cost') is not None or parent.get('covered_by_package')
                    or (markup_source.get('cost_type') not in ('SUBCONTRACTOR','LABOR','MATERIAL') and not installed_allowance)
                    or markup_source.get('parent')!=parent.get('name')):
                raise ValueError('Supplemental package needs an unpriced trade group and matching markup source')
            if any(r.get('package_scope_id')==supplemental['scope_id'] and r['parent_row_id']==supplemental['parent_row_id'] for r in extras):
                raise ValueError('Supplemental package scope is already assigned')
            row={'row_id':identity,'parent_row_id':supplemental['parent_row_id'],
                 'package_scope_id':supplemental['scope_id'],'name':supplemental['name'],
                 'parent':parent['name'],'cost_type':markup_source['cost_type'],'unit':'each',
                 'markup_pct':markup_source['markup_pct'],'markup_source_row_id':markup_source['row_id'],
                 'draft_quantity':None,'unit_cost':None,'line_cost':None,'line_price':None,
                 'pricing_role':'cost_line','completion_status':'evidence_in_progress',
                 'certified':False,'current_price_certified':False,'quantity_sources':[],
                 'assembly_inputs':[],'scope_note':package['scope_note']}
            extras.append(row);rows[identity]=row
            if installed_allowance:row['installed_scope']=supplemental['installed_scope']
            if 'quantity_reference' in supplemental:
                if supplemental['quantity_reference']!='floating_floor_wall_runs':
                    raise ValueError('Unknown supplemental quantity reference')
                from floor_trim_reference import floating_floor_wall_runs
                row['assembly_inputs']=[floating_floor_wall_runs(draft)]
        if (scope['plan_sha256']!=draft['plan_sha256'] or
                scope['measurement_version']!=draft['measurement_version'] or
                package.get('reviewed_draft_sha256')!=original_digest):
            if withhold_stale:
                for identity in package['covered_row_ids']:
                    if identity in rows:
                        rows[identity]['price_status']='Package allowance withheld: estimate changed; scope review required'
                result.setdefault('pending_packages',[]).append({'row_id':package['row_id'],
                    'reason':'Estimate changed; package scope review required'})
                continue
            raise ValueError('Package review belongs to a different estimate draft')
        if package.get('scope_mapping_reviewed') is not True:
            raise ValueError('Package template ownership needs review')
        target=package['row_id'];covered=package['covered_row_ids']
        if not covered or len(set(covered))!=len(covered) or target not in covered:
            raise ValueError('Package needs unique covered rows including its cost row')
        if any(i not in rows or i in claimed for i in covered):
            raise ValueError('Unknown or overlapping package row ownership')
        for identity in covered:
            row=rows[identity]
            if row.get('cost_owner_row_id') or any(r['parent_row_id']==identity for r in result.get('additional_cost_rows',[])):
                raise ValueError('Package scope has supplemental purchase owners; reconcile them before pricing')
            if (row.get('pricing_role')=='input_only' or row.get('parent','').strip().upper()=='INPUTS'
                    or row['cost_type']=='GROUP' or row['completion_status'].startswith('not_applicable')):
                raise ValueError('Package cannot own input, group or excluded rows')
            if row['cost_type'] not in ('ASSEMBLY','MATERIAL','LABOR','SUBCONTRACTOR','ALLOWANCE','EQUIPMENT','FEE'):
                raise ValueError('Package cannot cover summary or unknown template roles')
            if row.get('line_cost') is not None or row.get('covered_by_package'):
                raise ValueError('Package scope already has a price or package owner')
        row=rows[target]
        fixed_package=package.get('billing_basis')=='fixed_package'
        if package.get('billing_basis') not in (None,'fixed_package'):
            raise ValueError('Unknown package billing basis')
        allowed_types=('SUBCONTRACTOR','ALLOWANCE')+ (('MATERIAL','LABOR','EQUIPMENT','FEE') if fixed_package else ())
        if (not row['unit'] or (not fixed_package and row['unit'] not in ('each','EA'))
                or row['cost_type'] not in allowed_types):
            raise ValueError('Package cost belongs on a subcontractor each row or an allowance each row')
        if not fixed_package and row.get('draft_quantity') not in (None,1):
            raise ValueError('Package must not replace a measured multi-unit quantity')
        unpriced_scope=package.get('unpriced_scope',[])
        if not isinstance(unpriced_scope,list) or any(not isinstance(s,str) or not s.strip() for s in unpriced_scope):
            raise ValueError('Unpriced package scope must be a list of nonempty descriptions')
        comparison=compare_quotes(scope,package['quotes'],as_of,evidence_root)
        matches=[q for q in comparison['quotes'] if q['id']==package['quote_id']]
        if len(matches)!=1:
            raise ValueError('Package requires a current, reviewed, complete-scope quote')
        quote=matches[0];allowance=quote.get('same_scope_dated_allowance',False)
        if allowance:
            authority=package.get('allowance_authorization',{})
            root=Path(evidence_root).resolve();source=(root/authority.get('source_file','')).resolve()
            if (not source.is_relative_to(root) or not source.is_file()
                    or hashlib.sha256(source.read_bytes()).hexdigest()!=authority.get('source_sha256')):
                raise ValueError('Dated package allowance needs unchanged owner authorization')
            if json.loads(source.read_text(encoding='utf-8')).get('answer')!='Use saved rates as dated allowances':
                raise ValueError('Dated package allowance needs owner authorization')
        elif not quote['same_scope_current_quote']:
            raise ValueError('Package requires a current, reviewed, complete-scope quote')
        key=quote['source_sha256']
        raw_quote=next(q for q in package['quotes'] if q['id']==package['quote_id'])
        count_review = package.get('package_count_review')
        count_source = None
        if count_review is not None:
            root = Path(evidence_root).resolve()
            source = (root/count_review['source_file']).resolve()
            if (not source.is_relative_to(root) or not source.is_file()
                    or hashlib.sha256(source.read_bytes()).hexdigest()!=count_review['source_sha256']):
                raise ValueError('Package count review evidence changed')
            count_source = json.loads(source.read_bytes())
            if (not fixed_package or row['unit'] not in ('each','EA')
                    or count_source.get('plan_sha256')!=draft['plan_sha256']
                    or count_source.get('row_id')!=target
                    or type(count_source.get('quantity')) is not int or count_source['quantity']!=1
                    or count_source.get('unit')!='each' or not count_source.get('basis')
                    or count_source.get('quote_source_sha256')!=quote['source_sha256']):
                raise ValueError('Package count needs reviewed one-package source and matching each row')
            if row.get('draft_quantity') not in (None,1) or isinstance(row.get('draft_quantity'),bool):
                raise ValueError('One-package count conflicts with the measured quantity')
        if 'invoice_allocations' in raw_quote:
            if not fixed_package:raise ValueError('Invoice allocations require fixed package billing')
            allocations=validate_allocations(raw_quote['invoice_allocations'],quote,evidence_root)
            for claim in allocations['claims']:
                source=claim['source_sha256'];part=claim['allocation_id']
                prior=used_allocations.get(source)
                if source in used_quotes or (prior and (prior['ledger']!=allocations['source_sha256'] or part in prior['parts'])):
                    raise ValueError('Invoice allocation already charged or review partition changed')
                used_allocations.setdefault(source,{'ledger':allocations['source_sha256'],'parts':set()})['parts'].add(part)
            quote['invoice_allocations']=allocations
        else:
            if key in used_quotes or key in used_allocations:raise ValueError('Quote package already charged')
            used_quotes.add(key)
        claimed.update(covered)
        cost=Decimal(quote['quoted_total']);markup=Decimal(str(row['markup_pct']))
        if not markup.is_finite() or markup<0:raise ValueError('Invalid template markup')
        if cost!=cost.quantize(Decimal('.01')):raise ValueError('Package amount needs whole cents')
        tax_status=''
        if 'purchase_tax' in package:
            if not allowance or not fixed_package or row['cost_type']!='MATERIAL':
                raise ValueError('Package purchase tax requires a fixed dated material allowance')
            from viewer.dated_price_allowances import allowance_purchase_tax
            taxed,current,tax_status=allowance_purchase_tax(row,package,float(cost),as_of,
                Path(evidence_root).resolve(),draft['plan_sha256'])
            cost=Decimal(str(taxed)) if current else None
        sell=(cost*(1+markup/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if cost is not None else None
        for identity in covered:rows[identity]['covered_by_package']=target
        row.update(line_cost=float(cost) if cost is not None else None,line_price=float(sell) if sell is not None else None,
            pricing_basis='dated_package_allowance' if allowance else 'reviewed_package',
            price_status=(f"Dated package estimating allowance: {quote['supplier']}, {quote['date']}; current supplier price unverified"
                          if allowance else 'current_reviewed_package')+tax_status,
            price_evidence={'quote':quote,'scope_sha256':comparison['scope_sha256'],
                            'reviewed_draft_sha256':original_digest,'covered_row_ids':list(covered)})
        if 'purchase_tax' in package:
            row['price_evidence'].update(purchase_tax=copy.deepcopy(package['purchase_tax']),tax_included=False)
        if unpriced_scope:row['price_evidence']['unpriced_scope']=list(unpriced_scope)
        if fixed_package:
            # A quoted total does not establish area, count or a transferable unit rate.
            row['unit_cost']=None
            row['price_evidence']['billing_basis']='fixed_package'
            row['price_evidence']['scope_note']=package.get('scope_note','')
            if count_source is not None:
                row['draft_quantity']=1
                row['price_evidence']['package_count_review']=copy.deepcopy(count_review)
                row.setdefault('quantity_sources',[]).append({
                    'kind':'documented_package_count','quantity':1,'unit':'EA',
                    'basis':count_source['basis'],'source':copy.deepcopy(count_review),
                    'certified':False})
        else:
            row.update(draft_quantity=1,unit_cost=float(cost))
            if package.get('scope_note'):
                row['price_evidence']['scope_note']=package['scope_note']
        if allowance:
            row['current_price_certified']=False
            row['price_evidence']['authorization']=copy.deepcopy(package['allowance_authorization'])
            accept_estimating_price(row, as_of, 'authorized_dated_allowance')
        if count_source is not None:
            record_package_quantity_review(row, draft['plan_sha256'], draft['measurement_version'])
    result.update(package_pricing_as_of=as_of,whole_house_total=None,estimate_released=False,
                  status='Draft package pricing; whole-house completeness remains unverified')
    return result
