"""Screen alignment gaps for crossing pieces and perpendicular wall-end contacts."""
import math
import hashlib
import json
from wall_run_candidates import WALL_METHOD
from wall_classification_review import STROKE_METHODS

METHOD='current_wall_piece_gap_obstructions_v3'


def footprint(measurement):
    points=measurement['points']
    if measurement['kind']=='area' and len(points)==4:
        xs=sorted({p[0] for p in points});ys=sorted({p[1] for p in points})
        if len(xs)!=2 or len(ys)!=2 or {tuple(p) for p in points}!={(x,y) for x in xs for y in ys}:return None
        if any((a[0]==b[0])==(a[1]==b[1]) for a,b in zip(points,points[1:]+points[:1])):return None
        return [xs[0],ys[0],xs[1],ys[1]]
    if measurement['kind']!='length' or len(points)!=2:return None
    thickness=measurement.get('drawn_thickness_inches')
    if type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0:return None
    half=thickness/12*measurement['points_per_foot']/2
    a,b=points
    if abs(a[1]-b[1])<=1e-6:return [min(a[0],b[0]),a[1]-half,max(a[0],b[0]),a[1]+half]
    if abs(a[0]-b[0])<=1e-6:return [a[0]-half,min(a[1],b[1]),a[0]+half,max(a[1],b[1])]
    return None


def junction_contacts(runs,pieces):
    """Locate face-to-end contacts without filling the host's missing interval."""
    by_id={m['id']:(m,b) for m,b in pieces}
    accepted={identity:run for run in runs['run_candidates'] for identity in run['source_measurement_ids']}
    contacts={}
    for run in runs['run_candidates']:
        axis=0 if run['axis']=='horizontal' else 1
        tolerance=run['points_per_foot']*.25/12
        hosts=[by_id[i][1] for i in run['source_measurement_ids'] if i in by_id]
        for index,gap in enumerate(run['gaps']):
            identity=f"{run['id']}:gap-{index+1}";contacts[identity]=[]
            left=[b for b in hosts if abs(b[axis+2]-gap['from_pt'])<1e-6]
            right=[b for b in hosts if abs(b[axis]-gap['to_pt'])<1e-6]
            if not left or not right:continue
            neighbors=left+right
            if any(max(b[k] for b in neighbors)-min(b[k] for b in neighbors)>tolerance for k in (1-axis,3-axis)):continue
            lower=sum(b[1-axis] for b in neighbors)/len(neighbors)
            upper=sum(b[3-axis] for b in neighbors)/len(neighbors)
            candidates=[]
            for candidate,other in accepted.items():
                if (other['page']!=run['page'] or other['points_per_foot']!=run['points_per_foot']
                        or other['axis']==run['axis'] or candidate not in by_id):continue
                bounds=by_id[candidate][1]
                if bounds[axis]<gap['from_pt']-tolerance or bounds[axis+2]>gap['to_pt']+tolerance:continue
                start=max(bounds[axis],gap['from_pt']);end=min(bounds[axis+2],gap['to_pt'])
                if end-start<=1e-6:continue
                sides=[]
                if abs(bounds[3-axis]-lower)<=tolerance:sides.append('lower_face')
                if abs(bounds[1-axis]-upper)<=tolerance:sides.append('upper_face')
                for side in sides:
                    candidates.append({'measurement_id':candidate,'perpendicular_run_id':other['id'],
                        'host_face':side,'host_faces_pt':[lower,upper],'current_footprint_pt':bounds,
                        'gap_interval_pt':[gap['from_pt'],gap['to_pt']],
                        'covered_interval_pt':[start,end]})
            # Offset branches may jointly cover a junction. Do not treat a
            # partial contact, or a real gap between branches, as a closure.
            intervals=sorted(c['covered_interval_pt'] for c in candidates)
            if not intervals or intervals[0][0]-gap['from_pt']>tolerance:continue
            covered=intervals[0][1]
            for start,end in intervals[1:]:
                if start>covered+1e-6:break
                covered=max(covered,end)
            else:
                if gap['to_pt']-covered<=tolerance:contacts[identity]=candidates
    return contacts


def screen(runs,state):
    pieces=[];unassessed=[]
    excluded={m['measurement_id'] for m in runs.get('excluded_measurements',[])}
    for m in sorted(state['measurements'].values(),key=lambda m:m['id']):
        if m.get('source_method') not in (WALL_METHOD,*STROKE_METHODS) or m['id'] in excluded:continue
        bounds=footprint(m)
        if bounds is None:unassessed.append(m['id'])
        else:pieces.append((m,bounds))
    gaps={}
    for run in runs['run_candidates']:
        axis=0 if run['axis']=='horizontal' else 1
        low,high=run['centerline_coordinate_range_pt']
        for index,gap in enumerate(run['gaps']):
            hits=[]
            for m,bounds in pieces:
                if m['page']!=run['page'] or m['id'] in run['source_measurement_ids']:continue
                # Edge contact alone is not an obstruction. The footprint must
                # cross the entire narrow centerline range of this alignment.
                if not bounds[1-axis]+1e-6<low<=high<bounds[3-axis]-1e-6:continue
                start=max(gap['from_pt'],bounds[axis]);end=min(gap['to_pt'],bounds[axis+2])
                if end-start>1e-6:
                    hits.append({'measurement_id':m['id'],'overlap_interval_pt':[start,end],
                        'overlap_lf':(end-start)/run['points_per_foot'],'current_footprint_pt':bounds})
            gaps[f"{run['id']}:gap-{index+1}"]=hits
    identity={'footprints':[{'measurement_id':m['id'],'page':m['page'],'bounds_pt':b} for m,b in pieces],
        'unassessed_measurement_ids':unassessed}
    return {'method':METHOD,'obstructions_by_gap':gaps,'junctions_by_gap':junction_contacts(runs,pieces),
        'junction_contact_tolerance_inches':.25,'unassessed_measurement_ids':unassessed,
        'footprint_inputs_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
        'basis':'Other drawn wall pieces cross the gap centerline; this span is not one clear opening. Wall meaning remains unapproved.'}
