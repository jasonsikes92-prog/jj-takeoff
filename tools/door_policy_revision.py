"""Resolve door-core policy from frozen job inputs or an explicit narrow revision."""
import hashlib
import json
from pathlib import Path
from company_profile import resolve
from door_specifications import door_core_specifications
from door_hardware_specifications import KEY as HARDWARE_KEY

KEY='doors.interior_core_by_room'


def read_policy(folder,plan_sha256,*,hardware=False):
    key=HARDWARE_KEY if hardware else KEY
    folder=Path(folder).resolve();path=folder/('door_hardware_policy_revision.json' if hardware else 'door_policy_revision.json')
    revision=json.loads(path.read_bytes()) if path.exists() else None
    if revision is not None:
        if revision.get('plan_sha256')!=plan_sha256:raise ValueError('Door policy revision belongs to another drawing')
        if any(not isinstance(revision.get(k),str) or not revision[k].strip() for k in ('basis','reviewer')):
            raise ValueError('Door policy revision needs its basis and reviewer')
        intake_path=(folder/revision['base_intake_path']).resolve()
        if not intake_path.is_relative_to(folder.parent):raise ValueError('Base intake must remain inside the job')
    else:
        intake_path=folder.parent/'estimate_intake.json'
        if not intake_path.exists():return None
    raw=intake_path.read_bytes();intake=json.loads(raw);intake_sha=hashlib.sha256(raw).hexdigest()
    if intake['plan_sha256']!=plan_sha256:raise ValueError('Door policy intake belongs to another drawing')
    if revision is not None and revision['base_intake_sha256']!=intake_sha:raise ValueError('Base job decisions changed; review the door policy revision')
    base_path=(intake_path.parent/intake['company_profile_snapshot']).resolve()
    if not base_path.is_relative_to(intake_path.parent):raise ValueError('Base profile must remain inside its job')
    base_raw=base_path.read_bytes();base_profile=json.loads(base_raw)
    if hashlib.sha256(base_raw).hexdigest()!=intake['company_profile_sha256']:raise ValueError('Base company profile changed')
    if (intake['company_profile_id'],intake['company_profile_version'])!=(base_profile['profile_id'],base_profile['version']):
        raise ValueError('Base company profile identity differs from intake')
    replay=resolve(base_profile,intake['project_facts'],intake['project_overrides'])
    if any(replay[k]!=intake[k] for k in ('settings','provenance','resolved_conflicts')):
        raise ValueError('Saved job decisions differ from their profile and overrides')
    profile=base_profile;profile_sha=intake['company_profile_sha256']
    if revision is not None:
        profile_path=(folder/revision['profile_path']).resolve()
        if not profile_path.is_relative_to(folder):raise ValueError('Revised door profile must remain inside the measurement folder')
        profile_raw=profile_path.read_bytes();profile_sha=hashlib.sha256(profile_raw).hexdigest()
        if profile_sha!=revision['profile_sha256']:raise ValueError('Revised door profile changed')
        profile=json.loads(profile_raw)
        if profile['profile_id']!=base_profile['profile_id']:raise ValueError('Door policy revision belongs to another company profile')
        replay=resolve(profile,intake['project_facts'],intake['project_overrides'])
    if key not in replay['settings']:
        if revision is not None:raise ValueError('Revised profile does not resolve the requested door policy')
        return None
    return {'plan_sha256':plan_sha256,'company_profile_version':profile['version'],'company_profile_sha256':profile_sha,
        'settings':{key:replay['settings'][key]},'provenance':{key:replay['provenance'][key]},
        'resolved_conflicts':[c for c in replay['resolved_conflicts'] if c['key']==key],
        'policy_keys':[key],'base_intake_sha256':intake_sha,'base_profile_version':base_profile['version'],
        'revision_sha256':hashlib.sha256(json.dumps(revision,sort_keys=True).encode()).hexdigest() if revision else None,
        'revision_basis':revision['basis'] if revision else 'Original frozen job policy',
        'other_job_settings_changed':False}


def apply_policy(openings,policy):
    if policy is None:return None
    scopes={'interior_door':'interior','special_interior_door':'special_interior','exterior_door':'exterior',
        'open_passage':'open_passage',None:'unknown'}
    schedule={'plan_sha256':openings['plan_sha256'],'source':'Current source-bound opening schedule','openings':[]}
    for row in openings['openings']:
        if row['role']=='window':continue
        room=row.get('room_class')
        if room=='closet':room='other_interior'
        elif room=='toilet_room' and room not in policy['settings'].get(KEY,{}):room='bathroom'
        schedule['openings'].append({'opening_id':row['opening_id'],'scope':scopes[row['role']],
            'room_class':room,
            'room_source':row.get('room_source',row.get('role_source')),
            'project_core':row.get('project_core'),'project_core_source':row.get('project_core_source')})
    result=door_core_specifications(policy,schedule)
    inferred={o['opening_id']:o['native_interpretation'] for o in openings['openings'] if o.get('review_status')=='native_symbol_inference'}
    assignments={o['opening_id']:o['room_association'] for o in openings['openings'] if o.get('room_assignment_requires_review')}
    for row in result['openings']:
        if row['opening_id'] in assignments:
            row['automatic_room_assignment']=assignments[row['opening_id']]
            row['interpretation_requires_review']=True
            if row['basis']=='company_default_for_reviewed_room':row['basis']='company_default_for_inferred_room'
        if row['opening_id'] in inferred:
            row['automatic_interpretation']=inferred[row['opening_id']]
            row['interpretation_requires_review']=True
            if row['basis']=='company_default_for_reviewed_room':row['basis']='company_default_for_inferred_room'
    result['policy_context']={k:v for k,v in policy.items() if k not in ('settings','provenance')}
    result['stale_or_missing_label_ids']=openings['stale_or_missing_label_ids']
    result['opening_review_sha256']=openings['review_sha256']
    return result
