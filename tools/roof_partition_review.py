"""Measure roof overlaps and uncovered scope without snapping source geometry."""
import hashlib
import json
import math
import sys
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import polygonize, unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from area_cutouts import cutout_issues


def audit_faces(measurements, expected_outline=None, cutout_terms=None):
    """Audit one calibrated view; optional outline is an independent scope input.

    Surface bounds apply only to covered area. Where overlapping faces specify
    different slopes, retain the range instead of selecting a winner.
    Bounds assume one exposed surface per plan position; stacked roof levels
    may both require material and must be reviewed before any deduction.
    """
    if not measurements or len({m['id'] for m in measurements}) != len(measurements):
        raise ValueError('Unique roof measurements required')
    frames = {(m['page'], m['points_per_foot'], m['width_pt'], m['height_pt']) for m in measurements}
    if len(frames) != 1:
        raise ValueError('Roof faces must share one page, coordinate frame and scale')
    scale = measurements[0]['points_per_foot']
    if type(scale) not in (float,int) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Positive finite scale required')
    polygons = []
    factors = []
    for m in measurements:
        if m['kind'] != 'area': raise ValueError('Roof area geometry required')
        points = m['points']
        if any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Finite roof coordinates required')
        poly = Polygon(points)
        if not poly.is_valid or poly.is_empty or poly.area <= 0:
            raise ValueError('Valid roof polygon required')
        factor = m.get('surface_factor')
        if type(factor) not in (float,int) or not math.isfinite(factor) or factor < 1:
            raise ValueError('Explicit finite roof slope factor required')
        polygons.append(poly); factors.append(factor)
    deductions=[]
    if cutout_terms is not None:
        by_id={m['id']:m for m in measurements}
        ids=[t.get('measurement_id') for t in cutout_terms]
        if (len(ids)!=len(set(ids)) or set(ids)!=set(by_id) or any(
                t.get('kind')!='area' or t.get('operation') not in ('add','deduct') or
                (t['operation']=='deduct')!=('cutout_of' in t) for t in cutout_terms)):
            raise ValueError('Every roof component needs one explicit add or parent-linked deduction')
        issues=cutout_issues(by_id,cutout_terms)
        if issues:raise ValueError('Invalid roof cutout: '+issues[0]['reason'])
        shapes={m['id']:polygon for m,polygon in zip(measurements,polygons)}
        kept=[];resolved=[];kept_factors=[]
        for m,polygon,factor in zip(measurements,polygons,factors):
            term=next(t for t in cutout_terms if t['measurement_id']==m['id'])
            if term['operation']=='deduct':continue
            children=[t['measurement_id'] for t in cutout_terms if t.get('cutout_of')==m['id']]
            if children:
                polygon=polygon.difference(unary_union([shapes[child] for child in children]))
                deductions.append({'parent_id':m['id'],'cutout_ids':children,
                    'deducted_projected_sf':sum(shapes[c].area for c in children)/scale**2})
            kept.append(m);resolved.append(polygon);kept_factors.append(factor)
        measurements=kept;polygons=resolved;factors=kept_factors
    combined = unary_union(polygons)
    cells = []
    for cell in polygonize(unary_union([p.boundary for p in polygons])):
        point = cell.representative_point()
        owners = [i for i,p in enumerate(polygons) if p.covers(point)]
        if not owners: continue
        overlap={}
        if len(owners)>1:
            shape=cell.normalize()
            source_ids=sorted(measurements[i]['id'] for i in owners)
            identity=hashlib.sha256(shape.wkb+json.dumps(source_ids).encode()).hexdigest()[:16]
            overlap={'id':'roof-overlap-'+identity,'page':measurements[0]['page'],
                'points_per_foot':scale,'points':[list(p) for p in shape.exterior.coords[:-1]],
                'holes':[[list(p) for p in ring.coords[:-1]] for ring in shape.interiors]}
        cells.append({'area_sf':cell.area/scale**2,
                      'source_ids':[measurements[i]['id'] for i in owners],
                      **overlap,
                      'minimum_surface_factor':min(factors[i] for i in owners),
                      'maximum_surface_factor':max(factors[i] for i in owners)})
    union_area = combined.area/scale**2
    if not math.isclose(sum(c['area_sf'] for c in cells), union_area, rel_tol=1e-9, abs_tol=1e-8):
        raise ValueError('Partition does not reconcile to the polygon union')
    parts = list(combined.geoms) if combined.geom_type == 'MultiPolygon' else [combined]
    def regions(shape):
        parts=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]
        return [{'points':[list(p) for p in part.exterior.coords[:-1]],
            'holes':[[list(p) for p in ring.coords[:-1]] for ring in part.interiors],
            'projected_area_sf':part.area/scale**2} for part in parts if not part.is_empty]
    coverage = None
    if expected_outline is not None:
        outline = Polygon(expected_outline)
        if not outline.is_valid or outline.is_empty or outline.area <= 0:
            raise ValueError('Valid independently reviewed outline required')
        coverage = {'expected_projected_sf':outline.area/scale**2,
                    'missing_projected_sf':outline.difference(combined).area/scale**2,
                    'outside_projected_sf':combined.difference(outline).area/scale**2,
                    'missing_regions':regions(outline.difference(combined)),
                    'outside_regions':regions(combined.difference(outline))}
        coverage['symmetric_difference_percent'] = (
            (coverage['missing_projected_sf']+coverage['outside_projected_sf']) /
            coverage['expected_projected_sf']*100)
    face_references=[{'measurement_id':m['id'],'label':m.get('label',m['id']),'page':m['page'],
        'projected_area_sf':polygon.area/scale**2,'surface_factor':factor,
        'surface_area_sf':polygon.area*factor/scale**2,
        'cutout_ids':next((d['cutout_ids'] for d in deductions if d['parent_id']==m['id']),[]),
        'pitch_is_inferred':m.get('source_pitch_evidence',{}).get('pitch_is_inferred',False),
        'pitch_evidence':m.get('source_pitch_evidence',m.get('pitch_candidate')),
        **({'pitch_candidates':m['pitch_candidates']} if 'pitch_candidates' in m else {})}
        for m,polygon,factor in zip(measurements,polygons,factors)]
    return {'face_count':len(polygons),'face_references':face_references,'connected_components':len(parts),
            'interior_hole_count':sum(len(p.interiors) for p in parts),
            'raw_projected_sum_sf':sum(p.area for p in polygons)/scale**2,
            'projected_union_sf':union_area,
            'overlap_excess_sf':(sum(p.area for p in polygons)-combined.area)/scale**2,
            'overlapped_footprint_sf':sum(c['area_sf'] for c in cells if len(c['source_ids'])>1),
            'raw_sloped_sum_sf':sum(p.area*f for p,f in zip(polygons,factors))/scale**2,
            'covered_sloped_lower_sf':sum(c['area_sf']*c['minimum_surface_factor'] for c in cells),
            'covered_sloped_upper_sf':sum(c['area_sf']*c['maximum_surface_factor'] for c in cells),
            'surface_bounds_assumption':'One exposed surface per plan position; stacked roof levels require separate scope review',
            'coverage':coverage,'parent_cutout_deductions':deductions,
            'enclosed_voids':[region for part in parts for ring in part.interiors for region in regions(Polygon(ring))],
            'overlap_cells':[c for c in cells if len(c['source_ids'])>1],
            'geometry_changed':False,'certified':False,'order_released':False}
