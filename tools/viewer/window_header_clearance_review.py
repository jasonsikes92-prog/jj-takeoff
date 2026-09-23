"""Screen window head/header fit without turning unresolved gaps into purchases."""
import hashlib
import json
import math
from pathlib import Path
from measurement_store import MeasurementStore
from below_window_stock_review import from_folder as below_windows
from opening_header_review import from_folder as opening_headers
from owner_height_selection import select as select_height


def calculate(windows,scenarios,alternatives,top_plates_inches, *, selected_scenario=None):
    def positive(value):
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise ValueError('Positive finite height or depth required')
        return value
    positive(top_plates_inches)
    if not scenarios or len({s['id'] for s in scenarios})!=len(scenarios):
        raise ValueError('Unique wall-height scenarios required')
    if selected_scenario is not None and selected_scenario not in {s['id'] for s in scenarios}:
        raise ValueError('Selected clearance height must match a saved scenario')
    if len({w['opening_id'] for w in windows})!=len(windows):
        raise ValueError('Duplicate window')
    if not set(alternatives)<=set(w['opening_id'] for w in windows):
        raise ValueError('Header alternatives must belong to reviewed windows')
    rows=[];pending=[]
    for window in windows:
        identity=window['opening_id'];head=positive(window['head_datum_inches'])
        offset=window['base_offset_inches']
        if type(offset) not in (int,float) or not math.isfinite(offset):
            raise ValueError('Finite wall-base offset required')
        choices=alternatives.get(identity,[])
        if not choices:pending.append({'id':identity,'reason':'Header depth unresolved'});continue
        if len({a['id'] for a in choices})!=len(choices):raise ValueError('Duplicate header alternative')
        for scenario in scenarios:
            wall=positive(scenario['wall_height_inches'])
            available=wall+offset-top_plates_inches-(head+offset)
            for choice in choices:
                if not choice.get('source'):raise ValueError('Header dimension source required')
                depth=positive(choice['depth_inches']);gap=available-depth
                status=('vertical_overlap' if gap<0 else 'zero_clearance' if gap==0 else 'positive_gap_unresolved')
                rows.append({'opening_id':identity,'run':window['run'],'scenario_id':scenario['id'],
                    'header_alternative_id':choice['id'],'source':choice['source'],
                    'wall_top_above_base_inches':wall+offset,'head_above_base_inches':head+offset,
                    'top_plates_inches':top_plates_inches,'available_header_depth_inches':available,
                    'header_depth_inches':depth,'gap_inches':gap,'status':status,
                    'short_stud_quantity':None,'purchase_quantity':None,'detail_approved':False})
    if selected_scenario is not None:
        for row in rows:row['selected_wall_height']=row['scenario_id']==selected_scenario
    return {'comparisons':rows,'pending':pending,'selected_scenario':selected_scenario,
        'selected_header_alternative':None,'short_stud_quantity':None,'purchase_quantity':None,
        'structural_adequacy_verified':False,'purchase_order_released':False}


def from_folder(folder):
    folder=Path(folder).resolve();config_path=folder/'window_header_clearance_review.json'
    raw=config_path.read_bytes();config=json.loads(raw);checked={config_path:raw}
    def load(ref):
        path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Clearance evidence must remain inside the job')
        content=path.read_bytes();checked[path]=content
        if hashlib.sha256(content).hexdigest()!=ref['sha256']:
            raise ValueError('Window clearance evidence changed: '+ref['path'])
        return json.loads(content)
    lower_config=load(config['lower_mapping']);header_config=load(config['header_mapping'])
    heights=load(lower_config['height_basis']);headers=load(header_config['headers'])
    supplier=load(header_config['supplier_headers'])
    state=MeasurementStore(folder).read();lower=below_windows(folder);header_review=opening_headers(folder,state)
    if config['plan_sha256']!=state['plan_sha256'] or lower['measurement_version']!=state['version']:
        raise ValueError('Window clearance sources do not describe the current drawing')
    selection=select_height(load(config['height_selection']),state['plan_sha256'],heights['scenarios']) if config.get('height_selection') else None
    bindings={b['opening_id']:b for b in header_config['bindings']}
    by_header={h['id']:h for h in headers['headers']}
    by_supplier={h['opening_id']:h for h in supplier['openings']}
    alternatives={};unresolved=[]
    for window in lower['windows']:
        identity=window['opening_id'];binding=bindings[identity];choices=[]
        plan_header=by_header[binding['header_id']];label=plan_header['material_label']
        depth=config['plan_depths_inches'].get(label)
        if depth is not None:
            choices.append({'id':'plan:'+plan_header['id'],'depth_inches':depth,
                'source':{'kind':'plan','header_id':plan_header['id'],'callout':plan_header['source_text'],
                    'inventory_sha256':header_config['headers']['sha256']}})
        else:unresolved.append({'id':identity,'reason':'Plan header depth not interpreted: '+label})
        alternate=by_supplier.get(identity)
        if alternate:
            if alternate['header_id']!=binding['header_id']:raise ValueError('Header mapping conflict')
            depth=config['supplier_depths_inches'].get(alternate['product'])
            if depth is not None:
                choices.append({'id':'supplier:'+alternate['member_id'],'depth_inches':depth,
                    'source':{'kind':'supplier','member_id':alternate['member_id'],'product':alternate['product'],
                        'reference':alternate['source'],'adopted_as_replacement':False,
                        'evidence_sha256':header_config['supplier_headers']['sha256']}})
            else:unresolved.append({'id':identity,'reason':'Supplier header depth not interpreted: '+alternate['product']})
        alternatives[identity]=choices
    selected=selection['id'] if selection and lower['status']!='withheld_geometry_changed' else None
    result=calculate(lower['windows'],heights['scenarios'],alternatives,config['top_plates_inches'],selected_scenario=selected)
    result['pending'].extend(lower['pending']+unresolved)
    if lower.get('head_datum_confirmation'):
        result['head_datum_confirmation']=lower['head_datum_confirmation']
    result.update(status='withheld_geometry_changed' if lower['status']=='withheld_geometry_changed' else
        'selected_wall_height_header_unresolved' if selected else 'unselected_clearance_scenarios',
        plan_sha256=state['plan_sha256'],measurement_version=state['version'],
        source_hashes={str(p.relative_to(folder)):hashlib.sha256(b).hexdigest() for p,b in checked.items()},
        lower_geometry_sha256=lower['geometry_sha256'],header_geometry_sha256=header_review['opening_geometry_sha256'],
        basis=config['basis'],dimension_reference=config['dimension_reference'],remaining=config['remaining'])
    if (any(p.read_bytes()!=b for p,b in checked.items()) or MeasurementStore(folder).read()!=state
            or below_windows(folder)!=lower or opening_headers(folder,state)!=header_review):
        raise ValueError('Window clearance sources changed during calculation; retry')
    return result
