"""Apply wall finishes to connected room/doorway fields without eroding finish transitions."""
import copy
import hashlib
import json
import math
from pathlib import Path
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from measurement_store import calculate


def finish_room_geometry(state, room_ids, passages, thickness_inches):
    if (not room_ids or len(room_ids)!=len(set(room_ids)) or isinstance(thickness_inches,bool)
            or not math.isfinite(thickness_inches) or not 0<thickness_inches<6):
        raise ValueError('Finish geometry needs unique rooms and a positive finish thickness')
    first=state['measurements'][room_ids[0]];scale=first['points_per_foot'];page=first['page']
    rooms={};pieces={};outside_masks=[];seen=set();door_reviews=[]
    def check(m,kind):
        if (m['kind']!=kind or m['page']!=page or m.get('surface_factor',1)!=1
                or not math.isclose(m['points_per_foot'],scale,rel_tol=1e-12)):
            raise ValueError('Finish geometry requires one calibrated flat sheet')
        calculate(m)
    for identity in room_ids:
        m=state['measurements'][identity];check(m,'area');rooms[identity]=Polygon(m['points'])
        pieces[identity]=[rooms[identity]]
    raw=unary_union(list(rooms.values()))
    if not math.isclose(raw.area,math.fsum(p.area for p in rooms.values()),abs_tol=1e-7):
        raise ValueError('Finish room contours overlap')
    for passage in passages:
        identity=passage['measurement_id'];m=state['measurements'][identity];check(m,'length')
        if identity in seen or len(m['points'])!=2:raise ValueError('Finish passage identities must be unique straight lines')
        seen.add(identity);(x0,y0),(x1,y1)=m['points'];sides=passage['sides']
        vertical=math.isclose(x0,x1,abs_tol=1e-7);horizontal=math.isclose(y0,y1,abs_tol=1e-7)
        if vertical==horizontal:raise ValueError('Finish passage must be horizontal or vertical')
        if (len(sides)!=2 or sorted(s['side'] for s in sides)!=[-1,1]
                or sum(s['room_id'] is None for s in sides)>1
                or any(s['room_id'] is not None and s['room_id'] not in rooms for s in sides)
                or sides[0]['room_id']==sides[1]['room_id']):
            raise ValueError('Finish passage requires two distinct adjacent sides')
        a,b=sorted([y0,y1] if vertical else [x0,x1]);center=x0 if vertical else y0
        half=scale*.5;bridges=[]
        for side in sides:
            c,d=sorted([center,center+side['side']*half])
            bridge=box(c,a,d,b) if vertical else box(a,c,b,d)
            bridges.append(bridge);room=side['room_id']
            if room is None:
                outside_masks.append(bridge);continue
            if bridge.intersection(rooms[room]).area<=1e-8:
                raise ValueError('Finish passage no longer meets its assigned room; review adjacency')
            if bridge.intersection(unary_union([p for key,p in rooms.items() if key!=room])).area>1e-7:
                raise ValueError('Finish passage crosses an unassigned room')
            pieces[room].append(bridge)
        door_reviews.append({'measurement_id':identity,'sides':copy.deepcopy(sides),
            'drawn_width_lf':(b-a)/scale,'termination':'wall centerline estimating allowance',
            'exterior_or_garage':any(s['room_id'] is None for s in sides)})
    zones={identity:unary_union(parts) for identity,parts in pieces.items()}
    combined=unary_union(list(zones.values()))
    if not math.isclose(combined.area,math.fsum(p.area for p in zones.values()),abs_tol=1e-7):
        raise ValueError('Finish passage allocations overlap')
    # Outside masks protect threshold centerlines from an artificial drywall deduction.
    # Clip them away again after offsetting actual wall and jamb boundaries.
    domain=unary_union([combined,*outside_masks]);finished=domain.buffer(-thickness_inches/12*scale,join_style='mitre')
    result=copy.deepcopy(state);details=[]
    for identity,zone in zones.items():
        face=finished.intersection(zone)
        if face.geom_type!='Polygon' or face.interiors or face.area<=0:
            raise ValueError('Finish room must remain a connected simple field')
        result['measurements'][identity]['points']=[list(p) for p in list(face.exterior.coords)[:-1]]
        result['measurements'][identity]['result']=calculate(result['measurements'][identity])
        details.append({'measurement_id':identity,'original_room_sf':rooms[identity].area/scale**2,
            'doorway_added_sf':zone.difference(rooms[identity]).area/scale**2,
            'wall_finish_deducted_sf':zone.difference(face).area/scale**2,
            'finished_field_sf':face.area/scale**2})
    if not math.isclose(sum(r['finished_field_sf'] for r in details),finished.intersection(combined).area/scale**2,abs_tol=1e-7):
        raise ValueError('Finish room partition does not reconcile')
    return result,{'rooms':details,'passages':door_reviews,'wall_finish_thickness_inches':thickness_inches,
        'room_measurement_version':state['version'],'drawn_jamb_and_centerline_allowance':True,
        'actual_jamb_and_transition_locations_verified':False,'purchase_quantity':None}


def reviewed_finish_faces(state,config,folder):
    root=Path(folder).resolve();path=(root/config['source_file']).resolve()
    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Floor finish-face source changed')
    source=json.loads(path.read_bytes())
    for item in source.get('job_sources',[]):
        dependency=(root/item['file']).resolve()
        if not dependency.is_relative_to(root) or hashlib.sha256(dependency.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Floor finish-face job evidence changed')
    if source['plan_sha256']!=state['plan_sha256'] or any(source[k]!=config[k] for k in ('room_ids','passages','wall_finish_thickness_inches')):
        raise ValueError('Floor finish-face mapping differs from reviewed source')
    result,review=finish_room_geometry(state,config['room_ids'],config['passages'],config['wall_finish_thickness_inches'])
    review.update(source_file=str(path),source_sha256=config['source_sha256'],basis=config['basis'])
    return result,review


def derive_linked_finish_field(state, source_state, config, folder):
    """Rebuild a reviewed room field while retaining separately edited shower/cabinet footprints."""
    from measurement_quantities import geometry_digest
    root=Path(folder).resolve();path=(root/config['source_file']).resolve()
    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Derived floor field evidence changed')
    recipe=json.loads(path.read_bytes());identity=recipe['measurement_id'];ids=recipe['room_ids']
    if 'owner_answer_source' in recipe:
        answer_source=recipe['owner_answer_source'];answer_path=(root/answer_source['file']).resolve()
        if (not answer_path.is_relative_to(root) or not answer_path.is_file()
                or hashlib.sha256(answer_path.read_bytes()).hexdigest()!=answer_source['sha256']):
            raise ValueError('Derived floor field owner answer evidence changed or missing')
        if json.loads(answer_path.read_bytes())['plan_sha256']!=state['plan_sha256']:
            raise ValueError('Derived floor field owner answers belong to another plan')
    if (source_state is None or source_state['plan_sha256']!=state['plan_sha256']
            or recipe['plan_sha256']!=state['plan_sha256']):
        raise ValueError('Derived floor field needs current source geometry on the same plan')
    original=state['measurements'][identity]
    if geometry_digest(original)!=recipe['original_geometry_sha256']:
        raise ValueError('Derived floor outline was edited directly; reconcile it with the source rooms')
    if not ids or len(ids)!=len(set(ids)) or not set(ids).issubset(recipe['finish_faces']['room_ids']):
        raise ValueError('Derived floor field needs unique reviewed source rooms')
    finished,review=reviewed_finish_faces(source_state,recipe['finish_faces'],folder)
    selected=[finished['measurements'][i] for i in ids]
    if (original['kind']!='area' or original['page']!=selected[0]['page']
            or not math.isclose(original['points_per_foot'],selected[0]['points_per_foot'],rel_tol=1e-12)):
        raise ValueError('Derived floor field must share the source room calibration')
    field=unary_union([Polygon(m['points']) for m in selected])
    if field.geom_type!='Polygon' or field.interiors or field.area<=0:
        raise ValueError('Derived floor field must be a connected simple polygon')
    result=copy.deepcopy(state)
    result['measurements'][identity]['points']=[list(p) for p in list(field.exterior.coords)[:-1]]
    result['measurements'][identity]['result']=calculate(result['measurements'][identity])
    return result,{'source_measurement_version':source_state['version'],'measurement_id':identity,
        'room_ids':ids,'source_file':str(path),'source_sha256':config['source_sha256'],
        'finish_face_source_sha256':review['source_sha256'],'purchase_quantity':None,
        'basis':recipe['basis']}
