"""Measure exact shared roof boundaries; retain near seams and overlaps for review."""
import math
from collections import defaultdict
from itertools import combinations
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import unary_union


def calculate(faces,gradients,*,rise_allowance_inches=None):
    if not faces or len({f['id'] for f in faces})!=len(faces):
        raise ValueError('Unique roof faces required')
    first=faces[0];frame=tuple(first[k] for k in ('page','width_pt','height_pt','points_per_foot'))
    scale=frame[-1]
    if type(scale) not in (float,int) or not math.isfinite(scale) or scale<=0:
        raise ValueError('Finite positive roof scale required')
    if set(gradients)!={f['id'] for f in faces}:raise ValueError('Every roof face needs its own gradient')
    numerical_tolerance_inches=.0001
    if rise_allowance_inches is not None and (type(rise_allowance_inches) not in (int,float)
            or not math.isfinite(rise_allowance_inches) or rise_allowance_inches<numerical_tolerance_inches):
        raise ValueError('Finite reviewed rise allowance at least the numerical tolerance required')
    epsilon_pt=scale*numerical_tolerance_inches/12
    allowed_rise_pt=scale*(rise_allowance_inches or numerical_tolerance_inches)/12
    polygons={}
    for face in faces:
        if face['kind']!='area' or tuple(face[k] for k in ('page','width_pt','height_pt','points_per_foot'))!=frame:
            raise ValueError('Roof junctions require one calibrated area coordinate frame')
        gradient=gradients[face['id']]
        if (len(gradient)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in gradient)
                or not math.isclose(math.hypot(1,*gradient),face.get('surface_factor',1),rel_tol=1e-8)):
            raise ValueError('Roof gradient and measured pitch disagree')
        polygon=Polygon(face['points'])
        if not polygon.is_valid or polygon.area<=0:raise ValueError('Valid roof polygon required')
        polygons[face['id']]=polygon
    candidates=[];unresolved=[];boundaries=[]
    for a,b in combinations(polygons,2):
        left,right=polygons[a],polygons[b]
        intersection=left.intersection(right)
        significant_overlap=intersection.area>epsilon_pt*max(intersection.length,epsilon_pt)
        if significant_overlap:
            unresolved.append({'face_ids':[a,b],'reason':'Projected face overlap; resolve roof levels and boundary ownership',
                'overlap_projected_sf':intersection.area/scale**2,'quantity_lf':None})
        shared=left.boundary.intersection(right.boundary)
        lines=list(shared.geoms) if hasattr(shared,'geoms') else [shared]
        for line in lines:
            if line.geom_type!='LineString' or line.length<=1e-8:continue
            # Preserve each change in direction; it can change the junction role.
            for start,end in zip(line.coords,list(line.coords)[1:]):
                dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy)
                if length<=1e-8:continue
                segment=LineString([start,end]);boundaries.append(segment)
                base={'face_ids':[a,b],'points':[list(start),list(end)],'projected_lf':length/scale}
                if any(p.boundary.intersection(segment).length>1e-8 for i,p in polygons.items() if i not in (a,b)):
                    unresolved.append({**base,'reason':'More than two faces own part of this boundary','quantity_lf':None});continue
                if significant_overlap:
                    unresolved.append({**base,'reason':'Shared boundary of overlapping projections','quantity_lf':None});continue
                rises=[gradients[i][0]*dx+gradients[i][1]*dy for i in (a,b)]
                if abs(rises[0]-rises[1])>allowed_rise_pt:
                    unresolved.append({**base,'reason':'Adjacent roof slopes disagree along the shared boundary',
                        'rise_difference_inches':abs(rises[0]-rises[1])/scale*12,'quantity_lf':None});continue
                normal=(-dy/length,dx/length);mid=segment.interpolate(.5,normalized=True)
                epsilon=min(length/1000,scale/1200)
                samples=[Point(mid.x+s*epsilon*normal[0],mid.y+s*epsilon*normal[1]) for s in (1,-1)]
                sides=[]
                for polygon in (left,right):
                    contains=[polygon.contains(p) for p in samples]
                    sides.append(1 if contains==[True,False] else -1 if contains==[False,True] else 0)
                if 0 in sides or sides[0]==sides[1]:
                    unresolved.append({**base,'reason':'Face interiors do not establish opposite boundary sides','quantity_lf':None});continue
                inward=[sum(g*n for g,n in zip(gradients[i],normal))*side for i,side in zip((a,b),sides)]
                if all(v>1e-8 for v in inward):kind='valley'
                elif all(v< -1e-8 for v in inward):kind='ridge' if max(map(abs,rises))<=epsilon_pt else 'hip'
                else:
                    unresolved.append({**base,'reason':'Slope break or coplanar seam; not a ridge/hip/valley member','quantity_lf':None});continue
                lengths=[math.hypot(length,rise)/scale for rise in rises]
                candidates.append({**base,'kind':kind,'quantity_lf':max(lengths),
                    'length_bounds_lf':[min(lengths),max(lengths)],
                    'rise_difference_inches':abs(rises[0]-rises[1])/scale*12,
                    'uses_reviewed_slope_approximation':abs(rises[0]-rises[1])>epsilon_pt,
                    'role_is_inferred':True,'absolute_elevations_verified':False,'member_size':None,
                    'plies':None,'stock_quantity':None,'support_layout':None})
    totals=defaultdict(float)
    for candidate in candidates:totals[candidate['kind']]+=candidate['quantity_lf']
    shared=unary_union(boundaries)
    return {'candidate_segments':candidates,'candidate_length_by_kind_lf':dict(totals),
        'numerical_tolerance_inches':numerical_tolerance_inches,
        'estimating_rise_allowance_inches':rise_allowance_inches,
        'unresolved_junctions':unresolved,'exact_shared_projected_lf':shared.length/scale,
        'unmatched_boundary_by_face_lf':{i:polygon.boundary.difference(shared).length/scale for i,polygon in polygons.items()},
        'basis':'Exact coincident boundaries only; no snapping or gap closure. Each face pair is counted once.',
        'remaining':['Unmatched boundaries include exterior edges and noncoincident interior seams; classify against source drawings.',
            'Equal along-edge slopes do not establish equal absolute roof elevations.',
            'Inferred junctions need source confirmation, member sizes/plies, end cuts, support and splice layouts.',
            'Segment count is not member count. These lengths exclude unresolved boundaries and are not a complete framing order.'],
        'complete_member_quantity':None,'purchase_authorized':False,'certified':False}
