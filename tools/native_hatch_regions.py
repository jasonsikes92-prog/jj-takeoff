"""Identify white backing polygons followed by a dense colored line hatch.

These are drawing-reference candidates, not certified construction boundaries.
Original path indexes are preserved and printed area values are never consulted.
"""
import math
from shapely.geometry import Polygon, MultiPoint, LineString


def area_drawings(page):
    drawings=page.get_drawings()
    result=list(drawings)
    for index,path in enumerate(drawings):
        if path.get('fill')!=(1.,1.,1.) or path.get('fill_opacity',1)<=0:continue
        items=path['items']
        if len(items)<3 or any(item[0]!='l' for item in items):continue
        if any(tuple(items[j][2])!=tuple(items[(j+1)%len(items)][1]) for j in range(len(items))):continue
        polygon=Polygon([tuple(item[1]) for item in items])
        if not polygon.is_valid or polygon.area<=0 or not polygon.equals(polygon.convex_hull):continue
        color=None;segments=[];indexes=[]
        for following in range(index+1,len(drawings)):
            stroke=drawings[following];candidate=stroke.get('color')
            if (stroke['type']!='s' or candidate is None or max(candidate)-min(candidate)<.05
                    or stroke.get('stroke_opacity',1)<=0 or stroke.get('dashes') not in ('[] 0',None)
                    or len(stroke['items'])!=1 or stroke['items'][0][0]!='l'):break
            if color is not None and candidate!=color:break
            color=candidate
            a,b=map(tuple,stroke['items'][0][1:])
            segments.append((a,b));indexes.append(following)
        if len(segments)<3:continue
        # Reject colored details outside the backing or confined to one small corner.
        # CAD hatch endpoints may round just beyond the polygon edge. This
        # 0.2-point tolerance classifies strokes only; it never expands the area.
        if any(not polygon.buffer(.2).covers(LineString(s)) for s in segments):continue
        hull=MultiPoint([p for s in segments for p in s]).convex_hull
        if hull.intersection(polygon).area/polygon.area<.9:continue
        longest=max(segments,key=lambda s:math.dist(*s))
        dx=longest[1][0]-longest[0][0];dy=longest[1][1]-longest[0][1]
        length=math.hypot(dx,dy)
        if length<=2:continue
        if any(abs(dx*(b[1]-a[1])-dy*(b[0]-a[0]))/(length*math.dist(a,b))>.04
               for a,b in segments if math.dist(a,b)>2):continue
        result[index]={**path,'fill':color,'hatch_source_paths':indexes,
                       'source_method':'white backing polygon with contained parallel colored hatch'}
    return result
