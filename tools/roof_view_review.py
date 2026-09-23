"""Read a source-bound roof viewport; selecting a view does not calibrate it."""
import hashlib
import json
import math
from pathlib import Path
import fitz


def read_roof_view_review(job,roof_page):
    job=Path(job);path=job/'roof_view_review.json'
    if not path.exists():return None
    raw=path.read_bytes();review=json.loads(raw)
    if review.get('plan_sha256')!=hashlib.sha256((job/'plan.pdf').read_bytes()).hexdigest():
        raise ValueError('Roof view belongs to another drawing')
    if type(roof_page) is not int or type(review.get('page')) is not int or review['page']!=roof_page:
        raise ValueError('Roof view must use the reviewed roof-plan page')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Roof view requires a reviewer and scope explanation')
    bounds=review.get('view_bounds_pt')
    if not isinstance(bounds,list) or len(bounds)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds):
        raise ValueError('Roof view requires finite rectangle coordinates')
    styles=[]
    with fitz.open(job/'plan.pdf') as doc:
        if not 1<=roof_page<=len(doc):raise ValueError('Roof view page is outside the drawing')
        page=doc[roof_page-1];a,b,c,d=bounds
        if not 0<=a<c<=page.rect.width or not 0<=b<d<=page.rect.height:
            raise ValueError('Roof view rectangle is outside the drawing')
        if 'roof_edge_examples' in review:
            examples=review['roof_edge_examples']
            if not isinstance(examples,list) or len(examples)<2:
                raise ValueError('Review at least two roof-edge examples')
            drawings=page.get_drawings();seen=set()
            for example in examples:
                ref,item=example.get('path'),example.get('item')
                if (type(ref) is not int or type(item) is not int or not 0<=ref<len(drawings)
                        or not 0<=item<len(drawings[ref]['items']) or (ref,item) in seen):
                    raise ValueError('Invalid or repeated roof-edge example')
                seen.add((ref,item));drawing=drawings[ref];edge=drawing['items'][item]
                color=drawing.get('color');width=drawing.get('width')
                if (drawing['type']!='s' or edge[0]!='l' or color is None or min(color)>=.99
                        or drawing.get('stroke_opacity',1)<=0 or drawing.get('dashes') not in ('[] 0',None)
                        or type(width) not in (int,float) or not math.isfinite(width) or width<=0):
                    raise ValueError('Roof-edge example must be a visible solid line')
                points=[list(p) for p in edge[1:]]
                if (points!=example.get('points_pt') or math.dist(*points)<1
                        or any(not a<=x<=c or not b<=y<=d for x,y in points)):
                    raise ValueError('Roof-edge evidence differs or lies outside the selected view')
                style={'color':list(color),'width_pt':round(width,5)}
                if style not in styles:styles.append(style)
    return {**review,'review_sha256':hashlib.sha256(raw).hexdigest(),
        **({'allowed_styles':styles} if styles else {}),
        'scope_certified':False,'method':'reviewed roof-plan viewport; independent calibration required'}
