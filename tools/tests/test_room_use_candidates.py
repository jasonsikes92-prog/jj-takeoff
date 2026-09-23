import copy
import unittest
from room_use_candidates import apply, label_use
from room_use_review import apply as review_uses, binding
from door_room_associations import associate
from door_hardware_specifications import apply_hardware_policy
import test_door_room_associations as fixtures


class NativeRoomUses(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.DoorRoomAssociations()
        fixture.setUp()
        self.schedule, self.rooms, self.policy = fixture.schedule, fixture.rooms, fixture.policy
        for region, text in zip(self.rooms['regions'], ['BEDROOM 2', 'HALL']):
            region.pop('room_use_review')
            region['room_use_confirmed'] = False
            region['printed_labels'] = [{'id': region['id']+'label', 'text': text}]

    def test_exact_label_grammar_and_unknowns(self):
        cases = {'Master Bedroom': 'bedroom', 'Primary Bath': 'bathroom', 'Guest Closet': 'closet',
            'BEDROOM #2': 'bedroom', 'WIC': 'closet', 'WC': 'toilet_room', 'Powder Room': 'bathroom',
            'Laundry Room': 'laundry', 'BATH FRAMING': None, 'BEDROOM DEMO': None,
            'NOT A BEDROOM': None, '3068': None, 'WH': None, 'BONUS': None, '': None}
        for text, expected in cases.items():
            with self.subTest(text=text): self.assertEqual(label_use(text), expected)

    def test_recognition_preserves_geometry_and_never_claims_source_review(self):
        before = copy.deepcopy(self.rooms)
        result = apply(self.rooms)
        self.assertEqual([r['room_use_inference']['room_use'] for r in result['regions']], ['bedroom', 'hall'])
        self.assertEqual(result['room_use_candidates']['automatic_candidate_count'], 2)
        self.assertFalse(result['room_use_candidates']['complete_room_interpretation'])
        self.assertTrue(all(not r['room_use_confirmed'] for r in result['regions']))
        self.assertEqual(self.rooms, before)
        self.assertEqual([r['points'] for r in result['regions']], [r['points'] for r in before['regions']])

    def test_open_living_labels_share_one_candidate_and_conflicting_labels_do_not(self):
        labels = self.rooms['regions'][0]['printed_labels']
        labels[:] = [{'id': str(i), 'text': text} for i, text in enumerate(['KITCHEN', 'LIVING', 'DINING'])]
        self.assertEqual(apply(self.rooms)['regions'][0]['room_use_inference']['room_use'], 'open_living_kitchen_dining')
        labels.append({'id': 'bed', 'text': 'BEDROOM'})
        candidate = apply(self.rooms)['regions'][0]['room_use_inference']
        self.assertIsNone(candidate['room_use'])
        self.assertEqual(candidate['status'], 'conflicting_labels_in_one_region')
        labels.clear()
        self.assertIsNone(apply(self.rooms)['regions'][0]['room_use_inference']['room_use'])

    def test_review_takes_precedence_and_stale_review_does_not_fall_back_to_labels(self):
        region = self.rooms['regions'][0]
        review = {'plan_sha256': 'plan', 'reviewer': 'Fixture', 'decisions': [{'region_id': region['id'],
            'source_sha256': binding('plan', region), 'room_use': 'office', 'name': 'Revised office',
            'basis': 'Reviewed project redline'}]}
        result = apply(review_uses(self.rooms, review))
        self.assertEqual(result['regions'][0]['room_use_review']['room_use'], 'office')
        self.assertIsNone(result['regions'][0]['room_use_inference']['room_use'])
        region['points'][0][0] += 1
        candidate = apply(review_uses(self.rooms, review))['regions'][0]['room_use_inference']
        self.assertIsNone(candidate['room_use'])
        self.assertEqual(candidate['status'], 'previous_room_review_is_stale')

    def test_native_room_candidates_drive_draft_hardware_with_explicit_review_flag(self):
        result = associate(self.schedule, apply(self.rooms))
        row = result['openings'][0]
        self.assertEqual(row['room_class'], 'bedroom')
        self.assertTrue(row['room_assignment_requires_review'])
        self.assertEqual(row['room_association']['status'], 'resolved_from_native_room_labels')
        hardware = apply_hardware_policy(result, self.policy)
        self.assertEqual(hardware['openings'][0]['hardware_function'], 'privacy')
        self.assertIn('requiring review', hardware['openings'][0]['room_source'])
        self.assertFalse(hardware['complete_hardware_schedule'])

    def test_native_label_conflict_cannot_override_reviewed_door_room_selection(self):
        self.schedule['openings'][0]['room_class'] = 'toilet_room'
        result = associate(self.schedule, apply(self.rooms))['openings'][0]
        self.assertEqual(result['room_class'], 'toilet_room')
        self.assertEqual(result['room_association']['status'], 'native_labels_conflict_with_reviewed_door_room')
        self.assertTrue(result['room_assignment_requires_review'])


if __name__ == '__main__': unittest.main()
