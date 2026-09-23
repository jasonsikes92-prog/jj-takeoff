import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from company_profile import DEFAULT_PROFILE, resolve
from door_specifications import door_core_specifications, read_door_specifications
from new_plan_intake import create_job
from new_plan_measure import measure_job


class DoorSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(DEFAULT_PROFILE.read_bytes())
        self.intake = {**resolve(self.profile), 'plan_sha256':'a'*64,
            'company_profile_version':self.profile['version'], 'company_profile_sha256':'b'*64}

    def opening(self, identity, room, scope='interior', **other):
        return {'opening_id':identity, 'room_class':room, 'scope':scope,
            'room_source':'Synthetic reviewed room association', **other}

    def schedule(self, openings, digest=None):
        return {'plan_sha256':digest or self.intake['plan_sha256'],
            'source':'Synthetic drawing schedule', 'openings':openings}

    def test_known_rooms_resolve_without_reasking_and_unknowns_never_default_hollow(self):
        openings = [self.opening(str(i), room) for i, room in enumerate(
            ['bedroom','bathroom','toilet_room','other_interior',None,'unclassified'])]
        openings.append(self.opening('unsourced', 'bedroom', room_source=''))
        result = door_core_specifications(self.intake, self.schedule(openings))
        self.assertEqual([o['core'] for o in result['openings']], ['solid','solid','solid','hollow',None,None,None])
        self.assertEqual(result['unresolved_opening_ids'], ['4','5','unsourced'])
        self.assertFalse(result['complete_door_schedule'])
        self.assertEqual(result['current_prices'], {})
        self.assertEqual(result['purchase_quantities'], {})

    def test_garage_exterior_special_and_open_passages_do_not_use_ordinary_default(self):
        openings = [self.opening(scope, 'other_interior', scope) for scope in
            ('garage_entry','exterior','special_interior','open_passage','unknown')]
        result = door_core_specifications(self.intake, self.schedule(openings))
        self.assertTrue(all(o['core'] is None for o in result['openings']))
        self.assertNotIn('open_passage', result['unresolved_opening_ids'])
        self.assertEqual(len(result['unresolved_opening_ids']), 4)

    def test_project_selection_overrides_default_with_source_and_conflict(self):
        opening = self.opening('bed', 'bedroom', project_core='hollow', project_core_source='Explicit fixture owner selection')
        original = copy.deepcopy(opening)
        result = door_core_specifications(self.intake, self.schedule([opening]))['openings'][0]
        self.assertEqual(result['core'], 'hollow')
        self.assertEqual(result['basis'], 'project_specification')
        self.assertEqual(result['resolved_conflict']['company_default'], 'solid')
        self.assertEqual(original, opening)
        opening['project_core_source'] = ''
        with self.assertRaises(ValueError):
            door_core_specifications(self.intake, self.schedule([opening]))

    def test_wrong_plan_duplicate_identity_and_passage_override_rejected(self):
        opening = self.opening('bed', 'bedroom')
        for schedule in (self.schedule([opening], 'wrong'), self.schedule([opening, opening]),
                self.schedule([self.opening('passage', None, 'open_passage', project_core='solid', project_core_source='invalid')])):
            with self.assertRaises(ValueError):
                door_core_specifications(self.intake, schedule)

    def test_missing_schedule_and_old_profile_keep_scope_unknown(self):
        missing = door_core_specifications(self.intake)
        self.assertEqual(missing['openings'], [])
        self.assertIn('extraction', missing['status'])
        old = copy.deepcopy(self.intake)
        del old['settings']['doors.interior_core_by_room']
        result = door_core_specifications(old, self.schedule([self.opening('bed','bedroom')]))
        self.assertIsNone(result['openings'][0]['core'])

    def make_job(self, root):
        plan = root/'source.pdf'
        with fitz.open() as pdf:
            pdf.new_page(width=500,height=500).insert_text((30,30), 'FLOOR PLAN')
            pdf.save(plan)
        digest = hashlib.sha256(plan.read_bytes()).hexdigest()
        profile = root/'profile.json'
        profile.write_bytes(DEFAULT_PROFILE.read_bytes())
        job = root/'job'
        create_job(plan, job, profile, {'door_schedule':self.schedule([
            self.opening('bed','bedroom'),self.opening('closet','other_interior'),
            self.opening('garage','other_interior','garage_entry')], digest)})
        return job, profile, digest

    def test_intake_uses_frozen_profile_and_preserves_existing_job(self):
        with tempfile.TemporaryDirectory() as folder:
            job, profile, _ = self.make_job(Path(folder))
            result = read_door_specifications(job)
            self.assertEqual([o['core'] for o in result['openings']], ['solid','hollow',None])
            self.assertEqual(result['unresolved_opening_ids'], ['garage'])
            saved = {p.name:p.read_bytes() for p in job.iterdir() if p.is_file()}
            profile.write_text('{}')
            self.assertEqual(read_door_specifications(job), result)
            with self.assertRaises(FileExistsError):
                create_job(job/'plan.pdf', job)
            self.assertEqual(saved, {p.name:p.read_bytes() for p in job.iterdir() if p.is_file()})

    def test_changed_schedule_defaults_plan_or_derived_result_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            job, _, _ = self.make_job(Path(folder))
            for name in ('door_schedule.json','estimate_intake.json','company_profile_snapshot.json','door_core_specifications.json','plan.pdf'):
                path = job/name
                original = path.read_bytes()
                try:
                    if name == 'plan.pdf':
                        path.write_bytes(original + b'\nchanged')
                    else:
                        value = json.loads(original)
                        if name == 'door_schedule.json':value['openings'][0]['room_class']='other_interior'
                        elif name == 'estimate_intake.json':value['settings']['doors.interior_core_by_room']['bedroom']='hollow'
                        elif name == 'company_profile_snapshot.json':value['version']+=1
                        else:value['openings'][0]['core']='hollow'
                        path.write_text(json.dumps(value))
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        read_door_specifications(job)
                finally:
                    path.write_bytes(original)
            self.assertEqual(read_door_specifications(job)['openings'][0]['core'], 'solid')

    def test_measurement_pipeline_keeps_specification_source_and_refuses_changed_input(self):
        with tempfile.TemporaryDirectory() as folder:
            job, _, digest = self.make_job(Path(folder))
            review = {'coverage_passed':True, 'review_sha256':'fixture', 'unique_role_pages':{'floor':1},
                'roles_requiring_disambiguation':{}}
            engine_result = {'status':'more_information_required', 'pages':{}, 'lines':[]}
            with patch('new_plan_measure.read_sheet_review', return_value=review), patch('jnj_takeoff.run_takeoff', return_value=engine_result):
                summary = measure_job(job)
            self.assertEqual(summary['door_core_assigned_openings'], 2)
            self.assertEqual(summary['door_core_unresolved_opening_ids'], ['garage'])
            self.assertTrue(summary['door_core_schedule_available'])
            self.assertFalse(summary['door_core_schedule_complete'])
            self.assertEqual(summary['door_core_specifications_sha256'], hashlib.sha256((job/'door_core_specifications.json').read_bytes()).hexdigest())
            self.assertFalse(summary['estimate_released'])
            value=json.loads((job/'door_schedule.json').read_bytes())
            value['openings'][0]['room_class']='other_interior'
            (job/'door_schedule.json').write_text(json.dumps(value))
            with patch('jnj_takeoff.run_takeoff') as engine, self.assertRaises(ValueError):
                measure_job(job)
            engine.assert_not_called()


if __name__ == '__main__':
    unittest.main()
