"""Review diagonal alignments in their own frame; never certify an opening."""
import hashlib
import json
import math
from shapely.geometry import LineString,Polygon
from wall_classification_review import resolve,source_digest,STROKE_METHODS
from wall_run_candidates import WALL_METHOD

METHOD='reviewed_diagonal_wall_gaps_v2'


def dot(a,b):return a[0]*b[0]+a[1]*b[1]


def direction(points):
    a,b=sorted(points)
    length=math.dist(a,b)
    return [(b[k]-a[k])/length for k in (0,1)] if length else None


def footprint(m):
    points=m['points']
    if m['kind']=='area' and len(points)>=3:
        polygon=Polygon(points)
    elif m['kind']=='length' and len(points)==2:
        thickness=m.get('drawn_thickness_inches')
        if type(thickness) not in (int,float) or not math.isfinite(thickness) or thickness<=0:return None
        if math.dist(*points)<=1e-9:return None
        polygon=LineString(points).buffer(thickness*m['points_per_foot']/24,cap_style='flat')
    else:return None
    return polygon if polygon.is_valid and polygon.area>0 else None


def junction_contacts(group,start,end,polygons,decisions):
    """Match reviewed branch end caps to the host faces bounding this gap."""
    result={'contacts':[],'covers_gap':False}
    by_id={m['id']:(m,p) for m,p in polygons}
    neighbors=[i for i,(a,b) in group['members'] if abs(b-start)<1e-6 or abs(a-end)<1e-6]
    if not neighbors or any(i not in by_id for i in neighbors):return result
    tolerance=group['ppf']*.25/12
    faces=[]
    for identity in neighbors:
        coordinates=[dot(p,group['v']) for p in by_id[identity][1].exterior.coords]
        faces.append([min(coordinates),max(coordinates)])
    if any(max(p[k] for p in faces)-min(p[k] for p in faces)>tolerance for k in (0,1)):return result
    lower,upper=[sum(p[k] for p in faces)/len(faces) for k in (0,1)]
    members={i for i,span in group['members']}
    for m,polygon in polygons:
        d=decisions.get(m['id'],{})
        if (m['id'] in members or m['page']!=group['page'] or m['points_per_foot']!=group['ppf']
                or not d.get('current') or d.get('decision')!='wall_faces'
                or m['kind']!='length' or len(m['points'])!=2):continue
        u=direction(m['points']);v=[-u[1],u[0]]
        half=m['drawn_thickness_inches']*group['ppf']/24
        for index,p in enumerate(m['points']):
            cap=[[p[k]+sign*v[k]*half for k in (0,1)] for sign in (-1,1)]
            normals=[dot(q,group['v']) for q in cap]
            far=dot(m['points'][1-index],group['v'])
            along=sorted(dot(q,group['u']) for q in cap)
            if along[0]<start-tolerance or along[1]>end+tolerance:continue
            a,b=max(start,along[0]),min(end,along[1])
            if b-a<=1e-6:continue
            for side,face in [('lower',lower),('upper',upper)]:
                if max(abs(n-face) for n in normals)>tolerance:continue
                if not (far<face-tolerance if side=='lower' else far>face+tolerance):continue
                result['contacts'].append({'measurement_id':m['id'],'host_face':side,
                    'host_faces_pt':[lower,upper],'branch_end_cap_pt':cap,'covered_interval_pt':[a,b]})
    intervals=sorted(c['covered_interval_pt'] for c in result['contacts'])
    if not intervals or intervals[0][0]-start>tolerance:return result
    covered=intervals[0][1]
    for a,b in intervals[1:]:
        if a>covered+1e-6:return result
        covered=max(covered,b)
    result['covers_gap']=end-covered<=tolerance
    return result


def from_state(state,labels,classification_review=None):
    decisions,review_digest=resolve(state,classification_review)
    walls=sorted((m for m in state['measurements'].values()
        if m.get('source_method') in (WALL_METHOD,*STROKE_METHODS)),key=lambda m:m['id'])
    groups=[];unresolved=[];polygons=[];unassessed=[]
    for m in walls:
        decision=decisions.get(m['id'],{})
        if decision.get('current') and decision.get('decision')=='not_wall_faces':continue
        polygon=footprint(m)
        if polygon is None:unassessed.append(m)
        else:polygons.append((m,polygon))
        points=m['points']
        if m['kind']!='length' or len(points)!=2:
            if m.get('source_method')=='native_parallel_diagonal_wall_strokes_v1':
                unresolved.append({'measurement_id':m['id'],'reason':'Short outline or polyline needs run-direction review'})
            continue
        u=direction(points)
        if u is None or min(abs(v) for v in u)<1e-6:continue
        if not decision.get('current') or decision.get('decision')!='wall_faces':
            unresolved.append({'measurement_id':m['id'],'reason':'Current source-bound wall-face review required'})
            continue
        # Compare all endpoints in the first piece's frame. Do not allow a
        # chain of near-aligned pieces to drift across the tolerance envelope.
        match=None;tolerance=m['points_per_foot']*.25/12
        for g in groups:
            if (m['page'],m['points_per_foot'])!=(g['page'],g['ppf']):continue
            if abs(u[0]*g['u'][1]-u[1]*g['u'][0])>1e-6:continue
            across=[dot(p,g['v']) for p in points]
            if max(g['high'],*across)-min(g['low'],*across)<=tolerance:
                match=g;break
        if match is None:
            v=[-u[1],u[0]];across=[dot(p,v) for p in points]
            match={'page':m['page'],'ppf':m['points_per_foot'],'u':u,'v':v,
                'low':min(across),'high':max(across),'members':[]}
            groups.append(match)
        across=[dot(p,match['v']) for p in points]
        match['low']=min(match['low'],*across);match['high']=max(match['high'],*across)
        match['members'].append((m['id'],sorted(dot(p,match['u']) for p in points)))
    runs=[];gaps=[];uses={label['id']:[] for label in labels}
    for g in groups:
        members=sorted(i for i,span in g['members']);spans=[]
        for low,high in sorted(span for i,span in g['members']):
            if spans and low<=spans[-1][1]+1e-8:spans[-1][1]=max(spans[-1][1],high)
            else:spans.append([low,high])
        identity='diagonal-wall-run-'+hashlib.sha256(json.dumps(members).encode()).hexdigest()[:16]
        visible=sum(b-a for a,b in spans)/g['ppf'];across=(g['low']+g['high'])/2
        def point(along):return [along*g['u'][k]+across*g['v'][k] for k in (0,1)]
        runs.append({'id':identity,'page':g['page'],'axis':'diagonal','direction':g['u'],
            'points_per_foot':g['ppf'],'source_measurement_ids':members,
            'centerline_coordinate_range_pt':[g['low'],g['high']],
            'visible_intervals_pt':spans,'visible_union_lf':visible,
            'gross_alignment_span_lf':(spans[-1][1]-spans[0][0])/g['ppf'],
            'overlapping_piece_lf':max(0,sum(b-a for i,(a,b) in g['members'])/g['ppf']-visible)})
        for index,(left,right) in enumerate(zip(spans,spans[1:])):
            start,end=left[1],right[0];points=[point(start),point(end)]
            gap_id=f'{identity}:gap-{index+1}';matches=[];hits=[]
            for label in labels:
                if label['page']!=g['page']:continue
                heading=label.get('direction')
                if not heading or math.hypot(*heading)==0:continue
                if abs(dot(heading,g['u']))/math.hypot(*heading)<math.cos(math.radians(1)):continue
                x0,y0,x1,y1=label['bbox_pt'];center=[(x0+x1)/2,(y0+y1)/2]
                along,normal=dot(center,g['u']),dot(center,g['v'])
                tolerance=g['ppf']*3/12
                if start<along<end and g['low']-tolerance<=normal<=g['high']+tolerance:matches.append(label['id'])
            line=LineString(points)
            for m,polygon in polygons:
                if m['page']!=g['page'] or m['id'] in members:continue
                # Interior intersection only. Merely touching a wall face is
                # still a possible junction and cannot certify an opening.
                overlap=line.intersection(polygon.buffer(-1e-7)).length
                if overlap>1e-6:hits.append({'measurement_id':m['id'],'overlap_lf':overlap/g['ppf']})
            unknown=[m['id'] for m in unassessed if m['page']==g['page']]
            junction=junction_contacts(g,start,end,polygons,decisions)
            if not hits and not unknown and not junction['contacts']:
                for i in matches:uses[i].append(gap_id)
            gaps.append({'id':gap_id,'run_id':identity,'page':g['page'],'points_pt':points,
                'drawn_gap_lf':(end-start)/g['ppf'],'candidate_label_ids':sorted(matches),
                'obstructions':hits,'unassessed_measurement_ids':unknown,'junction_review':junction})
    for gap in gaps:
        matches=gap['candidate_label_ids']
        gap['status']=('drawn_piece_obstructs_gap' if gap['obstructions'] else
            'unassessed_wall_footprints' if gap['unassessed_measurement_ids'] else
            'junction_tag_conflict' if gap['junction_review']['covers_gap'] and matches else
            'wall_junction_candidate' if gap['junction_review']['covers_gap'] else
            'partial_wall_contact_requires_review' if gap['junction_review']['contacts'] else
            'no_aligned_tag' if not matches else 'multiple_tags_require_review' if len(matches)>1 else
            'tag_shared_by_multiple_gaps' if len(uses[matches[0]])>1 else 'tag_location_requires_junction_review')
    identity=[{'id':m['id'],'source_sha256':source_digest(m)} for m in walls]
    return {'method':METHOD,'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
        'measurement_inputs_sha256':hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
        'classification_review_sha256':review_digest,'run_candidates':runs,'gaps':gaps,
        'unresolved_measurements':unresolved,'shared_label_ids':sorted(i for i,v in uses.items() if len(v)>1),
        'alignment_tolerance_inches':.25,'junction_contact_tolerance_inches':.25,
        'maximum_tag_offset_inches':3,'maximum_tag_angle_degrees':1,
        'certified':False,'purchase_quantity':None,'estimate_released':False,
        'limitations':['Only current explicit wall-face reviews enter diagonal alignments.',
            'Gap spans are not added to wall quantities or treated as approved openings.',
            'Junction contacts are geometry candidates, not approved backing assemblies or added wall length.',
            'Continuous wall faces, completeness and short-piece directions still require review.',
            'Projected intervals use the reported direction and its left normal; gap points retain PDF coordinates.']}
