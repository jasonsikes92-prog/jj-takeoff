"""Bind reviewed tile/substrate assignments to current measured floor geometry."""
import copy
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import Polygon,mapping
from shapely.affinity import scale as scale_geometry,translate
from shapely.ops import unary_union
from measurement_store import calculate


def import_underlayment(draft, state, folder):
    root=Path(folder).resolve();path=root/'tile_underlayment_review.json'
    raw=path.read_bytes();config=json.loads(raw)
    if (state is None or state['plan_sha256']!=draft['plan_sha256']
            or config['plan_sha256']!=draft['plan_sha256']
            or state['version']!=draft['measurement_version']):
        raise ValueError('Tile underlayment needs the current drawing and measurement revision')
    source=(root/config['source_file']).resolve()
    if (not source.is_relative_to(root) or not source.is_file()
            or hashlib.sha256(source.read_bytes()).hexdigest()!=config['source_sha256']):
        raise ValueError('Tile substrate assignment evidence changed')
    proof=json.loads(source.read_bytes())
    if any(proof.get(k)!=config[k] for k in ('plan_sha256','groups')):
        raise ValueError('Tile substrate assignments differ from their reviewed evidence')
    if 'tile_underlayment_review' in draft:raise ValueError('Tile underlayment already imported')
    specs=[s for s in draft['company_scope_review']['specifications']
           if s['source_rule']=='tile.floor_underlayment_by_substrate']
    if len(specs)!=1:raise ValueError('Tile underlayment needs one frozen company specification')
    spec=specs[0];groups=config['groups'];seen=set();fields=[];domains=[]
    if not groups:raise ValueError('Tile substrate assignment needs measured fields')
    for group in groups:
        identity=group['id'];refs=group['measurement_ids'];deduct=group.get('deduction_ids',[])
        if (not isinstance(identity,str) or not identity or identity in seen or not group.get('basis')
                or not refs or len(refs+deduct)!=len(set(refs+deduct))):
            raise ValueError('Tile fields need unique identities, measurements and a source basis')
        seen.add(identity)
        substrate=group['substrate'];practice=spec['value'].get(substrate)
        if substrate not in ('wood_floor','concrete_slab') or not practice:
            raise ValueError('Tile field substrate has no saved specification')
        measurements=[state['measurements'][i] for i in refs+deduct]
        first=measurements[0];scale=first['points_per_foot'];page=first['page']
        for m in measurements:
            calculate(m)
            if (m['kind']!='area' or m.get('surface_factor',1)!=1 or m['page']!=page
                    or not math.isclose(m['points_per_foot'],scale,rel_tol=1e-12)):
                raise ValueError('Tile field requires flat areas on one calibrated sheet')
        rooms=[Polygon(m['points']) for m in measurements[:len(refs)]]
        holes=[Polygon(m['points']) for m in measurements[len(refs):]]
        gross=unary_union(rooms);removed=unary_union(holes)
        outside=removed.difference(gross).area
        clip=group.get('clip_deductions_to_field',False)
        if type(clip) is not bool:raise ValueError('Tile deduction clipping must be explicit')
        if (not math.isclose(gross.area,sum(p.area for p in rooms),abs_tol=1e-7)
                or not math.isclose(removed.area,sum(p.area for p in holes),abs_tol=1e-7)
                or (outside>1e-7 and not clip)):
            raise ValueError('Tile areas overlap or deductions extend outside their floor field')
        if any(h.intersection(gross).area<=1e-7 for h in holes):
            raise ValueError('Tile deduction does not intersect its floor field')
        removed=removed.intersection(gross)
        net=gross.difference(removed)
        if net.area<=0:raise ValueError('Tile field has no remaining floor area')
        for other_page,other_scale,other in domains:
            if page==other_page:
                if not math.isclose(scale,other_scale,rel_tol=1e-12) or gross.intersection(other).area>1e-7:
                    raise ValueError('Tile substrate fields overlap or disagree on sheet scale')
        domains.append((page,scale,gross))
        thickness=spec['value'].get('wood_floor_board_thickness_inches') if substrate=='wood_floor' and practice=='cement_board' else None
        if thickness is not None and (type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0):
            raise ValueError('Tile board thickness must be positive and finite')
        origin=net.bounds[:2]
        feet=scale_geometry(translate(net,-origin[0],-origin[1]),1/scale,1/scale,origin=(0,0))
        fields.append({'id':identity,'substrate':substrate,'underlayment':practice,
            'board_thickness_inches':thickness,'measurement_ids':list(refs),'deduction_ids':list(deduct),
            'gross_sf':gross.area/scale**2,'deducted_sf':removed.area/scale**2,'net_sf':net.area/scale**2,
            'deduction_outside_field_sf':outside/scale**2,
            'geometry_ft':json.loads(json.dumps(mapping(feet))),
            'coordinate_origin_plan_points':list(origin),'plan_pdf_page':page,
            'basis':group['basis'],'purchase_quantity':None})
    result=copy.deepcopy(draft)
    result['tile_underlayment_review']={'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
        'intake_sha256':spec['intake_sha256'],'source_rule':spec['source_rule'],
        'mapping_sha256':hashlib.sha256(raw).hexdigest(),'source_sha256':config['source_sha256'],
        'fields':fields,'whole_house_coverage_verified':False,'ready_to_order':False,
        'remaining':['Only explicitly assigned tile fields are included; verify complete room coverage.',
            'Choose products and calculate layout, waste, whole purchase units and installation supplies before ordering.']}
    return result
