"""Source-bound opening roles with printed nominal sizes kept apart from gaps."""
import hashlib
import json
import re
from pathlib import Path
from wall_alignment_breaks import source_binding,read_review as alignment_review
from wall_classification_review import read_review as wall_review
from wall_run_candidates import from_state
from wall_gap_labels import from_plan_state
from door_policy_revision import read_policy,apply_policy
from door_hardware_specifications import apply_hardware_policy


def printed_size(text):
    match=re.fullmatch(r'(\d)(\d)(\d)(\d)([A-Z]*)',text)
    if not match:return None
    wf,wi,hf,hi=map(int,match.groups()[:4])
    width,height=12*wf+wi,12*hf+hi
    if width<=0 or height<=0:return None
    return {'width_inches':width,'height_inches':height,'type_code':match.group(5) or None,
        'basis':'Four-digit feet/inches tag convention; nominal size, not product rough opening'}


def schedule(state,runs,gaps,review=None):
    by_run={r['id']:r for r in runs['run_candidates']};labels={l['id']:l for l in gaps['labels']}
    decisions={}
    if review is not None:
        if review.get('plan_sha256')!=state['plan_sha256']:raise ValueError('Opening schedule review belongs to another drawing')
        if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():raise ValueError('Opening schedule reviewer required')
        if not isinstance(review.get('openings'),list):raise ValueError('Opening schedule review records required')
        for record in review['openings']:
            identity=record.get('label_id')
            if not isinstance(identity,str) or not identity or identity in decisions:raise ValueError('Unique opening label IDs required')
            if record.get('role') not in ('window','interior_door','special_interior_door','exterior_door','open_passage'):
                raise ValueError('Explicit opening role required')
            if any(not isinstance(record.get(k),str) or not record[k].strip() for k in ('basis','location')):
                raise ValueError('Opening role needs source basis and location')
            if record.get('room_class') is not None and not isinstance(record['room_class'],str):
                raise ValueError('Opening room class must be text or unknown')
            configurations={'interior_door':('single_hinged',),'special_interior_door':('pocket','bypass','bifold','double_hinged','sliding'),
                'exterior_door':('single_hinged','double_hinged','sliding')}
            if record.get('door_configuration') is not None and record['door_configuration'] not in configurations.get(record['role'],()):
                raise ValueError('Door configuration must match the source-reviewed opening role')
            panels=record.get('drawn_panel_count')
            if panels is not None and (type(panels) is not int or panels<=0 or not record.get('door_configuration')):
                raise ValueError('Drawn door panel count needs a reviewed configuration and positive integer')
            if record.get('project_core') is not None and (record['role'] in ('window','open_passage')
                    or record['project_core'] not in ('solid','hollow')
                    or not isinstance(record.get('project_core_source'),str) or not record['project_core_source'].strip()):
                raise ValueError('Door core override needs an explicit door selection and source')
            if record.get('project_hardware') is not None and (record['role'] in ('window','open_passage')
                    or not isinstance(record['project_hardware'],str) or not record['project_hardware'].strip()
                    or not isinstance(record.get('project_hardware_source'),str) or not record['project_hardware_source'].strip()):
                raise ValueError('Door hardware override needs an explicit door selection and source')
            count=record.get('window_component_count')
            if count is not None and (record['role']!='window' or type(count) is not int or count<=0):
                raise ValueError('Window component counts must be positive integers on windows')
            decisions[identity]=record
    openings=[];used=set()
    for gap in gaps['gaps']:
        if gap['status']!='unique_tag_location_candidate':continue
        label=labels[gap['candidate_label_ids'][0]];identity=label['id'];used.add(identity)
        run=by_run[gap['run_id']]
        binding=hashlib.sha256(json.dumps({'gap_source':source_binding(state,run,gap),'label':label},sort_keys=True).encode()).hexdigest()
        record=decisions.get(identity);current=bool(record and record.get('source_sha256')==binding)
        legacy_direction=False
        # Older cardinal labels stored axis but not the redundant direction vector.
        # Recompute that exact old fingerprint; all geometry and other evidence remain bound.
        cardinal={'horizontal':([1.0,0.0],[-1.0,0.0]),'vertical':([0.0,1.0],[0.0,-1.0])}
        if record and not current and label.get('direction') in cardinal.get(label.get('axis'),()):
            old_label={k:v for k,v in label.items() if k!='direction'}
            old_binding=hashlib.sha256(json.dumps({'gap_source':source_binding(state,run,gap),'label':old_label},sort_keys=True).encode()).hexdigest()
            legacy_direction=record.get('source_sha256')==old_binding
            current=legacy_direction
        nominal=printed_size(label['text']);center=sum(run['centerline_coordinate_range_pt'])/2
        endpoints=([[gap['from_pt'],center],[gap['to_pt'],center]] if gap['axis']=='horizontal'
            else [[center,gap['from_pt']],[center,gap['to_pt']]])
        openings.append({'opening_id':'opening-'+identity.removeprefix('printed-tag-'),
            'label_id':identity,'tag':label['text'],'page':gap['page'],'label_bounds_pt':label['bbox_pt'],
            'gap_id':gap['id'],'run_id':run['id'],'source_sha256':binding,'points':endpoints,
            'points_per_foot':run['points_per_foot'],'drawn_gap_width_inches':gap['drawn_gap_lf']*12,
            'printed_nominal_size':nominal,'product_rough_opening_width_inches':None,
            'role':record['role'] if current else None,'location':record['location'] if current else None,
            'room_class':record.get('room_class') if current else None,
            'door_configuration':record.get('door_configuration') if current else None,
            'drawn_panel_count':record.get('drawn_panel_count') if current else None,
            'project_core':record.get('project_core') if current else None,
            'project_core_source':record.get('project_core_source') if current else None,
            'window_component_count':record.get('window_component_count') if current else None,
            'review_status':'current_source_review' if current else 'stale_source_review' if record else 'role_unreviewed',
            'role_source':record['basis'] if current else None,'purchase_released':False})
        if legacy_direction:openings[-1]['review_binding_basis']='legacy_cardinal_label_without_direction'
        if current and record.get('project_hardware') is not None:
            openings[-1].update(project_hardware=record['project_hardware'],
                project_hardware_source=record['project_hardware_source'])
    windows=[o for o in openings if o['role']=='window']
    counts={role:sum(o['role']==role for o in openings) for role in
        ('window','interior_door','special_interior_door','exterior_door','open_passage')}
    unresolved=[o['opening_id'] for o in openings if o['role'] is None]
    unlocated=[{'opening_id':'opening-'+identity.removeprefix('printed-tag-'),'label_id':identity,
        'tag':label['text'],'page':label['page'],'label_bounds_pt':label['bbox_pt'],
        'reason':'Printed opening tag has no unique current wall-gap association; do not treat it as excluded scope.'}
        for identity,label in labels.items() if identity not in used and printed_size(label['text']) is not None]
    unresolved+= [o['opening_id'] for o in unlocated]
    missing=sorted(set(decisions)-used)
    return {'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],'openings':openings,
        'reviewed_role_counts':counts,'unresolved_opening_ids':unresolved,'unlocated_opening_tags':unlocated,
        'stale_or_missing_label_ids':missing,
        'enumerated_window_unit_count':sum(o['window_component_count'] for o in windows)
            if windows and not unresolved and not missing and all(o['window_component_count'] is not None for o in windows) else None,
        'review_sha256':hashlib.sha256(json.dumps(review,sort_keys=True).encode()).hexdigest() if review is not None else None,
        'reviewer':review['reviewer'] if review is not None else None,'reviewer_identity_authenticated':False,
        'coverage_certified':False,'purchase_quantity':None,'estimate_released':False,
        'limitations':['Only uniquely located printed tags are enumerated; untagged or undetected openings remain outside this schedule.',
            'Role and component counts require source review. Bare numeric tags do not establish doors; mull tags do not establish unit counts.',
            'Printed nominal sizes, drawn gaps and manufacturer rough openings are different references.',
            'Door leaves, hardware, header/support details and product selections remain separate scope.']}


def withhold_symbol_conflicts(result):
    """Keep contradictory review evidence visible, but exclude it from quantities."""
    conflicts={c['opening_id']:c for c in result['door_symbol_candidates']['candidates']
        if c['status'] in ('conflicts_with_review','ambiguous_symbols')}
    for row in result['openings']:
        if row['opening_id'] not in conflicts or row['review_status']!='current_source_review':continue
        keys=('role','door_configuration','drawn_panel_count','window_component_count','room_class','role_source')
        row['conflicting_source_review']={k:row.get(k) for k in keys}
        for key in keys:row[key]=None
        row['review_status']='symbol_conflict_requires_review'
        if row['opening_id'] not in result['unresolved_opening_ids']:result['unresolved_opening_ids'].append(row['opening_id'])
    result['reviewed_role_counts']={role:sum(o['role']==role for o in result['openings'])
        for role in result['reviewed_role_counts']}
    if result['unresolved_opening_ids']:result['enumerated_window_unit_count']=None
    return result


def from_folder(folder,state,include_company_policy=True):
    folder=Path(folder);walls=wall_review(folder);runs=from_state(state,walls)
    gaps=from_plan_state(folder/'plan.pdf',state,walls,alignment_review(folder))
    path=folder/'opening_schedule_review.json'
    review=json.loads(path.read_bytes()) if path.exists() else None
    result=schedule(state,runs,gaps,review)
    if (folder/'plan.pdf').is_file():
        from door_symbol_candidates import from_plan as door_symbols
        result['door_symbol_candidates']=door_symbols(folder/'plan.pdf',result['openings'],state['plan_sha256'])
        result=withhold_symbol_conflicts(result)
        from window_symbol_candidates import apply_from_plan as window_symbols
        result=window_symbols(folder/'plan.pdf',result)
    if (folder/'room_use_review.json').exists() or ((folder/'plan.pdf').is_file() and any(
            o['role'] in ('interior_door','special_interior_door') for o in result['openings'])) or result.get('door_symbol_candidates',{}).get('candidates'):
        from room_region_candidates import from_folder as room_regions
        from door_room_associations import associate
        from native_door_interpretation import interpret
        rooms=room_regions(folder,state,include_surfaces=False)
        result=associate(interpret(result,rooms),rooms)
    if include_company_policy:
        result['door_core_review']=apply_policy(result,read_policy(folder,state['plan_sha256']))
        hardware_policy=read_policy(folder,state['plan_sha256'],hardware=True)
        if hardware_policy is not None:
            result['door_hardware_review']=apply_hardware_policy(result,hardware_policy)
    return result
