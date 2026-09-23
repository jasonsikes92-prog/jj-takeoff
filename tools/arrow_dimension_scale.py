"""Corroborate scale with four source-linked, opposed-arrow dimensions.

This complements long split-line dimensions without relaxing their thresholds.
At least two controls per axis, 24-point spans and a matching printed scale are
required. Arrow geometry and label color must agree; ambiguity stays unresolved.
"""
import itertools
import math
import statistics
from jnj_takeoff import parse_dim


def arrow_dimension_scale(page,view_bounds_pt,printed):
    a,b,c,d=view_bounds_pt
    inside=lambda point:a<=point[0]<=c and b<=point[1]<=d
    incident={}
    for index,drawing in enumerate(page.get_drawings()):
        color=drawing.get('color')
        if (drawing.get('type')!='s' or color is None or drawing.get('stroke_opacity',1)<=0
                or drawing.get('dashes') not in ('[] 0',None)):continue
        rgb=tuple(round(channel*255) for channel in color)
        style=(rgb,round(drawing.get('width',0),5))
        for item in drawing['items']:
            if item[0]!='l':continue
            first,last=map(tuple,item[1:])
            if not inside(first) or not inside(last) or not 1<=math.dist(first,last)<=30:continue
            for tip,tail in ((first,last),(last,first)):
                key=(tuple(round(v,3) for v in tip),style)
                incident.setdefault(key,[]).append((tail,index))
    heads=[]
    for (tip,style),wings in incident.items():
        for (first,i),(second,j) in itertools.combinations(wings,2):
            for axis in (0,1):
                u=[first[n]-tip[n] for n in (axis,1-axis)]
                v=[second[n]-tip[n] for n in (axis,1-axis)]
                if (u[0]*v[0]<=0 or u[1]*v[1]>=0 or abs(u[0]-v[0])>.25
                        or abs(u[1]+v[1])>.25):continue
                if not all(.1<=abs(x[1]/x[0])<=.6 for x in (u,v)):continue
                head={'tip':tip,'axis':axis,'direction':1 if u[0]>0 else -1,
                    'style':style,'paths':sorted({i,j})}
                if head not in heads:heads.append(head)
    controls=[];seen=set();ambiguous=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            box=line['bbox']
            if not inside(box[:2]) or not inside(box[2:]):continue
            text=''.join(span['text'] for span in line['spans']).strip();feet=parse_dim(text)
            if feet is None or feet<=0:continue
            if any(span.get('alpha',255)<=0 for span in line['spans']):continue
            colors={span['color'] for span in line['spans']}
            if len(colors)!=1:continue
            color=next(iter(colors));rgb=((color>>16)&255,(color>>8)&255,color&255)
            axis=0 if abs(line['dir'][0])>.99 else 1 if abs(line['dir'][1])>.99 else None
            if axis is None:continue
            low,high=box[axis],box[axis+2];height=box[3-axis]-box[1-axis]
            center=(box[1-axis]+box[3-axis])/2
            nearby=[head for head in heads if head['axis']==axis and head['style'][0]==rgb
                and abs(head['tip'][1-axis]-center)<=2*height]
            pairs=[]
            for first in nearby:
                for last in nearby:
                    lo,hi=first['tip'][axis],last['tip'][axis]
                    if (first['direction']!=1 or last['direction']!=-1 or first['style']!=last['style']
                            or abs(first['tip'][1-axis]-last['tip'][1-axis])>.01 or hi-lo<24):continue
                    if not lo-height/4<=low<high<=hi+height/4:continue
                    if abs((low+high-lo-hi)/2)>height/2:continue
                    pair=(first,last)
                    if pair not in pairs:pairs.append(pair)
            if len(pairs)!=1:
                if pairs:ambiguous.append({'text':text,'label_bbox_pt':list(box),'arrow_pair_count':len(pairs)})
                continue
            first,last=pairs[0];key=(first['tip'],last['tip'],feet)
            if key in seen:continue
            seen.add(key);span=last['tip'][axis]-first['tip'][axis]
            controls.append({'text':text,'feet':feet,'axis':'horizontal' if axis==0 else 'vertical',
                'span_pt':span,'points_per_foot':span/feet,'label_bbox_pt':list(box),
                'dimension_endpoints_pt':[list(first['tip']),list(last['tip'])],
                'cad_paths':sorted(set(first['paths']+last['paths']))})
    numeric={round(row['nominal_points_per_foot'],6) for row in printed['labels'] if not row['not_to_scale']}
    printed_ok=(len(numeric)==1 and not printed['mixed_view_scales']
        and not any(row['not_to_scale'] for row in printed['labels']))
    nominal=next(iter(numeric)) if printed_ok else None
    agreeing=[row for row in controls if nominal and abs(row['points_per_foot']/nominal-1)<=.005]
    usable=(printed_ok and not ambiguous and len(controls)>=4 and len(agreeing)==len(controls)
        and all(sum(row['axis']==axis for row in controls)>=2 for axis in ('horizontal','vertical')))
    return {'points_per_foot':statistics.median(row['points_per_foot'] for row in controls) if usable else None,
        'controls':controls,'agreeing_controls':len(agreeing),'usable_candidate':bool(usable),
        'ambiguous_labels':ambiguous,'confidence':'review','certified':False,
        'method':'four opposed-arrow dimensions in both axes corroborated by printed scale',
        'printed_scale_evidence':printed['labels'],
        'note':'Source-coordinate scale candidate only; roof geometry and complete coverage require separate review.'}
