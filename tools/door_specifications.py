"""Apply saved door-core practices to source-bound room/door associations."""
import hashlib
import json
from pathlib import Path

from company_profile import resolve


def door_core_specifications(intake, schedule=None):
    key = 'doors.interior_core_by_room'
    defaults = intake['settings'].get(key, {})
    if not isinstance(defaults, dict) or any(v not in ('solid', 'hollow') for v in defaults.values()):
        raise ValueError('Door core defaults must identify solid or hollow cores')
    result = {'plan_sha256':intake['plan_sha256'], 'company_profile_version':intake['company_profile_version'],
        'company_profile_sha256':intake['company_profile_sha256'],
        'default_rule':{'key':key, 'value':defaults, 'provenance':intake['provenance'].get(key)},
        'openings':[], 'unresolved_opening_ids':[], 'schedule_sha256':None,
        'complete_door_schedule':False, 'purchase_quantities':{}, 'current_prices':{}, 'estimate_released':False}
    if schedule is None:
        result['status'] = 'Door and room associations need extraction; the company default is saved'
        return result
    if schedule['plan_sha256'] != intake['plan_sha256']:
        raise ValueError('Door schedule belongs to another plan')
    if not isinstance(schedule.get('source'), str) or not schedule['source'].strip():
        raise ValueError('Identify the reviewed door/room schedule source')
    openings = schedule['openings']
    if not isinstance(openings, list):
        raise ValueError('Door schedule must contain an opening list')
    seen = set()
    for opening in openings:
        identity, scope = opening['opening_id'], opening['scope']
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError('Door opening identities must be unique and nonempty')
        seen.add(identity)
        if scope not in ('interior', 'special_interior', 'garage_entry', 'exterior', 'open_passage', 'unknown'):
            raise ValueError('Classify the opening scope explicitly')
        room = opening.get('room_class')
        if room is not None and not isinstance(room, str):
            raise ValueError('Room class must be a string or unknown')
        room_source = opening.get('room_source')
        override = opening.get('project_core')
        if override is not None and (override not in ('solid', 'hollow')
                or not isinstance(opening.get('project_core_source'), str) or not opening['project_core_source'].strip()):
            raise ValueError('A project door-core selection needs its source')
        if scope == 'open_passage' and override is not None:
            raise ValueError('An open passage cannot have a door-core selection')
        core, basis, conflict = None, 'scope_or_room_unresolved', None
        if override is not None:
            core, basis = override, 'project_specification'
            if scope == 'interior' and room in defaults and defaults[room] != core:
                conflict = {'company_default':defaults[room], 'project_value':core,
                            'resolution':'Explicit project specification takes precedence'}
        elif scope == 'open_passage':
            basis = 'not_a_door'
        elif scope != 'interior':
            basis = 'separate_assembly_specification_required'
        elif room in defaults and isinstance(room_source, str) and room_source.strip():
            core=defaults[room]
            basis=('project_room_policy' if intake['provenance'].get(key,{}).get('basis')=='project_override'
                else 'company_default_for_reviewed_room')
        record = {'opening_id':identity, 'scope':scope, 'room_class':room, 'room_source':room_source,
            'core':core, 'basis':basis, 'project_core_source':opening.get('project_core_source'),
            'resolved_conflict':conflict,
            'assembly_specification_review_required':scope in ('special_interior','garage_entry','exterior','unknown'),
            'dimensions_hardware_and_leaf_count_verified':False, 'purchase_released':False}
        result['openings'].append(record)
        if (core is None and scope != 'open_passage') or record['assembly_specification_review_required']:
            result['unresolved_opening_ids'].append(identity)
    result['schedule_sha256'] = hashlib.sha256(json.dumps(schedule, sort_keys=True, allow_nan=False).encode()).hexdigest()
    result['schedule_source'] = schedule['source']
    result['status'] = 'Core defaults resolved for supplied associations; full plan enumeration and complete door assemblies remain unverified'
    return result


def read_door_specifications(job):
    """Reproduce the saved result from this job's frozen profile and source inputs."""
    job = Path(job)
    intake_bytes = (job/'estimate_intake.json').read_bytes()
    intake = json.loads(intake_bytes)
    profile_bytes = (job/'company_profile_snapshot.json').read_bytes()
    if (hashlib.sha256(profile_bytes).hexdigest() != intake['company_profile_sha256']
            or hashlib.sha256((job/'plan.pdf').read_bytes()).hexdigest() != intake['plan_sha256']):
        raise ValueError('Door specifications belong to changed plan or company-profile sources')
    replay = resolve(json.loads(profile_bytes), intake['project_facts'], intake['project_overrides'])
    if any(replay[key] != intake[key] for key in ('settings','provenance','resolved_conflicts')):
        raise ValueError('Saved company settings differ from the source-backed inputs')
    path = job/'door_schedule.json'
    schedule = json.loads(path.read_bytes()) if path.exists() else None
    expected = door_core_specifications(intake, schedule)
    expected['company_intake_sha256'] = hashlib.sha256(intake_bytes).hexdigest()
    actual = json.loads((job/'door_core_specifications.json').read_bytes())
    if actual != expected:
        raise ValueError('Door source inputs or specifications changed; regenerate the specification review')
    return actual
