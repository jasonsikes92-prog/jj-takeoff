"""Window-role hypotheses from coded tags and native frame/glazing geometry."""
import copy
import hashlib
import json
import math
from pathlib import Path
import fitz


def recognize(openings,drawings_by_page,plan_sha256):
    pages={}
    for page,drawings in drawings_by_page.items():
        lines=[]
        for index,drawing in enumerate(drawings):
            if (drawing.get('type') not in ('s','fs') or not drawing.get('color')
                    or min(drawing['color'])>=.99 or drawing.get('stroke_opacity',1)<=0
                    or drawing.get('dashes') not in (None,'[] 0')):continue
            for item,edge in enumerate(drawing['items']):
                if edge[0]=='l':lines.append({'path':index,'item':item,'points':[list(p) for p in edge[1:]]})
        pages[page]=lines
    results=[]
    for opening in openings:
        nominal=opening.get('printed_nominal_size') or {}
        if nominal.get('type_code') not in ('SH','FX'):continue
        width=nominal['width_inches'];scale=opening['points_per_foot']/12
        if not 12<=width<=144 or not 12<=nominal['height_inches']<=120 or scale<=0:continue
        a,b=opening['points'];axis=0 if abs(a[1]-b[1])<1e-6 else 1 if abs(a[0]-b[0])<1e-6 else None
        if axis is None or abs(math.dist(a,b)/scale-width)>1:continue
        origin=min(a[axis],b[axis]);center=(a[1-axis]+b[1-axis])/2
        longitudinal=[];cross=[]
        for line in pages.get(opening['page'],[]):
            points=[[(p[axis]-origin)/scale,(p[1-axis]-center)/scale] for p in line['points']]
            if not all(-1<=p[0]<=width+1 and abs(p[1])<=8 for p in points):continue
            p,q=points
            if abs(p[1]-q[1])<.01:
                lo,hi=sorted((p[0],q[0]))
                if .25<=lo<=3 and width-3<=hi<=width-.25:longitudinal.append((lo,hi,(p[1]+q[1])/2,line))
            elif abs(p[0]-q[0])<.01:
                lo,hi=sorted((p[1],q[1]));cross.append(((p[0]+q[0])/2,lo,hi,line))
        matches=[]
        for index,p in enumerate(longitudinal):
            for q in longitudinal[index+1:]:
                if abs(p[0]-q[0])>.05 or abs(p[1]-q[1])>.05 or not .25<=abs(p[2]-q[2])<=2:continue
                lo,hi=sorted((p[2],q[2]))
                if max(abs(lo),abs(hi))>4:continue
                # Both glazing ends and outer jambs must cross the two lines.
                supports=[[c for c in cross if abs(c[0]-x)<=.05 and c[1]<=lo+.05 and c[2]>=hi-.05]
                          for x in (p[0],p[1],0,width)]
                if not all(supports):continue
                key=[round(v,3) for v in (p[0],p[1],lo,hi)]
                if any(m['geometry_inches']==key for m in matches):continue
                matches.append({'geometry_inches':key,'glazing_lines':[p[3],q[3]],
                    'jamb_lines':[group[0][3] for group in supports]})
        if not matches:continue
        current=opening['review_status']=='current_source_review'
        conflict=current and opening.get('role')!='window'
        evidence={'plan_sha256':plan_sha256,'opening_source_sha256':opening['source_sha256'],
            'opening_points':opening['points'],'points_per_foot':opening['points_per_foot'],
            'tag':opening['tag'],'matches':matches}
        results.append({'opening_id':opening['opening_id'],'page':opening['page'],'tag':opening['tag'],
            'opening_source_sha256':opening['source_sha256'],'evidence':evidence,
            'source_sha256':hashlib.sha256(json.dumps(evidence,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'status':'ambiguous_symbols' if len(matches)!=1 else 'conflicts_with_review' if conflict else
                'corroborates_review' if current else 'stale_review_requires_reconciliation' if opening['review_status']=='stale_source_review'
                else 'candidate_requires_review',
            'window_component_count':None,'product_fit_verified':False,'purchase_released':False})
    return {'method':'native_window_frame_at_coded_tag_v1','candidates':results,
        'coverage_certified':False,'purchase_released':False,
        'limitations':['SH/FX tags plus frame/glazing geometry support an estimating window-role hypothesis only.',
            'The code convention is not a product specification; bare tags and unsupported symbols remain unresolved.',
            'Individual units, mulling, operation, performance and manufacturer rough openings require separate evidence.']}


def apply_from_plan(plan,schedule):
    plan=Path(plan);digest=schedule['plan_sha256']
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=digest:raise ValueError('Window symbol drawing changed')
    with fitz.open(plan) as doc:
        pages={o['page'] for o in schedule['openings']}
        drawings={p:doc[p-1].get_drawings() for p in sorted(pages) if 1<=p<=len(doc)}
    candidates=recognize(schedule['openings'],drawings,digest)
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=digest:raise ValueError('Window symbol drawing changed during extraction')
    result=copy.deepcopy(schedule);result['window_symbol_candidates']=candidates
    by_id={c['opening_id']:c for c in candidates['candidates']}
    for opening in result['openings']:
        symbol=by_id.get(opening['opening_id'])
        if not symbol:continue
        if opening['review_status']=='current_source_review' and symbol['status'] in ('conflicts_with_review','ambiguous_symbols'):
            keys=('role','door_configuration','drawn_panel_count','window_component_count','room_class','role_source')
            opening['conflicting_source_review']={k:opening.get(k) for k in keys}
            for key in keys:opening[key]=None
            opening['review_status']='symbol_conflict_requires_review'
        elif opening['review_status']=='role_unreviewed' and symbol['status']=='candidate_requires_review':
            opening.update(role='window',location='Window at printed tag '+opening['tag'],
                review_status='native_symbol_inference',interpretation_requires_review=True,
                role_source='Automatic estimating interpretation: window-coded tag and native frame/glazing lines at the current wall gap. Unit count and product specifications remain unresolved.',
                native_interpretation={'kind':'window','source_sha256':symbol['source_sha256'],'evidence':symbol['evidence']})
    result['unresolved_opening_ids']=([o['opening_id'] for o in result['openings'] if o['role'] is None]
        +[o['opening_id'] for o in result.get('unlocated_opening_tags',[])])
    result['inferred_opening_ids']=[o['opening_id'] for o in result['openings'] if o['review_status']=='native_symbol_inference']
    result['reviewed_role_counts']={role:sum(o['role']==role and o['review_status']=='current_source_review' for o in result['openings'])
        for role in result['reviewed_role_counts']}
    result['inferred_role_counts']={role:sum(o['role']==role and o['review_status']=='native_symbol_inference' for o in result['openings'])
        for role in result['reviewed_role_counts']}
    if result['unresolved_opening_ids'] or result['inferred_opening_ids']:result['enumerated_window_unit_count']=None
    return result
