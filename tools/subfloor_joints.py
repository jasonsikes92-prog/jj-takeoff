"""Measure shared panel seams once; no installed gap, glue or fastening rule is implied."""
import math
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union


def from_layout(layout):
    pieces=sorted(layout['pieces'],key=lambda p:p['id'])
    if not pieces or len({p['id'] for p in pieces})!=len(pieces):
        raise ValueError('Unique subfloor panel pieces required')
    shapes=[]
    for piece in pieces:
        if type(piece['course']) is not int or piece['course']<1:
            raise ValueError('Positive integer panel course required')
        parts=[Polygon(points) for points in piece['footprint_polygons_ft']]
        if not parts or any(not p.is_valid or not math.isfinite(p.area) or p.area<=0 for p in parts):
            raise ValueError('Valid panel polygons required')
        shape=unary_union(parts)
        if abs(shape.area-sum(p.area for p in parts))>1e-7:
            raise ValueError('Panel parts overlap')
        shapes.append(shape)
    union=unary_union(shapes)
    if (abs(union.area-sum(s.area for s in shapes))>1e-7
            or abs(union.area-layout['gross_surface_sf'])>1e-6):
        raise ValueError('Panel coverage overlaps or differs from measured floor area')
    def lines(geometry):
        if geometry.geom_type=='LineString':yield geometry
        elif geometry.geom_type in ('MultiLineString','GeometryCollection'):
            for part in geometry.geoms:yield from lines(part)
    seams=[];segments=[]
    for i,a in enumerate(shapes):
        for j in range(i+1,len(shapes)):
            for line in lines(a.boundary.intersection(shapes[j].boundary)):
                for start,end in zip(line.coords,list(line.coords)[1:]):
                    start,end=sorted([list(start),list(end)])
                    segment=LineString([start,end])
                    if segment.length<1e-8:continue
                    horizontal=abs(start[1]-end[1])<1e-7
                    vertical=abs(start[0]-end[0])<1e-7
                    same_course=pieces[i]['course']==pieces[j]['course']
                    if not ((horizontal and not same_course) or (vertical and same_course)):
                        raise ValueError('Shared seam conflicts with orthogonal panel course layout')
                    kind='tongue_and_groove' if horizontal else 'butt'
                    seams.append({'id':f'J{len(seams)+1:03}',
                        'piece_ids':[pieces[i]['id'],pieces[j]['id']],
                        'kind':kind,'points_ft':[start,end],'length_lf':segment.length})
                    segments.append(segment)
    total=math.fsum(s['length_lf'] for s in seams)
    # Every internal seam belongs to two pieces; the exterior perimeter belongs to one.
    if (abs(total-unary_union(segments).length)>1e-6
            or abs(sum(s.length for s in shapes)-union.length-2*total)>1e-6):
        raise ValueError('Shared seam accounting is incomplete or duplicated')
    return {'seams':seams,'tongue_and_groove_lf':math.fsum(s['length_lf'] for s in seams if s['kind']=='tongue_and_groove'),
        'butt_joint_lf':math.fsum(s['length_lf'] for s in seams if s['kind']=='butt'),
        'total_shared_joint_lf':total,'footprint_perimeter_lf':union.length,
        'piece_count':len(pieces),'joint_length_is_adhesive_run':False,
        'adhesive_purchase_quantity':None,'fastener_purchase_quantity':None}
