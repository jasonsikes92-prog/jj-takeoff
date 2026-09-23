"""Recalculate draft supply pools from current measured tile fields and dated products."""
import copy
import hashlib
import json
import math
from pathlib import Path
from shapely.geometry import shape
from floor_sundries import calculate_pooled_allowance


def import_purchases(draft,folder):
    root=Path(folder).resolve();path=root/'floor_supply_purchase_review.json'
    raw=path.read_bytes();config=json.loads(raw);review=draft.get('tile_underlayment_review')
    if (not review or config['plan_sha256']!=draft['plan_sha256']
            or review['plan_sha256']!=draft['plan_sha256']
            or review['measurement_version']!=draft['measurement_version']):
        raise ValueError('Floor supply pools need current source-bound tile fields')
    if 'floor_supply_purchase_review' in draft:raise ValueError('Floor supply pools already imported')
    fields={f['id']:f for f in review['fields']};seen=set();pool_ids=set();pools=[]
    if not config['pools']:raise ValueError('Floor supply review needs at least one product pool')
    for pool in config['pools']:
        identity=pool['id'];ids=pool['field_ids']
        if (not identity or identity in pool_ids or not ids or len(ids)!=len(set(ids))
                or seen.intersection(ids) or not set(ids).issubset(fields)):
            raise ValueError('Floor supply pools need distinct current fields and pool identities')
        pool_ids.add(identity);seen.update(ids)
        source=(root/pool['source_file']).resolve()
        if (not source.is_relative_to(root) or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest()!=pool['source_sha256']):
            raise ValueError('Floor supply product or assignment evidence changed')
        proof=json.loads(source.read_bytes())
        if proof['plan_sha256']!=draft['plan_sha256'] or proof['field_ids']!=ids:
            raise ValueError('Floor supply product assignment differs from its reviewed evidence')
        selected=[fields[i] for i in ids];geometry=[];thickness=proof['products']['board'].get('thickness_inches')
        if thickness is not None and (type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0):
            raise ValueError('Board product thickness must be positive and finite')
        for field in selected:
            if field['underlayment']!='cement_board':raise ValueError('Board supply pool assigned to a different underlayment practice')
            required=field['board_thickness_inches']
            if thickness is not None and required is not None and not math.isclose(thickness,required):
                raise ValueError('Board product thickness conflicts with the saved floor requirement')
            polygon=shape(field['geometry_ft'])
            if not math.isclose(polygon.area,field['net_sf'],abs_tol=1e-7):
                raise ValueError('Floor supply geometry and measured area disagree')
            geometry.append({'id':field['id'],'geometry':polygon})
        calculation=calculate_pooled_allowance(geometry,proof['products'])
        pools.append({'id':identity,'field_ids':list(ids),'source_file':pool['source_file'],
            'source_sha256':pool['source_sha256'],'calculation':calculation,
            'required_board_thickness_inches':{f['id']:f['board_thickness_inches'] for f in selected},
            'product_thickness_verified':thickness is not None and all(f['board_thickness_inches'] is not None for f in selected),
            'current_supplier_price_verified':False})
    result=copy.deepcopy(draft)
    result['floor_supply_purchase_review']={'plan_sha256':draft['plan_sha256'],
        'measurement_version':draft['measurement_version'],'mapping_sha256':hashlib.sha256(raw).hexdigest(),
        'tile_field_mapping_sha256':review['mapping_sha256'],'pools':pools,
        'unassigned_field_ids':[f for f in fields if f not in seen],
        'included_in_estimate_total':False,'ready_to_order':False,
        'remaining':['Product compatibility and installation details remain subject to review.',
            'Resolve unassigned fields and full trade coverage; pooled candidate costs are not added to estimate rows.']}
    return result
