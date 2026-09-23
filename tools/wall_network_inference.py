"""Infer wall-body hypotheses from unchanged, depth-compatible CAD networks."""
import hashlib
import json
import math
from wall_classification_review import STROKE_METHODS, source_digest


def candidate(m):
    if m.get('source_method') not in STROKE_METHODS:return None
    if m.get('kind')=='area':
        from wall_short_piece_directions import projections
        bounds=m.get('source_bounds_pt',[])
        if len(bounds)!=4:return None
        a,b,c,d=bounds
        if {tuple(p) for p in m['points']}!={(a,b),(c,b),(c,d),(a,d)}:return None
        possibilities=[candidate({**m,'kind':'length','points':points})
                       for axis,points,short in projections(m) if short]
        possibilities=[p for p in possibilities if p is not None]
        return {**possibilities[0],'short_piece':True} if len(possibilities)==1 else None
    if m.get('kind')!='length':return None
    points=m.get('points',[]);bounds=m.get('source_bounds_pt',[])
    if len(points)!=2 or len(bounds)!=4 or not m.get('source_edges'):return None
    a,b=points;axis=0 if abs(a[1]-b[1])<1e-6 else 1 if abs(a[0]-b[0])<1e-6 else None
    if axis is None:return None
    scale=m['points_per_foot'];depth=m.get('wall_depth_basis',{}).get('depth_inches')
    if depth not in (3.5,5.5) or m.get('expected_depth_inches')!=depth:return None
    thickness=m.get('drawn_thickness_inches')
    if not isinstance(thickness,(int,float)) or abs(thickness-depth)>.125:return None
    half=thickness*scale/24
    current=([min(a[0],b[0]),a[1]-half,max(a[0],b[0]),a[1]+half] if axis==0
             else [a[0]-half,min(a[1],b[1]),a[0]+half,max(a[1],b[1])])
    if any(abs(x-y)>1e-5 for x,y in zip(bounds,current)):return None
    faces=set()
    for edge in m['source_edges']:
        p,q=edge['points_pt']
        if abs(p[1-axis]-q[1-axis])>1e-5:continue
        if min(p[axis],q[axis])>bounds[axis]+1e-5 or max(p[axis],q[axis])<bounds[axis+2]-1e-5:continue
        for side in (bounds[1-axis],bounds[3-axis]):
            if abs(p[1-axis]-side)<1e-5:faces.add(side)
    if len(faces)!=2:return None
    return {'id':m['id'],'key':(m['page'],scale,depth),'axis':axis,'bounds':bounds,
            'points':points,'length_lf':math.dist(a,b)/scale,'thickness':thickness}


def infer(state,decisions):
    """Never replace an explicit decision, including uncertain or stale records."""
    pieces={};blocked=set()
    for identity,m in state['measurements'].items():
        decision=decisions.get(identity)
        if decision and decision['current'] and decision['decision']=='not_wall_faces':continue
        value=candidate(m)
        if value is None and m.get('kind') in ('length','area') and len(m.get('source_bounds_pt',[]))==4:
            # An edited line cannot support inference. Its original paired
            # source still obstructs a competing layer interpretation nearby.
            a,b,c,d=m['source_bounds_pt']
            original=([[a,b],[c,b],[c,d],[a,d]] if m['kind']=='area' else
                      [[a,(b+d)/2],[c,(b+d)/2]] if c-a>d-b else [[(a+c)/2,b],[(a+c)/2,d]])
            value=candidate({**m,'points':original})
            if value:blocked.add(identity)
        if decision and (not decision['current'] or decision['decision']!='wall_faces'):blocked.add(identity)
        if value and decision and decision.get('axis') and decision['axis']!=('horizontal' if value['axis']==0 else 'vertical'):
            blocked.add(identity)
        if value:pieces[identity]=value
    ambiguous=set();layer_pairs=[];contacts={identity:[set(),set()] for identity in pieces};alignments=[]
    for identity,a in pieces.items():
        axis=a['axis'];scale=a['key'][1];bounds=a['bounds']
        for other,b in pieces.items():
            if other==identity or a['key']!=b['key']:continue
            bb=b['bounds']
            if axis==b['axis']:
                overlap=min(bounds[axis+2],bb[axis+2])-max(bounds[axis],bb[axis])
                distance=abs((bounds[1-axis]+bounds[3-axis]-bb[1-axis]-bb[3-axis])/2)
                if overlap>=2*scale and distance<=scale:
                    ambiguous.update((identity,other))
                    if identity<other:layer_pairs.append((identity,other))
                if identity<other and distance<=scale*.25/12 and -8*scale<=overlap<0:
                    alignments.append((identity,other))
                continue
            for end,p in enumerate(a['points']):
                distance=math.hypot(max(bb[0]-p[0],0,p[0]-bb[2]),max(bb[1]-p[1],0,p[1]-bb[3]))
                if distance<=scale*(a['thickness']/2+.25)/12:
                    contacts[identity][end].add(other)
    # A unique outline with actual face-to-face contact at both end caps can
    # supply the wall boundary. Nearby disconnected outlines stay unresolved.
    # Edited or explicitly classified group members prevent this inference.
    independent=set(pieces)-ambiguous-blocked;resolutions=[];remaining_layers=set(ambiguous)
    while remaining_layers:
        group={min(remaining_layers)}
        while True:
            expanded=group|{i for pair in layer_pairs if set(pair)&group for i in pair}
            if expanded==group:break
            group=expanded
        remaining_layers-=group
        if group&(blocked|set(decisions)):continue
        connected={}
        for identity in sorted(group):
            a=pieces[identity];axis=a['axis'];bounds=a['bounds'];supports=[]
            for end in (bounds[axis],bounds[axis+2]):
                support=[]
                for other in sorted(independent):
                    b=pieces[other];bb=b['bounds']
                    if b['key']!=a['key'] or b['axis']==axis:continue
                    if (bb[axis]-1e-5<=end<=bb[axis+2]+1e-5
                            and max(bounds[1-axis],bb[1-axis])<=min(bounds[3-axis],bb[3-axis])+1e-5):
                        support.append(other)
                supports.append(support)
            if all(supports):connected[identity]=supports
        if len(connected)!=1:continue
        selected=next(iter(connected));ambiguous.remove(selected)
        resolutions.append({'selected_wall_id':selected,'unresolved_layer_ids':sorted(group-{selected}),
            'endpoint_supports':connected[selected],'requires_review':True,
            'basis':'Only this unchanged paired outline physically meets independent perpendicular wall faces at both end caps.'})
    active=set(pieces)-ambiguous-blocked
    graph={identity:set().union(*contacts[identity])&active for identity in active}
    for a,b in alignments:
        if a in active and b in active:
            graph[a].add(b);graph[b].add(a)
    for identity,neighbors in list(graph.items()):
        for other in neighbors:graph[other].add(identity)
    components=[];remaining=set(active)
    while remaining:
        pending=[min(remaining)];component=set()
        while pending:
            identity=pending.pop()
            if identity in component:continue
            component.add(identity);pending.extend(graph[identity]-component)
        remaining-=component
        anchors=[identity for identity in sorted(component) if pieces[identity]['length_lf']>=4
                 and all(end&active for end in contacts[identity])]
        bounds=[pieces[i]['bounds'] for i in component];scale=pieces[min(component)]['key'][1]
        spans=[(max(b[axis+2] for b in bounds)-min(b[axis] for b in bounds))/scale for axis in (0,1)]
        if len(anchors)<2 or min(spans)<6:continue
        components.append({'measurement_ids':sorted(component),'anchor_ids':anchors,
            'unmeasured_alignment_links':[list(pair) for pair in sorted(alignments)
                if set(pair)<=component]})
    inferred={}
    for component in components:
        evidence={'plan_sha256':state['plan_sha256'],**component,
                  'source_sha256':{i:source_digest(state['measurements'][i]) for i in component['measurement_ids']}}
        relevant=[r for r in resolutions if r['selected_wall_id'] in component['measurement_ids']]
        if relevant:
            evidence['parallel_layer_resolutions']=relevant
            dependencies={i for r in relevant for i in r['unresolved_layer_ids']}
            evidence['layer_source_sha256']={i:source_digest(state['measurements'][i]) for i in sorted(dependencies)}
        digest=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
        for identity in component['measurement_ids']:
            if identity in decisions:continue
            inferred[identity]={'measurement_id':identity,'decision':'wall_faces','current':True,
                'source_sha256':source_digest(state['measurements'][identity]),
                'basis':'Unchanged paired CAD faces match the saved stud-depth assumption and a connected wall network; estimating inference requiring review.',
                'inferred':True,'requires_review':True,'network_sha256':digest,'evidence':evidence}
            if pieces[identity].get('short_piece'):
                inferred[identity]['axis']='horizontal' if pieces[identity]['axis']==0 else 'vertical'
    return {'method':'native_wall_network_inference_v1','decisions':inferred,
            'parallel_layer_ambiguities':sorted(ambiguous),'parallel_layer_resolutions':resolutions,'components':components,
            'maximum_unmeasured_alignment_gap_inches':96,
            'purchase_quantity':None,'certified':False}
