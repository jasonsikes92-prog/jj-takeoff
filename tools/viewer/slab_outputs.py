"""Version-bound physical quantities and template outputs for the slab trial."""
import csv
import hashlib
import io
import json
import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from slab_geometry import area, concrete_volume, grade_beam_volume, rebar_grid, roll_layout
from slab_materials import whole_units, substrate_coverage, plastic_layout, material_allowances


def profile_hash(profile):
    return hashlib.sha256(json.dumps(profile,sort_keys=True,allow_nan=False).encode()).hexdigest()


def material_notes(profile):
    specs=profile.get('material_specs',{})
    notes=list(profile.get('scope_notes',[]))
    labor=profile.get('slab_labor')
    if labor is not None:
        budget=labor.get('bobcat_budget_usd')
        if type(budget) not in (int,float) or not math.isfinite(budget) or budget<0:
            raise ValueError('Bobcat budget must be a finite nonnegative dollar amount')
        if labor.get('bulk_grading_by')!='separate_grader' or labor.get('included_scopes')!=['touch-up grading','steel placement','finishing','saw cuts']:
            raise ValueError('Record the confirmed grader and concrete labor scopes separately')
        pending='Labor billing basis/rate remains pending' if profile.get('pump') else 'Labor billing basis/rate and pumping charges remain pending'
        if labor.get('billing_basis')=='measured_net_sf':
            rate=profile.get('prices',{}).get(labor['estimate_item_id'],{}).get('unit_price')
            pending='Labor uses measured net slab square feet, without material waste or whole-unit rounding'
            if rate is not None:pending+=f'; recorded rate ${rate:,.2f}/SF'
        notes.append(f"Concrete labor includes touch-up grading, steel placement, finishing and saw cuts, confirmed by Jason. Bulk grading is priced separately under the grader. Bobcat use is a separate approximate ${budget:,.2f} budget allowance, counted once. {pending}; purchased materials retain their separate rows.")
    if profile.get('pump'):
        pump=profile['pump'];rate=profile.get('prices',{}).get(pump['estimate_item_id'],{}).get('unit_price')
        notes.append(f"Pump: one slab mobilization plus {pump['separate_footer_mobilizations']} separate footing mobilization(s) in this package. "+(f"Jason's rate is ${rate:,.2f} per mobilization. " if rate is not None else '')+'An additional footing pour adds a separate mobilization; separately estimated house/wall footings are not charged again inside the garage slab.')
    mix=profile.get('concrete_mix')
    if mix is not None:
        if any(type(mix.get(k)) not in (int,float) or not math.isfinite(mix[k]) or mix[k]<=0 for k in ('strength_psi','target_slump_inches')):
            raise ValueError('Concrete strength and target slump must be positive numbers')
        if mix.get('grade')!='interior' or mix.get('finish')!='smooth_trowel':raise ValueError('Record the confirmed interior concrete grade and smooth trowel finish')
        notes.append(f"Concrete confirmed by Jason: {mix['strength_psi']:g} PSI, interior grade, {mix['target_slump_inches']:g}-inch target slump, smooth trowel finish. Slump is not slab thickness. Air content and mix submittal remain supplier/project checks.")
    joints=profile.get('saw_cut_preferences')
    if joints is not None:
        values=[joints.get(k) for k in ('spacing_min_ft','spacing_max_ft')]
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values) or values[0]>values[1] or type(joints.get('symmetrical')) is not bool:
            raise ValueError('Saw-cut preferences need ordered positive spacing and a symmetry decision')
        notes.append(f"Saw-cut joints: Jason prefers {values[0]:g}-{values[1]:g} feet depending on garage size, with "+('symmetrical cuts' if joints['symmetrical'] else 'layout set by project conditions')+'. This is a layout preference; final cut paths, corners, depth and reinforcement continuity require review.')
    edge_methods=specs.get('deep_edge_support',{})
    if not isinstance(edge_methods,dict) or set(edge_methods)-{'mesh','grid'} or any(
        method not in (('mesh_spans_slope','chairs') if name=='mesh' else ('chairs',)) for name,method in edge_methods.items()):
        raise ValueError('Record mesh span and grid chair decisions separately')
    if edge_methods.get('mesh')=='mesh_spans_slope':
        notes.append('Mesh itself spans the slope, confirmed by Jason. Flat-slab mesh chairs remain included; no extra tall mesh chairs or tie-wire quantity is inferred from this answer. Placement and elevation remain unverified.')
    height=specs.get('grid_edge_chair_height_inches')
    if height is not None:
        if type(height) not in (int,float) or not math.isfinite(height) or height<=0 or edge_methods.get('grid')!='chairs':
            raise ValueError('A positive edge chair height requires grid chair support')
        notes.append(f'Jason confirmed {height:g}-inch rebar chairs beneath the grid over the sloped edges. The height answer does not change the flat-slab chair product. Support bearing and final steel elevation remain unverified.')
    elif edge_methods.get('grid')=='chairs':notes.append('The rebar grid uses rebar chairs, confirmed by Jason. Deep-edge chair height/type remains separate from the standard flat-slab chair allowance.')
    lap_rule=specs.get('rebar_lap_rule')
    if lap_rule:
        if lap_rule!='irc2024_no4_grade60' or specs.get('rebar_grade')!=60 or specs.get('footer_rebar_size','#4')!='#4':
            raise ValueError('The recorded lap rule requires #4 Grade 60 steel; other steel needs a sourced rule')
        for key,included in [('rebar_grid_lap_inches',specs.get('rebar_grid_included')),('footer_rebar_lap_inches',specs.get('footer_rebar_runs'))]:
            if not included:continue
            lap=specs.get(key)
            if type(lap) not in (int,float) or not math.isfinite(lap) or lap<30:
                raise ValueError('Active #4 Grade 60 rebar laps must be at least 30 inches under the recorded IRC rule')
        notes.append('Rebar lap specification: #4 Grade 60 steel, minimum 30-inch laps per 2024 IRC Table R608.5.4(1). This supersedes the earlier 6-inch rebar input. Confirm steel grade, governing permit requirements and structural applicability before release.')
        if specs.get('footer_end_connection'):
            if specs['footer_end_connection']!='lap_to_projecting_wall_rebar':raise ValueError('Unknown footer wall connection')
            notes.append(f"Footer bars lap onto projecting wall rebar, confirmed by Jason. The estimating specification requires {specs['footer_rebar_lap_inches']:g}-inch contact laps at those connections; available projection and anchorage within the existing wall are unverified. Projecting bars remain in the separate wall scope.")
        elif specs.get('footer_rebar_runs'):
            notes.append(f"Footer laps: {specs['footer_rebar_lap_inches']:g} inches. Corner continuity, bar offsets and end anchorage still need a project detail; a 6-inch hook tail is not a lap splice.")
    for key in ('vapor_lap_inches','mesh_lap_inches'):
        if key in specs and (type(specs[key]) not in (int,float) or not math.isfinite(specs[key]) or specs[key]<=0):
            raise ValueError('Plastic and mesh overlaps must be positive inches')
    if 'gravel_depth_inches' in specs:
        depth=specs['gravel_depth_inches']
        if type(depth) not in (int,float) or not math.isfinite(depth) or depth<=0:
            raise ValueError('Gravel depth must be a positive number of inches')
        detail=('Plastic and gravel follow the haunch to its junction with the footer; gravel thickness is perpendicular to the slope. Compaction and delivered conversion remain unresolved.' if specs.get('substrate_extent')=='footer_haunch_junction' else 'Coverage, compaction and delivered quantity remain unresolved.')
        if profile.get('gravel_delivery'):detail='Plastic and gravel follow the haunch to its junction with the footer; gravel thickness is perpendicular to the slope. Full-truck conversion is recorded below; quarry density and placement remain estimating assumptions.'
        notes.append(f'Gravel: {depth:g} inches thick, confirmed by Jason. '+detail)
    if 'vapor_barrier_mil' in specs:
        thickness=specs['vapor_barrier_mil']
        if type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0:
            raise ValueError('Vapor-barrier thickness must be a positive number of mils')
        roll=specs.get('vapor_roll_coverage_sf')
        if roll is not None and (type(roll) not in (int,float) or not math.isfinite(roll) or roll<=0):
            raise ValueError('Plastic roll coverage must be positive square feet')
        detail=f'{roll:g} SF per roll; laps remain unresolved.' if roll is not None else 'Roll size and laps remain unresolved.'
        if roll is not None and 'vapor_lap_inches' in specs:
            detail=f"{roll:g} SF per roll; {specs['vapor_lap_inches']:g}-inch overlaps confirmed by Jason."
        if specs.get('vapor_product_name'):detail=specs['vapor_product_name']+'. '+detail
        notes.append(f'Vapor barrier: {thickness:g} mil plastic ({thickness*0.0254:g} mm), confirmed by Jason. '+detail)
    elif specs.get('vapor_barrier_reported'):
        notes.append('Vapor barrier reported as '+specs['vapor_barrier_reported']+'. Confirm 6 mil (0.1524 mm) versus 6 millimeters before selecting the material.')
    if specs.get('welded_wire_mesh'):
        detail=('Cutting layout and laps remain unresolved.' if specs.get('mesh_product_confirmed') is True
                else 'Wire gauge, roll dimensions and laps remain unresolved.')
        if 'mesh_lap_inches' in specs:
            detail=(f"{specs['mesh_lap_inches']:g}-inch sheet-edge overlap used for the provisional roll calculation. "
                'This is not a verified code splice. Confirm reinforcement purpose, applicable splice requirement '
                'and cross-wire end overhangs before finalizing the overlap and purchasing mesh.')
        notes.append('Reinforcement: '+specs['welded_wire_mesh']+', confirmed by Jason. '+detail)
    if 'rebar_grid_included' in specs:
        included=specs['rebar_grid_included']
        if included is not None and type(included) is not bool:
            raise ValueError('The rebar-grid decision must be yes, no or unresolved')
        if included is True:
            spacing=specs.get('rebar_grid_spacing_inches')
            if spacing is not None:
                if not isinstance(spacing,list) or len(spacing)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in spacing):
                    raise ValueError('Grid spacing needs two positive inch dimensions')
                detail='Edge clearances and laps remain unresolved.'
                if 'rebar_grid_setback_inches' in specs and 'rebar_grid_lap_inches' in specs:
                    setback=specs['rebar_grid_setback_inches'];lap=specs['rebar_grid_lap_inches']
                    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (setback,lap)):
                        raise ValueError('Grid setback and lap must be positive inches')
                    detail=f'Jason specified {setback:g}-inch edge setback and {lap:g}-inch bar overlap for estimating.'
                    if lap_rule:detail=f'Jason specified {setback:g}-inch edge setback; the revised #4 Grade 60 specification uses {lap:g}-inch laps.'
                notes.append(f'Additional #4 rebar grid included at {spacing[0]:g} by {spacing[1]:g} inches on center. '+detail)
            else:
                notes.append('Additional #4 rebar grid included for this slab. Grid spacing, edge clearances and laps must be resolved before calculating bars.')
        elif included is False:
            notes.append('Additional #4 rebar grid excluded by the recorded project decision; welded wire mesh remains included.')
        else:
            notes.append('Additional #4 rebar grid: project decision required. Backfill prompts review and does not automatically add the grid.')
    return notes


def validate_profile(config, profile):
    if profile['schema']!='jnj.slab-construction.v1' or profile['plan_sha256']!=config['plan_sha256']:
        raise ValueError('Construction rules belong to a different drawing')
    if profile['outline'] not in ('red','blue'):
        raise ValueError('Construction rules need a known measurement')
    if len(profile['reference_points'])!=len(profile['edge_roles']) or any(r not in ('bearing','thickened') for r in profile['edge_roles']):
        raise ValueError('Classify each slab edge before calculating concrete')
    ids={line['estimate_item_id'] for line in config['assembly']['lines']}
    if profile['concrete_item_id'] not in ids:
        raise ValueError('Concrete must link to an existing template row')
    roll_ids=profile.get('roll_item_ids',{})
    if set(roll_ids)-{'plastic','mesh'} or len(set(roll_ids.values()))!=len(roll_ids):
        raise ValueError('Plastic and mesh need separate known row mappings')
    for item_id in roll_ids.values():
        if item_id not in ids or item_id==profile['concrete_item_id']:
            raise ValueError('Roll quantities must link to separate existing template rows')
        if next(r for r in config['assembly']['lines'] if r['estimate_item_id']==item_id)['unit'] not in ('each','roll'):
            raise ValueError('Roll quantity requires a roll or each template unit')
    purchase_ids=profile.get('purchase_item_ids',{})
    if set(purchase_ids)-{'gravel','mesh_chairs'}:raise ValueError('Unknown purchase row mapping')
    mapped=[profile['concrete_item_id'],*roll_ids.values(),*purchase_ids.values()]
    if len(mapped)!=len(set(mapped)):raise ValueError('Each purchase scope needs a separate template row')
    if profile.get('pump'):
        pump=profile['pump'];matches=[r for r in config['assembly']['lines'] if r['estimate_item_id']==pump.get('estimate_item_id')]
        if len(matches)!=1 or pump['estimate_item_id'] in mapped or pump['estimate_item_id']==profile.get('slab_labor',{}).get('estimate_item_id'):
            raise ValueError('Pump needs a separate existing template row')
        if type(pump.get('separate_footer_mobilizations')) is not int or pump['separate_footer_mobilizations'] not in (0,1):raise ValueError('Record zero or one separate footing pump mobilization')
    if set(profile.get('scope_prices',{}))-{'grid','grid_chairs','grid_edge_chairs','footer_rebar','footer_chairs'}:raise ValueError('Unknown material pricing scope')
    if profile.get('slab_labor') is not None:
        labor_id=profile['slab_labor'].get('estimate_item_id')
        matches=[r for r in config['assembly']['lines'] if r['estimate_item_id']==labor_id]
        if len(matches)!=1 or matches[0].get('type')!='LABOR' or labor_id in mapped:
            raise ValueError('Slab labor must map to one separate existing labor row')
        basis=profile['slab_labor'].get('billing_basis')
        if basis not in (None,'measured_net_sf') or (basis=='measured_net_sf' and matches[0]['unit']!='sq ft'):
            raise ValueError('Slab labor billing basis requires a square-foot template row')
    for item_id in purchase_ids.values():
        if item_id not in ids or next(r for r in config['assembly']['lines'] if r['estimate_item_id']==item_id).get('type')!='MATERIAL':
            raise ValueError('Purchase scope must map to an existing material row')
    if profile.get('purchase_rounding') not in (None,'whole_units'):raise ValueError('Unknown purchase rounding rule')
    for rule in profile.get('support_rules',{}).values():
        if type(rule.get('pack_size')) is not int or rule['pack_size']<=0:raise ValueError('Chair package size must be a positive integer')
        if 'spacing_inches' in rule and (type(rule['spacing_inches']) not in (int,float) or not math.isfinite(rule['spacing_inches']) or rule['spacing_inches']<=0):raise ValueError('Chair spacing must be positive inches')
    if 'footer_rebar_runs' in profile.get('material_specs',{}) and (type(profile['material_specs']['footer_rebar_runs']) is not int or profile['material_specs']['footer_rebar_runs']<=0):raise ValueError('Footer rebar run count must be positive')
    date.fromisoformat(profile['pricing_as_of'])
    material_notes(profile)


def apply_price(row, price, as_of, markup_unit='PERCENT', bulk_quantity=None):
    owner_rate=price.get('validity_policy')=='owner_rate_until_changed'
    if owner_rate:
        if price.get('evidence_kind')!='jason_approved_rate' or 'valid_through' in price:
            raise ValueError('Standing owner rates cannot replace supplier quote expirations')
        date_valid=price.get('active') is True and date.fromisoformat(price['date'])<=date.fromisoformat(as_of)
    else:
        date_valid=date.fromisoformat(price['date'])<=date.fromisoformat(as_of)<=date.fromisoformat(price['valid_through'])
    valid=(price.get('source') and price.get('unit')==row['unit'] and price.get('currency')=='USD' and date_valid)
    rate=Decimal(str(price['unit_price']))
    if not rate.is_finite() or rate<0:raise ValueError('Invalid current unit price')
    if 'bulk_minimum' in price:
        minimum=price['bulk_minimum'];bulk=Decimal(str(price['bulk_unit_price']))
        if type(minimum) is not int or minimum<=0 or not bulk.is_finite() or bulk<0:raise ValueError('Invalid bulk price threshold or rate')
        if bulk_quantity is not None and bulk_quantity>=minimum:rate=bulk
    if not valid:
        row['price_status']='owner rate inactive, future-dated or unit-mismatched' if owner_rate else 'price evidence expired, future-dated or unit-mismatched';return
    row.update(unit_price=float(rate),price_status=price.get('basis','dated evidence attached'),price_source=price['source'])
    if row['quantity'] is not None:
        cost=(Decimal(str(row['quantity']))*rate).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        row['cost']=float(cost)
        if row['markup_percent'] is not None:
            if markup_unit!='PERCENT':raise ValueError('Unsupported template markup type')
            row['sell_amount']=float((cost*(1+Decimal(str(row['markup_percent']))/100)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def template_rows(config, profile, quantity, roll_counts=None, purchases=None, labor_sf=None):
    rows=[]
    for source in config['assembly']['lines']:
        concrete=source['estimate_item_id']==profile['concrete_item_id']
        qty=round(quantity,9) if concrete and quantity is not None else None
        roll_qty=(roll_counts or {}).get(source['estimate_item_id'])
        if roll_qty is not None:qty=roll_qty
        row={'estimate_item_id':source['estimate_item_id'],'name':source['name'],
             'unit':'CY' if concrete else source['unit'],'template_unit':source['unit'],
             'quantity':qty,'unit_price':None,'cost':None,'sell_amount':None,
             'markup_percent':float(source.get('markup_value',0)),
             'price_status':'current dated price required',
             'quantity_status':'calculated allowance including concrete waste' if qty is not None else 'scope or conversion needs confirmation'}
        if roll_qty is not None:row.update(unit='roll',quantity_status='whole-roll cutting allowance for planar footprint; includes seam overlaps and trim')
        purchase=(purchases or {}).get(row['estimate_item_id'])
        if purchase:
            row.update({k:purchase[k] for k in ('quantity','unit','measured_quantity','measured_unit','quantity_status')})
            qty=row['quantity']
            if row['estimate_item_id']==profile.get('purchase_item_ids',{}).get('gravel') and profile.get('gravel_delivery'):row['name']='#57 stone - full truckloads'
        if row['estimate_item_id']==profile.get('pump',{}).get('estimate_item_id'):
            row.update(quantity=1+profile['pump']['separate_footer_mobilizations'],unit='mobilization',
                quantity_status='one slab pour plus recorded separate footing pour; no historical hourly conversion')
        if concrete and profile.get('concrete_mix'):
            mix=profile['concrete_mix']
            row['name']+=f"; {mix['strength_psi']:g} PSI interior grade, {mix['target_slump_inches']:g}-inch slump"
            row['quantity_status']+='; smooth trowel finish specified'
            if profile.get('saw_cut_preferences'):
                joints=profile['saw_cut_preferences']
                row['quantity_status']+=f"; saw-cut preference {joints['spacing_min_ft']:g}-{joints['spacing_max_ft']:g} feet; final joint layout pending"
        if source['estimate_item_id']==profile.get('slab_labor',{}).get('estimate_item_id'):
            row['name']+='; touch-up grading, steel placement, finishing and saw cuts included'
            row['quantity_status']='billing basis required; bulk grading and separate Bobcat allowance excluded'
            if profile['slab_labor'].get('billing_basis')=='measured_net_sf':
                row.update(quantity=labor_sf,quantity_status=('measured net slab area; no waste, historical multiplier or whole-unit rounding; bulk grading and Bobcat excluded' if labor_sf is not None else 'slab area withheld until boundary construction labels are valid'))
        price=profile.get('prices',{}).get(row['estimate_item_id'])
        if price:
            apply_price(row,price,profile['pricing_as_of'],source.get('markup_unit','PERCENT'))
        rows.append(row)
    return rows


def apply_estimate_policy(rows, profile):
    policy=profile['pricing_policy'];tax=policy['retail_tax'];delivery=policy['delivery']
    for value in (policy['material_markup_percent'],policy['labor_markup_percent'],tax['percent'],delivery['cost']):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('Markup, purchase tax and delivery need finite nonnegative values')
    if not policy.get('source') or not tax.get('source') or not delivery.get('source'):
        raise ValueError('Markup, purchase tax and delivery need recorded sources')
    if not date.fromisoformat(tax['effective_from'])<=date.fromisoformat(profile['pricing_as_of'])<=date.fromisoformat(tax['effective_through']):
        raise ValueError('Purchase tax source is not effective for the pricing date')
    money=lambda v:float(Decimal(str(v)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    rows.append({'name':'Home Depot delivery','scope':'retail_delivery','estimate_item_id':None,'quantity':1,'unit':'delivery',
        'unit_price':delivery['cost'],'cost':delivery['cost'],'sell_amount':None,'markup_percent':None,
        'quantity_status':'one combined material delivery for this garage','price_status':'Jason-provided delivery allowance',
        'price_source':delivery['source']})
    mapped=[]
    for row in rows:
        key=row['estimate_item_id'] or row.get('scope');mapping=policy['row_mapping'].get(key)
        if not mapping or not mapping.get('row_id'):raise ValueError('Each priced scope needs a distinct target template row')
        row.update(template_row_id=mapping['row_id'],template_row_origin=mapping['origin'],cost_code='04.15')
        mapped.append(row['template_row_id'])
        labor=key==profile['slab_labor']['estimate_item_id'] or key=='bobcat_use'
        row['markup_percent']=policy['labor_markup_percent'] if labor else policy['material_markup_percent']
        row['supplier_cost']=row['cost'];row['purchase_tax']=None if row['cost'] is None else 0
        price=profile.get('prices',{}).get(key,profile.get('scope_prices',{}).get(key,{}))
        retail=row.get('price_source','').startswith('https://www.homedepot.com/') or key=='retail_delivery'
        if retail and row['cost'] is not None and price.get('tax_included') is not True:
            row['purchase_tax']=money(Decimal(str(row['cost']))*Decimal(str(tax['percent']))/100)
            row['cost']=money(Decimal(str(row['cost']))+Decimal(str(row['purchase_tax'])))
            row['price_status']=row['price_status'].replace('tax/delivery excluded','delivery priced separately')+f"; estimated {tax['percent']:g}% purchase tax included in cost"
        multiplier=1+Decimal(str(row['markup_percent']))/100
        if row['cost'] is not None:row['sell_amount']=money(Decimal(str(row['cost']))*multiplier)
        if row.get('budget_cost') is not None:
            row['budget_sell_amount']=money(Decimal(str(row['budget_cost']))*multiplier)
            row['price_status']=f"Jason-provided equipment budget; {row['markup_percent']:g}% concrete subcontractor markup; quote confirmation pending"
    if len(mapped)!=len(set(mapped)):raise ValueError('Target template rows cannot be shared by separate scopes')


def calculate_outputs(config, points, profile):
    validate_profile(config,profile)
    result={'status':'more information required','verification_valid':False,'calculation_valid':False,
            'current_total':None,'priced_subtotal':None,'missing_information':profile['required_information']}
    reference=profile['reference_points']
    try:
        if len(points)!=len(reference):raise ValueError('Corner count changed; review the edge construction labels')
        for i,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
            ra,rb=reference[i],reference[(i+1)%len(reference)]
            axis=0 if ra[0]!=rb[0] else 1
            if abs(a[1-axis]-b[1-axis])>1e-7 or (b[axis]-a[axis])*(rb[axis]-ra[axis])<=0:
                raise ValueError('Edge direction changed; review the edge construction labels')
        ppf=config['scale']['ppf']; feet=[[x/ppf,y/ppf] for x,y in points]
        section=profile['exterior']; beam=profile['interior_grade_beam']
        concrete=concrete_volume(feet,[i for i,r in enumerate(profile['edge_roles']) if r=='thickened'],
            profile['slab_inches'],section['total_depth_inches'],section['bottom_width_inches'],
            section['vertical_inches_above_bottom'],section['angle_degrees'],profile['waste_percent'])
        gb=grade_beam_volume(beam['eligible_wall_lf'],profile['slab_inches'],beam['total_depth_inches'],
                            beam['bottom_width_inches'],profile['waste_percent'],beam['angle_degrees'])
        # This bounded garage trial has no interior walls; overlapping beam runs need geometry first.
        if beam['eligible_wall_lf']!=0:raise ValueError('Interior beam runs need measured intersection and edge-overlap checks')
        result.update(calculation_valid=True,concrete=concrete,grade_beam=gb,
                      thickened_edge_lf=sum(math.dist(feet[i],feet[(i+1)%len(feet)]) for i,r in enumerate(profile['edge_roles']) if r=='thickened'),
                      bearing_edge_lf=sum(math.dist(feet[i],feet[(i+1)%len(feet)]) for i,r in enumerate(profile['edge_roles']) if r=='bearing'))
    except ValueError as error:
        result['reason']=str(error)
    roll_counts={};specs=profile.get('material_specs',{})
    if result['calculation_valid'] and specs.get('substrate_extent'):
        try:result['substrate_coverage']=substrate_coverage(feet,profile,result['concrete'])
        except ValueError as error:result['substrate_error']=str(error)
    if result['calculation_valid']:
        for name,product_key,lap_key in [('plastic','vapor_product','vapor_lap_inches'),('mesh','mesh_product','mesh_lap_inches')]:
            if lap_key not in specs:continue
            product=specs.get(product_key,{})
            try:
                if name=='plastic' and specs.get('substrate_extent'):
                    if 'substrate_error' in result:raise ValueError(result['substrate_error'])
                    layout=plastic_layout(result['substrate_coverage'],specs,result['concrete'])
                else:layout=roll_layout(feet,product.get('width_ft'),product.get('length_ft'),specs[lap_key])
                result.setdefault('roll_layouts',{})[name]=layout
                item_id=profile.get('roll_item_ids',{}).get(name)
                if item_id:roll_counts[item_id]=layout['roll_count']
            except ValueError as error:result.setdefault('roll_layout_errors',{})[name]=str(error)
    labor_sf=area(points)/(config['scale']['ppf']**2) if result['calculation_valid'] else None
    result['estimate_rows']=template_rows(config,profile,result['concrete']['with_waste_cy'] if result['calculation_valid'] else None,roll_counts,labor_sf=labor_sf)
    if profile.get('material_specs',{}).get('rebar_grid_included') is True:
        specs=profile['material_specs'];grid=None
        keys=('rebar_grid_spacing_inches','rebar_grid_setback_inches','rebar_grid_lap_inches','rebar_stock_length_ft')
        if result['calculation_valid'] and all(k in specs for k in keys):
            try:
                grid=rebar_grid(feet,*(specs[k] for k in keys));result['rebar_grid']=grid
            except ValueError as error:result['rebar_grid_reason']=str(error)
        result['estimate_rows'].append({'estimate_item_id':None,'name':'Additional #4 rebar grid','unit':'LF',
            'quantity':None,'unit_price':None,'markup_percent':None,'cost':None,'sell_amount':None,
            'quantity_status':('included scope; clearances, laps and template row mapping required' if profile['material_specs'].get('rebar_grid_spacing_inches')
                               else 'included scope; grid spacing, clearances, laps and template row mapping required'),
            'price_status':'current dated price required'})
        if profile.get('pricing_policy'):result['estimate_rows'][-1]['scope']='grid'
        if grid:result['estimate_rows'][-1].update(quantity=round(grid['cut_lf'],9),
            quantity_status='calculated cut length including laps; separate template mapping and reinforcement review required')
        elif 'rebar_grid_setback_inches' in specs:result['estimate_rows'][-1]['quantity_status']=result.get('rebar_grid_reason','grid layout or stock length still required')
    if profile.get('purchase_rounding')=='whole_units' and result['calculation_valid']:
        purchases,chairs=material_allowances(feet,profile,result)
        result.update(purchase_materials=purchases,chair_allowances=chairs)
        mapped={profile['concrete_item_id']:purchases['concrete']}
        for name,item_id in {**profile.get('roll_item_ids',{}),**profile.get('purchase_item_ids',{})}.items():
            if name in purchases:mapped[item_id]=purchases[name]
        rows=template_rows(config,profile,result['concrete']['with_waste_cy'],roll_counts,mapped,labor_sf)
        linked=set(profile.get('roll_item_ids',{}))|set(profile.get('purchase_item_ids',{}))|{'concrete'}
        for name,purchase in purchases.items():
            if name in linked:continue
            rows.append(dict(purchase,estimate_item_id=None,unit_price=None,cost=None,sell_amount=None,markup_percent=None,price_status='current dated price and template mapping required'))
            if profile.get('pricing_policy'):rows[-1]['scope']=name
            price=profile.get('scope_prices',{}).get(name)
            if price:
                rebar_quantities=[purchases.get(k,{}).get('quantity',0) for k in ('grid','footer_rebar')]
                bulk_quantity=sum(rebar_quantities) if name in ('grid','footer_rebar') and None not in rebar_quantities else None
                apply_price(rows[-1],price,profile['pricing_as_of'],bulk_quantity=bulk_quantity)
        for name,chair in chairs.items():
            if chair.get('special_height_count') and 'edge_packs' not in chair:
                rows.append({'name':name.capitalize()+' supports at thickened edges','quantity':None,'unit':'box',
                    'measured_quantity':chair['special_height_count'],'measured_unit':'each','estimate_item_id':None,
                    'unit_price':None,'cost':None,'sell_amount':None,'markup_percent':None,
                    'quantity_status':(f"{chair['edge_chair_height_inches']:g}-inch chairs confirmed; product, packaging and placement pending" if 'edge_chair_height_inches' in chair else 'support positions counted; compatible height, type and packaging required'),
                    'price_status':'current dated price and template mapping required'})
        result['estimate_rows']=rows
    if profile.get('slab_labor') is not None:
        result['estimate_rows'].append({'name':'Bobcat use for concrete touch-up (budget allowance)','scope':'bobcat_use',
            'estimate_item_id':None,'quantity':1,'unit':'allowance','unit_price':None,'cost':None,'sell_amount':None,
            'markup_percent':None,'budget_cost':profile['slab_labor']['bobcat_budget_usd'],
            'quantity_status':'one allowance for this garage; separate from included touch-up labor and bulk grading',
            'price_status':'approximate amount reported by Jason; current quote and template mapping pending'})
    if profile.get('pricing_policy'):apply_estimate_policy(result['estimate_rows'],profile)
    known=[r['sell_amount'] for r in result['estimate_rows'] if r['sell_amount'] is not None]
    if known:result['priced_subtotal']=float(sum(Decimal(str(v)) for v in known))
    if len(known)==len(result['estimate_rows']):result['current_total']=result['priced_subtotal']
    if profile.get('material_specs') or profile.get('concrete_mix') or profile.get('saw_cut_preferences') or profile.get('slab_labor') or profile.get('pump'):result['material_notes']=material_notes(profile)
    if profile.get('pricing_notes'):
        result['priced_cost_subtotal']=float(sum(Decimal(str(r['cost'])) for r in result['estimate_rows'] if r['cost'] is not None))
        result['material_notes'].extend(profile['pricing_notes'])
        labor_costed=any(r['estimate_item_id']==profile.get('slab_labor',{}).get('estimate_item_id') and r['estimate_item_id'] is not None and r['cost'] is not None for r in result['estimate_rows'])
        excluded='Tax and any unlisted delivery fees' if labor_costed else 'Slab labor, tax and any unlisted delivery fees'
        exclusions_note=profile.get('pricing_exclusions_note',f'{excluded} are not included in this subtotal.')
        result['material_notes'].append(f"Costed lines subtotal: ${result['priced_cost_subtotal']:,.2f}, plus the separate Bobcat budget. {exclusions_note}")
    if profile.get('pricing_policy'):
        rows=result['estimate_rows'];amounts=[r.get('budget_sell_amount',r['sell_amount']) for r in rows]
        result['budget_sell_total']=None if None in amounts else float(sum(Decimal(str(v)) for v in amounts))
        result['budget_cost_total']=None if any(r['cost'] is None and r.get('budget_cost') is None for r in rows) else float(sum(Decimal(str(r['cost'] if r['cost'] is not None else r['budget_cost'])) for r in rows))
        result['purchase_tax_total']=float(sum(Decimal(str(r['purchase_tax'])) for r in rows if r['purchase_tax'] is not None))
        if result['budget_sell_total'] is not None:
            result['material_notes'].append(f"Working garage budget: ${result['budget_cost_total']:,.2f} cost; ${result['budget_sell_total']:,.2f} with the approved markup and Bobcat allowance. Estimated Home Depot purchase tax: ${result['purchase_tax_total']:,.2f}. Project verification remains open.")
    for name,layout in result.get('roll_layouts',{}).items():
        if name=='plastic' and specs.get('substrate_extent'):
            result['material_notes'].append(f"Plastic: {layout['roll_count']} whole box(es); {layout['net_coverage_sf']:.2f} SF surface through the haunch. {layout['strip_count']} conservative strips, {layout['cut_length_ft']:.2f} feet long, including 6-inch seams and trim. Stops at the footer/haunch junction.")
        else:
            result['material_notes'].append(f"{name.capitalize()} planar allowance: {layout['roll_count']} roll(s); {layout['strip_count']} strips cut {layout['cut_length_ft']:.2f} feet long with {layout['lap_inches']:g}-inch seams. Turn-downs and vertical surfaces are separate pending scope.")
    for name,reason in result.get('roll_layout_errors',{}).items():
        result['material_notes'].append(name.capitalize()+' quantity withheld: '+reason)
    if result.get('rebar_grid'):
        g=result['rebar_grid']
        result['material_notes'].append(f"Grid allowance: {g['net_lf']:.2f} LF net + {g['lap_lf']:.2f} LF laps = {g['cut_lf']:.2f} LF cut length; {g['stock_count']} x {g['stock_length_ft']:g}-foot sticks with offcut reuse. Stock length from the saved template; estimating layout requires reinforcement review.")
    if result.get('purchase_materials'):
        result.setdefault('material_notes',[])
        c=result['purchase_materials']['concrete']
        result['material_notes'].append(f"Concrete: {c['measured_quantity']:.2f} CY including waste rounds up to {c['quantity']} whole CY. All material allowances use whole purchase units; measurements remain unrounded.")
        if result.get('substrate_coverage'):
            coverage=result['substrate_coverage'];gravel=result['purchase_materials'].get('gravel')
            result['material_notes'].append(f"Plastic/gravel surface: {coverage['flat']['net_sf']:.2f} SF flat + {coverage['haunch_surface_sf']:.2f} SF sloped. Stops {coverage['stopping_depth_below_slab_top_inches']:g} inches below slab top.")
            if gravel:
                if result.get('gravel_delivery'):
                    d=result['gravel_delivery'];result['material_notes'].append(f"#57 stone: {gravel['measured_quantity']:.2f} CY x {d['tons_per_cy']:g} tons/CY = {d['required_tons']:.2f} tons; buy {d['truckloads']} full {d['tons_per_load']:g}-ton truck(s). Each load is approximately {d['cy_per_load']:.2f} CY. Density is a supplier-based estimating factor; actual quarry density and placement can vary.")
                else:result['material_notes'].append(f"Gravel: {gravel['measured_quantity']:.2f} CY in place, rounded to {gravel['quantity']} CY; compaction and delivery conversion still require review.")
        for name,chair in result.get('chair_allowances',{}).items():
            detail=f"{chair['count']} support positions; {chair['standard_packs']} box(es) of model {chair['model']} for standard-height locations."
            if 'edge_packs' in chair:detail+=f" {chair['special_height_count']} edge positions: budget {chair['edge_packs']} bucket(s) of {chair['edge_pack_size']} {chair['edge_chair_height_inches']:g}-inch chairs, model {chair['edge_model']}. Placement and steel elevation remain unverified."
            elif 'edge_chair_height_inches' in chair:detail+=f" {chair['special_height_count']} edge positions use {chair['edge_chair_height_inches']:g}-inch chairs per Jason; product, packaging and placement pending."
            elif chair.get('special_height_count'):detail+=f" {chair['special_height_count']} edge positions need a compatible taller/support detail."
            if chair.get('spanned_edge_candidate_count'):detail+=f" {chair['spanned_edge_candidate_count']} former edge-chair candidates are excluded because Jason confirmed the mesh spans the slope. These are not tie-wire quantities."
            result['material_notes'].append(name.capitalize()+' chairs: '+detail)
        if result.get('footer_rebar'):
            f=result['footer_rebar']
            if 'budget_sticks' in f:
                result['material_notes'].append(f"Footer budget allowance: {f['runs']} runs / {f['measured_lf']:.2f} LF boundary length + {f['internal_lap_lf']:.2f} LF internal laps = {f['budget_length_lf']:.2f} LF before final bend detailing; {f['budget_sticks']} whole {f['stock_length_ft']:g}-foot sticks. {f['wall_connection_count']} wall-bar lap connections lie within those runs and are not added twice. Final bend/cut schedule remains unverified.")
            elif 'lap_inches' in f:
                result['material_notes'].append(f"Footer reinforcement: {f['runs']} runs = {f['measured_lf']:.2f} LF before {f['lap_inches']:g}-inch laps and bends. Final purchase count awaits the corner, offset and anchorage schedule.")
            else:
                result['material_notes'].append(f"Footer reinforcement: {f['runs']} runs = {f['measured_lf']:.2f} LF before laps/bends. At least {f['minimum_sticks_before_laps']} stock sticks; final purchase count withheld until the lap/corner schedule is resolved.")
    return result


def estimate_csv(snapshot):
    if 'construction' not in snapshot:raise ValueError('Save a version with the confirmed construction rules first')
    output=io.StringIO(newline='')
    fields=['measurement_version','plan_sha256','construction_sha256','estimate_item_id','name','quantity','unit',
            'unit_price','markup_percent','cost','sell_amount','quantity_status','price_status']
    if snapshot['construction']['profile'].get('purchase_rounding')=='whole_units':fields+=['measured_quantity','measured_unit']
    if snapshot['construction']['profile'].get('slab_labor'):fields+=['budget_cost']
    if snapshot['construction']['profile'].get('pricing_notes'):fields+=['price_source']
    if snapshot['construction']['profile'].get('pricing_policy'):fields+=['template_row_id','template_row_origin','cost_code','supplier_cost','purchase_tax','budget_sell_amount']
    writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for row in snapshot['construction']['outputs']['estimate_rows']:
        record={k:row.get(k) for k in fields}
        record.update(measurement_version=snapshot['version'],plan_sha256=snapshot['plan_sha256'],
                      construction_sha256=snapshot['construction']['profile_sha256'])
        writer.writerow(record)
    return output.getvalue()


def construction_trade_draft(config, snapshot):
    attachment=snapshot['construction']; result=attachment['outputs']; profile=attachment['profile']
    lines=['# DRAFT — Roberts garage slab scope','', 'More information required; not issued for bidding.','',
           f"Drawing: {config['plan_name']} / page {config['page']+1}",f"Drawing SHA-256: {snapshot['plan_sha256']}",
           f"Measurement version: {snapshot['version']}",f"Construction SHA-256: {attachment['profile_sha256']}",
           f"Measurement: {snapshot['outline']} outline",f"Change note: {snapshot['note']}",'',
           f"Net garage slab: {snapshot['results']['net_sf']:.2f} SF",'']
    if result['calculation_valid']:
        c=result['concrete']; e=profile['exterior']; g=profile['interior_grade_beam']
        lines += [f"Slab: {profile['slab_inches']} inches. Exposed edges: {result['thickened_edge_lf']:.2f} LF.",
                  f"Separate-wall bearing edges: {result['bearing_edge_lf']:.2f} LF; 4-inch slab overlap.",
                  f"Exterior section: approximately {e['total_depth_inches']} inches total depth, {e['bottom_width_inches']}-inch bottom; {e['angle_degrees']}-degree haunch starts {e['vertical_inches_above_bottom']} inches above bottom.",
                  f"Interior beams: {g['eligible_wall_lf']} LF in this garage; {g['bottom_width_inches']}-inch bottom, {g['total_depth_inches']}-inch total depth from slab top, {g['angle_degrees']}-degree sides.",
                  f"Slab concrete: {c['slab_cy']:.2f} CY; added exterior edge/haunch: {c['extra_edge_cy']:.2f} CY.",
                  f"Net concrete: {c['net_cy']:.2f} CY. Waste: {profile['waste_percent']}%, applied once.",
                  f"Concrete allowance including waste: {c['with_waste_cy']:.2f} CY.",
                  f"Separate {profile.get('separate_wall_material','poured')} walls/footings, porch slab and driveway/apron are excluded.",'']
    else:lines += ['Concrete quantities withheld: '+result['reason'],'']
    if result.get('material_notes'):
        mesh_note=next((note for note in material_notes(profile) if note.startswith('Reinforcement:')),None)
        notes=[mesh_note if mesh_note and note.startswith('Reinforcement:') else note
            for note in result['material_notes']]
        lines += ['## Recorded material inputs','',*notes,'']
    for name,layout in result.get('roll_layouts',{}).items():
        lines += ['## '+name.capitalize()+' roll cutting allowance','',layout['basis'],
            f"{layout['roll_count']} rolls, each {layout['roll_width_ft']:g} x {layout['roll_length_ft']:g} feet; {layout['lap_inches']:g}-inch overlaps. Direction: {layout['direction']}.",
            f"Plan coverage: {layout['net_coverage_sf']:.2f} SF; lap material: {layout['lap_area_sf']:.2f} SF; trim: {layout['trim_area_sf']:.2f} SF; uncut roll remainder: {layout['uncut_remaining_sf']:.2f} SF.",
            'No concrete waste percentage added. Review material extent at slab edges and thickened sections before ordering.','',
            '| Strip | Roll | Cut length, feet |','|---|---|---:|']
        lines += [f"| {s['id']} | {s['roll']} | {s['cut_length_ft']:.3f} |" for s in layout['strips']]
        lines.append('')
    if result.get('rebar_grid'):
        grid=result['rebar_grid']
        lines += ['## Rebar estimating layout','',grid['layout_basis'],grid['cutting_basis'],
            f"{grid['run_count']} runs; {grid['splice_count']} overlaps. Remaining offcuts: {grid['offcut_lf']:.2f} LF. No automatic concrete-waste percentage added to steel.",
            'The recorded setback/lap are Jason\'s estimating inputs; governing reinforcement details still require review.','',
            '| Run | Direction | Net LF | Cuts in feet |','|---|---|---:|---|']
        for run in grid['segments']:
            lines.append(f"| {run['id']} | {run['direction']} | {run['net_lf']:.3f} | "+' + '.join(f'{v:.3f}' for v in run['cuts_ft'])+' |')
        lines += ['','| Stock stick | Cuts: run/piece, feet | Remaining LF |','|---|---|---:|']
        for stock in grid['stocks']:
            cuts='; '.join(f"{c['run_id']}/{c['piece']}: {c['length_ft']:.3f}" for c in stock['cuts'])
            lines.append(f"| {stock['id']} | {cuts} | {stock['remaining_ft']:.3f} |")
        lines.append('')
    lines += ['## Linked estimate rows','', '| Item | Quantity | Unit | Unit price | Amount |','|---|---:|---|---:|---:|']
    for row in result['estimate_rows']:
        show=lambda v:'Pending' if v is None else f'{v:.2f}'
        amount=f"~${row.get('budget_sell_amount',row['budget_cost']):.2f} budget" if row.get('budget_cost') is not None else show(row['sell_amount'])
        if row['sell_amount'] is None and row.get('cost') is not None:amount=f"${row['cost']:.2f} cost; markup pending"
        lines.append(f"| {row['name']} | {show(row['quantity'])} | {row['unit']} | {show(row['unit_price'])} | {amount} |")
    if profile.get('retail_chair_prices'):
        evidence=profile['retail_chair_prices']
        lines += ['', '## Dated retail chair observations', '',
            'Observed '+evidence['observed_on']+'. '+evidence['status']+'. These are candidate material costs, not an issued order or approved estimate total.', '',
            ('| Support | Package allowance | Pack size | Price per package | Candidate material cost |' if profile.get('material_specs',{}).get('grid_edge_chair_height_inches') is not None else '| Support | Box allowance | Pack size | Price per box | Candidate material cost |'),
            '|---|---:|---:|---:|---:|']
        for product in evidence['products']:
            purchase=result.get('purchase_materials',{}).get(product['scope'],{})
            qty=purchase.get('quantity');price=product['observed_pack_price']
            cost='Pending' if qty is None else '$'+format(qty*price,'.2f')
            lines.append(f"| [{product['name']}]({product['retailer_url']}) | {qty if qty is not None else 'Pending'} | {product['pack_size']} | ${price:.2f} | {cost} |")
        if profile.get('material_specs',{}).get('grid_edge_chair_height_inches') is not None:
            height=profile['material_specs']['grid_edge_chair_height_inches']
            lines += ['', f'Flat-slab chairs retain their separate allowance. The mesh spans the slope per Jason. His confirmed {height:g}-inch grid-edge chairs have a separate whole-bucket budget; support bearing and final steel elevation remain unverified.']
        elif profile.get('material_specs',{}).get('deep_edge_support',{}).get('mesh')=='mesh_spans_slope':
            lines += ['', 'Short slab-chair allowances cover positions over flat substrate. Mesh spans the slope per Jason, so no extra tall mesh chairs are included. Rebar-grid chairs at deep edges still require a compatible height/type and price.']
        else:
            lines += ['', 'Short slab-chair allowances cover only positions over flat substrate. Deeper edge positions are counted separately and require a compatible height/type; their prices remain pending.']
        for name,chair in result.get('chair_allowances',{}).items():
            lines += ['', name.capitalize()+': '+chair['basis'], 'Manufacturer: '+chair['spacing_source']]
    lines += ['', '## Resolve before requesting firm prices','',*['- '+r for r in result['missing_information']],
              '', '## Bid response fields','', '- Dated price, expiry, included labor/material/equipment and delivery.',
              '- Explicit exclusions, allowances, pumping/access, lead time and scope-change unit prices.',
              '', 'No current total is released while quantities or prices remain unresolved. No bid request has been sent.','']
    return '\n'.join(lines)
