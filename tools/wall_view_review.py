"""Validate the drawing-specific view and wall-face style examples for extraction.

This records a reviewer's source interpretation, not automatic wall approval.
"""
import hashlib
import json
import math
from pathlib import Path
import fitz


def read_wall_view_review(job,floor_page):
    job=Path(job);path=job/'floor_wall_view_review.json'
    if not path.exists():return None
    raw=path.read_bytes();review=json.loads(raw)
    if review.get('extraction_method','stroked') not in ('stroked','filled_and_stroked'):
        raise ValueError('Unknown wall-view extraction method')
    digest=hashlib.sha256((job/'plan.pdf').read_bytes()).hexdigest()
    if review.get('plan_sha256')!=digest:raise ValueError('Wall view belongs to another drawing')
    if type(floor_page) is not int or type(review.get('page')) is not int or review['page']!=floor_page:
        raise ValueError('Wall view must use the reviewed floor-plan page')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Wall view requires a reviewer and scope explanation')
    bounds=review.get('view_bounds_pt');anchors=review.get('wall_face_examples')
    if not isinstance(bounds,list) or len(bounds)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds):
        raise ValueError('Wall view requires finite rectangle coordinates')
    if not isinstance(anchors,list) or len(anchors)<2:
        raise ValueError('Review at least two wall-face examples in both axes')
    with fitz.open(job/'plan.pdf') as doc:
        if not 1<=floor_page<=len(doc):raise ValueError('Wall view page is outside the drawing')
        page=doc[floor_page-1];a,b,c,d=bounds
        if not 0<=a<c<=page.rect.width or not 0<=b<d<=page.rect.height:
            raise ValueError('Wall view rectangle is outside the drawing')
        drawings=page.get_drawings();styles=[];axes=set();seen=set()
        for anchor in anchors:
            ref,item=anchor.get('path'),anchor.get('item')
            if (type(ref) is not int or type(item) is not int or not 0<=ref<len(drawings)
                    or not 0<=item<len(drawings[ref]['items']) or (ref,item) in seen):
                raise ValueError('Invalid or repeated wall-face example')
            seen.add((ref,item));drawing=drawings[ref];edge=drawing['items'][item]
            color=drawing.get('color');width=drawing.get('width')
            if (drawing['type']!='s' or edge[0]!='l' or color is None or min(color)>=.99
                    or drawing.get('stroke_opacity',1)<=0 or drawing.get('dashes') not in ('[] 0',None)
                    or type(width) not in (int,float) or not math.isfinite(width) or width<=0):
                raise ValueError('Wall-face example must be a visible solid line')
            points=[list(p) for p in edge[1:]]
            if points!=anchor.get('points_pt') or any(not a<=x<=c or not b<=y<=d for x,y in points):
                raise ValueError('Wall-face evidence differs or lies outside the selected view')
            x,y=points
            axis=0 if abs(x[1]-y[1])<.001 else 1 if abs(x[0]-y[0])<.001 else None
            if axis is None or math.dist(x,y)<1:raise ValueError('Wall-face example must have a usable orthogonal span')
            axes.add(axis);style={'color':list(color),'width_pt':round(width,5)}
            if style not in styles:styles.append(style)
        if axes!={0,1}:raise ValueError('Wall-face examples must include both drawing axes')
    return {**review,'review_sha256':hashlib.sha256(raw).hexdigest(),'allowed_styles':styles,
        'scope_certified':False,'method':'reviewed plan view and wall-face stroke examples'}
