"""Validate an independently traced roof contour against native source strokes."""
import hashlib
import json
import math
from pathlib import Path
import fitz
from shapely.geometry import LineString,Polygon
from shapely.ops import unary_union
from roof_partition_review import audit_faces


def read_review(job,plan_sha256,page):
    job=Path(job);path=job/'roof_coverage_review.json'
    if not path.exists():return None
    raw=path.read_bytes();review=json.loads(raw)
    if review.get('plan_sha256')!=plan_sha256:raise ValueError('Roof outline belongs to another drawing')
    if type(page) is not int or type(review.get('page')) is not int or review['page']!=page:
        raise ValueError('Roof outline must use the selected roof page')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Roof outline requires reviewer and scope explanation')
    with fitz.open(job/'plan.pdf') as doc:
        if not 1<=page<=len(doc):raise ValueError('Roof outline page is outside the drawing')
        source=doc[page-1];points=review.get('points',[])
        audit_faces([{'id':'outline','page':page,'kind':'area','points':points,'surface_factor':1,
            'points_per_foot':1,'width_pt':source.rect.width,'height_pt':source.rect.height}])
        if any(not 0<=x<=source.rect.width or not 0<=y<=source.rect.height for x,y in points):
            raise ValueError('Roof outline is outside the page')
        refs=review.get('source_cad_paths');drawings=source.get_drawings()
        if not isinstance(refs,list) or not refs or any(type(i) is not int or not 0<=i<len(drawings) for i in refs):
            raise ValueError('Roof outline requires source CAD paths')
        tolerance=review.get('source_tolerance_pt',.001)
        if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not .001<=tolerance<=.25:
            raise ValueError('Source tolerance must be between .001 and .25 PDF points')
        if tolerance>.001 and (not isinstance(review.get('tolerance_basis'),str) or not review['tolerance_basis'].strip()):
            raise ValueError('Expanded source tolerance requires an explicit basis')
        lines=[]
        for ref in refs:
            drawing=drawings[ref]
            if (drawing.get('type')!='s' or drawing.get('stroke_opacity',1)<=0 or drawing.get('color') is None
                    or drawing.get('dashes') not in ('[] 0',None)):
                raise ValueError('Roof contour requires visible solid source lines')
            if tolerance>.001 and tolerance>drawing.get('width',0)/2:
                raise ValueError('Source tolerance exceeds the printed stroke half-width')
            for item in drawing['items']:
                if item[0]=='l':lines.append(LineString([tuple(item[1]),tuple(item[2])]))
                elif item[0]=='re':
                    rect=item[1];corners=[rect.tl,rect.tr,rect.br,rect.bl,rect.tl]
                    lines.extend(LineString([tuple(a),tuple(b)]) for a,b in zip(corners,corners[1:]))
        if not lines or not Polygon(points).boundary.difference(unary_union(lines).buffer(tolerance)).is_empty:
            raise ValueError('Roof outline is not supported by its source strokes')
    return {**review,'review_sha256':hashlib.sha256(raw).hexdigest(),
        'source_tolerance_pt':tolerance,'scope_certified':False,'reviewer_identity_authenticated':False}
