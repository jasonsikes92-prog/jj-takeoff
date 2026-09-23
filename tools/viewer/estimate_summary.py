"""Read the template footer separately from purchasable construction scope."""
from decimal import Decimal, InvalidOperation


FOOTER=('Summary','Totals','Builder Fixed Cost','Allowances','Overheads',
        'Insurances','Markup','Total Tax','Adjust','Total')


def summary_layout(template):
    """Recognize the complete imported footer, never an isolated matching name.

    Buildern exports summary amounts in column C, where construction rows have
    cost types. These source amounts are not approved values for a new estimate.
    Unknown or altered layouts remain unresolved for source review.
    """
    rows=template['rows'][-len(FOOTER):]
    if tuple(r.get('name') for r in rows)!=FOOTER:return {}
    try:
        numbers=[int(r['excel_row']) for r in rows]
        if numbers!=list(range(numbers[0],numbers[0]+len(FOOTER))):return {}
        if len({r['row_id'] for r in rows})!=len(rows):return {}
        for index,row in enumerate(rows):
            if any(row.get(k,'')!='' for k in ('parent','unit','markup_pct')):return {}
            value=row.get('cost_type','')
            if index<2:
                if value!='':return {}
            elif value!='':
                if isinstance(value,bool) or not Decimal(str(value)).is_finite():return {}
    except (KeyError,ValueError,InvalidOperation):return {}
    return {r['row_id']:'summary_heading' if i<2 else 'summary_field'
            for i,r in enumerate(rows)}


def review_summary(draft,template):
    from estimate_readiness import readiness,valid_number
    audit=readiness(draft,template)
    details={r['row_id']:r for r in audit['rows']+audit['additional_cost_rows']}
    layout=summary_layout(template)
    fields=[];priced=[];unpriced=[];conflicts=[]
    allowed_issues={'Quantity unresolved','Only partial assembly inputs available',
        'Quantity and assembly certification outstanding','Current price certification outstanding'}
    for row in draft['rows']+draft.get('additional_cost_rows',[]):
        identity=row['row_id'];detail=details[identity]
        role=detail.get('role','supplemental_cost_line')
        if identity in layout:
            fields.append({'row_id':identity,'excel_row':row['excel_row'],'name':row['name'],
                'role':layout[identity],'amount':None,'issues':detail['issues']})
        cost=row.get('line_cost');price=row.get('line_price')
        eligible=role in ('cost_line','supplemental_cost_line')
        if cost is None and price is None:
            if eligible:unpriced.append(identity)
            continue
        problems=[i for i in detail['issues'] if i not in allowed_issues
                  and not i.startswith('Measurement scope review outstanding:')]
        if not eligible:problems.append('Only separate construction cost owners enter the subtotal')
        if not valid_number(cost) or not valid_number(price):problems.append('Both finite nonnegative line amounts are required')
        if problems:
            conflicts.append({'row_id':identity,'issues':problems});continue
        priced.append({'row_id':identity,'name':row['name'],'cost_type':row['cost_type'],
            'line_cost':cost,'line_price':price,'pricing_basis':row.get('pricing_basis'),
            'current_price_certified':row.get('current_price_certified',False)})
    totals=None
    if priced and not conflicts:
        cost=sum((Decimal(str(r['line_cost'])) for r in priced),Decimal(0))
        price=sum((Decimal(str(r['line_price'])) for r in priced),Decimal(0))
        totals={'line_cost':str(cost),'line_price':str(price),'included_line_markup':str(price-cost)}
    return {'plan_sha256':draft['plan_sha256'],'measurement_version':draft['measurement_version'],
        'template_sha256':draft.get('template_sha256',template.get('template_sha256')),
        'summary_layout_recognized':bool(layout),'summary_fields':fields,
        'priced_cost_rows':priced,'unpriced_cost_row_ids':unpriced,'conflicts':conflicts,
        'known_line_subtotals':totals,'whole_house_total':None,'estimate_released':False,
        'limitations':['Known line subtotals are incomplete and may include dated allowances.',
            'Summary source zeros are not confirmed job amounts. Summary amounts and inclusion bases remain unresolved.',
            'Line markup and purchase tax already in line amounts are not added again.',
            'Overhead, insurance, allowances, adjustment and final summary formulas require separate reconciliation.']}
