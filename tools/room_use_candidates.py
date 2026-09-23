"""Interpret exact native room labels as explicit, uncertified estimating candidates."""
import copy
import hashlib
import json
import re
from room_use_review import binding

NAMES = {'BEDROOM': 'bedroom', 'BED': 'bedroom', 'BATHROOM': 'bathroom', 'BATH': 'bathroom',
    'POWDER': 'bathroom', 'POWDER ROOM': 'bathroom', 'WC': 'toilet_room',
    'CLOSET': 'closet', 'WIC': 'closet', 'OFFICE': 'office', 'STUDY': 'office',
    'LAUNDRY': 'laundry', 'LAUNDRY ROOM': 'laundry', 'PANTRY': 'pantry',
    'UTILITY': 'utility', 'UTILITY ROOM': 'utility', 'STORAGE': 'storage',
    'HALL': 'hall', 'HALLWAY': 'hall', 'FOYER': 'foyer', 'GARAGE': 'garage',
    'LIVING': 'living', 'LIVING ROOM': 'living', 'FAMILY': 'living', 'FAMILY ROOM': 'living',
    'KITCHEN': 'kitchen', 'DINING': 'dining', 'DINING ROOM': 'dining'}


def label_use(text):
    if not isinstance(text, str): return None
    name = ' '.join(text.upper().split())
    name = re.sub(r'\s*#?\s*\d+$', '', name).strip()
    name = re.sub(r'^(?:MASTER|PRIMARY|GUEST) (?=(?:BEDROOM|BED|BATHROOM|BATH|CLOSET)$)', '', name)
    return NAMES.get(name)


def apply(result):
    output = copy.deepcopy(result)
    stale = {d['region_id'] for d in result.get('room_use_review', {}).get('unresolved_decisions', [])}
    candidates = []
    for region in output['regions']:
        labels = region['printed_labels']
        uses = [label_use(label['text']) for label in labels]
        selected = None
        status = 'unlabeled_or_unsupported_room'
        if region.get('room_use_confirmed'):
            status = 'source_review_takes_precedence'
        elif region['id'] in stale:
            status = 'previous_room_review_is_stale'
        elif region.get('boundary_source_issues'):
            status = 'region_boundary_source_requires_review'
        elif uses and all(uses):
            if len(set(uses)) == 1:
                selected, status = uses[0], 'native_label_inference'
            elif set(uses).issubset({'living', 'kitchen', 'dining'}):
                selected, status = 'open_living_kitchen_dining', 'native_label_inference'
            else:
                status = 'conflicting_labels_in_one_region'
        candidate = {'region_id': region['id'], 'room_use': selected, 'status': status,
            'source_sha256': binding(output['plan_sha256'], region), 'labels': copy.deepcopy(labels),
            'basis': 'Exact supported native room labels wholly contained in this current region; estimating interpretation only',
            'requires_review': not region.get('room_use_confirmed',False), 'certified': False, 'owner_approved': False}
        region['room_use_inference'] = candidate
        candidates.append(candidate)
    output['room_use_candidates'] = {'method': 'exact_native_room_labels_v1', 'candidates': candidates,
        'automatic_candidate_count': sum(c['room_use'] is not None for c in candidates),
        'complete_room_interpretation': False}
    output['source_sha256'] = hashlib.sha256(json.dumps([result['source_sha256'], candidates],
        sort_keys=True, allow_nan=False).encode()).hexdigest()
    return output
