"""Check explicitly transcribed quote pricing without inventing a billing basis."""
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP


def number(value):
    if value is None:return None
    if isinstance(value,bool):raise ValueError('Quote pricing numbers cannot be booleans')
    try:result=Decimal(str(value))
    except InvalidOperation as exc:raise ValueError('Invalid quote pricing number') from exc
    if not result.is_finite() or result<0:raise ValueError('Quote pricing numbers must be finite and nonnegative')
    return result


def review_measurement_adjustments(practice,line):
    """Compare quoted billing adjustments; never turn billing waste into purchase waste."""
    if practice is None:return []
    prefix=line['id']+': '
    if not isinstance(practice,dict):raise ValueError('Estimating practice must be an object')
    expected_deductions=practice.get('deduct_window_door_openings')
    if expected_deductions is not None and type(expected_deductions) is not bool:
        raise ValueError('Job opening-deduction practice must be a boolean')
    expected_waste=number(practice.get('billing_waste_percent'))
    quoted=line.get('measurement_adjustments')
    if (not isinstance(quoted,dict) or quoted.get('reviewed') is not True
            or not isinstance(quoted.get('source_ref'),str) or not quoted['source_ref'].strip()):
        return [prefix+'opening deductions and billing waste need a source-linked review']
    if quoted.get('basis')=='fixed_package':
        if (line.get('basis')!='lump_sum' or not isinstance(quoted.get('reason'),str)
                or not quoted['reason'].strip()
                or any(quoted.get(k) is not None for k in ('deduct_window_door_openings','billing_waste_percent'))):
            return [prefix+'fixed-package adjustment exception needs a lump sum, source explanation and no conflicting adjustment values']
        return []
    if quoted.get('basis')!='billing_quantity':
        return [prefix+'measurement-adjustment basis is unconfirmed']
    deductions=quoted.get('deduct_window_door_openings')
    if deductions is not None and type(deductions) is not bool:
        raise ValueError('Quoted opening deductions must be a boolean or unknown')
    waste=number(quoted.get('billing_waste_percent'));issues=[]
    if expected_deductions is None:issues.append(prefix+'job opening-deduction practice is unresolved')
    if expected_waste is None:issues.append(prefix+'job billing-waste practice is unresolved')
    if deductions is None:issues.append(prefix+'quoted opening deductions are unknown')
    elif expected_deductions is not None and deductions!=expected_deductions:
        issues.append(prefix+'quoted window/door deductions differ from the job estimating practice')
    if waste is None:issues.append(prefix+'quoted billing waste is unknown')
    elif expected_waste is not None and waste!=expected_waste:
        issues.append(prefix+f'quoted billing waste ({waste}%) differs from the job estimating practice ({expected_waste}%)')
    if line.get('quantity_source')=='measured_reference' and (deductions is True or (waste is not None and waste!=0)):
        issues.append(prefix+'adjusted billing quantity cannot use an unadjusted measured reference; review the quoted basis')
    return issues


def review_pricing(scope,quote):
    required_work=scope.get('required_work')
    if required_work is not None and required_work not in ('materials','labor','complete'):
        raise ValueError('Required work must identify materials, labor or complete scope')
    lines=quote.get('pricing_lines')
    if lines is None and not scope.get('requires_pricing_basis_review') and required_work is None:return None
    if not lines:return {'issues':['Pricing lines and billing basis have not been reviewed'],'charged_line_total':None}
    if not isinstance(lines,list):raise ValueError('Quote pricing lines must be a list')
    required={i['id']:i for i in scope['items']};by_id={};issues=[];amounts={}
    for line in lines:
        identity=line.get('id')
        if not isinstance(identity,str) or not identity or identity in by_id:raise ValueError('Unique pricing line IDs required')
        by_id[identity]=line
        ids=line.get('scope_ids')
        if not isinstance(ids,list) or not ids or len(set(ids))!=len(ids) or any(i not in required for i in ids):
            raise ValueError('Pricing lines need unique known surface scope IDs')
        if line.get('work') not in ('materials','labor','complete'):raise ValueError('Pricing line work must identify materials, labor or complete scope')
        if not isinstance(line.get('source_ref'),str) or not line['source_ref'].strip():issues.append(identity+': pricing source location is missing')
        amount=number(line.get('amount'));amounts[identity]=amount
        if amount is None:issues.append(identity+': amount is unknown')
        basis=line.get('basis')
        if basis=='lump_sum':
            if line.get('quantity') is not None or line.get('unit_rate') is not None:
                issues.append(identity+': lump-sum line has conflicting quantity/rate fields')
            continue
        if basis not in ('floor_sf','wall_sf','ceiling_sf','wall_ceiling_sf','sheet',
                         'roof_sf','roofing_square','shingle_bundle','metal_panel','linear_foot'):
            issues.append(identity+': billing unit is unconfirmed');continue
        quantity=number(line.get('quantity'));rate=number(line.get('unit_rate'))
        if quantity is None or rate is None:issues.append(identity+': quantity or unit rate is unknown')
        elif amount is not None and (quantity*rate).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)!=amount:
            issues.append(identity+': quantity times rate does not match line amount')
        if line.get('quantity_source')=='measured_reference':
            allowed={'wall_sf':{'gross wall SF'},'ceiling_sf':{'ceiling surface SF'},
                'wall_ceiling_sf':{'gross wall SF','ceiling surface SF'},
                'roof_sf':{'SF'},'roofing_square':{'SF'},'linear_foot':{'LF'}}.get(basis,set())
            refs=[required[i] for i in ids]
            roof_basis=basis in ('roof_sf','roofing_square')
            if any(r.get('reference_unit') not in allowed or
                    (roof_basis and r.get('surface')!='roof') for r in refs):
                issues.append(identity+': billing unit does not match the measured reference unit')
            elif any(r.get('reference_quantity') is None for r in refs):
                issues.append(identity+': measured reference coverage is incomplete')
            elif quantity is not None and abs(sum(number(r['reference_quantity']) for r in refs)/
                    (Decimal(100) if basis=='roofing_square' else Decimal(1))-quantity)>Decimal('.005'):
                issues.append(identity+': quoted quantity differs from the measured reference')
        elif (line.get('quantity_source')!='quoted_basis' or line.get('quantity_basis_reviewed') is not True
                or not isinstance(line.get('quantity_basis_source_ref'),str) or not line['quantity_basis_source_ref'].strip()):
            issues.append(identity+': independent quoted quantity basis has not been reviewed')
    charged=[];valid_inclusions=True
    for identity,line in by_id.items():
        parent=line.get('included_in')
        if parent is None:
            charged.append(line)
            issues.extend(review_measurement_adjustments(scope.get('estimating_practice'),line))
            continue
        package=by_id.get(parent)
        if (package is None or parent==identity or package.get('included_in') is not None
                or not set(line['scope_ids'])<=set(package['scope_ids'])
                or package['work'] not in ('complete',line['work'])):
            issues.append(identity+': included-in-package relationship is invalid');valid_inclusions=False
    for index,a in enumerate(charged):
        for b in charged[index+1:]:
            if set(a['scope_ids'])&set(b['scope_ids']) and (a['work']==b['work'] or 'complete' in (a['work'],b['work'])):
                issues.append(a['id']+' / '+b['id']+': overlapping charges may duplicate package scope')
    covered={i for line in charged for i in line['scope_ids']}
    included={i['scope_id'] for i in quote.get('scope_items',[]) if i['status']=='included' and i['scope_id'] in required}
    if included-covered:issues.append('Included surface scope is missing from the priced lines')
    if required_work is not None:
        needed={'materials','labor'} if required_work=='complete' else {required_work}
        for identity in required:
            supplied=set()
            for line in charged:
                if identity in line['scope_ids']:
                    supplied.update(('materials','labor') if line['work']=='complete' else (line['work'],))
            for missing in sorted(needed-supplied):
                issues.append(identity+': required '+missing+' is missing from the priced lines')
    total=sum((amounts[l['id']] for l in charged),Decimal(0)) if valid_inclusions and all(amounts[l['id']] is not None for l in charged) else None
    quoted=number(quote.get('total'))
    if total is not None and quoted is not None and total!=quoted:issues.append('Charged line total differs from the quoted package total')
    return {'issues':issues,'charged_line_total':str(total) if total is not None else None,
        'charged_line_ids':[l['id'] for l in charged],'purchase_authorized':False,
        'basis':'Checks explicit source-linked pricing transcription; arithmetic agreement does not prove scope completeness'}
