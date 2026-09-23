"""Recover reviewed colored area outlines using independently calibrated linework."""
import hashlib
import json
import math
from pathlib import Path
import fitz
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union


def registered_scale(reference_page,target_page,calibration,anchors,reference_bounds,target_bounds):
    """Transfer scale between matching unrotated views, retaining line evidence."""
    scale=calibration.get('points_per_foot')
    if (not calibration.get('usable_candidate') or calibration.get('mixed_view_scales')
            or type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0
            or {c['axis'] for c in calibration['controls']}!={'horizontal','vertical'}):
        raise ValueError('Source scale needs agreeing horizontal and vertical dimensions')
    drawings=[reference_page.get_drawings(),target_page.get_drawings()]
    bounds=[box(*reference_bounds),box(*target_bounds)]
    def edge(side,ref):
        path=drawings[side][ref['path']];item=path['items'][ref['item']]
        if item[0]!='l':raise ValueError('Registration anchor must be a native line')
        points=np.array(sorted([tuple(item[1]),tuple(item[2])]))
        if not all(bounds[side].covers(Point(p)) for p in points):raise ValueError('Anchor outside reviewed view')
        return points,path
    pairs=[];styles=[set(),set()];axes=set()
    def style(path):return (path['type'],tuple(path['color'] or []),round(path['width'] or 0,5))
    for anchor in anchors:
        a,da=edge(0,anchor['reference']);b,db=edge(1,anchor['target'])
        delta=a[1]-a[0];target_delta=b[1]-b[0];axis=int(np.argmax(abs(delta)))
        if abs(delta[1-axis])>.01 or abs(target_delta[1-axis])>.01 or delta[axis]<=0 or target_delta[axis]<=0:
            raise ValueError('Anchors require corresponding horizontal or vertical directions')
        ratio=target_delta[axis]/delta[axis]
        pairs.append((a,b,ratio,delta[axis]));axes.add(axis)
        styles[0].add(style(da));styles[1].add(style(db))
    if axes!={0,1}:raise ValueError('Two-axis view anchors required')
    ratio=max(pairs,key=lambda p:p[3])[2]
    if any(abs(p[2]/ratio-1)>.005 for p in pairs):raise ValueError('View anchor scales disagree')
    offset=np.median(np.vstack([b-a*ratio for a,b,_,_ in pairs]),axis=0)
    def segments(side):
        result=[]
        for i,path in enumerate(drawings[side]):
            if style(path) not in styles[side]:continue
            for j,item in enumerate(path['items']):
                if item[0]!='l':continue
                points=np.array(sorted([tuple(item[1]),tuple(item[2])]))
                if not all(bounds[side].covers(Point(p)) for p in points):continue
                if np.linalg.norm(points[1]-points[0])<20:continue
                result.append((i,j,points))
        return result
    source,target=segments(0),segments(1)
    if not target:raise ValueError('No matching target linework')
    tree=cKDTree([p.flatten() for _,_,p in target]);matches=[];used=set()
    for i,j,points in source:
        distance,index=tree.query((points*ratio+offset).flatten(),p=np.inf)
        if distance>.15 or index in used:continue
        used.add(index);other=target[index]
        matches.append({'reference_path':i,'reference_item':j,'reference_points':points.tolist(),
            'target_path':other[0],'target_item':other[1],'target_points':other[2].tolist()})
    if len(matches)<20:raise ValueError('Too few independent matching segments')
    a=np.vstack([m['reference_points'] for m in matches]);b=np.vstack([m['target_points'] for m in matches])
    design=np.zeros((len(a)*2,3));design[::2,0]=a[:,0];design[1::2,0]=a[:,1]
    design[::2,1]=1;design[1::2,2]=1
    ratio,dx,dy=np.linalg.lstsq(design,b.flatten(),rcond=None)[0]
    residual=float(np.max(abs(b-(a*ratio+[dx,dy]))))
    # Coverage is relative to relevant linework, not blank sheet margins.
    # Check both views so a small repeated corner cannot anchor a larger view.
    source_span=np.ptp(np.vstack([p for _,_,p in source]),axis=0)
    target_span=np.ptp(np.vstack([p for _,_,p in target]),axis=0)
    source_coverage=np.ptp(a,axis=0)/source_span
    target_coverage=np.ptp(b,axis=0)/target_span
    if ratio<=0 or residual>.15 or min(*source_coverage,*target_coverage)<.5:
        raise ValueError('View registration residual or spatial coverage failed')
    return {'points_per_foot':float(scale*ratio),'scale_ratio':float(ratio),'offset_pt':[float(dx),float(dy)],
        'maximum_endpoint_residual_pt':residual,'matched_segments':matches,
        'source_linework_coverage_by_axis':source_coverage.tolist(),
        'target_linework_coverage_by_axis':target_coverage.tolist(),
        'reference_calibration':calibration,'certified':False}


def filled_regions(page,view_bounds,fill_labels,registration):
    """Union same-color native triangles; a reviewed view keeps legend swatches out."""
    from native_hatch_regions import area_drawings
    scale=registration['points_per_foot'];bounds=box(*view_bounds);groups={}
    if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:raise ValueError('Valid transferred scale required')
    drawings=area_drawings(page)
    selectors={}
    for key,item in enumerate(fill_labels):
        paths=item.get('source_paths')
        if paths is not None:
            if (not paths or any(type(i) is not int or i<0 or i>=len(drawings) for i in paths)
                    or len(set(paths))!=len(paths)):raise ValueError('Invalid area source paths')
            selectors[key]=set(paths)
        for previous in range(key):
            if tuple(fill_labels[previous]['fill'])==tuple(item['fill']) and (paths is None or previous not in selectors):
                raise ValueError('Duplicate area fill mapping needs source paths')
    for i,path in enumerate(drawings):
        color=tuple(path['fill']) if path.get('fill') else None
        owners=[key for key,item in enumerate(fill_labels)
                if (i in selectors[key] if key in selectors else color==tuple(item['fill']))]
        if not owners:continue
        if len(owners)>1:raise ValueError('Area source path has multiple owners')
        key=owners[0]
        if color!=tuple(fill_labels[key]['fill']):raise ValueError('Area source path color changed')
        if not bounds.intersects(box(*path['rect'])):continue
        items=path['items']
        if not items or any(item[0]!='l' for item in items):raise ValueError('Area fill needs native straight closed edges')
        if any(tuple(items[j][2])!=tuple(items[(j+1)%len(items)][1]) for j in range(len(items))):
            raise ValueError('Area fill edges do not form one closed ring')
        polygon=Polygon([tuple(item[1]) for item in items])
        if not polygon.is_valid or polygon.area<=0:raise ValueError('Invalid filled area polygon')
        if not bounds.covers(polygon):raise ValueError('Filled area crosses reviewed view boundary')
        groups.setdefault(key,[]).append((i,polygon))
    if set(groups)!=set(range(len(fill_labels))):raise ValueError('A reviewed area color has no geometry')
    for key,paths in selectors.items():
        if paths!={i for i,_ in groups[key]}:raise ValueError('Area source paths outside view')
    measurements=[]
    for key,parts in groups.items():
        color=tuple(fill_labels[key]['fill'])
        merged=unary_union([p for _,p in parts])
        polygons=list(merged.geoms) if merged.geom_type=='MultiPolygon' else [merged]
        for polygon in polygons:
            if polygon.interiors:raise ValueError('Area with holes needs explicit parent and cutout measurements')
            normalized=polygon.normalize()
            identity=hashlib.sha256(normalized.wkb+json.dumps(color).encode()).hexdigest()[:16]
            measurements.append({'id':'native-area-'+identity,'label':fill_labels[key]['label'],'page':page.number+1,
                'kind':'area','points':[list(p) for p in normalized.exterior.coords[:-1]],
                'points_per_foot':scale,'width_pt':page.rect.width,'height_pt':page.rect.height,
                'color':'#'+''.join(f'{round(c*255):02x}' for c in color),'dependent_rows':[],
                'source_cad_paths':[i for i,p in parts if p.intersection(polygon).area>0],
                'source_hatch_paths':[h for i,p in parts if p.intersection(polygon).area>0
                                      for h in drawings[i].get('hatch_source_paths',[])],
                'source_method':'native backing and hatch polygons merged by reviewed color and view' if any(drawings[i].get('hatch_source_paths') for i,p in parts if p.intersection(polygon).area>0) else 'native filled polygons merged by reviewed color and view',
                'scope_status':'Drawing area reference; verify finish boundaries and trade-specific deductions before pricing',
                'scale_source':'cross-sheet native line registration to two-axis dimension controls'})
    return measurements


def from_review(job,plan_sha256,allowed_pages=None):
    path=Path(job)/'native_area_view_review.json'
    if not path.exists():return None
    raw=path.read_bytes();config=json.loads(raw);plan=Path(job)/'plan.pdf'
    if config['plan_sha256']!=plan_sha256 or hashlib.sha256(plan.read_bytes()).hexdigest()!=plan_sha256:
        raise ValueError('Area view belongs to another drawing')
    from dimension_scale import split_dimension_scale
    from sheet_scale_labels import scale_labels,corroborate_dimension_scale
    with fitz.open(plan) as doc:
        pages=[config['reference_page'],config['page']]
        if any(type(p) is not int or not 1<=p<=len(doc) for p in pages):raise ValueError('Area view page outside drawing')
        if allowed_pages is not None and not set(pages).issubset(allowed_pages):raise ValueError('Area view outside reviewed subset')
        reference,target=[doc[p-1] for p in pages]
        bounds=config['reference_bounds_pt']
        printed=scale_labels(reference,bounds)
        calibration={**corroborate_dimension_scale(split_dimension_scale(reference,bounds),printed),
            'mixed_view_scales':printed['mixed_view_scales']}
        registration=registered_scale(reference,target,calibration,config['anchors'],bounds,config['view_bounds_pt'])
        measurements=filled_regions(target,config['view_bounds_pt'],config['fills'],registration)
    if path.read_bytes()!=raw or hashlib.sha256(plan.read_bytes()).hexdigest()!=plan_sha256:
        raise ValueError('Area source changed during extraction')
    return {'plan_sha256':plan_sha256,'review_sha256':hashlib.sha256(raw).hexdigest(),
        'registration':registration,'measurements':measurements,'certified':False,'order_released':False}
