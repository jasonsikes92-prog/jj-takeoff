"""Geometric rafter stations and provisional exact-SKU cuts, with no span approval."""
import math
from collections import Counter
from shapely.geometry import Polygon,LineString
if __package__:
    from .linear_stock import pack_sawn_cuts
else:
    from linear_stock import pack_sawn_cuts


def stations(face, gradient, spacing_inches=16, first_center_inches=.75):
    scale=face['points_per_foot'];gx,gy=gradient
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in
           [scale,gx,gy,spacing_inches,first_center_inches]) or min(scale,spacing_inches)<=0:
        raise ValueError('Finite rafter scale, direction and spacing required')
    if not 0<first_center_inches<spacing_inches:
        raise ValueError('First rafter center must fall inside its first spacing interval')
    if (gx==0)==(gy==0):raise ValueError('Rafter study requires one reviewed cardinal run direction')
    axis=0 if gx else 1;cross=1-axis;slope=math.hypot(gx,gy);factor=math.hypot(1,slope)
    if not math.isclose(factor,face['surface_factor'],rel_tol=1e-8):
        raise ValueError('Rafter direction and roof pitch disagree')
    polygon=Polygon(face['points'])
    if not polygon.is_valid or polygon.area<=0:raise ValueError('Valid roof face required')
    bounds=polygon.bounds;station=bounds[cross]+first_center_inches*scale/12
    step=spacing_inches*scale/12;segments=[]
    while station<bounds[cross+2]-1e-8:
        a=[0.,0.];b=[0.,0.];a[cross]=b[cross]=station
        a[axis]=bounds[axis]-scale;b[axis]=bounds[axis+2]+scale
        cut=polygon.intersection(LineString([a,b]))
        lines=[cut] if cut.geom_type=='LineString' else [g for g in getattr(cut,'geoms',[]) if g.geom_type=='LineString']
        for line in sorted(lines,key=lambda g:g.bounds[axis]):
            if line.length<=1e-8:continue
            start,end=line.bounds[axis],line.bounds[axis+2]
            segments.append({'id':f"{face['id']}-S{len(segments)+1:03}",'roof_face':face['id'],
                'run_axis':axis,'station_coordinate_pt':station,'run_start_pt':start,'run_end_pt':end,
                'sloped_segment_ft':(end-start)/scale*factor,'pitch':slope*12})
        station+=step
    if not segments:raise ValueError('Roof face has no stations at this datum; review the edge layout')
    return segments


def allocate(segments, stock, maximum_stock_ft=26, member_depth_inches=5.5, kerf_inches=.125):
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0
           for v in [maximum_stock_ft,member_depth_inches]):
        raise ValueError('Positive finite rafter stock limit and member depth required')
    if not stock or len({s['sku'] for s in stock})!=len(stock):
        raise ValueError('Unique available stock SKUs required')
    if len({s['length_ft'] for s in stock})!=len(stock):
        raise ValueError('Select one material per stock length before calculating rafters')
    for item in stock:
        if (type(item['length_ft']) not in (int,float) or not math.isfinite(item['length_ft'])
                or not 0<item['length_ft']<=maximum_stock_ft or item['size']!='2x6'
                or not item.get('invoice_grade_species')):
            raise ValueError('Stock must be identified 2x6 within the maximum length')
    pieces=[];oversized=[];seen=set()
    for segment in segments:
        if segment['id'] in seen:raise ValueError('Duplicate rafter station segment')
        seen.add(segment['id']);length=segment['sloped_segment_ft'];pitch=segment['pitch']
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in [length,pitch]):
            raise ValueError('Positive finite rafter geometry required')
        allowance=member_depth_inches*pitch/12;cut=math.ceil((length*12+allowance)*8)/8
        piece={'id':segment['id'],'roof_face':segment['roof_face'],'geometric_sloped_ft':length,
               'pitch':pitch,'plumb_cut_allowance_inches':allowance,'cut_inches':cut,
               'final_member_cut_verified':False}
        selected=next((s for s in sorted(stock,key=lambda s:(s['length_ft'],s['sku'])) if cut<=s['length_ft']*12),None)
        if selected:
            pieces.append({**piece,'sku':selected['sku'],'stock_length_ft':selected['length_ft'],
                           'invoice_species_grade':selected['invoice_grade_species']})
        else:oversized.append(piece)
    boards=pack_sawn_cuts(pieces,kerf_inches)
    if Counter(c['piece_id'] for b in boards for c in b['cuts'])!=Counter(p['id'] for p in pieces):
        raise ValueError('Rafter stock allocation lost or duplicated a piece')
    return {'segments':segments,'pieces':pieces,'boards':boards,'requires_splice_layout':oversized,
        'candidate_board_counts':dict(Counter(b['sku'] for b in boards)),
        'geometric_segments':len(segments),'candidate_cut_piece_count':len(pieces),
        'candidate_boards':len(boards),'purchase_quantity':None,'price_applied':False,
        'structural_adequacy_verified':False,'maximum_stock_ft':maximum_stock_ft,
        'member_depth_inches':member_depth_inches,'kerf_inches':kerf_inches}
