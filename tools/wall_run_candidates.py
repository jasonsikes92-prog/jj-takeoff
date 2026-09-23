"""Describe collinear native wall pieces without filling openings or pricing runs."""
import hashlib
import json
from wall_classification_review import resolve,STROKE_METHODS

METHOD='collinear_wall_run_candidates_v1'
WALL_METHOD='native_filled_wall_rectangles_v1'


def from_state(state,classification_review=None):
    decisions,review_digest=resolve(state,classification_review)
    from wall_network_inference import infer
    inference=infer(state,decisions)
    decisions.update(inference['decisions'])
    walls=sorted((m for m in state['measurements'].values() if m.get('source_method') in
        (WALL_METHOD,*STROKE_METHODS)),key=lambda m:m['id'])
    identity=[{k:m[k] for k in ('id','page','kind','points','points_per_foot')} for m in walls]
    digest=hashlib.sha256(json.dumps(sorted(identity,key=lambda m:m['id']),sort_keys=True).encode()).hexdigest()
    pieces=[];unresolved=[];excluded=[]
    for m in walls:
        decision=decisions.get(m['id'])
        if m['source_method']!=WALL_METHOD or decision is not None or m.get('requires_wall_classification'):
            if decision and decision['current'] and decision['decision']=='not_wall_faces':
                excluded.append({'measurement_id':m['id'],'reason':decision['basis']})
                continue
            if not decision or not decision['current'] or decision['decision']!='wall_faces':
                reason=('Wall classification is stale after geometry, scale or source changes' if decision and not decision['current']
                    else decision['basis'] if decision else 'Parallel-stroke candidate needs wall/layer classification before run and opening analysis')
                unresolved.append({'measurement_id':m['id'],'reason':reason})
                continue
        points=m['points'];kind=m['kind']
        if kind=='area' and decision and decision.get('axis'):
            from wall_short_piece_directions import projections
            direction=0 if decision['axis']=='horizontal' else 1
            matches=[p for axis,p,short in projections(m) if axis==direction and short]
            if matches:points=matches[0];kind='length'
        if kind!='length' or len(points)!=2:
            unresolved.append({'measurement_id':m['id'],'reason':'Short-piece outline or edited polyline needs a run-direction review'})
            continue
        a,b=points
        axis=0 if abs(a[1]-b[1])<=1e-6 else 1 if abs(a[0]-b[0])<=1e-6 else None
        if axis is None:
            unresolved.append({'measurement_id':m['id'],'reason':'Diagonal edited segment is outside the orthogonal run calculation'})
            continue
        pieces.append({'measurement_id':m['id'],'page':m['page'],'ppf':m['points_per_foot'],
                       'axis':axis,'coordinate':(a[1-axis]+b[1-axis])/2,
                       'low':min(a[axis],b[axis]),'high':max(a[axis],b[axis])})
    groups=[]
    for p in sorted(pieces,key=lambda p:(p['page'],p['ppf'],p['axis'],p['coordinate'],p['low'],p['measurement_id'])):
        tolerance=p['ppf']*.25/12
        matching=[g for g in groups if (g['page'],g['ppf'],g['axis'])==(p['page'],p['ppf'],p['axis'])
                  and p['coordinate']-g['minimum_coordinate']<=tolerance]
        if matching:
            matching[-1]['parts'].append(p)
        else:
            groups.append({'page':p['page'],'ppf':p['ppf'],'axis':p['axis'],
                           'minimum_coordinate':p['coordinate'],'parts':[p]})
    runs=[]
    for group in groups:
        parts=sorted(group['parts'],key=lambda p:(p['low'],p['high'],p['measurement_id']))
        spans=[]
        for p in parts:
            if spans and p['low']<=spans[-1][1]:
                spans[-1][1]=max(spans[-1][1],p['high'])
            else:
                spans.append([p['low'],p['high']])
        ppf=group['ppf'];visible=sum(b-a for a,b in spans)/ppf
        gaps=[{'from_pt':a[1],'to_pt':b[0],'length_lf':(b[0]-a[1])/ppf,
               'status':'Unmeasured gap; reconcile opening or separate wall scope'} for a,b in zip(spans,spans[1:])]
        member_ids=sorted(p['measurement_id'] for p in parts)
        runs.append({'id':'wall-run-'+hashlib.sha256(json.dumps(member_ids).encode()).hexdigest()[:16],
            'page':group['page'],'axis':'horizontal' if group['axis']==0 else 'vertical',
            'points_per_foot':ppf,'source_measurement_ids':member_ids,
            'centerline_coordinate_range_pt':[min(p['coordinate'] for p in parts),max(p['coordinate'] for p in parts)],
            'visible_intervals_pt':spans,'visible_union_lf':visible,'gaps':gaps,
            'gross_alignment_span_lf':(spans[-1][1]-spans[0][0])/ppf,
            'overlapping_piece_lf':max(0,sum(p['high']-p['low'] for p in parts)/ppf-visible),
            'scope_status':'Collinear candidate only; wall meaning, openings and junctions require review'})
        inferred={i:decisions[i]['network_sha256'] for i in member_ids if decisions.get(i,{}).get('inferred')}
        if inferred:
            runs[-1]['inferred_wall_sources']=inferred
            runs[-1]['wall_interpretation_requires_review']=True
    return {'method':METHOD,'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
            'measurement_inputs_sha256':digest,'source_wall_candidates':len(walls),
            'run_candidates':runs,'unresolved_measurements':unresolved,
            'excluded_measurements':excluded,'classification_review_sha256':review_digest,
            'classification_reviewer':classification_review['reviewer'] if classification_review else None,
            'classification_decisions':decisions,'reviewer_identity_authenticated':False,
            'wall_network_inference':inference,
            'alignment_tolerance_inches':.25,'whole_wall_quantity':None,'purchase_quantity':None,
            'certified':False,'estimate_released':False,
            'limitations':['Collinearity does not establish a continuous wall; disconnected objects can share an alignment.',
                'Gap spans are not added to visible wall length or converted into studs, plates, headers or finish area.',
                'Short pieces, polylines and diagonal edits remain unresolved; no column or corner direction is inferred.',
                'Overlaps are reported within an alignment only; perpendicular intersections and wall assembly ownership need separate review.']}
