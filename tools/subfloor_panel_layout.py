"""Staggered T&G modules with unrotated, product-width strip reuse."""
import math
from collections import Counter
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
if __package__:
    from .linear_stock import pack_sawn_cuts
else:
    from linear_stock import pack_sawn_cuts


def calculate(points, points_per_foot, course_inches=48, stagger_inches=38.4, kerf_inches=.125,
              panel_width_inches=48):
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0
           for v in [points_per_foot,course_inches,stagger_inches,kerf_inches,panel_width_inches]):
        raise ValueError('Positive finite subfloor dimensions required')
    if course_inches>panel_width_inches or panel_width_inches>48 or stagger_inches>=96:
        raise ValueError('Subfloor modules must fit nominal 96 x 48 stock')
    if len(points)<4:raise ValueError('Subfloor polygon requires at least four corners')
    polygon=Polygon(points)
    if not polygon.is_valid or polygon.area<=0 or polygon.interiors:
        raise ValueError('Subfloor footprint must be one valid polygon without holes')
    for a,b in zip(points,points[1:]+points[:1]):
        dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1])
        if not ((dx<1e-7 and dy>1e-7) or (dy<1e-7 and dx>1e-7)):
            raise ValueError('Subfloor footprint must have orthogonal, nonzero edges')
    ox,oy,_,_=polygon.bounds
    polygon=Polygon([((x-ox)/points_per_foot,(y-oy)/points_per_foot) for x,y in points])
    _,_,width,height=polygon.bounds;course=course_inches/12;pieces=[];clips=[]
    for row in range(math.ceil(height/course)):
        y0,y1=row*course,(row+1)*course;offset=stagger_inches/12 if row%2 else 0
        for col in range(-1,math.ceil(width/8)+1):
            x0,x1=col*8+offset,(col+1)*8+offset
            clip=polygon.intersection(box(x0,y0,x1,y1))
            if clip.area<=1e-8:continue
            identity=f'P{len(pieces)+1:03}';left,top,right,bottom=clip.bounds
            parts=[clip] if clip.geom_type=='Polygon' else [p for p in clip.geoms if p.area>1e-8]
            rectangular=clip.symmetric_difference(box(left,top,right,bottom)).area<1e-7
            # Only an un-ripped product-width strip retains both tongue/groove edges.
            reusable=rectangular and abs((bottom-top)*12-panel_width_inches)<1e-7 and right-left<8-1e-7
            pieces.append({'id':identity,'course':row+1,'module_bounds_ft':[x0,y0,x1,y1],
                'net_area_sf':clip.area,'footprint_polygons_ft':[list(p.exterior.coords)[:-1] for p in parts],
                'full_module':abs(clip.area-8*course)<1e-7,'full_width_strip_reusable':reusable,
                'strip_cut_inches':math.ceil((right-left)*12*8-1e-8)/8 if reusable else None})
            clips.append(clip)
    eligible=[{'id':p['id'],'sku':'NOMINAL-TG-FULL-WIDTH','stock_length_ft':8,
               'cut_inches':p['strip_cut_inches']} for p in pieces if p['full_width_strip_reusable']]
    sheets=pack_sawn_cuts(eligible,kerf_inches)
    dedicated=[p['id'] for p in pieces if not p['full_width_strip_reusable']]
    if Counter(dedicated+[c['piece_id'] for s in sheets for c in s['cuts']])!=Counter(p['id'] for p in pieces):
        raise ValueError('Subfloor stock allocation lost or duplicated a piece')
    if (abs(math.fsum(p['net_area_sf'] for p in pieces)-polygon.area)>1e-6
            or polygon.symmetric_difference(unary_union(clips)).area>1e-6):
        raise ValueError('Subfloor modules do not cover the footprint exactly once')
    return {'pieces':pieces,'dedicated_sheet_modules':dedicated,'reuse_sheets':sheets,
        'candidate_sheets':len(dedicated)+len(sheets),'modules_before_reuse':len(pieces),
        'gross_surface_sf':polygon.area,'course_inches':course_inches,'stagger_inches':stagger_inches,
        'kerf_inches':kerf_inches,'panel_width_inches':panel_width_inches,
        'origin_pt':[ox,oy],'purchase_quantity':None}
