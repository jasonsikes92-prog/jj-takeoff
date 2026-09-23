"""Derive a straight stair reference from source-bound finished dimensions."""
import copy
import hashlib
import json
import math
from pathlib import Path


def straight_stair(width_inches, total_rise_inches, tread_inches, max_riser_inches):
    for value in (width_inches,total_rise_inches,tread_inches,max_riser_inches):
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
            raise ValueError('Stair dimensions must be positive finite numbers')
    risers=math.ceil(total_rise_inches/max_riser_inches)
    treads=risers-1;rise=total_rise_inches/risers
    return {'riser_count':risers,'riser_height_inches':rise,'intermediate_treads':treads,
        'run_inches':treads*tread_inches,'tread_surface_sf':width_inches*treads*tread_inches/144,
        'intermediate_riser_face_sf':width_inches*treads*rise/144,
        'porch_edge_riser_face_sf':width_inches*rise/144,
        'two_side_faces_sf':tread_inches*rise*treads*(treads+1)/144,
        'gross_step_envelope_cf':width_inches*tread_inches*rise*treads*(treads+1)/2/1728}


def import_stair(draft,config,folder):
    root=Path(folder).resolve();path=(root/config['source_file']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=config['source_sha256']:
        raise ValueError('Stair dimension evidence missing or changed')
    source=json.loads(path.read_bytes())
    if source['plan_sha256']!=draft['plan_sha256'] or config['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Stair reference belongs to another drawing')
    if 'stair_quantity_review' in draft:raise ValueError('Stair reference already imported')
    dimensions=source['dimensions'];geometry=straight_stair(**dimensions)
    result=copy.deepcopy(draft)
    row=next(r for r in result['rows'] if r['row_id']==config['parent_row_id'])
    if row['cost_type']!='ASSEMBLY' or row.get('line_cost') is not None or row.get('covered_by_package'):
        raise ValueError('Stair reference needs an unpriced assembly')
    if geometry['intermediate_treads']!=source['owner_intermediate_step_count']:
        raise ValueError('Stair dimensions conflict with owner step count; review layout')
    for key,label,unit in [('riser_count','Finished risers','EA'),('intermediate_treads','Intermediate brick treads','EA'),
        ('tread_surface_sf','Tread surface reference','SF'),('intermediate_riser_face_sf','Intermediate riser face reference','SF'),
        ('two_side_faces_sf','Both step side faces reference','SF')]:
        row.setdefault('assembly_inputs',[]).append({'id':config['id']+'-'+key,'label':label,
            'quantity':geometry[key],'unit':unit,'use':'assembly_input','measurement_ids':[],
            'source_kind':'owner_dimensions','source':{'file':str(path),'sha256':config['source_sha256']},
            'basis':source['basis'],'remaining':source['remaining'],'certified':False,'order_released':False})
    result['stair_quantity_review']={'id':config['id'],'dimensions':dimensions,**geometry,
        'basis':source['basis'],'remaining':source['remaining'],'source_sha256':config['source_sha256'],
        'code_compliance_certified':False,'brick_purchase_count':None,'concrete_purchase_cy':None}
    result.update(whole_house_total=None,estimate_released=False)
    return result
