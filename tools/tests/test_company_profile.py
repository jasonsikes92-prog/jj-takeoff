import json
import hashlib
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from company_profile import DEFAULT_PROFILE, initialize, resolve

class CompanyProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(DEFAULT_PROFILE.read_text())

    def test_new_job_inherits_confirmed_practices(self):
        result = resolve(self.profile)
        self.assertEqual(result['settings']['framing.outside_corner_studs'], 3)
        self.assertEqual(result['settings']['framing.T_intersection_backing'], 'three_stud')
        self.assertEqual(result['settings']['concrete.waste_pct'], 10)
        self.assertEqual(result['settings']['framing.maximum_2x6_stock_ft'], 26)

    def test_plan_overrides_default_and_preserves_reason(self):
        result = resolve(self.profile, project_overrides={'framing.stud_size': '2x6'})
        self.assertEqual(result['settings']['framing.stud_size'], '2x6')
        self.assertEqual(len(result['resolved_conflicts']), 1)
        self.assertEqual(result['provenance']['framing.stud_size']['basis'], 'project_override')

    def test_cmu_practices_wait_for_material_and_do_not_apply_to_poured_walls(self):
        key='foundation.cmu_vertical_core_reinforcement'
        self.assertNotIn(key,resolve(self.profile)['settings'])
        self.assertIn('foundation_wall_material',resolve(self.profile)['facts_to_extract_from_plan'])
        self.assertNotIn(key,resolve(self.profile,{'foundation_wall_material':'poured_concrete'})['settings'])
        result=resolve(self.profile,{'foundation_wall_material':'CMU'})
        self.assertEqual(result['settings'][key]['filled_core_interval'],4)
        self.assertEqual(result['settings'][key]['bars_per_filled_core'],2)
        self.assertEqual(result['settings']['foundation.cmu_horizontal_reinforcement']['course_interval'],3)
        self.assertTrue(result['settings']['foundation.cmu_caps_within_overall_height'])
        self.assertEqual(result['quantity_measurements'],{})
        self.assertFalse(result['structural_approval'])

    def test_project_cmu_detail_overrides_practice_without_changing_next_job(self):
        key='foundation.cmu_vertical_core_reinforcement'
        override={'filled_core_interval':2,'bars_per_filled_core':1,'bar_size':'#5'}
        result=resolve(self.profile,{'foundation_wall_material':'CMU'},{key:override})
        self.assertEqual(result['settings'][key],override)
        self.assertEqual(result['resolved_conflicts'][0]['key'],key)
        self.assertEqual(resolve(self.profile,{'foundation_wall_material':'CMU'})['settings'][key]['bar_size'],'#4')

    def test_hose_bibbs_are_included_when_unmarked_without_invented_locations(self):
        result=resolve(self.profile)
        allowance=result['unlocated_scope_allowances'][0]
        self.assertEqual(allowance['quantity'],4)
        self.assertEqual(allowance['unit'],'EA')
        self.assertEqual(allowance['locations'],[])
        self.assertFalse(allowance['measured_from_plan'])
        self.assertEqual(allowance['provenance']['basis'],'company_default')
        self.assertEqual(result['quantity_measurements'],{})

    def test_explicit_hose_bibb_count_replaces_default_including_zero(self):
        for count in (0,5):
            value=resolve(self.profile,project_overrides={'plumbing.exterior_hose_bibbs':count})
            allowance=value['unlocated_scope_allowances'][0]
            self.assertEqual(allowance['quantity'],count)
            self.assertEqual(allowance['provenance']['basis'],'project_override')
        for count in (-1,2.5,True):
            with self.assertRaises(ValueError):resolve(self.profile,project_overrides={'plumbing.exterior_hose_bibbs':count})

    def test_supplier_expiration_practice_is_inherited_without_price_guarantee(self):
        key='pricing.supplier_quote_expiration'
        result=resolve(self.profile)
        self.assertEqual(result['settings'][key]['treatment'],'follow_up_not_automatic_rejection')
        self.assertFalse(result['settings'][key]['guarantees_unchanged_price'])
        self.assertEqual(result['current_prices'],{})
        override={'treatment':'supplier_confirmed_strict_expiry'}
        changed=resolve(self.profile,project_overrides={key:override})
        self.assertEqual(changed['settings'][key],override)
        self.assertEqual(changed['resolved_conflicts'][0]['key'],key)

    def test_roof_trusses_do_not_inherit_stick_rafters(self):
        result = resolve(self.profile, {'roof_system': 'trusses'})
        self.assertNotIn('roof.rafter_size', result['settings'])

    def test_no_slab_cannot_also_have_slab_features(self):
        for feature in ('backfilled_slab','thickened_slab_edge','interior_slab'):
            facts={'concrete_slab':False,feature:True}
            with self.subTest(feature=feature),self.assertRaisesRegex(ValueError,'conflict'):
                resolve(self.profile,facts)
            self.assertEqual(facts,{'concrete_slab':False,feature:True})
        result=resolve(self.profile,{'concrete_slab':False,'backfilled_slab':False})
        self.assertNotIn('slab.extra_rebar_grid',result['settings'])

    def test_unknown_fact_is_pending_not_a_negative_answer(self):
        result=resolve(self.profile,{'backfilled_slab':None,'concrete_slab':None,'roof_system':None})
        self.assertNotIn('slab.extra_rebar_grid',result['settings'])
        self.assertNotIn('roof.rafter_size',result['settings'])
        self.assertTrue({'backfilled_slab','concrete_slab','roof_system'}<=set(result['facts_to_extract_from_plan']))
        no_grid=resolve(self.profile,{'backfilled_slab':False})
        self.assertNotIn('backfilled_slab',no_grid['facts_to_extract_from_plan'])
        specified=resolve(self.profile,{'backfilled_slab':None},
                          {'slab.extra_rebar_grid':{'bar':'#5','spacing_each_direction_inches':16}})
        self.assertNotIn('backfilled_slab',specified['facts_to_extract_from_plan'])
        self.assertEqual(specified['settings']['slab.extra_rebar_grid']['bar'],'#5')

    def test_job_settings_cannot_mutate_company_defaults(self):
        first=resolve(self.profile,{'foundation_type':'crawlspace'})
        first['settings']['foundation.usual_pier']['blocks_per_course']=9
        first['settings']['doors.interior_core_by_room']['bedroom']='hollow'
        next_job=resolve(self.profile,{'foundation_type':'crawlspace'})
        self.assertEqual(next_job['settings']['foundation.usual_pier']['blocks_per_course'],2)
        self.assertEqual(next_job['settings']['doors.interior_core_by_room']['bedroom'],'solid')

    def test_override_and_conflict_records_are_independent_copies(self):
        key='doors.interior_core_by_room';override={'bedroom':'hollow'}
        result=resolve(self.profile,project_overrides={key:override})
        result['settings'][key]['bedroom']='solid'
        self.assertEqual(override,{'bedroom':'hollow'})
        self.assertEqual(result['resolved_conflicts'][0]['project_value'],{'bedroom':'hollow'})
        result['resolved_conflicts'][0]['company_default']['bedroom']='hollow'
        self.assertEqual(resolve(self.profile)['settings'][key]['bedroom'],'solid')

    def test_backfill_grid_only_applies_when_triggered(self):
        self.assertNotIn('slab.extra_rebar_grid', resolve(self.profile, {'backfilled_slab': False})['settings'])
        self.assertEqual(resolve(self.profile, {'backfilled_slab': True})['settings']['slab.extra_rebar_grid']['bar'], '#4')

    def test_ambiguous_boolean_plan_facts_cannot_silently_omit_scope(self):
        for key in ('backfilled_slab','concrete_slab','interior_slab'):
            for value in ('yes','no','true','false',1,0,[],{}):
                with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,key):
                    resolve(self.profile,{key:value})
            self.assertIn(key,resolve(self.profile,{key:None})['facts_to_extract_from_plan'])

    def test_invalid_boolean_intake_does_not_write_a_partial_job(self):
        with tempfile.TemporaryDirectory() as td:
            plan=Path(td)/'fixture.pdf';plan.write_bytes(b'%PDF-1.4\n% test only')
            job=Path(td)/'job'
            with self.assertRaisesRegex(ValueError,'backfilled_slab'):
                initialize(plan,job,facts={'backfilled_slab':'yes'})
            self.assertFalse(job.exists())

    def test_roberts_values_and_stale_prices_do_not_transfer(self):
        result = resolve(self.profile, {'foundation_type': 'crawlspace'})
        self.assertNotIn('foundation.average_wall_height_ft', result['settings'])
        self.assertEqual(result['quantity_measurements'], {})
        self.assertEqual(result['current_prices'], {})
        self.assertFalse(result['structural_approval'])

    def test_door_studs_apply_only_to_ordinary_interior_openings(self):
        key = 'framing.ordinary_interior_door_studs_per_side'
        self.assertEqual(resolve(self.profile, {'opening_class': 'ordinary_interior_door'})['settings'][key], {'king': 1, 'jack': 1})
        self.assertNotIn(key, resolve(self.profile, {'opening_class': 'garage_door'})['settings'])
        self.assertNotIn(key, resolve(self.profile)['settings'])
        self.assertEqual(resolve(self.profile, {'opening_class': 'ordinary_interior_door'}, {key: {'king': 2, 'jack': 2}})['settings'][key], {'king': 2, 'jack': 2})

    def test_plan_file_intake_loads_profile_and_preserves_existing_job(self):
        with tempfile.TemporaryDirectory() as td:
            plan = Path(td)/'fixture.pdf'
            plan.write_bytes(b'%PDF-1.4\n% synthetic intake hash fixture only')
            job = Path(td)/'new_job'
            target = initialize(plan, job)
            result = json.loads(target.read_text())
            self.assertEqual(result['company_profile_version'], self.profile['version'])
            self.assertEqual(result['settings']['framing.top_plates'], 2)
            with self.assertRaises(FileExistsError):
                initialize(plan, job)

    def test_saved_profile_and_inputs_reproduce_job_after_default_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan=root/'plan.pdf';plan.write_bytes(b'%PDF-1.4\n% fixture')
            profile=root/'profile.json';profile.write_bytes(DEFAULT_PROFILE.read_bytes())
            job=root/'job'
            target=initialize(plan,job,profile,{'roof_system':'trusses'},{'framing.stud_size':'2x6'})
            original=json.loads(target.read_text());snapshot=job/original['company_profile_snapshot']
            profile.write_text('{}')
            self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(),original['company_profile_sha256'])
            replay=resolve(json.loads(snapshot.read_text()),original['project_facts'],original['project_overrides'])
            self.assertEqual(replay['settings'],original['settings'])
            self.assertNotIn('roof.rafter_size',replay['settings'])

    def test_dated_allowance_policy_inherits_without_prices_and_allows_override(self):
        key='pricing.dated_allowance_fallback'
        result=resolve(self.profile)
        self.assertEqual(result['settings'][key]['selection'],'latest_saved_compatible_rate')
        self.assertTrue(result['settings'][key]['current_rate_takes_precedence'])
        self.assertEqual(result['current_prices'],{})
        self.assertEqual(resolve(self.profile,project_overrides={key:False})['settings'][key],False)
        self.assertIn('dated_allowance_policy',result['provenance'][key]['source'])

    def test_preexisting_profile_snapshot_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);plan=root/'plan.pdf';plan.write_bytes(b'%PDF-1.4\n% fixture')
            job=root/'job';job.mkdir();snapshot=job/'company_profile_snapshot.json';snapshot.write_text('preserve')
            with self.assertRaises(FileExistsError):initialize(plan,job)
            self.assertEqual(snapshot.read_text(),'preserve')
            self.assertFalse((job/'estimate_intake.json').exists())

if __name__ == '__main__':
    unittest.main()
