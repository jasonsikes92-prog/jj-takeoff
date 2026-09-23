"""Propose short wall-piece axes from neighboring pieces and printed gap tags."""
import copy
from wall_run_candidates import WALL_METHOD

METHOD='tag_supported_short_wall_directions_v1'


def projections(measurement):
    points=measurement['points']
    if measurement['kind']=='length' and len(points)==2:
        a,b=points
        axis=0 if abs(a[1]-b[1])<=1e-6 else 1 if abs(a[0]-b[0])<=1e-6 else None
        return [] if axis is None else [(axis,points,False)]
    if measurement['kind']!='area' or len(points)!=4:return []
    xs=sorted({p[0] for p in points});ys=sorted({p[1] for p in points})
    if len(xs)!=2 or len(ys)!=2 or {tuple(p) for p in points}!={(x,y) for x in xs for y in ys}:return []
    if any((a[0]==b[0])==(a[1]==b[1]) for a,b in zip(points,points[1:]+points[:1])):return []
    width=xs[1]-xs[0];height=ys[1]-ys[0]
    if min(width,height)<=0 or max(width,height)/min(width,height)>=1.25:return []
    ppf=measurement['points_per_foot']
    if min(width,height)/ppf*12<2.5 or max(width,height)/ppf*12>6:return []
    x=sum(xs)/2;y=sum(ys)/2
    return [(0,[[xs[0],y],[xs[1],y]],True),(1,[[x,ys[0]],[x,ys[1]]],True)]


def propose(state,labels):
    walls=sorted((m for m in state['measurements'].values() if m.get('source_method')==WALL_METHOD),key=lambda m:m['id'])
    candidates=[];short_ids=set();unusable=[]
    for m in walls:
        projected=projections(m)
        if m['kind']=='area':
            short_ids.add(m['id'])
            if not projected:unusable.append(m['id'])
        for axis,points,short in projected:
            candidates.append({'id':m['id'],'page':m['page'],'ppf':m['points_per_foot'],'axis':axis,
                'coordinate':points[0][1-axis],'low':min(p[axis] for p in points),
                'high':max(p[axis] for p in points),'points':points,'short':short})
    evidence={identity:[] for identity in short_ids}
    for piece in candidates:
        if not piece['short']:continue
        peers=[p for p in candidates if p['id']!=piece['id'] and
            (p['page'],p['ppf'],p['axis'])==(piece['page'],piece['ppf'],piece['axis']) and
            abs(p['coordinate']-piece['coordinate'])<=piece['ppf']*.25/12]
        # Only the closest aligned boundary on each side can bound this gap.
        for side in ('left','right'):
            eligible=[p for p in peers if (p['high']<piece['low'] if side=='left' else p['low']>piece['high'])]
            if not eligible:continue
            edge=max(p['high'] for p in eligible) if side=='left' else min(p['low'] for p in eligible)
            nearest=[p for p in eligible if (p['high'] if side=='left' else p['low'])==edge]
            if len(nearest)!=1:continue
            peer=nearest[0]
            start,end=(peer['high'],piece['low']) if side=='left' else (piece['high'],peer['low'])
            if any(p['low']<end and p['high']>start for p in peers if p['id']!=peer['id']):continue
            axis='horizontal' if piece['axis']==0 else 'vertical'
            matches=[]
            for label in labels:
                if label['page']!=piece['page'] or label['axis']!=axis:continue
                bounds=label['bbox_pt'];a=piece['axis']
                along=(bounds[a]+bounds[a+2])/2;across=(bounds[1-a]+bounds[3-a])/2
                if start<along<end and abs(across-piece['coordinate'])<=piece['ppf']*3/12:
                    matches.append(label['id'])
            if len(matches)==1:
                evidence[piece['id']].append({'axis':axis,'peer_measurement_id':peer['id'],
                    'peer_is_short_piece':peer['short'],'label_id':matches[0],'gap_interval_pt':[start,end],
                    'projected_points':piece['points']})
    axes={identity:{e['axis'] for e in items} for identity,items in evidence.items()}
    results=[];projected_state=copy.deepcopy(state)
    for identity in sorted(short_ids):
        usable=[e for e in evidence[identity] if not e['peer_is_short_piece'] or axes[e['peer_measurement_id']]=={e['axis']}]
        unique=next(iter(axes[identity])) if len(axes[identity])==1 and usable else None
        status='unique_direction_candidate' if unique else 'ambiguous_axes' if len(axes[identity])>1 else 'insufficient_direction_evidence'
        if identity in unusable:status='edited_outline_outside_short_rectangle_scope'
        results.append({'measurement_id':identity,'status':status,'axis':unique,'evidence':evidence[identity]})
        if unique:
            measurement=projected_state['measurements'][identity]
            measurement['kind']='length';measurement['points']=usable[0]['projected_points']
    return {'method':METHOD,'pieces':results,'certified':False,
        'basis':'A uniquely oriented tag in an otherwise clear gap to the nearest aligned piece supports a direction candidate; it does not approve wall meaning.'},projected_state
