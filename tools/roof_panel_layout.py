"""Nominal roof-panel modules and conservative, unrotated blank allocation."""
import math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union


def panel_modules(face, gradient):
    scale=face['points_per_foot'];gx,gy=gradient
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (scale,gx,gy)) or scale<=0:
        raise ValueError('Finite positive scale and gradient required')
    slope=math.hypot(gx,gy);factor=math.hypot(1,slope)
    if slope==0 or not math.isclose(factor,face['surface_factor'],rel_tol=1e-8):
        raise ValueError('Pitch and surface factor disagree')
    ox,oy=face['points'][0]
    points=[((-(x-ox)*gy+(y-oy)*gx)/(slope*scale),
             ((x-ox)*gx+(y-oy)*gy)*factor/(slope*scale)) for x,y in face['points']]
    polygon=Polygon(points)
    if not polygon.is_valid or polygon.area<=0:
        raise ValueError('Valid roof face required')
    xmin,ymin,xmax,ymax=polygon.bounds
    pieces=[];coverage=[]
    for row in range(math.ceil((ymax-ymin)/4)):
        start=xmin-(4 if row%2 else 0)
        for column in range(math.ceil((xmax-start)/8)):
            module=box(start+column*8,ymin+row*4,start+(column+1)*8,ymin+(row+1)*4)
            cut=polygon.intersection(module)
            if cut.area<=1e-8:continue
            left,bottom,right,top=cut.bounds
            # Round blanks upward to 1/8 inch; no diagonal nesting or axis rotation.
            width=math.ceil((right-left)*12*8-1e-7)/8
            height=math.ceil((top-bottom)*12*8-1e-7)/8
            polygons=[cut] if cut.geom_type=='Polygon' else [g for g in cut.geoms if g.geom_type=='Polygon']
            pieces.append({'id':f"{face['id']}-C{row+1:02}-P{column+1:02}",
                'face_id':face['id'],'course':row+1,'column':column+1,
                'width_inches':width,'height_inches':height,'covered_sf':cut.area,
                'surface_polygons_ft':[[list(p) for p in g.exterior.coords] for g in polygons]})
            coverage.append(cut)
    uncovered=polygon.difference(unary_union(coverage)).area
    overlap=sum(p.area for p in coverage)-unary_union(coverage).area
    if uncovered>1e-7 or abs(overlap)>1e-7:
        raise ValueError('Panel modules do not partition the face')
    return {'face_id':face['id'],'surface_polygon_ft':points,'surface_sf':polygon.area,
            'pieces':pieces,'uncovered_module_sf':uncovered,'overlap_module_sf':overlap,
            'module_basis':'Nominal 96 x 48-inch grid; alternate courses offset 48 inches. Actual panel sizing, gaps and support datum require product/detail review.'}


def pack_blanks(pieces, kerf_inches=.125):
    if type(kerf_inches) not in (int,float) or not math.isfinite(kerf_inches) or kerf_inches<0:
        raise ValueError('Finite nonnegative kerf required')
    identities=set()
    for p in pieces:
        if not p.get('id') or p['id'] in identities:
            raise ValueError('Unique panel-piece identities required')
        identities.add(p['id'])
        for key,limit in [('width_inches',96),('height_inches',48)]:
            value=p[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=limit:
                raise ValueError('Blank does not fit nominal panel without rotation')
    sheets=[]
    for p in sorted(pieces,key=lambda p:(-p['height_inches'],-p['width_inches'],p['id'])):
        width,height=p['width_inches'],p['height_inches']
        options=[(r[2]*r[3]-width*height,n,j) for n,s in enumerate(sheets)
                 for j,r in enumerate(s['free_rectangles_inches']) if width<=r[2] and height<=r[3]]
        if not options:
            sheets.append({'id':f"S{len(sheets)+1:03}",'cuts':[],
                           'free_rectangles_inches':[[0,0,96,48]]})
            n,j=len(sheets)-1,0
        else:_,n,j=min(options)
        sheet=sheets[n];x,y,free_width,free_height=sheet['free_rectangles_inches'].pop(j)
        sheet['cuts'].append({'piece_id':p['id'],'x_inches':x,'y_inches':y,
                              'width_inches':width,'height_inches':height,'rotated':False})
        # Horizontal guillotine cut followed by a vertical cut in the used strip.
        if free_width-width>kerf_inches:
            sheet['free_rectangles_inches'].append([x+width+kerf_inches,y,free_width-width-kerf_inches,height])
        if free_height-height>kerf_inches:
            sheet['free_rectangles_inches'].append([x,y+height+kerf_inches,free_width,free_height-height-kerf_inches])
    return sheets
