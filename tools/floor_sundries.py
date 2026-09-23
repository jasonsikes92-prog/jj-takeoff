"""Recalculating floor sundries allowance; installation review remains separate."""
import math
from decimal import Decimal, ROUND_CEILING
from cement_board_layout import calculate,material_allowance


def coverage_packages(quantity, coverage):
    # Normalize geometry to billionths of SF/LF before whole-package rounding.
    # This removes coordinate arithmetic noise, not construction waste.
    required=Decimal(str(round(quantity,9)))
    count=int((required/Decimal(str(coverage))).to_integral_value(rounding=ROUND_CEILING))
    return max(1,count) if quantity>0 else 0


def calculate_allowance(field, products):
    required={'board','screw_large','screw_small','bedding','setting','grout','tape'}
    if set(products)!=required:raise ValueError('Every floor sundries product is required')
    for product in products.values():
        if not product.get('source_url') or not product.get('observed_date'):
            raise ValueError('Dated product sources required')
        for key in ('coverage','price'):
            value=product[key]
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
                raise ValueError('Positive finite package coverage and price required')
    board=products['board'];width,height=board['dimensions_ft']
    if not math.isclose(width*height,board['coverage']):raise ValueError('Board dimensions differ from package coverage')
    options=[]
    for w,h in [(width,height),(height,width)]:
        for i in range(4):
            layout=calculate(field,w,h,w*i/4)
            allowance=material_allowance(layout)
            options.append((allowance['candidate_sheets'],layout['unique_seam_lf'],layout,allowance))
    _,_,layout,allowance=min(options,key=lambda x:x[:2])
    screws=allowance['fastener_allowance'];big=products['screw_large'];small=products['screw_small']
    if any(type(p['coverage']) is not int for p in [big,small]):raise ValueError('Screw packs require whole counts')
    mixes=[]
    for n in range(math.ceil(screws/big['coverage'])+1):
        m=max(0,math.ceil((screws-n*big['coverage'])/small['coverage']))
        mixes.append((n*Decimal(str(big['price']))+m*Decimal(str(small['price'])),n,m))
    _,n,m=min(mixes)
    quantities={'board':allowance['candidate_sheets'],'screw_large':n,'screw_small':m,
        'bedding':coverage_packages(field.area,products['bedding']['coverage']),
        'setting':coverage_packages(field.area,products['setting']['coverage']),
        'grout':coverage_packages(field.area,products['grout']['coverage']),
        'tape':coverage_packages(layout['unique_seam_lf'],products['tape']['coverage'])}
    rows=[{'component':key,'quantity':quantity,'product':dict(products[key]),
        'extended_cost':float(Decimal(str(products[key]['price']))*quantity)} for key,quantity in quantities.items()]
    return {'installed_area_sf':field.area,'components':rows,
        'partial_pretax_cost':float(sum(Decimal(str(r['extended_cost'])) for r in rows)),
        'layout':layout,'material_allowance':allowance,'order_released':False,
        'complete_sundries_scope':False,
        'remaining':['Back-troweling consumption','Movement-joint sealant and transition ownership',
            'Installation gaps, narrow cuts, subfloor seam offsets and floor suitability'],
        'tax_delivery_markup_included':False}


def calculate_pooled_allowance(fields, products):
    """Combine separate installation fields sharing this exact product set.

    Board layouts stay per room; no transfer of cut remnants between rooms is
    assumed. Loose screws, mortar, grout and tape are pooled before pack rounding.
    """
    ids=[f['id'] for f in fields]
    if not ids or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i for i in ids):
        raise ValueError('Pooled floor fields need unique nonempty identities')
    rooms=[{'id':f['id'],'calculation':calculate_allowance(f['geometry'],products)} for f in fields]
    area=math.fsum(r['calculation']['installed_area_sf'] for r in rooms)
    seam=math.fsum(r['calculation']['layout']['unique_seam_lf'] for r in rooms)
    screws=sum(r['calculation']['material_allowance']['fastener_allowance'] for r in rooms)
    boards=sum(r['calculation']['material_allowance']['candidate_sheets'] for r in rooms)
    big=products['screw_large'];small=products['screw_small'];mixes=[]
    for n in range(math.ceil(screws/big['coverage'])+1):
        m=max(0,math.ceil((screws-n*big['coverage'])/small['coverage']))
        mixes.append((n*Decimal(str(big['price']))+m*Decimal(str(small['price'])),n,m))
    _,n,m=min(mixes)
    quantities={'board':boards,'screw_large':n,'screw_small':m,
        'bedding':coverage_packages(area,products['bedding']['coverage']),
        'setting':coverage_packages(area,products['setting']['coverage']),
        'grout':coverage_packages(area,products['grout']['coverage']),
        'tape':coverage_packages(seam,products['tape']['coverage'])}
    rows=[{'component':key,'quantity':quantity,'product':dict(products[key]),
           'extended_cost':float(Decimal(str(products[key]['price']))*quantity)} for key,quantity in quantities.items()]
    # Per-room prices are comparison evidence, never extra cost lines in the order.
    separate=sum(Decimal(str(r['calculation']['partial_pretax_cost'])) for r in rooms)
    pooled=sum(Decimal(str(r['extended_cost'])) for r in rows)
    return {'fields':rooms,'installed_area_sf':area,'components':rows,
        'pooled_fastener_allowance':screws,'pooled_seam_lf':seam,'partial_pretax_cost':float(pooled),
        'separate_room_purchase_comparison_cost':float(separate),
        'difference_from_separate_room_purchases':float(separate-pooled),
        'pricing_basis':'Use pooled component costs once; per-room calculations are comparison evidence only.',
        'board_offcut_reuse_between_rooms_assumed':False,'order_released':False,
        'complete_sundries_scope':False,'tax_delivery_markup_included':False,
        'remaining':['Confirm every field uses the same product set; separate differing products and colors.',
            'Do not split a continuous installation field into arbitrary rooms for board layout.',
            *rooms[0]['calculation']['remaining']]}
