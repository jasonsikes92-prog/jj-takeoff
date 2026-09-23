"""Calculate reviewed ceiling surfaces without treating partial coverage as complete."""
import copy
import hashlib
import json
import math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union


def partitioned_surface(region,decision):
    """Require a complete, nonoverlapping partition before totaling mixed ceilings."""
    parts=decision.get('parts');seen=set();shapes=[];surfaces=[]
    if not isinstance(parts,list) or len(parts)<2:raise ValueError('Mixed ceiling needs at least two reviewed parts')
    scale=region['points_per_foot'];room=Polygon(region['points'],region['holes'])
    tolerance=scale**2*1e-8
    pitches={n['rise_inches']/n['run_inches']*12 for n in region['ceiling_notes'] if n['kind']=='vault_pitch'}
    for part in parts:
        identity=part.get('id');rise=part.get('rise_per_12')
        if not isinstance(identity,str) or not identity or identity in seen:raise ValueError('Unique ceiling part IDs required')
        seen.add(identity)
        if not isinstance(part.get('basis'),str) or not part['basis'].strip():raise ValueError('Each ceiling part needs source basis')
        if type(rise) not in (int,float) or not math.isfinite(rise) or rise<0:raise ValueError('Finite nonnegative ceiling part pitch required')
        if pitches and rise and rise not in pitches:raise ValueError('Ceiling part pitch conflicts with drawing notes')
        rings=[part.get('points',[]),*part.get('holes',[])]
        if any(len(r)<3 or any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in r) for r in rings):
            raise ValueError('Ceiling part needs finite polygon coordinates')
        shape=Polygon(rings[0],rings[1:])
        if not shape.is_valid or shape.area<=0 or shape.difference(room).area>tolerance:
            raise ValueError('Ceiling part must be valid and inside its room')
        if any(shape.intersection(other).area>tolerance for other in shapes):raise ValueError('Ceiling parts overlap')
        shapes.append(shape)
        area=shape.area/scale**2
        surfaces.append({**copy.deepcopy(part),'projected_area_sf':area,'surface_area_sf':area*math.hypot(1,rise/12)})
    if room.symmetric_difference(unary_union(shapes)).area>tolerance:raise ValueError('Ceiling parts leave uncovered room area')
    if pitches and not pitches.issubset({p['rise_per_12'] for p in parts}):raise ValueError('Ceiling partition omits noted vault pitch')
    if any(n['kind'] in ('vaulted','vault_pitch') for n in region['ceiling_notes']) and not any(p['rise_per_12'] for p in parts):
        raise ValueError('Flat ceiling parts conflict with vault notes')
    return surfaces


def binding(plan_sha256,region):
    fields=('id','page','points_per_foot','points','holes','ceiling_notes')
    return hashlib.sha256(json.dumps({'plan_sha256':plan_sha256,
        'region':{k:region[k] for k in fields}},sort_keys=True,allow_nan=False).encode()).hexdigest()


def apply(result,review):
    output=copy.deepcopy(result);regions={r['id']:r for r in output['regions']};seen=set();stale=[]
    for r in regions.values():r['ceiling_surface']={'status':'unreviewed','surface_area_sf':None,'purchase_quantity':None}
    if review is not None:
        if review.get('plan_sha256')!=result['plan_sha256']:raise ValueError('Ceiling surfaces belong to another drawing')
        if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():raise ValueError('Ceiling reviewer required')
        if not isinstance(review.get('decisions'),list):raise ValueError('Ceiling decisions required')
        for d in review['decisions']:
            identity=d.get('region_id')
            if not isinstance(identity,str) or not identity or identity in seen:raise ValueError('Ceiling decisions need unique region IDs')
            seen.add(identity)
            if not isinstance(d.get('basis'),str) or not d['basis'].strip():raise ValueError('Ceiling source basis required')
            if d.get('scope')!='entire_region':raise ValueError('Ceiling review must explicitly cover the entire region')
            mixed=d.get('surface_type')=='partitioned'
            if d.get('surface_type') not in ('flat','uniform_pitch','partitioned'):raise ValueError('Unknown ceiling surface type')
            rise=d.get('rise_per_12')
            if mixed and rise is not None:raise ValueError('Partitioned ceiling uses individual part pitches')
            if not mixed:
                if type(rise) not in (int,float) or not math.isfinite(rise) or rise<0:raise ValueError('Finite nonnegative ceiling pitch required')
                if (rise==0)!=(d['surface_type']=='flat'):raise ValueError('Ceiling type and pitch disagree')
            r=regions.get(identity)
            if r is None or d.get('source_sha256')!=binding(result['plan_sha256'],r):
                stale.append(identity)
                if r:r['ceiling_surface']['status']='stale_source_review'
                continue
            if r['ceiling_reference']['status']=='conflicting_notes':raise ValueError('Resolve conflicting ceiling notes before surface review')
            if mixed:
                parts=partitioned_surface(r,d)
                r['ceiling_surface']={'status':'current_source_review','scope':d['scope'],'surface_type':'partitioned',
                    'parts':parts,'projected_area_sf':math.fsum(p['projected_area_sf'] for p in parts),
                    'surface_area_sf':math.fsum(p['surface_area_sf'] for p in parts),
                    'basis':d['basis'],'reviewer':review['reviewer'],'source_sha256':d['source_sha256'],
                    'purchase_quantity':None,'finish_material':None}
                continue
            if d['surface_type']=='flat' and any(n['kind'] in ('vaulted','vault_pitch') for n in r['ceiling_notes']):
                raise ValueError('Flat ceiling review conflicts with current vault notes')
            pitches={n['rise_inches']/n['run_inches']*12 for n in r['ceiling_notes'] if n['kind']=='vault_pitch'}
            if pitches and pitches!={rise}:raise ValueError('Ceiling review pitch conflicts with current drawing notes')
            projected=Polygon(r['points'],r['holes']).area/r['points_per_foot']**2
            factor=math.hypot(1,rise/12)
            r['ceiling_surface']={'status':'current_source_review','scope':d['scope'],'surface_type':d['surface_type'],
                'projected_area_sf':projected,'rise_per_12':rise,'surface_factor':factor,
                'surface_area_sf':projected*factor,'basis':d['basis'],'reviewer':review['reviewer'],
                'source_sha256':d['source_sha256'],'purchase_quantity':None,'finish_material':None}
    surfaces=[r['ceiling_surface'] for r in regions.values() if r['ceiling_surface']['status']=='current_source_review']
    missing=[r['id'] for r in regions.values() if r['ceiling_surface']['status']!='current_source_review']
    output['ceiling_surface_review']={'reviewed_region_count':len(surfaces),'unreviewed_region_ids':missing,
        'stale_or_missing_region_ids':stale,
        'reviewed_surface_subtotal_sf':math.fsum(s['surface_area_sf'] for s in surfaces) if surfaces else None,
        'all_represented_regions_reviewed':bool(regions) and not missing and not stale,
        'whole_house_ceiling_surface_sf':None,'purchase_quantity':None,'estimate_released':False}
    digest=hashlib.sha256(json.dumps(review,sort_keys=True,allow_nan=False).encode()).hexdigest()
    output['source_sha256']=hashlib.sha256(json.dumps([result['source_sha256'],digest]).encode()).hexdigest()
    return output


def read_review(folder):
    path=Path(folder)/'ceiling_surface_review.json'
    return json.loads(path.read_bytes()) if path.exists() else None
