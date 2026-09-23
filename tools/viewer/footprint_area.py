"""Union minus exclusions for flat footprint measurements on one sheet."""
import math
from measurement_store import calculate


def footprint_area(measurements, include, exclude):
    ids=include+exclude
    if not include or len(set(ids))!=len(ids) or set(ids)!=set(measurements):
        raise ValueError('Footprint needs unique, fully assigned boundaries')
    frames=set();polygons={};orthogonal=True
    for identity,m in measurements.items():
        calculate(m)
        if m['kind']!='area' or m.get('surface_factor',1)!=1 or m.get('plane_gradients'):
            raise ValueError('Footprint requires flat area boundaries')
        frames.add((m['page'],m['points_per_foot']))
        points=m['points']
        if any(a[0]!=b[0] and a[1]!=b[1] for a,b in zip(points,points[1:]+points[:1])):
            orthogonal=False
        polygons[identity]=points
    if len(frames)!=1:raise ValueError('Footprints must share page and scale')
    if not orthogonal:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        included=unary_union([Polygon(polygons[i]) for i in include])
        excluded=unary_union([Polygon(polygons[i]) for i in exclude])
        return included.difference(excluded).area/next(iter(frames))[1]**2
    xs=sorted({p[0] for pts in polygons.values() for p in pts})
    ys=sorted({p[1] for pts in polygons.values() for p in pts})
    def inside(points,x,y):
        return sum((a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]
                   for a,b in zip(points,points[1:]+points[:1]))%2==1
    areas=[]
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            x,y=(x0+x1)/2,(y0+y1)/2
            if any(inside(polygons[i],x,y) for i in include) and not any(inside(polygons[i],x,y) for i in exclude):
                areas.append((x1-x0)*(y1-y0))
    return math.fsum(areas)/next(iter(frames))[1]**2
