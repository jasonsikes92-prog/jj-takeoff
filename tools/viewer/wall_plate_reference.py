"""Partial plate-length allowances from visible wall runs and frozen company practices."""
import copy
import hashlib
import json
import math
from pathlib import Path
from company_scope_review import read_decisions
from wall_run_candidates import from_state
from opening_schedule import schedule as opening_schedule
from wall_gap_labels import from_plan_state as wall_gaps
from wall_plate_connections import calculate as connection_references


def opening_references(runs,schedule,counts):
    """Net installed plate allowances at current reviewed door/window gaps."""
    if (runs['plan_sha256'],runs['measurement_version'])!=(schedule['plan_sha256'],schedule['measurement_version']):
        raise ValueError('Opening plate references belong to another drawing or revision')
    by_run={r['id']:r for r in runs['run_candidates']};items=[];pending=[];seen=set();used=set()
    for opening in schedule['openings']:
        identity=opening['opening_id']
        if identity in seen:raise ValueError('Duplicate opening plate reference')
        seen.add(identity)
        role=opening['role']
        if opening['review_status']!='current_source_review' or role not in ('window','interior_door','special_interior_door','exterior_door'):
            pending.append({'opening_id':identity,'reason':'Current door/window role required; passage plate continuity is unresolved'})
            continue
        run=by_run.get(opening['run_id'])
        if run is None:raise ValueError('Opening plate reference has no current wall run')
        if opening['page']!=run['page'] or opening['points_per_foot']!=run['points_per_foot']:
            raise ValueError('Opening plate page or scale differs from its wall')
        points=opening['points'];axis=0 if run['axis']=='horizontal' else 1
        if len(points)!=2 or any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Finite opening endpoints required')
        a,b=sorted(p[axis] for p in points);cross=sum(run['centerline_coordinate_range_pt'])/2
        matches=[i for i,g in enumerate(run['gaps'],1) if abs(g['from_pt']-a)<1e-7 and abs(g['to_pt']-b)<1e-7]
        if a>=b or len(matches)!=1 or any(abs(p[1-axis]-cross)>1e-7 for p in points):
            raise ValueError('Opening plate endpoints must match one current wall gap')
        gap_id=run['id']+':gap-'+str(matches[0])
        if opening['gap_id']!=gap_id or gap_id in used:raise ValueError('Opening gap mismatch or duplicate ownership')
        used.add(gap_id);length=(b-a)/run['points_per_foot']
        items.append({'opening_id':identity,'gap_id':gap_id,'run_id':run['id'],'role':role,
            'source_sha256':opening['source_sha256'],'role_source':opening['role_source'],
            'points':points,'page':opening['page'],'points_per_foot':run['points_per_foot'],
            'drawn_gap_lf':length,'top_plate_reference_lf':None if counts['top'] is None else length*counts['top'],
            'bottom_plate_reference_lf':None if role=='window' and counts['bottom'] is None else length*counts['bottom'] if role=='window' else 0})
    top=math.fsum(i['drawn_gap_lf'] for i in items)
    bottom=math.fsum(i['drawn_gap_lf'] for i in items if i['role']=='window')
    return {'openings':items,'pending_openings':pending,'stale_or_missing_label_ids':schedule['stale_or_missing_label_ids'],
        'reviewed_opening_gap_lf':top,'reviewed_window_gap_lf':bottom,
        'top_plate_reference_lf':None if not items or counts['top'] is None else top*counts['top'],
        'bottom_plate_reference_lf':None if not items or counts['bottom'] is None else bottom*counts['bottom'],
        'remaining_gap_count':sum(len(r['gaps']) for r in by_run.values())-len(used),
        'basis':'Partial net installed allowance: job top-plate courses across current reviewed door/window gaps; bottom plates beneath windows only. Drawn gaps, not nominal tags or manufacturer rough openings. Passage continuity, header/plate exceptions, pocket assemblies and temporary door-bottom stock still require review.'}


def calculate(runs,decisions):
    counts={}
    for side in ('top','bottom'):
        key='framing.'+side+'_plates';value=decisions['settings'].get(key)
        if value is not None and (type(value) is not int or value<0):
            raise ValueError('Plate course count must be a nonnegative integer or unknown')
        counts[side]=value
    details=[];seen=set()
    for run in runs['run_candidates']:
        if run['id'] in seen:raise ValueError('Duplicate wall run')
        seen.add(run['id']);scale=run['points_per_foot'];intervals=[]
        if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:
            raise ValueError('Positive wall scale required')
        for a,b in sorted(run['visible_intervals_pt']):
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in (a,b)) or a>=b:
                raise ValueError('Finite ordered wall intervals required')
            if intervals and a<=intervals[-1][1]:intervals[-1][1]=max(b,intervals[-1][1])
            else:intervals.append([a,b])
        if not intervals:raise ValueError('Visible wall intervals required')
        length=math.fsum(b-a for a,b in intervals)/scale
        details.append({'run_id':run['id'],'page':run['page'],'source_measurement_ids':run['source_measurement_ids'],
            'visible_intervals_pt':intervals,'points_per_foot':scale,'visible_wall_lf':length,
            'top_plate_reference_lf':None if counts['top'] is None else length*counts['top'],
            'bottom_plate_reference_lf':None if counts['bottom'] is None else length*counts['bottom'],
            'unassigned_gaps':run['gaps']})
    visible=math.fsum(r['visible_wall_lf'] for r in details) if details else None
    return {'plan_sha256':runs['plan_sha256'],'measurement_version':runs['measurement_version'],
        'runs':details,'visible_wall_lf':visible,'plate_courses':counts,
        'top_plate_reference_lf':None if visible is None or counts['top'] is None else visible*counts['top'],
        'bottom_plate_reference_lf':None if visible is None or counts['bottom'] is None else visible*counts['bottom'],
        'practice_provenance':{key:decisions['provenance'].get(key) for key in ('framing.top_plates','framing.bottom_plates')},
        'unresolved_measurements':runs['unresolved_measurements'],'excluded_measurements':runs['excluded_measurements'],
        'unassigned_gap_count':sum(len(r['unassigned_gaps']) for r in details),
        'basis':'Visible wall intervals only, multiplied by the job plate-course practice. Gaps are not filled. Wall-face classification is not a structural framing approval.',
        'remaining':['Resolve wall layers, openings, continuity and junction ownership before completing plate scope.',
            'Determine framing applicability, material size, bottom-plate treatment/support and special-height conditions.',
            'Add reviewed joints/laps and select whole-stock cuts; these linear references are not a purchase order.'],
        'complete_wall_plate_quantity':None,'purchase_quantity':None,'certified':False}


def from_folder(folder,state,config=None):
    folder=Path(folder);path=folder/'wall_plate_reference.json';raw=path.read_bytes()
    saved=json.loads(raw)
    if config is not None and saved!=config:raise ValueError('Wall plate mapping changed; reload and review')
    config=saved
    source_paths=[folder/name for name in ('wall_classification_review.json','wall_alignment_breaks.json','opening_schedule_review.json','plan.pdf')]
    source_bytes={p:p.read_bytes() if p.exists() else None for p in source_paths}
    wall_raw=source_bytes[source_paths[0]]
    decisions=read_decisions(folder,config,state['plan_sha256'])
    runs=from_state(state,json.loads(wall_raw) if wall_raw is not None else None)
    result=calculate(runs,decisions)
    gaps=wall_gaps(folder/'plan.pdf',state,json.loads(wall_raw) if wall_raw is not None else None,
        json.loads(source_bytes[source_paths[1]]) if source_bytes[source_paths[1]] is not None else None)
    schedule=opening_schedule(state,runs,gaps,
        json.loads(source_bytes[source_paths[2]]) if source_bytes[source_paths[2]] is not None else None)
    result['opening_plate_reference']=opening_references(runs,schedule,result['plate_courses'])
    result['connection_plate_reference']=connection_references(state,runs,gaps,result['opening_plate_reference'],result['plate_courses'])
    result['source_sha256']=hashlib.sha256(json.dumps({'mapping':config,'runs':runs,
        'opening_schedule':schedule,'wall_gaps':gaps,
        'settings':decisions['settings'],'provenance':decisions['provenance']},sort_keys=True,allow_nan=False).encode()).hexdigest()
    if path.read_bytes()!=raw or any((p.read_bytes() if p.exists() else None)!=data for p,data in source_bytes.items()):
        raise ValueError('Wall plate sources changed during calculation')
    if read_decisions(folder,config,state['plan_sha256'])!=decisions:raise ValueError('Plate practices changed during calculation')
    return result


def import_reference(draft,reference):
    if 'wall_plate_reference' in draft:raise ValueError('Wall plate reference already imported')
    if (draft['plan_sha256'],draft['measurement_version'])!=(reference['plan_sha256'],reference['measurement_version']):
        raise ValueError('Plate reference belongs to another drawing or measurement revision')
    result=copy.deepcopy(draft)
    rows=[r for r in result['rows'] if tuple(r[k].strip() for k in ('name','parent','cost_type'))==('Framing Lumber','Framing','MATERIAL')]
    if len(rows)!=1:raise ValueError('Unique framing-lumber template owner required')
    row=rows[0]
    if any(row.get(k) is not None for k in ('draft_quantity','line_cost')) or row.get('covered_by_package') or row['completion_status'].startswith('not_applicable'):
        raise ValueError('Framing row is already priced, assigned or excluded')
    for side in ('top','bottom'):
        identity='visible-wall-'+side+'-plate-reference'
        if any(a['id']==identity for r in result['rows'] for a in r.get('assembly_inputs',[])):
            raise ValueError('Visible plate reference already assigned')
        item={'id':identity,'label':'Visible wall '+side+' plate length (partial)',
            'quantity':reference[side+'_plate_reference_lf'],'unit':'LF','use':'assembly_input',
            'template_rows':[row['excel_row']],'certified':False,'basis':reference['basis'],
            'source_snapshot':{'source_sha256':reference['source_sha256']},'remaining':reference['remaining']}
        if item['quantity'] is None:
            item['reason']='Wall geometry or plate-course practice unresolved'
            result.setdefault('pending_quantities',[]).append(item)
        else:row.setdefault('assembly_inputs',[]).append(item)
    for key,prefix,label in (('opening_plate_reference','reviewed-opening','Reviewed opening'),
            ('connection_plate_reference','wall-connection','Wall connection')):
        component=reference.get(key)
        if component is None:continue
        for side in ('top','bottom'):
            identity=prefix+'-'+side+'-plate-reference'
            if any(a['id']==identity for r in result['rows'] for a in r.get('assembly_inputs',[])):
                raise ValueError('Plate component reference already assigned')
            item={'id':identity,'label':label+' '+side+' plate length (partial)',
                'quantity':component[side+'_plate_reference_lf'],'unit':'LF','use':'assembly_input',
                'template_rows':[row['excel_row']],'certified':False,'basis':component['basis'],
                'source_snapshot':{'source_sha256':reference['source_sha256']},'remaining':reference['remaining']}
            if item['quantity'] is None:
                item['reason']='Current '+label.lower()+' geometry or plate-course practice unresolved'
                result.setdefault('pending_quantities',[]).append(item)
            else:row.setdefault('assembly_inputs',[]).append(item)
    row['certified']=False
    result['wall_plate_reference']={k:reference[k] for k in ('source_sha256','visible_wall_lf',
        'top_plate_reference_lf','bottom_plate_reference_lf','unassigned_gap_count','unresolved_measurements','remaining')}
    for key in ('opening_plate_reference','connection_plate_reference'):
        if key in reference:result['wall_plate_reference'][key]=reference[key]
    return result
