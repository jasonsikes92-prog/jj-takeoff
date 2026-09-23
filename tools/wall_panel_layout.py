"""Nominal vertical wall-sheet blanks from explicitly supplied wall face polygons."""
import math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def wall_modules(identity, points_ft):
    if not isinstance(identity,str) or not identity.strip():
        raise ValueError('Wall face identity required')
    if any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points_ft):
        raise ValueError('Finite wall coordinates required')
    polygon=Polygon(points_ft)
    if not polygon.is_valid or polygon.area<=0:
        raise ValueError('Valid wall face required')
    xmin,ymin,xmax,ymax=polygon.bounds
    pieces=[];coverage=[]
    for column in range(math.ceil((xmax-xmin)/4)):
        for course in range(math.ceil((ymax-ymin)/8)):
            module=box(xmin+column*4,ymin+course*8,xmin+(column+1)*4,ymin+(course+1)*8)
            cut=polygon.intersection(module)
            if cut.area<=1e-8:continue
            left,bottom,right,top=cut.bounds
            # Stock x follows the vertical 96-inch sheet axis. Never rotate offcuts.
            vertical=math.ceil((top-bottom)*12*8-1e-7)/8
            horizontal=math.ceil((right-left)*12*8-1e-7)/8
            polygons=[cut] if cut.geom_type=='Polygon' else [g for g in cut.geoms if g.geom_type=='Polygon']
            pieces.append({'id':f'{identity}-C{column+1:02}-R{course+1:02}',
                'face_id':identity,'column':column+1,'course':course+1,
                'width_inches':vertical,'height_inches':horizontal,'covered_sf':cut.area,
                'surface_polygons_ft':[[list(p) for p in g.exterior.coords] for g in polygons]})
            coverage.append(cut)
    union=unary_union(coverage)
    if polygon.difference(union).area>1e-7 or abs(sum(p.area for p in coverage)-union.area)>1e-7:
        raise ValueError('Wall modules do not partition the face')
    return {'face_id':identity,'surface_polygon_ft':points_ft,'surface_sf':polygon.area,'pieces':pieces,
        'stock_axis':'96-inch sheet axis vertical; 48-inch sheet axis horizontal',
        'module_basis':'Nominal 4x8 vertical modules. Actual panel dimensions, gaps, seams and support details require review.'}
