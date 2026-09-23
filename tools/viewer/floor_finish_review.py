"""Separate an owner-selected room finish from an existing floor assembly."""
import copy
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import Polygon
from measurement_store import calculate


def import_finish(draft, state, config, folder):
    if config['plan_sha256'] != draft['plan_sha256'] or state['plan_sha256'] != draft['plan_sha256']:
        raise ValueError('Room finish belongs to another drawing')
    if draft['measurement_version'] != state['version']:
        raise ValueError('Room finish uses another measurement revision')
    root=Path(folder).resolve(); source=(root/config['source_file']).resolve()
    if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Room finish source changed')
    if 'floor_finish_review' in draft:
        raise ValueError('Room finish already applied')
    result=copy.deepcopy(draft); rows={r['row_id']:r for r in result['rows']}
    refs=config['measurement_ids']
    if not refs or len(refs)!=len(set(refs)) or not config.get('basis'):
        raise ValueError('Room finish needs unique measurements and a source basis')
    displaced=rows[config['displaced_row_id']]
    inputs=[q for q in displaced['assembly_inputs'] if q['id']==config['displaced_assembly_id']]
    if len(inputs)!=1:
        raise ValueError('Room finish needs the remaining floor assembly')
    other_ids=inputs[0]['measurement_ids']
    raw_state=state;face_review=None
    if 'finish_faces' in config:
        from floor_finish_faces import reviewed_finish_faces
        if not set(refs+other_ids).issubset(config['finish_faces']['room_ids']):
            raise ValueError('Floor finish-face review omits a selected floor room')
        state,face_review=reviewed_finish_faces(state,config['finish_faces'],folder)
    obstruction_review=None
    if 'fixed_obstructions' in config:
        from floor_obstructions import reviewed_obstructions
        obstruction_review=reviewed_obstructions(state,other_ids,config['fixed_obstructions'],folder,
                                                include_rooms='cost_allocation' in config,
                                                room_split=config.get('cost_allocation',{}).get('room_split'))
        raw_quantity=math.fsum(calculate(raw_state['measurements'][i])['quantity'] for i in other_ids)
        if not math.isclose(inputs[0]['quantity'],raw_quantity,abs_tol=1e-7):
            raise ValueError('Floor obstruction review needs the unadjusted room field')
        if face_review is not None:
            obstruction_review['finish_face_review']=face_review
        for row in result['rows']:
            for part in row.get('assembly_inputs',[]):
                if part['id']==config['displaced_assembly_id']:
                    if part['measurement_ids']!=other_ids:raise ValueError('Floor material and labor scopes disagree')
                    part.update(quantity=obstruction_review['net_sf'],measured_quantity=obstruction_review['net_sf'],
                                gross_quantity=obstruction_review['gross_sf'],obstruction_review=obstruction_review,
                                label='Floating-floor room field less fixed footprints',
                                basis=part['basis']+' '+config['fixed_obstructions']['basis'],
                                remaining=config['fixed_obstructions']['remaining'])
    if set(refs)&set(other_ids):
        raise ValueError('A room cannot be included in both finishes')
    selected=[]
    for identity in refs:
        m=state['measurements'][identity]
        if m['kind']!='area' or m.get('surface_factor',1)!=1:
            raise ValueError('Floor finish needs flat room area')
        selected.append((m,calculate(m)))
    # IDs alone do not prevent two overlapping outlines from counting the same floor.
    pairs=[m for m,_ in selected]+[state['measurements'][i] for i in other_ids]
    for index,(m,_) in enumerate(selected):
        for other in pairs[index+1:]:
            if m['page']==other['page']:
                if not math.isclose(m['points_per_foot'],other['points_per_foot'],rel_tol=1e-12):
                    raise ValueError('Floor finish scales disagree on the same sheet')
                if Polygon(m['points']).intersection(Polygon(other['points'])).area>1e-8:
                    raise ValueError('Floor finish boundaries overlap')
    quantity=math.fsum(v['quantity'] for _,v in selected)
    parent=rows[config['parent_row_id']]
    if (parent['cost_type']!='ASSEMBLY' or parent.get('covered_by_package')
            or any(parent.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
        raise ValueError('Room finish needs an unpriced assembly parent')
    extras=result.setdefault('additional_cost_rows',[])
    occupied=set(rows)|{r['row_id'] for r in extras}
    targets=config['cost_rows']
    if not targets:raise ValueError('Room finish needs cost owners')
    partial={'id':config['id'],'label':config['label'],'quantity':quantity,'measured_quantity':quantity,
        'unit':'SF','measurement_ids':list(refs),'use':'assembly_input','basis':config['basis'],
        'source':{'file':str(source),'sha256':config['source_sha256']},'remaining':config['remaining'],
        'certified':False,'order_released':False}
    if face_review is not None:partial['finish_face_review']=face_review
    for target in targets:
        identity=target['row_id'];markup=rows[target['markup_source_row_id']]
        if identity in occupied:raise ValueError('Duplicate room finish cost owner')
        if (markup['parent']!=parent['name'] or markup['cost_type'] not in ('ALLOWANCE','MATERIAL','LABOR','SUBCONTRACTOR')
                or target['unit'] not in ('sq yd','sq ft')):
            raise ValueError('Room finish needs a matching template markup and area unit')
        extras.append({'row_id':identity,'parent_row_id':parent['row_id'],'parent':parent['name'],
            'name':target['name'],'cost_type':markup['cost_type'],'unit':target['unit'],
            'markup_pct':markup['markup_pct'],'markup_source_row_id':markup['row_id'],
            'draft_quantity':None,'unit_cost':None,'line_cost':None,'line_price':None,
            'assembly_inputs':[copy.deepcopy(partial)],'quantity_sources':[],
            'pricing_role':'cost_line','completion_status':'evidence_in_progress',
            'certified':False,'current_price_certified':False})
        occupied.add(identity)
    result['floor_finish_review']={'id':config['id'],'finish_area_sf':quantity,
        'measurement_ids':list(refs),'remaining_finish_area_sf':inputs[0]['quantity'],
        'remaining_measurement_ids':list(other_ids),'measurement_version':state['version'],
        'plan_sha256':state['plan_sha256'],'source_sha256':config['source_sha256'],
        'basis':config['basis'],'remaining':config['remaining'],'purchase_quantity':None}
    if obstruction_review is not None:result['floor_finish_review']['obstructions']=obstruction_review
    if face_review is not None:result['floor_finish_review']['finish_faces']=face_review
    if 'cost_allocation' in config:
        allocate_floor_costs(result,config,folder)
        if 'billing_review' in config:
            apply_floor_billing(result,config['billing_review'],folder)
            if 'material_purchase' in config:
                from floor_material_purchase import apply_material_purchase
                apply_material_purchase(result, config['material_purchase'], folder)
    if 'baseboard_review' in config:
        from baseboard_review import apply_baseboard
        apply_baseboard(result, raw_state, config['baseboard_review'], folder)
    result.update(estimate_released=False,whole_house_total=None)
    return result


def allocate_floor_costs(draft, config, folder):
    """Assign each room to one material/labor pair without changing template prices or markups."""
    allocation=config['cost_allocation'];root=Path(folder).resolve()
    source=(root/allocation['source_file']).resolve()
    if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest()!=allocation['source_sha256']:
        raise ValueError('Floor cost allocation evidence changed')
    review=draft['floor_finish_review'];obstructions=review.get('obstructions',{})
    room_areas={r['measurement_id']:r for r in obstructions.get('rooms',[])}
    expected=list(review['remaining_measurement_ids']);groups=allocation['groups']
    if allocation.get('room_split'):
        split=allocation['room_split']
        if split['room_id'] not in expected or obstructions.get('room_split',{}).get('room_id')!=split['room_id']:
            raise ValueError('Floor cost allocation lacks its reviewed room division')
        expected.remove(split['room_id']);expected.extend([split['above_id'],split['below_id']])
    assigned=[identity for group in groups for identity in group['measurement_ids']]
    owners=[identity for group in groups for identity in group['cost_rows']]
    if (not groups or len({g['id'] for g in groups})!=len(groups)
            or len(assigned)!=len(set(assigned)) or set(assigned)!=set(expected)
            or set(room_areas)!=set(expected) or len(owners)!=len(set(owners))):
        raise ValueError('Floor cost allocation must assign every room once and use distinct cost owners')
    rows={r['row_id']:r for r in draft['rows']};original=config['displaced_assembly_id']
    source_owners={r['row_id'] for r in draft['rows'] if any(p['id']==original for p in r.get('assembly_inputs',[]))}
    if not source_owners or not source_owners.issubset(owners):
        raise ValueError('Floor cost allocation must replace every original pooled owner')
    planned=[]
    for group in groups:
        if not group['measurement_ids'] or len(group['cost_rows'])!=2 or not group.get('basis'):
            raise ValueError('Floor cost allocation needs rooms, a material/labor pair and a source basis')
        parts=[room_areas[i] for i in group['measurement_ids']]
        gross=math.fsum(r['gross_sf'] for r in parts);deducted=math.fsum(r['deducted_sf'] for r in parts)
        net=math.fsum(r['net_sf'] for r in parts)
        if not math.isclose(gross-deducted,net,abs_tol=1e-7):
            raise ValueError('Floor cost allocation does not reconcile')
        for identity in group['cost_rows']:
            row=rows[identity]
            if (row.get('covered_by_package') or row.get('pricing_role')!='cost_line'
                    or row.get('completion_status')=='excluded'
                    or any(row.get(k) is not None for k in ('draft_quantity','line_cost','line_price'))
                    or row.get('quantity_sources')
                    or any(p['id']!=original for p in row.get('assembly_inputs',[]))):
                raise ValueError('Floor cost allocation cannot replace another measured or priced scope')
        partial={'id':group['id'],'label':group['label'],'measurement_ids':list(group['measurement_ids']),
                 'unit':'SF','use':'assembly_input','rounding':'none','quantity':net,'measured_quantity':net,
                 'gross_quantity':gross,'deducted_quantity':deducted,'room_areas':parts,
                 'template_rows':[rows[i]['excel_row'] for i in group['cost_rows']],
                 'basis':group['basis'],'source':{'file':str(source),'sha256':allocation['source_sha256']},
                 'remaining':config['fixed_obstructions']['remaining'],
                 'certified':False,'order_released':False}
        planned.append((group,partial))
    if not math.isclose(math.fsum(p['quantity'] for _,p in planned),review['remaining_finish_area_sf'],abs_tol=1e-7):
        raise ValueError('Allocated floor areas differ from the measured floor field')
    # Validate the entire partition before replacing any cost-owner scope.
    for group,partial in planned:
        for identity in group['cost_rows']:rows[identity]['assembly_inputs']=[copy.deepcopy(partial)]
    review['cost_allocation']={'groups':[dict(g,net_sf=p['quantity'],gross_sf=p['gross_quantity'],
        deducted_sf=p['deducted_quantity']) for g,p in planned],
        'source_file':str(source),'source_sha256':allocation['source_sha256'],
        'each_room_assigned_once':True,'purchase_quantity':None}


def apply_floor_billing(draft, config, folder):
    """Price installed-area labor separately from waste and whole-carton material."""
    root=Path(folder).resolve();source=(root/config['source_file']).resolve()
    if (not source.is_relative_to(root) or not source.is_file()
            or hashlib.sha256(source.read_bytes()).hexdigest()!=config['source_sha256']):
        raise ValueError('Floor billing evidence changed')
    proof=json.loads(source.read_bytes())
    waste=proof.get('material_waste_pct')
    if (proof.get('plan_sha256')!=draft['plan_sha256']
            or proof.get('labor_basis')!='measured_installed_floor_area'
            or type(waste) not in (int,float) or not math.isfinite(waste) or waste<0):
        raise ValueError('Floor billing needs reviewed installed-area labor and material waste')
    rows={r['row_id']:r for r in draft['rows']}
    review=draft['floor_finish_review'];groups=review['cost_allocation']['groups'];planned=[]
    labor_ids=proof.get('labor_cost_owner_ids',[])
    if (len(labor_ids)!=len(set(labor_ids))
            or set(labor_ids)!={g['cost_rows'][1] for g in groups}):
        raise ValueError('Floor billing must explicitly identify every labor cost owner')
    for group in groups:
        material,labor=[rows[i] for i in group['cost_rows']]
        net=group['net_sf']
        if (material['cost_type'] not in ('MATERIAL','ALLOWANCE')
                or labor['cost_type'] not in ('LABOR','SUBCONTRACTOR','MATERIAL')
                or labor['unit'] not in ('SF','sq ft','ft2')
                or type(net) not in (int,float) or not math.isfinite(net) or net<0
                or labor.get('draft_quantity') is not None or labor.get('quantity_sources')
                or labor.get('covered_by_package') or labor.get('line_cost') is not None
                or len(labor.get('assembly_inputs',[]))!=1
                or labor['assembly_inputs'][0]['id']!=group['id']):
            raise ValueError('Floor billing needs one unpriced area-based labor owner per group')
        quantity=copy.deepcopy(labor['assembly_inputs'][0])
        quantity.update(use='template_quantity',kind='measured_floor_labor',rounding='none',
            quantity=net,measured_quantity=net,billing_basis=proof['labor_basis'],
            billing_source=copy.deepcopy(config),
            basis=quantity['basis']+' Owner confirms installed floor area for labor; material waste is excluded.',
            remaining=['Final jamb/transition positions and expansion clearances remain for verification. Current supplier rate is unverified.'])
        planned.append((labor,quantity))
    total=math.fsum(g['net_sf'] for g in groups)
    if not math.isclose(total,review['remaining_finish_area_sf'],abs_tol=1e-7):
        raise ValueError('Floor labor groups must reconcile with the whole installed field')
    for row,quantity in planned:
        row['draft_quantity']=quantity['quantity'];row['quantity_sources']=[quantity]
    review['billing_review']={'source':copy.deepcopy(config),'labor_basis':proof['labor_basis'],
        'installed_area_sf':total,'material_waste_pct':waste,
        'material_area_with_waste_sf':total*(1+waste/100),
        'material_purchase_quantity':None,'carton_coverage_sf':None,
        'remaining':'Verify carton coverage and round the shared product order to whole cartons; do not add material waste to labor.'}
