"""Deduct reviewed fixed footprints from live room contours without overlap."""
import hashlib
import math
import copy
from pathlib import Path
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from measurement_store import MeasurementStore,calculate


def net_floor_area(state, room_ids, obstruction_state, obstruction_ids, include_rooms=False):
    if state['plan_sha256']!=obstruction_state['plan_sha256']:
        raise ValueError('Floor obstructions belong to another drawing')
    if not room_ids or len(set(room_ids))!=len(room_ids) or not obstruction_ids or len(set(obstruction_ids))!=len(obstruction_ids):
        raise ValueError('Floor areas need unique room and obstruction identities')
    first=state['measurements'][room_ids[0]];scale=first['points_per_foot'];page=first['page']
    def polygon(m):
        if m['kind']!='area' or m.get('surface_factor',1)!=1 or m['page']!=page or not math.isclose(m['points_per_foot'],scale,rel_tol=1e-12):
            raise ValueError('Floor areas require flat polygons on one calibrated sheet')
        calculate(m)
        return Polygon(m['points'])
    rooms=[polygon(state['measurements'][i]) for i in room_ids]
    field=unary_union(rooms)
    if not math.isclose(field.area,sum(p.area for p in rooms),abs_tol=1e-7):
        raise ValueError('Floor room contours overlap')
    cuts=[];details=[]
    for identity in obstruction_ids:
        shape=polygon(obstruction_state['measurements'][identity]);inside=field.intersection(shape)
        if inside.area<=1e-8:raise ValueError('Fixed footprint is outside the selected floor rooms')
        cuts.append(inside)
        details.append({'measurement_id':identity,'gross_footprint_sf':shape.area/scale**2,
                        'inside_floor_sf':inside.area/scale**2,'outside_floor_sf':shape.difference(field).area/scale**2})
    combined=unary_union(cuts);net=field.difference(combined)
    if net.area<=0:raise ValueError('Fixed footprints remove the entire floor field')
    result={'gross_sf':field.area/scale**2,'deducted_sf':combined.area/scale**2,'net_sf':net.area/scale**2,
            'footprints':details,'room_measurement_version':state['version'],
            'obstruction_measurement_version':obstruction_state['version'],
            'overlapping_footprint_area_counted_once':True,'finish_faces_and_thresholds_verified':False}
    if include_rooms:
        result['rooms']=[{'measurement_id':identity,'gross_sf':shape.area/scale**2,
                         'deducted_sf':shape.intersection(combined).area/scale**2,
                         'net_sf':shape.difference(combined).area/scale**2}
                        for identity,shape in zip(room_ids,rooms)]
    return result


def split_room_at_boundary(state, room_ids, boundary_state, config):
    """Split an open room at an editable horizontal estimating division, not a wall."""
    if boundary_state['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Floor cost division belongs to another drawing')
    original=config['room_id'];ids=[config['above_id'],config['below_id']]
    if original not in room_ids or len(set(ids))!=2 or any(i in state['measurements'] for i in ids):
        raise ValueError('Floor cost division needs one existing room and two unique region identities')
    room=state['measurements'][original];line=boundary_state['measurements'][config['measurement_id']]
    calculate(line)
    if (line['kind']!='length' or len(line['points'])!=2 or line['page']!=room['page']
            or not math.isclose(line['points_per_foot'],room['points_per_foot'],rel_tol=1e-12)
            or not math.isclose(line['points'][0][1],line['points'][1][1],abs_tol=1e-7)):
        raise ValueError('Floor cost division must be a horizontal line on the calibrated room sheet')
    shape=Polygon(room['points']);x0,y0,x1,y1=shape.bounds;y=line['points'][0][1]
    if not y0<y<y1:
        raise ValueError('Floor cost division must cross the room')
    result=copy.deepcopy(state)
    for identity,clip in zip(ids,[box(x0,y0,x1,y),box(x0,y,x1,y1)]):
        part=shape.intersection(clip)
        if part.geom_type!='Polygon' or part.interiors or part.area<=0:
            raise ValueError('Floor cost division must leave two simple room regions')
        result['measurements'][identity]={**room,'id':identity,'points':[list(p) for p in list(part.exterior.coords)[:-1]]}
    return result,[i for i in room_ids if i!=original]+ids


def reviewed_obstructions(state, room_ids, config, folder, include_rooms=False, room_split=None):
    root=Path(folder).resolve();source=(root/config['source_file']).resolve()
    if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Floor obstruction scope evidence changed')
    job=(root/config['job']).resolve()
    if not (job/'measurement_edits.sqlite3').is_file():raise ValueError('Floor obstructions have no saved measurement history')
    store=MeasurementStore(job)
    if store.config_hash!=config['config_sha256']:raise ValueError('Floor obstruction mapping changed')
    split_review=None
    if room_split:
        split_job=(root/room_split['job']).resolve()
        if not (split_job/'measurement_edits.sqlite3').is_file():raise ValueError('Floor cost division has no saved measurement history')
        split_store=MeasurementStore(split_job)
        if split_store.config_hash!=room_split['config_sha256']:raise ValueError('Floor cost division mapping changed')
        split_state=split_store.read()
        state,room_ids=split_room_at_boundary(state,room_ids,split_state,room_split)
        split_review={**room_split,'measurement_version':split_state['version'],
                      'points':split_state['measurements'][room_split['measurement_id']]['points']}
    result=net_floor_area(state,room_ids,store.read(),config['measurement_ids'],include_rooms)
    if split_review:result['room_split']=split_review
    return {**result,'job':str(job),'config_sha256':store.config_hash,
            'source_file':str(source),'source_sha256':config['source_sha256'],
            'basis':config['basis']}
