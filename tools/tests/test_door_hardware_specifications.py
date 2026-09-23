import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from company_profile import resolve
from door_hardware_specifications import KEY, door_hardware_specifications, read_hardware_specifications
from new_plan_measure import measure_job
import test_door_specifications as door_fixtures


class HardwareSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = door_fixtures.DoorSpecificationTests()
        self.fixture.setUp()
        self.intake = self.fixture.intake

    def opening(self, identity, room, scope='interior', **other):
        return self.fixture.opening(identity, room, scope, **{
            'door_type': 'hinged', 'door_type_source': 'Synthetic reviewed door symbol', **other})

    def result(self, openings, intake=None):
        return door_hardware_specifications(intake or self.intake, self.fixture.schedule(openings))

    def test_room_and_pocket_rules_are_distinct_and_do_not_mutate_inputs(self):
        openings = [self.opening(str(i), room) for i, room in enumerate(
            ('bedroom', 'bathroom', 'toilet_room', 'other_interior', 'closet'))]
        openings += [self.opening('toilet-pocket', 'toilet_room', door_type='pocket'),
            self.opening('closet-pocket', 'closet', door_type='pocket')]
        before = copy.deepcopy(openings)
        result = self.result(openings)
        self.assertEqual([r['hardware_function'] for r in result['openings']],
            ['privacy', 'privacy', 'privacy', 'passage', 'passage', 'privacy latch', 'passage pull'])
        self.assertEqual(openings, before)
        self.assertEqual(result['unresolved_opening_ids'], [])
        self.assertFalse(result['complete_hardware_schedule'])
        self.assertEqual(result['purchase_quantities'], {})
        self.assertEqual(result['current_prices'], {})
        self.assertFalse(result['estimate_released'])

    def test_unknown_unsourced_and_special_openings_do_not_get_guessed_hardware(self):
        openings = [self.opening('missing-room', None), self.opening('missing-type', 'bedroom', door_type=None),
            self.opening('unsourced-room', 'bedroom', room_source=''),
            self.opening('unsourced-type', 'bedroom', door_type_source=''),
            self.opening('ambiguous-pocket', 'other_interior', door_type='pocket'),
            self.opening('bypass', 'closet', door_type='bypass')]
        openings += [self.opening(scope, 'bedroom', scope) for scope in
            ('garage_entry', 'exterior', 'special_interior', 'unknown', 'open_passage')]
        result = self.result(openings)
        self.assertTrue(all(r['hardware_function'] is None for r in result['openings']))
        self.assertEqual(result['unresolved_opening_ids'], [r['opening_id'] for r in openings[:-1]])

    def test_sourced_project_selection_wins_and_reports_conflict(self):
        opening = self.opening('bed', 'bedroom', project_hardware='passage', project_hardware_source='Owner selection')
        result = self.result([opening])['openings'][0]
        self.assertEqual(result['hardware_function'], 'passage')
        self.assertEqual(result['resolved_conflict']['resolved_default'], 'privacy')
        opening['project_hardware_source'] = ''
        with self.assertRaises(ValueError): self.result([opening])

    def test_project_room_policy_and_old_profiles(self):
        intake = copy.deepcopy(self.intake)
        intake.update(resolve(self.fixture.profile, project_overrides={KEY: {'bedroom_bath_hardware': 'passage'}}))
        row = self.result([self.opening('bed', 'bedroom')], intake)['openings'][0]
        self.assertEqual(row['hardware_function'], 'passage')
        self.assertEqual(row['basis'], 'project_room_policy')
        del intake['settings'][KEY]
        self.assertIsNone(self.result([self.opening('bed', 'bedroom')], intake)['openings'][0]['hardware_function'])
        self.assertIsNone(door_hardware_specifications(intake)['schedule_sha256'])

    def test_invalid_schedule_inputs_are_rejected(self):
        opening = self.opening('bed', 'bedroom')
        for rows in ([opening, opening], [self.opening('bad', 'bedroom', door_type='guess')],
                [self.opening('passage', None, 'open_passage', project_hardware='privacy', project_hardware_source='invalid')]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): self.result(rows)
        with self.assertRaises(ValueError):
            door_hardware_specifications(self.intake, self.fixture.schedule([opening], 'another-plan'))

    def test_intake_freezes_profile_and_detects_changed_or_deleted_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            job, profile, _ = self.fixture.make_job(Path(folder))
            initial = read_hardware_specifications(job)
            profile.write_text('{}')
            self.assertEqual(read_hardware_specifications(job), initial)
            for name in ('door_schedule.json', 'estimate_intake.json', 'company_profile_snapshot.json',
                    'door_hardware_specifications.json', 'plan.pdf'):
                path = job/name
                original = path.read_bytes()
                try:
                    if name == 'plan.pdf': path.write_bytes(original + b'changed')
                    elif name == 'door_hardware_specifications.json': path.unlink()
                    else:
                        value = json.loads(original)
                        if name == 'door_schedule.json': value['openings'][0]['door_type'] = 'pocket'
                        elif name == 'estimate_intake.json': value['settings'][KEY]['bedroom_bath_hardware'] = 'passage'
                        else: value['version'] += 1
                        path.write_text(json.dumps(value))
                    with self.subTest(name=name), self.assertRaises(ValueError): read_hardware_specifications(job)
                finally:
                    path.write_bytes(original)
            self.assertEqual(read_hardware_specifications(job), initial)

    def test_legacy_job_is_preserved_without_injecting_hardware_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            job, _, _ = self.fixture.make_job(Path(folder))
            (job/'door_hardware_specifications.json').unlink()
            path = job/'plan_inventory.json'
            inventory = json.loads(path.read_bytes())
            del inventory['door_hardware_specifications']
            path.write_text(json.dumps(inventory))
            before = {p.name: p.read_bytes() for p in job.iterdir() if p.is_file()}
            self.assertIsNone(read_hardware_specifications(job))
            self.assertEqual(before, {p.name: p.read_bytes() for p in job.iterdir() if p.is_file()})

    def test_measurement_summary_carries_hardware_and_rejects_tampering_before_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            # Add reviewed types before intake, so no derived artifact is manually patched.
            original = self.fixture.opening
            self.fixture.opening = lambda *args, **kwargs: original(*args, **kwargs,
                door_type='hinged', door_type_source='Synthetic plan symbol')
            job, _, _ = self.fixture.make_job(Path(folder))
            review = {'coverage_passed': True, 'review_sha256': 'fixture', 'unique_role_pages': {'floor': 1},
                'roles_requiring_disambiguation': {}}
            result = {'status': 'more_information_required', 'pages': {}, 'lines': []}
            with patch('new_plan_measure.read_sheet_review', return_value=review), patch('jnj_takeoff.run_takeoff', return_value=result):
                summary = measure_job(job)
            self.assertEqual(summary['door_hardware_assigned_openings'], 2)
            self.assertEqual(summary['door_hardware_unresolved_opening_ids'], ['garage'])
            self.assertFalse(summary['door_hardware_schedule_complete'])
            self.assertEqual(summary['door_hardware_specifications_sha256'],
                hashlib.sha256((job/'door_hardware_specifications.json').read_bytes()).hexdigest())
            path = job/'door_hardware_specifications.json'
            value = json.loads(path.read_bytes())
            value['openings'][0]['hardware_function'] = 'passage'
            path.write_text(json.dumps(value))
            with patch('jnj_takeoff.run_takeoff') as engine, self.assertRaises(ValueError): measure_job(job)
            engine.assert_not_called()


if __name__ == '__main__':
    unittest.main()
