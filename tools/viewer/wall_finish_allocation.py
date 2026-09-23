"""Map reviewed wall-finish fields onto a room perimeter before deducting area."""
import math
from shapely.geometry import box
from shapely.ops import unary_union
from measurement_store import calculate
from wall_boundary_surfaces import wall_surface, WallBoundaryReviewRequired


def allocate(room, height_ft, measurements, finish_terms, tolerance_ft=0):
    """Return gross wall area and unioned exclusions; this is not paint billing.

    Finish heights start at the floor. Parallel traces may differ by an explicit
    tolerance, including at their endpoints. Unmatched or ambiguous faces require
    review instead of subtracting an unrelated surface elsewhere in the room.
    """
    if (type(height_ft) not in (int,float) or not math.isfinite(height_ft) or height_ft<=0
            or type(tolerance_ft) not in (int,float) or not math.isfinite(tolerance_ft)
            or not 0<=tolerance_ft<=0.25):
        raise ValueError('Positive wall height and alignment tolerance from 0 to 0.25 feet required')
    value=calculate(room)
    if room['kind']!='area' or room.get('surface_factor',1)!=1 or 'plane_gradients' in room:
        raise WallBoundaryReviewRequired('Finish allocation requires a flat room outline')
    scale=room['points_per_foot'];points=room['points'];edges=list(zip(points,points[1:]+points[:1]))
    patches={};mapped=[];seen=set();tolerance=tolerance_ft*scale
    for term in finish_terms:
        if not term.get('id') or term['id'] in seen:raise ValueError('Finish IDs must be distinct')
        seen.add(term['id'])
        source=measurements[term['measurement_id']]
        if any(source.get(k)!=room.get(k) for k in ('page','width_pt','height_pt','points_per_foot')):
            raise WallBoundaryReviewRequired('Finish and room must share the drawing frame and scale')
        profile=wall_surface(measurements,term);finish_height=profile['height_ft']
        if finish_height>height_ft:raise WallBoundaryReviewRequired('Finish extends above the room wall')
        for face in profile['wall_segments']:
            p,q=face['points'];span=math.dist(p,q);matches=[]
            for i,(a,b) in enumerate(edges):
                length=math.dist(a,b);dx,dy=b[0]-a[0],b[1]-a[1]
                if abs(dx*(q[1]-p[1])-dy*(q[0]-p[0]))>1e-7*length*span:continue
                if max(abs(dx*(v[1]-a[1])-dy*(v[0]-a[0]))/length for v in (p,q))>tolerance+1e-7:continue
                positions=[((v[0]-a[0])*dx+(v[1]-a[1])*dy)/length for v in (p,q)]
                low,high=sorted(positions);start=max(0,low);end=min(length,high)
                if end-start<=1e-7:continue
                # Keep coverage along the source face as well as the target wall.
                source_span=sorted((abs(t-positions[0]) for t in (start,end)))
                matches.append((source_span,i,start/scale,end/scale))
            ordered=sorted(matches)
            if not ordered:raise WallBoundaryReviewRequired('Finish face does not match a room wall')
            if ordered[0][0][0]>tolerance+1e-7 or span-ordered[-1][0][1]>tolerance+1e-7:
                raise WallBoundaryReviewRequired('Finish endpoints exceed the room wall')
            for previous,current in zip(ordered,ordered[1:]):
                gap=current[0][0]-previous[0][1]
                if gap>1e-7:raise WallBoundaryReviewRequired('Finish crosses an unmapped wall gap')
                if gap < -1e-7:raise WallBoundaryReviewRequired('Finish matches multiple room walls')
            for _,i,start,end in ordered:
                patches.setdefault(i,[]).append(box(start,0,end,finish_height))
                mapped.append({'finish_id':term['id'],'face':face['face'],'room_edge_index':i,
                    'start_ft':start,'end_ft':end,'height_ft':finish_height,'surface_sf':(end-start)*finish_height})
    gross=value['perimeter_lf']*height_ft
    excluded=math.fsum(unary_union(rectangles).area for rectangles in patches.values())
    summed=math.fsum(m['surface_sf'] for m in mapped)
    if excluded>gross+1e-7:raise WallBoundaryReviewRequired('Finish exclusions exceed gross wall area')
    return {'gross_wall_sf':gross,'excluded_wall_sf':excluded,'remaining_wall_reference_sf':gross-excluded,
        'overlapping_exclusion_sf':max(0,summed-excluded),'mapped_faces':mapped,
        'alignment_tolerance_ft':tolerance_ft,'paint_quantity_certified':False,'purchase_quantity':None}
