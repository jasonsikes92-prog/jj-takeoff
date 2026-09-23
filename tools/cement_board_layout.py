"""Nominal staggered cement-board cuts and unique seams, before installation gaps."""
import math
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union
from linear_stock import pack_sawn_cuts


def calculate(field, sheet_width_ft=5, course_height_ft=3, offset_ft=0):
    if (field.geom_type not in ('Polygon','MultiPolygon') or not field.is_valid or field.area<=0
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in
                   (sheet_width_ft,course_height_ft,offset_ft))
            or min(sheet_width_ft,course_height_ft)<=0):
        raise ValueError('A valid positive floor field and sheet dimensions are required')
    left,top,right,bottom=field.bounds
    clips=[];pieces=[]
    for course in range(math.ceil((bottom-top)/course_height_ft)):
        y=top+course*course_height_ft
        origin=left+offset_ft+(sheet_width_ft/2 if course%2 else 0)
        for col in range(math.floor((left-origin)/sheet_width_ft),math.ceil((right-origin)/sheet_width_ft)):
            x=origin+col*sheet_width_ft
            cut=field.intersection(box(x,y,x+sheet_width_ft,y+course_height_ft))
            if cut.area<1e-9:continue
            if cut.geom_type=='GeometryCollection':
                cut=unary_union([part for part in cut.geoms if part.geom_type in ('Polygon','MultiPolygon')])
            clips.append(cut)
            pieces.append({'id':f'CB{len(pieces)+1:03}', 'course':course+1,
                'stock_bounds_ft':[x,y,x+sheet_width_ft,y+course_height_ft],
                'cut_geometry_ft':mapping(cut),'installed_sf':cut.area,
                'stock_sheets':1,'offcut_reuse_assumed':False})
    covered=unary_union(clips)
    if (covered.symmetric_difference(field).area>1e-7
            or abs(sum(c.area for c in clips)-field.area)>1e-7):
        raise ValueError('Cement-board cuts fail exact nominal floor coverage')
    seams=[]
    for i,a in enumerate(clips):
        for j,b in enumerate(clips[i+1:],i+1):
            joint=a.boundary.intersection(b.boundary)
            if joint.length>1e-8:
                seams.append({'boards':[pieces[i]['id'],pieces[j]['id']],
                    'length_lf':joint.length,'geometry_ft':mapping(joint)})
    unique=unary_union([a.boundary.intersection(b.boundary) for i,a in enumerate(clips) for b in clips[i+1:]])
    if abs(sum(s['length_lf'] for s in seams)-unique.length)>1e-7:
        raise ValueError('Board joints were counted more than once')
    return {'pieces':pieces,'seams':seams,'nominal_area_sf':field.area,
        'candidate_sheets_without_reuse':len(pieces),'unique_seam_lf':unique.length,
        'sheet_size_ft':[sheet_width_ft,course_height_ft],'offset_ft':offset_ft,
        'nominal_coverage_verified':True,'installation_gap_layout_verified':False,
        'subfloor_joint_conflicts_verified':False,'fastener_count':None,'purchase_quantity':None}


def material_allowance(layout, kerf_inches=.125, fastener_spacing_inches=8):
    """Reuse full-course strips; budget edge and field fasteners without a placement claim."""
    if (type(fastener_spacing_inches) not in (int,float)
            or not math.isfinite(fastener_spacing_inches) or fastener_spacing_inches<=0):
        raise ValueError('Positive finite fastener spacing required')
    width,height=layout['sheet_size_ft'];strips=[];dedicated=[];fasteners=[]
    for piece in layout['pieces']:
        cut=shape(piece['cut_geometry_ft']);left,top,right,bottom=cut.bounds
        rectangular=cut.symmetric_difference(box(left,top,right,bottom)).area<1e-8
        if rectangular and math.isclose(bottom-top,height,abs_tol=1e-8):
            strips.append({'id':piece['id'],'sku':'full-course-strip','stock_length_ft':width,
                'cut_inches':min(width*12,math.ceil((right-left)*12*8-1e-8)/8)})
        else:dedicated.append(piece['id'])
        parts=[cut] if cut.geom_type=='Polygon' else [p for p in cut.geoms if p.geom_type=='Polygon']
        count=0
        for part in parts:
            rings=[part.exterior,*part.interiors]
            # Separate edge allowance for each cut edge; corners intentionally not credited.
            edge=sum(math.ceil(math.dist(a,b)*12/fastener_spacing_inches)
                for ring in rings for a,b in zip(ring.coords,list(ring.coords)[1:]))
            x0,y0,x1,y1=part.bounds
            field=math.ceil((x1-x0)*12/fastener_spacing_inches)*math.ceil((y1-y0)*12/fastener_spacing_inches)
            count+=edge+field
        fasteners.append({'piece_id':piece['id'],'edge_and_field_allowance':count})
    stocks=pack_sawn_cuts(strips,kerf_inches)
    assigned=dedicated+[c['piece_id'] for s in stocks for c in s['cuts']]
    if sorted(assigned)!=sorted(p['id'] for p in layout['pieces']):
        raise ValueError('Stock assignment omitted or duplicated a board cut')
    return {'candidate_sheets':len(dedicated)+len(stocks),'dedicated_cut_ids':dedicated,
        'reused_strip_stock':stocks,'kerf_inches':kerf_inches,
        'fastener_allowance':sum(f['edge_and_field_allowance'] for f in fasteners),
        'fasteners_by_piece':fasteners,'fastener_spacing_basis_inches':fastener_spacing_inches,
        'fastener_basis':'Conservative separate edge and bounding-field allowances per cut polygon; overlaps retained. Not a screw placement plan or a code certification.',
        'optimal_stock_count_proven':False,'order_released':False}
