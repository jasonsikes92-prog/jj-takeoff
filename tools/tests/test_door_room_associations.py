import copy
import unittest
from door_room_associations import associate
from room_use_review import binding
from door_hardware_specifications import apply_hardware_policy, KEY
from door_policy_revision import apply_policy, KEY as CORE_KEY


class DoorRoomAssociations(unittest.TestCase):
    def setUp(self):
        self.schedule = {'plan_sha256': 'plan', 'measurement_version': 1, 'review_sha256': 'review',
            'stale_or_missing_label_ids': [], 'openings': [{'opening_id': 'door', 'page': 1,
            'role': 'interior_door', 'door_configuration': 'single_hinged',
            'role_source': 'Reviewed source symbol', 'room_class': None, 'review_status': 'current_source_review'}]}
        self.rooms = {'plan_sha256': 'plan', 'measurement_version': 1, 'source_sha256': 'rooms',
            'regions': [], 'opening_connections': [{'opening_id': 'door', 'page': 1, 'points_per_foot': 12,
            'status': 'two_region_boundaries', 'sides': [
                {'region_id': 'a', 'status': 'region_boundary'}, {'region_id': 'b', 'status': 'region_boundary'}]}]}
        for identity, use in [('a', 'bedroom'), ('b', 'hall')]:
            region = {'id': identity, 'page': 1, 'points_per_foot': 12, 'points': [[0,0],[10,0],[10,10],[0,10]],
                'holes': [], 'printed_labels': [], 'room_use_confirmed': True}
            region['room_use_review'] = {'room_use': use, 'status': 'current_source_review',
                'source_sha256': binding('plan', region), 'basis': 'Synthetic source review'}
            self.rooms['regions'].append(region)
        self.policy = {'plan_sha256': 'plan', 'company_profile_version': 1, 'company_profile_sha256': 'profile',
            'settings': {KEY: {'bedroom_bath_hardware': 'privacy', 'other_interior_hardware': 'passage',
                'closet_pocket_hardware': 'passage pull'}, CORE_KEY: {'bedroom': 'solid', 'other_interior': 'hollow'}},
            'provenance': {}}

    def result(self): return associate(self.schedule, self.rooms)

    def test_bedroom_against_reviewed_hall_resolves_without_per_door_room_entry(self):
        before = copy.deepcopy(self.schedule)
        result = self.result()
        self.assertEqual(result['openings'][0]['room_class'], 'bedroom')
        self.assertEqual(apply_hardware_policy(result, self.policy)['openings'][0]['hardware_function'], 'privacy')
        self.assertEqual(apply_policy(result, self.policy)['openings'][0]['core'], 'solid')
        self.assertEqual(self.schedule, before)

    def test_ambiguous_rooms_are_not_ranked_by_privacy_or_name(self):
        self.rooms['regions'][1]['room_use_review']['room_use'] = 'closet'
        result = self.result()
        self.assertIsNone(result['openings'][0]['room_class'])
        self.assertIn('ambiguous', result['door_room_associations']['decisions'][0]['status'])
        self.assertIsNone(apply_hardware_policy(result, self.policy)['openings'][0]['hardware_function'])

    def test_existing_broad_class_refines_closet_and_hollow_core_without_a_new_answer(self):
        self.rooms['regions'][1]['room_use_review']['room_use'] = 'closet'
        self.schedule['openings'][0].update(room_class='other_interior', role='special_interior_door', door_configuration='pocket')
        result = self.result()
        self.assertEqual(result['openings'][0]['room_class'], 'closet')
        self.assertEqual(apply_hardware_policy(result, self.policy)['openings'][0]['hardware_function'], 'passage pull')
        result['openings'][0].update(role='interior_door', door_configuration='single_hinged')
        self.assertEqual(apply_policy(result, self.policy)['openings'][0]['core'], 'hollow')

    def test_conflicting_review_withholds_default_but_sourced_project_spec_still_wins(self):
        self.schedule['openings'][0].update(room_class='toilet_room', project_hardware='keyed', project_hardware_source='Owner selection')
        result = self.result()
        self.assertIsNone(result['openings'][0]['room_class'])
        self.assertIn('conflicts', result['door_room_associations']['decisions'][0]['status'])
        self.assertEqual(apply_hardware_policy(result, self.policy)['openings'][0]['hardware_function'], 'keyed')

    def test_changed_geometry_missing_use_or_wrong_page_do_not_infer_rooms(self):
        for field, value in [('room_use_confirmed', False), ('page', 2), ('points_per_foot', 6),
                ('points', [[1,0],[10,0],[10,10],[0,10]])]:
            rooms = copy.deepcopy(self.rooms)
            rooms['regions'][0][field] = value
            result = associate(self.schedule, rooms)
            self.assertIsNone(result['openings'][0]['room_class'])
        self.schedule['openings'][0]['room_class'] = 'bedroom'
        self.rooms['regions'][0]['room_use_confirmed'] = False
        self.assertEqual(self.result()['openings'][0]['room_class'], 'bedroom')

    def test_unreviewed_external_and_open_passage_records_are_not_classified(self):
        for field, value in [('review_status', 'stale_source_review'), ('role', 'exterior_door'), ('role', 'open_passage')]:
            schedule = copy.deepcopy(self.schedule)
            schedule['openings'][0][field] = value
            self.assertEqual(associate(schedule, self.rooms)['door_room_associations']['decisions'], [])

    def test_wrong_revision_and_duplicate_connections_are_rejected(self):
        for field, value in [('plan_sha256', 'other'), ('measurement_version', 2)]:
            with self.assertRaises(ValueError): associate(self.schedule, {**self.rooms, field: value})
        self.rooms['opening_connections'] *= 2
        with self.assertRaises(ValueError): self.result()


if __name__ == '__main__': unittest.main()
