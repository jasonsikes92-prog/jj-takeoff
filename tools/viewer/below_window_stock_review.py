"""Reserve short studs below windows on the existing field layout datum."""
import hashlib
import json
import math
from pathlib import Path
from linear_stock import pack_sawn_cuts
from measurement_store import MeasurementStore
from window_sill_stock_review import from_folder as sill_stock
from exterior_field_stud_review import from_folder as exterior_layout


def confirmed_head(record, plan_sha256, head_inches):
    if (record.get('owner_confirmed') is not True or record.get('plan_sha256') != plan_sha256
            or record.get('datum') != 'rough_opening_head_above_main_subfloor'
            or type(record.get('head_inches')) not in (int,float)
            or not math.isfinite(record['head_inches']) or record['head_inches'] <= 0
            or record['head_inches'] != head_inches):
        raise ValueError('Owner-confirmed window head does not match this plan and calculation')
    return {'head_inches':head_inches,'datum':record['datum'],'owner_confirmed':True}


def calculate(field,state,assemblies,offsets,stock,head_inches,bottom_plate_inches,sill_inches):
    dims=[head_inches,bottom_plate_inches,sill_inches,field['points_per_foot'],stock['length_inches']]
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in dims):
        raise ValueError('Positive finite head, plate, sill, scale and stock dimensions required')
    stations=field['field_studs']+field['reserved_stations']
    if len({s['id'] for s in stations})!=len(stations):raise ValueError('Duplicate field station')
    pieces=[];pending=[];windows=[];seen=set();used=set();half=field['points_per_foot']/16
    for assembly in assemblies:
        identity=assembly['opening_id'];height=assembly['rough_opening_height_in']
        if identity in seen:raise ValueError('Window assembly counted twice')
        seen.add(identity)
        if type(assembly['assembly_quantity']) is not int or assembly['assembly_quantity']!=1:
            raise ValueError('One physical window assembly required per entry')
        if type(height) not in (int,float) or not math.isfinite(height) or height<=0:
            raise ValueError('Positive supplier rough-opening height required')
        measurement=state['measurements'].get(identity)
        runs={z['run'] for z in field['zones'] if z['assembly']==identity}
        if measurement is None or len(runs)!=1:
            pending.append({'id':identity,'reason':'Window needs a reviewed wall run, editable width and base/head datum.'});continue
        run=next(iter(runs))
        if run not in offsets or type(offsets[run]) not in (int,float) or not math.isfinite(offsets[run]):
            raise ValueError('Known wall-base height offset required: '+run)
        if (measurement['kind']!='length' or len(measurement['points'])!=2
                or measurement['points_per_foot']!=field['points_per_foot']):
            raise ValueError('Window requires a straight width on the current field-layout scale')
        a,b=measurement['points'];axis=0 if abs(a[1]-b[1])<1e-6 else 1
        if abs(a[1-axis]-b[1-axis])>=1e-6:raise ValueError('Orthogonal window width required')
        low,high=sorted([a[axis],b[axis]])
        raw_cut=head_inches+offsets[run]-height-bottom_plate_inches-sill_inches
        if raw_cut<=0:
            pending.append({'id':identity,'reason':'No positive below-window cut under this height interpretation; resolve the sill and wall base.'});continue
        selected=[]
        for station in stations:
            if station['run']!=run or not low+half<=station['along_pt']<=high-half:continue
            if station['assembly_owners']!=[identity]:
                pending.append({'id':identity+':'+station['id'],'reason':'Station is assigned to full-height or overlapping assemblies; reconcile ownership.'});continue
            if station['id'] in used:raise ValueError('Below-window station belongs to two openings')
            used.add(station['id']);selected.append(station['id'])
            pieces.append({'id':'below:'+identity+':'+station['id'],'opening_id':identity,'station_id':station['id'],
                'run':run,'point_pt':station['point_pt'],'raw_cut_inches':raw_cut,
                'cut_inches':math.ceil(raw_cut*8-1e-8)/8,'sku':stock['sku'],
                'stock_length_ft':stock['length_inches']/12})
        windows.append({'opening_id':identity,'run':run,'station_ids':selected,'member_count':len(selected),
            'head_datum_inches':head_inches,'base_offset_inches':offsets[run],
            'supplier_rough_height_inches':height,'raw_cut_inches':raw_cut})
    boards=pack_sawn_cuts(pieces,.125)
    return {'windows':windows,'pieces':pieces,'boards':boards,'pending':pending,
        'member_count':len(pieces),'candidate_whole_sticks':len(boards),
        'raw_member_lf':math.fsum(p['raw_cut_inches'] for p in pieces)/12,
        'kerf_inches':.125,'cut_rounding_inches':.125,'optimality_proven':False}


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'below_window_stock_review.json'
    raw=path.read_bytes();config=json.loads(raw);checked={path:raw}
    def read(ref):
        path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Below-window evidence must remain inside the job')
        content=path.read_bytes();checked[path]=content
        if hashlib.sha256(content).hexdigest()!=ref['sha256']:raise ValueError('Below-window evidence changed: '+ref['path'])
        return json.loads(content)
    sill_config=read(config['sill_mapping']);heights=read(config['height_basis'])
    confirmation=None
    if config.get('head_confirmation'):
        confirmation=confirmed_head(read(config['head_confirmation']),config['plan_sha256'],config['head_datum_inches'])
    schedule=read(sill_config['schedule']);sills=sill_stock(folder)
    store=MeasurementStore(folder);state=store.read();field=exterior_layout(folder)
    if (any(x!=state['plan_sha256'] for x in (config['plan_sha256'],heights['plan_sha256'],field['plan_sha256']))
            or sills['measurement_version']!=state['version'] or field['source_versions']['openings']!=state['version']):
        raise ValueError('Below-window sources do not describe one drawing revision')
    matches=[s for s in heights['stocks'] if s['sku']==config['stock_sku']]
    if len(matches)!=1:raise ValueError('One exact saved stock product required')
    changed=sills['changed_measurements']
    if changed:
        result={'windows':[],'pieces':[],'boards':[],'member_count':None,'candidate_whole_sticks':None,
            'pending':[{'id':i,'reason':'Window geometry changed; reconcile supplier dimensions before using old cuts.'} for i in changed]}
    else:
        result=calculate(field,state,schedule['assemblies'],heights['run_height_offsets_inches'],matches[0],
            config['head_datum_inches'],config['bottom_plate_inches'],config['sill_inches'])
    result.update(plan_sha256=state['plan_sha256'],measurement_version=state['version'],
        source_version=field['source_versions']['interior'],source_versions=field['source_versions'],
        mapping_sha256=hashlib.sha256(raw).hexdigest(),sill_mapping_sha256=sills['mapping_sha256'],
        geometry_sha256=field['geometry_sha256'],height_basis_sha256=config['height_basis']['sha256'],
        field_evidence_sha256=field['evidence_sha256'],profile_sha256=field['profile_sha256'],
        spacing_inches=field['spacing_inches'],first_center_inches=field['first_center_inches'],
        status='withheld_geometry_changed' if changed else 'documented_estimating_allowance',
        basis=config['basis'],remaining=config['remaining'],cross_scope_offcut_credit=False,
        purchase_quantity=None,purchase_order_released=False,structural_adequacy_verified=False,
        company_default_changed=False)
    if confirmation is not None:
        result['head_datum_confirmation']={**confirmation,'source':config['head_confirmation']}
    if (any(p.read_bytes()!=content for p,content in checked.items()) or store.read()!=state
            or exterior_layout(folder)!=field or sill_stock(folder)!=sills):
        raise ValueError('Below-window sources changed during calculation; retry')
    return result
