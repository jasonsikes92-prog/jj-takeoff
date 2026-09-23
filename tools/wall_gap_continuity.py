"""Recognize interrupted wall pairs only with a shared face and drawn wall body."""
import hashlib
from pathlib import Path
import fitz
from shapely.geometry import Polygon,box
from wall_gap_obstructions import footprint


def rectangle(drawing):
    if drawing.get('fill')!=(1.,1.,1.) or drawing.get('fill_opacity',1)!=1:return None
    items=drawing['items']
    if len(items)==1 and items[0][0]=='re':return list(items[0][1])
    if len(items)!=4 or any(i[0]!='l' for i in items):return None
    if any(tuple(a[2])!=tuple(b[1]) for a,b in zip(items,items[1:]+items[:1])):return None
    polygon=Polygon([list(i[1]) for i in items])
    if not polygon.is_valid or polygon.area<=0 or not polygon.equals(box(*polygon.bounds)):return None
    return list(polygon.bounds)


def detect(state,runs,gaps,drawings):
    by_run={r['id']:r for r in runs['run_candidates']};result={};bodies={}
    for gap in gaps:
        if gap['status']!='no_aligned_tag':continue
        run=by_run[gap['run_id']];axis=0 if run['axis']=='horizontal' else 1;page=run['page']
        pieces=[(state['measurements'][i],footprint(state['measurements'][i])) for i in run['source_measurement_ids']]
        left=[(m,b) for m,b in pieces if b and abs(b[axis+2]-gap['from_pt'])<1e-6]
        right=[(m,b) for m,b in pieces if b and abs(b[axis]-gap['to_pt'])<1e-6]
        if len(left)!=1 or len(right)!=1:continue
        (lm,lb),(rm,rb)=left[0],right[0]
        if any(abs(lb[k]-rb[k])>1e-6 for k in (1-axis,3-axis)):continue
        shared=[e for e in lm.get('source_edges',[]) if e in rm.get('source_edges',[])]
        valid=[]
        for edge in shared:
            path=edge['path'];item=edge['item']
            if not 0<=path<len(drawings[page]):continue
            drawing=drawings[page][path]
            if not 0<=item<len(drawing['items']) or drawing.get('dashes','[] 0') not in ('[] 0','[] 0.0'):continue
            native=drawing['items'][item]
            if native[0]!='l' or [list(native[1]),list(native[2])]!=edge['points_pt']:continue
            a,b=edge['points_pt']
            if abs(a[1-axis]-b[1-axis])>1e-6:continue
            if min(abs(a[1-axis]-lb[k]) for k in (1-axis,3-axis))>1e-6:continue
            if min(a[axis],b[axis])>lb[axis]+1e-6 or max(a[axis],b[axis])<rb[axis+2]-1e-6:continue
            valid.append(edge)
        if not valid:continue
        if page not in bodies:
            bodies[page]=[(i,b) for i,d in enumerate(drawings[page]) if (b:=rectangle(d)) is not None]
        matching=[(i,b) for i,b in bodies[page] if all(abs(b[k]-lb[k])<=1e-6 for k in (1-axis,3-axis))
            and b[axis]<=lb[axis]+1e-6 and b[axis+2]>=rb[axis+2]-1e-6]
        if not matching:continue
        result[gap['id']]={'source_measurement_ids':[lm['id'],rm['id']],
            'continuous_face_edges':valid,'native_wall_body_rectangles':[{'path':i,'bounds_pt':b} for i,b in matching],
            'basis':'Reviewed wall pairs share a continuous native face; an exact-width native wall-body rectangle spans both pieces and the gap'}
    return result


def apply_from_plan(plan,state,runs,result):
    plan=Path(plan)
    if not any(g['status']=='no_aligned_tag' for g in result['gaps']):return
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:raise ValueError('Wall continuity drawing changed')
    pages={r['page'] for r in runs['run_candidates']}
    with fitz.open(plan) as doc:drawings={p:doc[p-1].get_drawings() for p in pages}
    evidence=detect(state,runs,result['gaps'],drawings)
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:raise ValueError('Drawing changed during wall continuity check')
    for gap in result['gaps']:
        if gap['id'] in evidence:
            gap['status']='continuous_wall_body_candidate';gap['continuity_source']=evidence[gap['id']]
    for section in result['alignment_review']['candidate_sections']:
        section['unresolved_gap_ids']=[i for i in section['unresolved_gap_ids'] if i not in evidence]
