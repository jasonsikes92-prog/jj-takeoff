"""Source-linked scale candidates from split dimension lines flanking full labels."""
import math
import statistics
from jnj_takeoff import parse_dim


def split_dimension_scale(page,view_bounds_pt=None):
    def inside(point):
        return view_bounds_pt is None or (view_bounds_pt[0]<=point[0]<=view_bounds_pt[2]
            and view_bounds_pt[1]<=point[1]<=view_bounds_pt[3])
    segments=[];fills=[]
    for index,drawing in enumerate(page.get_drawings()):
        if (drawing.get('type') in ('f','fs') and drawing.get('fill_opacity',0)>0
                and all(item[0]=='l' for item in drawing['items'])):
            points=[tuple(point) for item in drawing['items'] for point in item[1:]]
            box=drawing['rect']
            if points and all(inside(point) for point in points) and max(box.width,box.height)<=30:
                fills.append({'points':points,'box':box,'color':drawing['fill'],'path':index})
        if (drawing.get('type')!='s' or drawing.get('dashes') not in ('[] 0',None)
                or drawing.get('stroke_opacity',1)<=0):continue
        for item in drawing['items']:
            if item[0]!='l':continue
            a,b=item[1:]
            if not inside(a) or not inside(b):continue
            axis=0 if abs(a.y-b.y)<.01 else (1 if abs(a.x-b.x)<.01 else None)
            if axis is None or math.dist(a,b)<5:continue
            segments.append({'axis':axis,'low':min(a[axis],b[axis]),'high':max(a[axis],b[axis]),
                'fixed':a[1-axis],'path':index,'style':(drawing.get('color'),drawing.get('width'))})
    def endpoint(segment,side):
        axis=segment['axis'];fixed=segment['fixed'];value=segment[side]
        arrows=[]
        for fill in fills:
            if fill['color']!=segment['style'][0]:continue
            points=fill['points'];box=fill['box']
            length=box[axis+2]-box[axis];width=box[3-axis]-box[1-axis]
            if not (1<=length<=30 and .1<=width/length<=.8):continue
            if not any(abs(p[axis]-value)<.05 and abs(p[1-axis]-fixed)<.05 for p in points):continue
            tip=min(p[axis] for p in points) if side=='low' else max(p[axis] for p in points)
            tip_points={tuple(round(v,3) for v in p) for p in points if abs(p[axis]-tip)<.01}
            if len(tip_points)!=1 or abs(next(iter(tip_points))[1-axis]-fixed)>.05:continue
            if not .5<abs(tip-value)<length:continue
            witnesses=[s for s in segments if s['axis']!=axis and s['style']==segment['style']
                and abs(s['fixed']-tip)<.05 and s['low']+.1<fixed<s['high']-.1]
            arrows.append((tip,[fill['path']]+[s['path'] for s in witnesses],bool(witnesses)))
        if not arrows:return value,[],False
        if len(arrows)!=1 or not arrows[0][2]:return None,[],True
        return arrows[0][0],arrows[0][1],True
    controls=[];seen=set()
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            if not inside(line['bbox'][:2]) or not inside(line['bbox'][2:]):continue
            text=''.join(s['text'] for s in line['spans']).strip();feet=parse_dim(text)
            if feet is None or feet<8:continue
            axis=0 if abs(line['dir'][0])>.99 else (1 if abs(line['dir'][1])>.99 else None)
            if axis is None:continue
            box=line['bbox'];low,high=box[axis],box[axis+2]
            fixed_low,fixed_high=box[1-axis],box[3-axis]
            tolerance=max(3,(fixed_high-fixed_low)/2)
            nearby=[s for s in segments if s['axis']==axis and fixed_low<=s['fixed']<=fixed_high]
            left=[s for s in nearby if 0<=low-s['high']<=tolerance]
            right=[s for s in nearby if 0<=s['low']-high<=tolerance]
            pairs=[(a,b) for a in left for b in right if a['style']==b['style'] and abs(a['fixed']-b['fixed'])<.01]
            if len(pairs)!=1:continue
            a,b=pairs[0];key=(axis,round(a['low'],3),round(b['high'],3),feet)
            if key in seen:continue
            seen.add(key)
            start,start_paths,start_arrow=endpoint(a,'low')
            end,end_paths,end_arrow=endpoint(b,'high')
            if start is None or end is None or start_arrow!=end_arrow:continue
            span=end-start
            controls.append({'text':text,'feet':feet,'axis':'horizontal' if axis==0 else 'vertical',
                'span_pt':span,'points_per_foot':span/feet,
                'cad_paths':[a['path'],b['path']]+start_paths+end_paths,
                'endpoint_method':'filled_arrow_tips_at_witness_lines' if start_arrow else 'split_line_endpoints',
                'label_bbox_pt':list(box),'dimension_endpoints_pt':
                    [[start,a['fixed']],[end,b['fixed']]] if axis==0 else
                    [[a['fixed'],start],[b['fixed'],end]]})
    median=statistics.median(c['points_per_foot'] for c in controls) if controls else None
    agreeing=[c for c in controls if abs(c['points_per_foot']/median-1)<=.005] if median else []
    usable=(len(agreeing)>=3 and len(agreeing)>=.8*len(controls)
            and {c['axis'] for c in agreeing}=={'horizontal','vertical'})
    return {'points_per_foot':statistics.median(c['points_per_foot'] for c in agreeing) if usable else None,
        'controls':controls,'agreeing_controls':len(agreeing),'usable_candidate':usable,
        'confidence':'review','method':'full-label split dimension lines',
        'certified':False,'note':'Requires geometry and source review; multiple scales or insufficient controls are not resolved by guessing.'}
