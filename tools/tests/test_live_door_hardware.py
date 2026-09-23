import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from company_profile import DEFAULT_PROFILE
from door_hardware_specifications import KEY, apply_hardware_policy
from door_policy_revision import read_policy
from opening_schedule import schedule, from_folder
from opening_bid_scope import build_scope, render_markdown
from wall_run_candidates import from_state
from wall_gap_labels import match_labels
import test_opening_schedule as opening_fixtures
import test_door_policy_revision as policy_fixtures
from opening_references import references


class LiveHardwareTests(unittest.TestCase):
    def setUp(self):
        self.fixture = opening_fixtures.OpeningSchedule()
        self.fixture.setUp()
        self.state, self.runs, self.gaps = self.fixture.state, self.fixture.runs, self.fixture.gaps
        self.review = copy.deepcopy(self.fixture.review)
        row = self.review['openings'][0]
        row.pop('window_component_count')
        row.update(role='interior_door', room_class='bedroom', door_configuration='single_hinged')
        profile = json.loads(DEFAULT_PROFILE.read_bytes())
        rule = next(r for r in profile['rules'] if r['key'] == KEY)
        self.policy = {'settings': {KEY: rule['value']}, 'provenance': {KEY: {'basis': 'company_default'}},
            'plan_sha256': self.state['plan_sha256'], 'company_profile_version': profile['version'],
            'company_profile_sha256': hashlib.sha256(DEFAULT_PROFILE.read_bytes()).hexdigest()}

    def current(self):
        return schedule(self.state, self.runs, self.gaps, self.review)

    def test_edit_reopens_hardware_and_restore_recovers_it(self):
        initial = apply_hardware_policy(self.current(), self.policy)
        self.assertEqual(initial['openings'][0]['hardware_function'], 'privacy')
        changed = copy.deepcopy(self.state)
        changed['measurements']['b']['points'][0][0] += 1
        runs = from_state(changed)
        result = schedule(changed, runs, match_labels(runs, [self.fixture.label]), self.review)
        reopened = apply_hardware_policy(result, self.policy)
        self.assertIsNone(reopened['openings'][0]['hardware_function'])
        self.assertEqual(reopened['unresolved_opening_ids'], ['opening-test'])
        self.assertEqual(apply_hardware_policy(self.current(), self.policy), initial)

    def test_room_type_and_override_changes_update_bid_function(self):
        row = self.review['openings'][0]
        for room, role, kind, function in (
                ('bedroom', 'interior_door', 'single_hinged', 'privacy'),
                ('other_interior', 'interior_door', 'single_hinged', 'passage'),
                ('toilet_room', 'special_interior_door', 'pocket', 'privacy latch'),
                ('closet', 'special_interior_door', 'pocket', 'passage pull'),
                ('closet', 'special_interior_door', 'bypass', None),
                ('bedroom', 'exterior_door', 'single_hinged', None)):
            row.update(room_class=room, role=role, door_configuration=kind)
            current = self.current()
            current['door_hardware_review'] = apply_hardware_policy(current, self.policy)
            scope = build_scope(current)
            self.assertEqual(scope['hardware_references'][0]['hardware_function'], function)
            self.assertIsNone(scope['hardware_references'][0]['purchase_quantity'])
            self.assertFalse(scope['ready_to_order'])
            if function: self.assertIn(function, render_markdown(scope))
        row.update(role='interior_door', room_class='bedroom', project_hardware='passage', project_hardware_source='Owner override')
        result = apply_hardware_policy(self.current(), self.policy)['openings'][0]
        self.assertEqual(result['hardware_function'], 'passage')
        self.assertEqual(result['resolved_conflict']['resolved_default'], 'privacy')

    def test_invalid_override_rejected_and_stale_override_withheld(self):
        row = self.review['openings'][0]
        row.update(project_hardware='passage', project_hardware_source='Owner selection')
        row['source_sha256'] = 'stale'
        self.assertNotIn('project_hardware', self.current()['openings'][0])
        row['project_hardware_source'] = ''
        with self.assertRaises(ValueError): self.current()

    def test_folder_reader_and_homeowner_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'opening_schedule_review.json').write_text(json.dumps(self.review))
            with patch('opening_schedule.from_state', return_value=self.runs), \
                    patch('opening_schedule.from_plan_state', return_value=self.gaps), \
                    patch('opening_schedule.read_policy', side_effect=lambda *a, **k: self.policy if k.get('hardware') else None):
                result = from_folder(folder, self.state)
            self.assertEqual(result['door_hardware_review']['openings'][0]['hardware_function'], 'privacy')
            public = references(result)
            self.assertNotIn('door_hardware_review', json.dumps(public))
            result['door_hardware_review']['default_rule']['value'] = {'private': 'changed'}
            self.assertEqual(references(result), public)

    def test_hardware_revision_is_narrow_and_independent_of_core_revision(self):
        fixture = policy_fixtures.DoorPolicyRevision()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.latest['rules'].append({'key': KEY, 'value': self.policy['settings'][KEY], 'source': 'Saved owner practice'})
        fixture.profile.write_text(json.dumps(fixture.latest))
        fixture.revision['profile_sha256'] = fixture.sha(fixture.profile)
        fixture.enable()
        self.assertIsNone(read_policy(fixture.folder, 'plan', hardware=True))
        path = fixture.folder/'door_hardware_policy_revision.json'
        path.write_text(json.dumps(fixture.revision))
        result = read_policy(fixture.folder, 'plan', hardware=True)
        self.assertEqual(result['policy_keys'], [KEY])
        self.assertNotIn('unrelated', result['settings'])
        fixture.overrides = {KEY: {'bedroom_bath_hardware': 'passage'}}
        fixture.write_base()
        fixture.revision['base_intake_sha256'] = fixture.sha(fixture.job/'estimate_intake.json')
        path.write_text(json.dumps(fixture.revision))
        self.assertEqual(read_policy(fixture.folder, 'plan', hardware=True)['settings'][KEY]['bedroom_bath_hardware'], 'passage')
        fixture.profile.write_bytes(fixture.profile.read_bytes()+b' ')
        with self.assertRaises(ValueError): read_policy(fixture.folder, 'plan', hardware=True)


if __name__ == '__main__':
    unittest.main()
