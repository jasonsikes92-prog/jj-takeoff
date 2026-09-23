"""Feed distinct hardware-set references into the template without duplicate prices."""
import copy
import hashlib
import json


def apply_hardware_quantities(draft, schedule, target):
    if 'hardware_quantity_review' in draft:
        raise ValueError('Hardware quantities already imported')
    if (draft['plan_sha256'] != schedule['plan_sha256']
            or draft['measurement_version'] != schedule['measurement_version']):
        raise ValueError('Hardware quantities belong to different plan measurements')
    result = copy.deepcopy(draft)
    matches = [r for r in result['rows'] if r['row_id'] == target['row_id']]
    if len(matches) != 1:
        raise ValueError('Hardware target must identify one template row')
    row = matches[0]
    if (any(row.get(k) != target[k] for k in ('name', 'parent'))
            or row.get('cost_type') != 'ALLOWANCE' or row.get('unit') not in ('EA', 'each')
            or row.get('completion_status', '').startswith('not_applicable')
            or row.get('covered_by_package') or row.get('cost_owner_row_id')
            or row.get('quantity_sources') or row.get('assembly_inputs') or row.get('assembly_input_cost_owners')
            or any(row.get(k) is not None for k in ('draft_quantity', 'unit_cost', 'line_cost', 'line_price'))):
        raise ValueError('Hardware target is incompatible, excluded, assigned or priced')
    openings = schedule['openings']
    if len({o['opening_id'] for o in openings}) != len(openings):
        raise ValueError('Hardware opening identities must be unique')
    policy = schedule.get('door_hardware_review')
    functions = {o['opening_id']: o for o in (policy or {}).get('openings', [])}
    current = (bool(openings) and not schedule['unresolved_opening_ids']
        and not schedule['stale_or_missing_label_ids']
        and all(o['review_status'] in ('current_source_review','native_symbol_inference') for o in openings))
    ordinary = [o for o in openings if o['role'] == 'interior_door']
    pockets = [o for o in openings if o['role'] == 'special_interior_door' and o.get('door_configuration') == 'pocket']
    summaries = []
    row['pricing_role'] = 'input_only'
    for identity, function, group, configuration, valid_functions in (
            ('privacy', 'privacy', ordinary, 'single_hinged', ('privacy', 'passage')),
            ('passage', 'passage', ordinary, 'single_hinged', ('privacy', 'passage')),
            ('pocket-privacy', 'privacy latch', pockets, 'pocket', ('privacy latch', 'passage pull')),
            ('pocket-passage', 'passage pull', pockets, 'pocket', ('privacy latch', 'passage pull'))):
        ready = (current and bool(group) and policy is not None
            and all(o.get('door_configuration') == configuration and o.get('drawn_panel_count') == 1
                and functions.get(o['opening_id'], {}).get('hardware_function') in valid_functions for o in group))
        selected = [o for o in group if functions.get(o['opening_id'], {}).get('hardware_function') == function]
        inferred=[o for o in group if o['review_status']=='native_symbol_inference' or o.get('room_assignment_requires_review')]
        quantity = len(selected) if ready else None
        source = {'id': 'opening-hardware-'+identity, 'label': function.title()+' hardware set reference',
            'kind': 'inferred_hardware_set_reference' if inferred else 'reviewed_hardware_set_reference', 'quantity': quantity, 'unit': 'EA', 'use': 'assembly_input',
            'template_rows': [row['excel_row']], 'opening_ids': [o['opening_id'] for o in selected],
            'opening_sources': {o['opening_id']: o['source_sha256'] for o in selected},
            'hardware_function': function, 'policy_source': copy.deepcopy(policy),
            'basis': 'One complete set per inferred single-leaf opening; interpretation requires review.' if inferred else 'One complete hardware set per reviewed single-leaf opening; not one knob per face.',
            'remaining': ['Confirm complete plan coverage, compatible product and purchasing unit.',
                'Resolve supplier-package inclusion before assigning a separate purchase owner or price.',
                'Stops, bypass/bifold/exterior hardware and installation ownership remain separate.'],
            'certified': False, 'coverage_certified': False, 'purchase_released': False}
        if inferred:
            source['automatic_interpretations']={o['opening_id']:copy.deepcopy(o['native_interpretation']) for o in inferred if o.get('native_interpretation')}
            source['automatic_room_assignments']={o['opening_id']:copy.deepcopy(o['room_association']) for o in inferred if o.get('room_assignment_requires_review')}
            source['interpretation_requires_review']=True
        if ready:
            row.setdefault('assembly_inputs', []).append(source)
        else:
            result.setdefault('pending_quantities', []).append({**source,
                'reason': 'Hardware group needs current room/type/function and one-leaf source review; absence is not a zero count'})
        summaries.append({'id': source['id'], 'hardware_function': function, 'quantity': quantity,
            'opening_ids': source['opening_ids'], 'purchase_quantity': None})
    result['hardware_quantity_review'] = {'target_row_id': row['row_id'], 'groups': summaries,
        'opening_review_sha256': schedule['review_sha256'],
        'schedule_sha256': hashlib.sha256(json.dumps(schedule, sort_keys=True, allow_nan=False).encode()).hexdigest(),
        'coverage_certified': False, 'purchase_released': False}
    result.update(whole_house_total=None, estimate_released=False)
    return result
