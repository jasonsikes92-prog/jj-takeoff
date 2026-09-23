"""Expose row-level gaps in one draft without certifying a complete house."""
from collections import Counter
from decimal import Decimal, InvalidOperation
from estimate_summary import summary_layout
from count_reference_reviews import current_count_review
from estimating_price_review import accepted_estimating_price
from package_quantity_review import current_package_quantity_review
from input_purchase_coverage import purchase_coverage


def valid_number(value):
    if value is None or isinstance(value,bool):return False
    try:number=Decimal(str(value))
    except InvalidOperation:return False
    return number.is_finite() and number>=0


def quantity_source_gaps(row):
    """Keep explicit unfinished source scope visible beside certification status."""
    gaps=[]
    for source in row.get('quantity_sources',[]):
        remaining=source.get('remaining',[])
        if isinstance(remaining,str):remaining=[remaining]
        for item in remaining:
            if isinstance(item,str) and item.strip():
                issue='Quantity source needs resolution: '+item.strip()
                if issue not in gaps:gaps.append(issue)
    return gaps


def readiness(draft, template):
    expected={r['row_id']:r for r in template['rows']}
    rows={r['row_id']:r for r in draft['rows']}
    if len(expected)!=len(template['rows']) or len(rows)!=len(draft['rows']):
        raise ValueError('Duplicate template row identities')
    if set(rows)!=set(expected):raise ValueError('Draft does not preserve every template row')
    summary=summary_layout(template)
    details=[]
    extra_by_id={r['row_id']:r for r in draft.get('additional_cost_rows',[])}
    ordered=list(expected.values())
    for index,(identity,original) in enumerate(expected.items()):
        row=rows[identity];issues=[];warnings=[];input_coverage={}
        children=[]
        if original.get('cost_type')=='ASSEMBLY':
            for candidate in ordered[index+1:]:
                if candidate.get('cost_type') in ('GROUP','ASSEMBLY'):break
                if candidate.get('parent')==original['name']:children.append(candidate['row_id'])
        for key in ('excel_row','name','parent','cost_type','unit','markup_pct'):
            if row.get(key)!=original.get(key):issues.append('Template field changed: '+key)
        status=row.get('completion_status','')
        if row.get('applicability_review',{}).get('status') == 'source_or_revision_changed_review_required':
            issues.append('Scope applicability needs renewed review')
        owner=row.get('covered_by_package')
        if identity in summary:
            role=summary[identity]
            if role=='summary_field':issues.append('Summary amount and inclusion basis unresolved')
            if row.get('draft_quantity') is not None or row.get('assembly_inputs'):
                issues.append('Summary row contains a construction quantity')
            if row.get('unit_cost') is not None or owner or row.get('cost_owner_row_id'):
                issues.append('Summary row has construction pricing or purchase ownership')
        elif row.get('cost_type')=='GROUP':role='rollup'
        elif row.get('parent','').strip().upper()=='INPUTS' or row.get('pricing_role')=='input_only':role='input'
        elif status.startswith('not_applicable'):role='excluded_by_saved_baseline'
        elif row.get('cost_owner_row_id'):role='cost_reference'
        elif row.get('cost_type')=='ASSEMBLY' and children:role='assembly_rollup'
        elif row.get('cost_type') not in ('MATERIAL','LABOR','SUBCONTRACTOR','ALLOWANCE','EQUIPMENT','FEE'):
            role='template_role_unresolved';issues.append('Confirm summary, layout or cost-row role')
        elif owner and owner!=identity:role='covered_by_package'
        else:role='cost_line'
        if role in ('rollup','assembly_rollup','input','excluded_by_saved_baseline','summary_heading','summary_field') and any(row.get(k) is not None for k in ('line_cost','line_price')):
            issues.append('Nonbillable row contains a price')
        if role=='input' and not valid_number(row.get('draft_quantity')):
            owners=row.get('assembly_input_cost_owners',{})
            if owners:
                for quantity in row.get('assembly_inputs',[]):
                    coverage=purchase_coverage(quantity,draft['rows'])
                    if coverage:
                        input_coverage[quantity['id']]=coverage
                    if coverage and (coverage['status']=='duplicate' or
                                     (coverage['status']=='covered' and quantity['id'] in owners)):
                        issues.append('Assembly input has multiple purchase owners: '+quantity['id'])
                    elif quantity['id'] not in owners:
                        if coverage and coverage['status']=='covered':
                            warnings.append('Assembly input included in priced template row '+coverage['owner_row_ids'][0]+': '+quantity['id'])
                        elif coverage and coverage['status']=='owner_excluded':
                            warnings.append('Assembly input excluded by owner zero count: '+quantity['id'])
                        else:issues.append('Assembly input has no purchase owner: '+quantity['id'])
                for pending in draft.get('pending_quantities',[]):
                    if str(row['excel_row']) in map(str,pending['template_rows']):
                        issues.append('Measurement scope review outstanding: '+pending['label'])
                for input_id,owner_id in owners.items():
                    replacement=extra_by_id.get(owner_id,{})
                    if replacement.get('source_row_id')!=identity or replacement.get('source_assembly_input_id')!=input_id:
                        issues.append('Assembly input purchase owner is missing or mismatched: '+input_id)
            else:issues.append('Input value unresolved')
        if role=='cost_reference':
            purchase_owner=rows.get(row['cost_owner_row_id'])
            replacement=extra_by_id.get(row['cost_owner_row_id'],{})
            if purchase_owner is not None:
                sources=[s for s in purchase_owner.get('quantity_sources',[])
                         if s.get('kind')=='whole_tile_packages' and identity in s.get('included_row_ids',[])]
                if (purchase_owner is row or purchase_owner.get('cost_owner_row_id')
                        or purchase_owner.get('covered_by_package') or len(sources)!=1
                        or not valid_number(purchase_owner.get('line_cost'))):
                    issues.append('Shared material purchase owner is missing, unpriced or mismatched')
                else:
                    warnings.append('Material included in template purchase row '+purchase_owner['row_id'])
            elif replacement.get('replaces_row_id')!=identity:
                issues.append('Supplemental purchase owner is missing or mismatched')
            if any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price')):
                issues.append('Reference row has a duplicate price')
        if role=='covered_by_package':
            package=rows.get(owner,{})
            covered=package.get('price_evidence',{}).get('covered_row_ids',[])
            if package.get('pricing_basis') not in ('reviewed_package','dated_package_allowance') or identity not in covered or not valid_number(package.get('line_cost')):
                issues.append('Package ownership is not supported by a priced package')
            if row.get('line_cost') is not None or row.get('line_price') is not None:
                issues.append('Covered row has a duplicate price')
            if package.get('price_evidence',{}).get('billing_basis')=='fixed_package':
                for pending in draft.get('pending_quantities',[]):
                    if str(row['excel_row']) in map(str,pending['template_rows']):
                        issues.append('Measurement scope review outstanding: '+pending['label'])
                if not valid_number(row.get('draft_quantity')):
                    issues.append('Only partial assembly inputs available' if row.get('assembly_inputs') else 'Quantity unresolved')
                if row.get('certified') is not True and not current_count_review(row):
                    issues.append('Quantity and assembly certification outstanding')
        if role=='cost_line':
            issues.extend('Unpriced package scope: '+item for item in row.get('price_evidence',{}).get('unpriced_scope',[]))
            for pending in draft.get('pending_quantities',[]):
                if str(row['excel_row']) in map(str,pending['template_rows']):
                    issues.append('Measurement scope review outstanding: '+pending['label'])
            if not valid_number(row.get('draft_quantity')):
                issues.append('Only partial assembly inputs available' if row.get('assembly_inputs') else 'Quantity unresolved')
            if not valid_number(row.get('line_cost')) or not valid_number(row.get('line_price')):
                issues.append('Current line pricing unresolved')
            elif not row.get('price_evidence'):issues.append('Price source evidence missing')
            billing_count=current_package_quantity_review(row,draft['plan_sha256'],draft['measurement_version'])
            if billing_count:
                warnings.append('Billing package count verified; physical quantities and complete trade scope remain separate')
            owner_count=current_count_review(row,'owner_confirmed_count')
            if owner_count:
                warnings.append('Owner-confirmed item count; not independently measured')
            if current_count_review(row,'supplier_schedule_count') and row['count_reference_review'].get('count_basis')=='trim_assembly':
                warnings.append(row['count_reference_review']['scope'])
                issues.extend(row['count_reference_review'].get('remaining_scope',[]))
            if (row.get('certified') is not True and not current_count_review(row,'selected_fixture_count')
                    and not current_count_review(row,'supplier_schedule_count') and not billing_count and not owner_count):
                issues.append('Quantity and assembly certification outstanding')
            if row.get('current_price_certified') is not True:
                if accepted_estimating_price(row):
                    warnings.append('Accepted estimating allowance; current supplier price unverified')
                else:issues.append('Current price certification outstanding')
        if ('Quantity and assembly certification outstanding' in issues
                or (row.get('certified') is True and role in ('cost_line','covered_by_package'))):
            issues.extend(quantity_source_gaps(row))
        details.append({'row_id':identity,'excel_row':row['excel_row'],'name':row['name'],
            'component_row_ids':children,
            'parent':row.get('parent',''),'role':role,'issues':issues,'warnings':warnings,
            'estimating_price_accepted':accepted_estimating_price(row),
            **({'assembly_input_purchase_coverage':input_coverage} if input_coverage else {}),
            'applicability_review':row.get('applicability_review'),
            'count_reference_review':row.get('count_reference_review'),
            'package_quantity_review':row.get('package_quantity_review'),
            'partial_assembly_ids':[a['id'] for a in row.get('assembly_inputs',[])],
            'covered_by_package':owner,'cost_owner_row_id':row.get('cost_owner_row_id')})
    extra_details=[];extra_ids=set()
    for row in draft.get('additional_cost_rows',[]):
        identity=row['row_id'];parent=rows.get(row['parent_row_id'],{})
        if identity in rows or identity in extra_ids:raise ValueError('Duplicate supplemental cost ownership')
        extra_ids.add(identity);issues=[];warnings=[]
        issues.extend('Unpriced package scope: '+item for item in row.get('price_evidence',{}).get('unpriced_scope',[]))
        for pending in draft.get('pending_quantities',[]):
            if identity in pending.get('row_ids',[]) or identity in pending.get('template_rows',[]):
                issues.append('Measurement scope review outstanding: '+pending['label'])
        if row.get('replaces_row_id') and rows.get(row['replaces_row_id'],{}).get('cost_owner_row_id')!=identity:
            issues.append('Replacement template reference is missing or mismatched')
        group_replacement=(parent.get('cost_type')=='GROUP' and row.get('replaces_row_id')
                           and rows.get(row['replaces_row_id'],{}).get('parent')==parent.get('name'))
        source=rows.get(row.get('source_row_id'),{})
        input_reference=(source.get('pricing_role')=='input_only' and source.get('parent')==parent.get('name')
                         and source.get('assembly_input_cost_owners',{}).get(row.get('source_assembly_input_id'))==identity)
        if row.get('source_row_id') and not input_reference:
            issues.append('Supplemental assembly input reference is missing or mismatched')
        group_input=parent.get('cost_type')=='GROUP' and input_reference
        markup_source=rows.get(row.get('markup_source_row_id'),{})
        group_package=(parent.get('cost_type') in ('GROUP','ASSEMBLY') and bool(row.get('package_scope_id'))
                       and (row.get('cost_type') in ('SUBCONTRACTOR','LABOR','MATERIAL')
                            or (row.get('cost_type')=='ALLOWANCE' and isinstance(row.get('installed_scope'),str) and bool(row['installed_scope'].strip())))
                       and markup_source.get('cost_type')==row.get('cost_type')
                       and markup_source.get('parent')==parent.get('name')
                       and row.get('markup_pct')==markup_source.get('markup_pct'))
        if row.get('package_scope_id') and valid_number(row.get('line_cost')):
            evidence=row.get('price_evidence',{})
            if (not group_package or row.get('covered_by_package')!=identity
                    or evidence.get('covered_row_ids')!=[identity] or evidence.get('billing_basis')!='fixed_package'):
                issues.append('Supplemental package ownership is not supported by a priced package')
        measured_sources=[q for q in row.get('quantity_sources',[]) if q.get('kind')=='measured_supplemental_surface']
        group_surface=(parent.get('cost_type')=='GROUP' and row.get('cost_type')=='MATERIAL'
                       and row.get('unit')=='sq ft' and markup_source.get('cost_type')=='MATERIAL'
                       and markup_source.get('unit') in ('sq ft','ft2','SF')
                       and row.get('markup_pct')==markup_source.get('markup_pct') and len(measured_sources)==1
                       and row.get('measured_surface_scope_id')==measured_sources[0].get('id')
                       and bool(measured_sources[0].get('scope_source')) and bool(measured_sources[0].get('linked_review')))
        if (parent.get('cost_type')!='ASSEMBLY' and not group_replacement and not group_input and not group_package and not group_surface) or parent.get('line_cost') is not None or parent.get('covered_by_package'):
            issues.append('Supplemental parent ownership is unresolved or already priced')
        if not valid_number(row.get('draft_quantity')):issues.append('Quantity unresolved')
        package_owner=row.get('covered_by_package')
        if package_owner and package_owner!=identity:
            package=rows.get(package_owner,{})
            if (package.get('pricing_basis') not in ('reviewed_package','dated_package_allowance')
                    or identity not in package.get('price_evidence',{}).get('covered_row_ids',[])
                    or not valid_number(package.get('line_cost'))):
                issues.append('Supplemental package ownership is not supported by a priced package')
            if any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price')):
                issues.append('Covered supplemental row has a duplicate price')
        elif not valid_number(row.get('line_cost')) or not valid_number(row.get('line_price')):issues.append('Current line pricing unresolved')
        elif not row.get('price_evidence'):issues.append('Price source evidence missing')
        billing_count=current_package_quantity_review(row,draft['plan_sha256'],draft['measurement_version'])
        if billing_count:
            warnings.append('Billing package count verified; physical quantities and complete trade scope remain separate')
        if row.get('certified') is not True and not billing_count:issues.append('Quantity and assembly certification outstanding')
        if row.get('current_price_certified') is not True:
            if accepted_estimating_price(row):
                warnings.append('Accepted estimating allowance; current supplier price unverified')
            else:issues.append('Current price certification outstanding')
        if 'Quantity and assembly certification outstanding' in issues or row.get('certified') is True:
            issues.extend(quantity_source_gaps(row))
        extra_details.append({'row_id':identity,'name':row['name'],'parent_row_id':row['parent_row_id'],
            'issues':issues,'warnings':warnings,'estimating_price_accepted':accepted_estimating_price(row),
            'package_quantity_review':row.get('package_quantity_review')})
    return {'plan_sha256':draft['plan_sha256'],'measurement_version':draft['measurement_version'],
        'additional_cost_rows':extra_details,
        'unapplied_prices':draft.get('unapplied_prices',[]),
        'additional_rows_with_open_issues':sum(bool(d['issues']) for d in extra_details),
        'pending_quantities':draft.get('pending_quantities',[]),
        'unmapped_measurements':draft.get('unmapped_measurements',[]),
        'template_rows':len(details),'roles':dict(Counter(d['role'] for d in details)),
        'rows_with_open_issues':sum(bool(d['issues']) for d in details),
        'saved_trade_review_required':draft.get('saved_trade_review_required'),
        'foundation_separate_scope':list(draft.get('foundation_snapshot',{}).get('unresolved_and_separate_scope',{})),
        'issue_counts':dict(Counter(i for d in details+extra_details for i in d['issues'])),
        'warning_counts':dict(Counter(i for d in details+extra_details for i in d['warnings'])),
        'accepted_estimating_price_rows':sum(d['estimating_price_accepted'] for d in details+extra_details),
        'unassigned_slab_supplemental_items':[{'id':r['template_row_id'],'name':r.get('name',''),
            'quantity':r['quantity'],'unit':r['unit']} for r in draft.get('slab_snapshot',{}).get('supplemental_rows',[]) if r['template_row_id'] not in extra_ids],
        'rows':details,'whole_house_total':None,'estimate_released':False,
        'limitation':'Audits this integrated draft only. Separate trade work is not counted until integrated; saved exclusions and source certifications require independent verification.'}
