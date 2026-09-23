"""Use source-reviewed adjacent rooms to resolve a door's estimating room class."""
import copy
import hashlib
import json
from room_use_review import binding
from door_swing_room import candidate as swing_room

CLASSES = {'bedroom': 'bedroom', 'bathroom': 'bathroom', 'toilet_room': 'toilet_room',
    'closet': 'closet', 'office': 'other_interior', 'laundry': 'other_interior',
    'pantry': 'other_interior', 'utility': 'other_interior', 'storage': 'other_interior',
    'hall': 'other_interior', 'hallway': 'other_interior', 'circulation': 'other_interior',
    'foyer': 'other_interior', 'open_living_kitchen_dining': 'other_interior',
    'living': 'other_interior', 'kitchen': 'other_interior', 'dining': 'other_interior'}
CIRCULATION = {'hall', 'hallway', 'circulation', 'foyer'}


def associate(schedule, rooms):
    if (schedule['plan_sha256'] != rooms['plan_sha256']
            or schedule['measurement_version'] != rooms['measurement_version']):
        raise ValueError('Door-room associations require the same plan and measurement revision')
    regions = {r['id']: r for r in rooms['regions']}
    links = {r['opening_id']: r for r in rooms['opening_connections']}
    if len(regions) != len(rooms['regions']) or len(links) != len(rooms['opening_connections']):
        raise ValueError('Door-room regions and opening connections must have unique identities')
    result = copy.deepcopy(schedule)
    symbols={s['opening_id']:s for s in schedule.get('door_symbol_candidates',{}).get('candidates',[])}
    decisions = []
    for opening in result['openings']:
        if opening['review_status'] not in ('current_source_review','native_symbol_inference') or opening['role'] not in ('interior_door', 'special_interior_door'):
            continue
        link = links.get(opening['opening_id'])
        adjacent = []
        if link and link['status'] == 'two_region_boundaries':
            for side in link['sides']:
                region = regions.get(side.get('region_id'))
                review = (region or {}).get('room_use_review', {}) if (region or {}).get('room_use_confirmed') else (region or {}).get('room_use_inference', {})
                if (side['status'] == 'region_boundary' and region
                        and region['page'] == opening['page'] == link['page']
                        and region['points_per_foot'] == link['points_per_foot']
                        and review.get('status') in ('current_source_review','native_label_inference','equipment_symbol_inference','shelf_symbol_inference')
                        and review.get('source_sha256') == binding(rooms['plan_sha256'], region)
                        and review.get('room_use') in CLASSES):
                    adjacent.append({'region_id': region['id'], 'room_use': review['room_use'],
                        'room_class': CLASSES[review['room_use']], 'review': copy.deepcopy(review)})
        original = opening.get('room_class');swing=None;closet=None
        selected, status = original, 'adjacent_room_review_incomplete'
        inferred = any(r['review']['status'] in ('native_label_inference','equipment_symbol_inference','shelf_symbol_inference') for r in adjacent)
        equipment = any(r['review']['status']=='equipment_symbol_inference' for r in adjacent)
        if len(adjacent) == 2 and len({r['region_id'] for r in adjacent}) == 2:
            if original is not None:
                matches = [r for r in adjacent if r['room_class'] == original
                    or original == 'other_interior' and r['room_class'] == 'closet']
                if matches:
                    selected = matches[0]['room_class'] if len({r['room_class'] for r in matches}) == 1 else original
                    status = 'reviewed_room_class_supported_by_adjacent_rooms'
                else:
                    selected, status = (original, 'native_labels_conflict_with_reviewed_door_room') if inferred else (
                        None, 'reviewed_room_class_conflicts_with_adjacent_rooms')
            else:
                candidates = [r for r in adjacent if r['room_use'] not in CIRCULATION]
                if not candidates: candidates = adjacent
                classes = {r['room_class'] for r in candidates}
                if len(classes) == 1:
                    selected, status = next(iter(classes)), 'resolved_from_adjacent_reviewed_rooms'
                else:
                    selected, status = None, 'served_room_ambiguous_between_adjacent_rooms'
                    swing=swing_room(opening,adjacent,regions,symbols.get(opening['opening_id'],{}))
                    if swing:
                        selected,status=swing['room_class'],'resolved_from_native_swing_and_room_evidence'
                        inferred=True
                    reach_ins=[r for r in adjacent if r['review']['status']=='shelf_symbol_inference'
                        and r['room_class']=='closet'
                        and r['review'].get('shelf_evidence',{}).get('connection')==link]
                    if not swing and len(reach_ins)==1:
                        closet=copy.deepcopy(reach_ins[0]['review']['shelf_evidence'])
                        selected,status='closet','resolved_from_reach_in_closet_evidence'
            opening['room_class'] = selected
            if status!='native_labels_conflict_with_reviewed_door_room':
                opening['room_source'] = ('Current measured opening faces and '
                    + ('native swing and room evidence requiring review; ' if swing else
                        'native shelf-and-rod closet evidence requiring review; ' if closet else
                        'equipment and room-label estimating candidates requiring review; ' if equipment else
                        'native-label estimating candidates requiring review; ' if inferred else 'source-bound room-use reviews; ')
                    + ', '.join(r['region_id'] for r in adjacent)) if selected is not None else None
            if inferred:
                opening['room_assignment_requires_review']=True
                status={'resolved_from_adjacent_reviewed_rooms':'resolved_from_native_room_labels',
                    'reviewed_room_class_supported_by_adjacent_rooms':'room_class_supported_by_native_labels'}.get(status,status)
                if equipment and status in ('resolved_from_native_room_labels','room_class_supported_by_native_labels'):
                    status='room_class_supported_by_equipment_and_room_evidence'
        decision = {'opening_id': opening['opening_id'], 'original_room_class': original,
            'resolved_room_class': selected, 'status': status, 'adjacent_rooms': adjacent,
            'connection': copy.deepcopy(link), 'room_sources_sha256': rooms['source_sha256'],
            'native_room_interpretation_used': inferred, 'requires_room_use_review': inferred}
        if swing:decision['swing_evidence']=swing
        if closet:decision['closet_evidence']=closet
        opening['room_association'] = decision
        decisions.append(decision)
    result['door_room_associations'] = {'decisions': decisions, 'room_sources_sha256': rooms['source_sha256'],
        'source_sha256': hashlib.sha256(json.dumps(decisions, sort_keys=True, allow_nan=False).encode()).hexdigest(),
        'coverage_certified': False, 'purchase_released': False}
    return result
