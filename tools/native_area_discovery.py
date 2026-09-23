"""Discover labeled colored area views and cross-sheet registration candidates."""
from collections import defaultdict
import re
import numpy as np
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from native_area_candidates import registered_scale,filled_regions
from native_hatch_regions import area_drawings


AREA_LABEL=re.compile(r'(?:HEATED(?: AREA)?|LIVING AREA|BASEMENT|(?:FIRST|MAIN|SECOND|THIRD) FLOOR|GARAGE|(?:(?:FRONT|REAR|BACK|SIDE) )?(?:(?:COVERED|UNCOVERED) )?(?:PATIO|PORCH|DECK)(?: (?:LEFT|RIGHT))?)')


def view_story_caption(page,view_bounds):
    """Propose a story from one nearby floor-view caption paired with a scale."""
    stories={'1ST FLOOR':'FIRST FLOOR','FIRST FLOOR':'FIRST FLOOR','MAIN FLOOR':'MAIN FLOOR',
             '2ND FLOOR':'SECOND FLOOR','SECOND FLOOR':'SECOND FLOOR',
             '3RD FLOOR':'THIRD FLOOR','THIRD FLOOR':'THIRD FLOOR','BASEMENT':'BASEMENT'}
    lines=set()
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=' '.join(''.join(s['text'] for s in line['spans']).upper().split())
            lines.add((text,tuple(line['bbox'])))
    candidates=[]
    for text,bounds in lines:
        if text not in stories:continue
        x0,y0,x1,y1=bounds;height=y1-y0
        if not (view_bounds[0]<=x0<x1<=view_bounds[2] and 0<=y0-view_bounds[3]<=6*height):continue
        scales=[(t,b) for t,b in lines if re.fullmatch(r'\d+(?:/\d+)? IN = \d+ FT',t)
                and -.1*height<=b[1]-y1<=height and abs((b[0]+b[2]-x0-x1)/2)<=max(x1-x0,b[2]-b[0])/2]
        if len(scales)==1:
            candidates.append({'story':stories[text],'text':text,'bounds_pt':list(bounds),
                'scale_caption':scales[0][0],'scale_caption_bounds_pt':list(scales[0][1]),
                'basis':'Unique nearby floor-view caption paired with scale text; scope review required'})
    return candidates[0] if len(candidates)==1 else None


def discover_view(page):
    """Read labels inside colored polygons; never use schedule quantities as scale."""
    labels=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=' '.join(''.join(span['text'] for span in line['spans']).split()).upper()
            if AREA_LABEL.fullmatch(text):labels.append((text,box(*line['bbox'])))
    if not labels:return None
    colors=defaultdict(list)
    for index,path in enumerate(area_drawings(page)):
        fill=path.get('fill');items=path['items']
        # Accept pale area shading; retain a margin against near-gray linework.
        if not fill or max(fill)-min(fill)<.05 or path.get('fill_opacity',1)<=0:continue
        if not items or any(item[0]!='l' for item in items):continue
        if any(tuple(items[j][2])!=tuple(items[(j+1)%len(items)][1]) for j in range(len(items))):continue
        polygon=Polygon([tuple(item[1]) for item in items])
        if polygon.is_valid and polygon.area>0:colors[tuple(fill)].append((index,polygon))
    found=[]
    for color,parts in colors.items():
        merged=unary_union([p for _,p in parts])
        polygons=list(merged.geoms) if merged.geom_type=='MultiPolygon' else [merged]
        for polygon in polygons:
            inside=[(text,rect) for text,rect in labels if polygon.covers(rect)]
            if len(inside)>1:raise ValueError('Multiple area labels inside one colored region')
            if not inside:continue
            text,rect=inside[0]
            found.append({'fill':list(color),'label':text.title()+f' gross area - Sheet {page.number+1}',
                'source_label':text,'label_bounds_pt':list(rect.bounds),'polygon':polygon,
                'source_paths':[i for i,p in parts if p.intersection(polygon).area>0]})
    if not found:return None
    if len({f['source_label'] for f in found})!=len(found):raise ValueError('Repeated area labels need view assignment')
    bounds=list(unary_union([f['polygon'] for f in found]).bounds)
    # Tight view limits must not silently include an unlabeled same-color object.
    chosen={i for f in found for i in f['source_paths']}
    for f in found:
        for i,p in colors[tuple(f['fill'])]:
            if i not in chosen and box(*bounds).intersects(p):
                raise ValueError('Unlabeled same-color geometry intersects discovered area view')
    return {'view_bounds_pt':bounds,'fills':[{k:v for k,v in f.items() if k!='polygon'} for f in found],
        'source_cad_paths':sorted(chosen),'method':'native area label contained by colored source polygon',
        'printed_schedule_used':False}


def automatic_registration(reference,target,calibration,reference_bounds,target_bounds):
    """Vote for uniform scale/translation, then require broad two-axis native matches."""
    def lines(page,bounds):
        found=defaultdict(list);view=box(*bounds)
        for i,path in enumerate(page.get_drawings()):
            color=path.get('color')
            if path['type']!='s' or color is None or max(color)>.2 or path.get('stroke_opacity',1)<=0:continue
            if path.get('dashes') not in ('[] 0',None):continue
            style=(tuple(color),round(path['width'] or 0,5))
            for j,item in enumerate(path['items']):
                if item[0]!='l':continue
                points=np.array(sorted([tuple(item[1]),tuple(item[2])]))
                if not all(view.covers(Point(p)) for p in points):continue
                delta=points[1]-points[0];axis=int(np.argmax(abs(delta)))
                if abs(delta[1-axis])>.01 or delta[axis]<20:continue
                found[(style,axis)].append((float(delta[axis]),i,j,points))
        return {key:sorted(values,key=lambda v:(-v[0],v[1],v[2]))[:80] for key,values in found.items()}
    source,destination=lines(reference,reference_bounds),lines(target,target_bounds)
    votes=defaultdict(list)
    for key,left in source.items():
        for a in left:
            for b in destination.get(key,[]):
                ratio=b[0]/a[0]
                if not .05<=ratio<=20:continue
                offset=b[3][0]-a[3][0]*ratio
                bucket=(round(ratio/.002),round(float(offset[0])/2),round(float(offset[1])/2))
                votes[bucket].append((key[1],a,b))
    ranked=sorted(votes.values(),key=len,reverse=True)
    if not ranked:raise ValueError('No corresponding native line styles')
    candidates=[];attempted=set()
    for group in ranked:
        if len(group)<max(4,len(ranked[0])*.5) or len(attempted)>=8:break
        if {v[0] for v in group}!={0,1}:continue
        seeds=[max((v for v in group if v[0]==axis),key=lambda v:v[1][0]) for axis in (0,1)]
        anchors=[{'reference':{'path':a[1],'item':a[2]},'target':{'path':b[1],'item':b[2]}} for _,a,b in seeds]
        identity=tuple((a['reference']['path'],a['reference']['item'],a['target']['path'],a['target']['item']) for a in anchors)
        if identity in attempted:continue
        attempted.add(identity)
        try:result=registered_scale(reference,target,calibration,anchors,reference_bounds,target_bounds)
        except ValueError:continue
        if any(abs(result['scale_ratio']/r['scale_ratio']-1)<.001 and np.linalg.norm(np.array(result['offset_pt'])-r['offset_pt'])<.2 for r in candidates):continue
        result['discovered_anchors']=anchors;result['seed_votes']=len(group);candidates.append(result)
    if len(candidates)!=1:raise ValueError('Automatic view registration is missing or ambiguous')
    return {**candidates[0],'anchor_method':'native two-axis segment transform voting'}


def discover(reference,target,calibration,reference_bounds):
    view=discover_view(target)
    if view is None:return None
    registration=automatic_registration(reference,target,calibration,reference_bounds,view['view_bounds_pt'])
    measurements=filled_regions(target,view['view_bounds_pt'],view['fills'],registration)
    story=view_story_caption(target,view['view_bounds_pt'])
    for measurement in measurements:
        source=next(f for f in view['fills'] if f['label']==measurement['label'])
        measurement['source_area_label']=source['source_label']
        measurement['source_area_label_bounds_pt']=source['label_bounds_pt']
        if story is not None and source['source_label'] in ('HEATED','HEATED AREA','LIVING AREA'):
            measurement['source_story_caption']=story
    if {i for m in measurements for i in m['source_cad_paths']}!=set(view['source_cad_paths']):
        raise ValueError('Discovered area paths differ from extracted region paths')
    return {'view_discovery':view,'registration':registration,'measurements':measurements,
        'certified':False,'order_released':False,'status':'automatically_discovered_candidates_require_review'}
