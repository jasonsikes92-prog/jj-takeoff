"""Resolve hardware functions from frozen practices and reviewed door associations."""
import hashlib
import json
from pathlib import Path

from door_specifications import door_core_specifications, read_door_specifications

KEY = 'doors.interior_hardware_by_room'


def door_hardware_specifications(intake, schedule=None):
    # Share plan, identity, scope and room validation with the existing door schedule.
    cores = door_core_specifications(intake, schedule)
    defaults = intake['settings'].get(KEY, {})
    if not isinstance(defaults, dict) or any(
            not isinstance(v, str) or not v.strip() for v in defaults.values()):
        raise ValueError('Door hardware defaults must contain named hardware functions')
    result = {k: cores[k] for k in ('plan_sha256', 'company_profile_version',
        'company_profile_sha256', 'schedule_sha256')}
    result.update(default_rule={'key': KEY, 'value': defaults,
        'provenance': intake['provenance'].get(KEY)}, openings=[], unresolved_opening_ids=[],
        complete_hardware_schedule=False, purchase_quantities={}, current_prices={}, estimate_released=False)
    if schedule is None:
        result['status'] = 'Door types and room associations need extraction; saved hardware practices are retained'
        return result
    result['schedule_source'] = schedule['source']
    for opening in schedule['openings']:
        scope, room = opening['scope'], opening.get('room_class')
        kind = opening.get('door_type')
        if kind is not None and kind not in ('hinged', 'pocket', 'bypass', 'bifold', 'sliding', 'unknown'):
            raise ValueError('Classify the door type explicitly')
        sourced = all(isinstance(opening.get(k), str) and opening[k].strip()
            for k in ('room_source', 'door_type_source'))
        policy_key = None
        if scope == 'interior' and sourced:
            if kind == 'hinged':
                if room in ('bedroom', 'bathroom', 'toilet_room'):
                    policy_key = 'bedroom_bath_hardware'
                elif room in ('other_interior', 'closet'):
                    policy_key = 'other_interior_hardware'
            elif kind == 'pocket':
                policy_key = {'toilet_room': 'toilet_room_pocket_hardware',
                    'closet': 'closet_pocket_hardware'}.get(room)
        default = defaults.get(policy_key)
        override = opening.get('project_hardware')
        if override is not None and (not isinstance(override, str) or not override.strip()
                or not isinstance(opening.get('project_hardware_source'), str)
                or not opening['project_hardware_source'].strip()):
            raise ValueError('A project hardware selection needs its source')
        if scope == 'open_passage' and override is not None:
            raise ValueError('An open passage cannot have door hardware')
        hardware, basis, conflict = None, 'scope_room_or_door_type_unresolved', None
        if override is not None:
            hardware, basis = override, 'project_specification'
            if default is not None and default != override:
                conflict = {'resolved_default': default, 'project_value': override,
                    'resolution': 'Explicit project specification takes precedence'}
        elif scope == 'open_passage':
            basis = 'not_a_door'
        elif default is not None:
            hardware = default
            basis = ('project_room_policy' if intake['provenance'].get(KEY, {}).get('basis') == 'project_override'
                else 'company_default_for_reviewed_room_and_type')
        result['openings'].append({'opening_id': opening['opening_id'], 'scope': scope,
            'room_class': room, 'room_source': opening.get('room_source'), 'door_type': kind,
            'door_type_source': opening.get('door_type_source'), 'hardware_function': hardware,
            'policy_key': policy_key, 'basis': basis, 'resolved_conflict': conflict,
            'project_hardware_source': opening.get('project_hardware_source'),
            'complete_assembly_verified': False, 'purchase_released': False})
        if hardware is None and scope != 'open_passage':
            result['unresolved_opening_ids'].append(opening['opening_id'])
    result['status'] = ('Hardware functions resolved for supplied associations; full door enumeration, '
        'leaf counts, compatible products, stops, installation and pricing remain unverified')
    return result


def read_hardware_specifications(job):
    job = Path(job)
    inventory = json.loads((job/'plan_inventory.json').read_bytes())
    path = job/'door_hardware_specifications.json'
    if not path.exists() and 'door_hardware_specifications' not in inventory:
        return None  # Preserve older jobs without silently applying a newer policy.
    read_door_specifications(job)  # Validates the frozen plan, profile, overrides and schedule.
    intake_bytes = (job/'estimate_intake.json').read_bytes()
    schedule_path = job/'door_schedule.json'
    schedule = json.loads(schedule_path.read_bytes()) if schedule_path.exists() else None
    expected = door_hardware_specifications(json.loads(intake_bytes), schedule)
    expected['company_intake_sha256'] = hashlib.sha256(intake_bytes).hexdigest()
    if not path.exists() or json.loads(path.read_bytes()) != expected:
        raise ValueError('Door hardware inputs or specifications changed; regenerate the specification review')
    return expected


def apply_hardware_policy(openings, policy):
    """Recompute functions from the current editable opening review, not intake counts."""
    if policy is None:
        return None
    scopes = {'interior_door': 'interior', 'special_interior_door': 'special_interior',
        'exterior_door': 'exterior', 'open_passage': 'open_passage', None: 'unknown'}
    types = {'single_hinged': 'hinged', 'double_hinged': 'hinged',
        'pocket': 'pocket', 'bypass': 'bypass', 'bifold': 'bifold', 'sliding': 'sliding'}
    schedule = {'plan_sha256': openings['plan_sha256'],
        'source': 'Current source-bound editable opening review', 'openings': []}
    for row in openings['openings']:
        current = row['review_status'] in ('current_source_review','native_symbol_inference')
        role = row['role'] if current else None
        if role == 'window':
            continue
        kind = types.get(row.get('door_configuration')) if current else None
        scope = scopes[role]
        # Pocket hardware has an explicit saved policy; other special assemblies do not.
        if role == 'special_interior_door' and kind == 'pocket':
            scope = 'interior'
        schedule['openings'].append({'opening_id': row['opening_id'], 'scope': scope,
            'room_class': row.get('room_class') if current else None,
            'room_source': row.get('room_source', row.get('role_source')) if current else None,
            'door_type': kind, 'door_type_source': row.get('role_source') if current else None,
            'project_hardware': row.get('project_hardware') if current else None,
            'project_hardware_source': row.get('project_hardware_source') if current else None})
    result = door_hardware_specifications(policy, schedule)
    inferred={o['opening_id']:o['native_interpretation'] for o in openings['openings'] if o['review_status']=='native_symbol_inference'}
    assignments={o['opening_id']:o['room_association'] for o in openings['openings'] if o.get('room_assignment_requires_review')}
    for row in result['openings']:
        if row['opening_id'] in assignments:
            row['automatic_room_assignment']=assignments[row['opening_id']]
            row['interpretation_requires_review']=True
            if row['basis']=='company_default_for_reviewed_room_and_type':row['basis']='company_default_for_inferred_room_and_type'
        if row['opening_id'] in inferred:
            row['automatic_interpretation']=inferred[row['opening_id']]
            row['interpretation_requires_review']=True
            if row['basis']=='company_default_for_reviewed_room_and_type':row['basis']='company_default_for_inferred_room_and_type'
    result['policy_context'] = {k: v for k, v in policy.items() if k not in ('settings', 'provenance')}
    result['stale_or_missing_label_ids'] = openings['stale_or_missing_label_ids']
    result['opening_review_sha256'] = openings['review_sha256']
    return result
