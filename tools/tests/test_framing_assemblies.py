import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_profile import DEFAULT_PROFILE
from framing_assemblies import calculate,openings_from_schedule,documented_group_allowances

class FramingAssembliesTests(unittest.TestCase):
    def setUp(self):self.profile=json.loads(DEFAULT_PROFILE.read_text())

    def test_pocket_door_never_receives_ordinary_jamb_default(self):
        result=calculate(self.profile,[{'id':'D1','source':'sheet 2','classification':'pocket_door'}],[])
        self.assertEqual(result['component_totals'],{'king_studs':0,'jack_studs':0,'junction_studs':0,'pocket_frame_kits':1})
        self.assertFalse(result['purchase_order_released'])

    def test_unknown_door_stays_pending_and_is_not_zero_cost_scope(self):
        result=calculate(self.profile,[{'id':'D1','source':'sheet 2'}],[])
        self.assertEqual(result['components'],[])
        self.assertEqual(len(result['pending']),1)

    def test_plan_support_override_takes_precedence(self):
        result=calculate(self.profile,[{'id':'D1','source':'detail A','classification':'ordinary_interior_door','studs_per_side':{'king':2,'jack':3},'bearing_verified':True}],[])
        self.assertEqual(result['component_totals']['king_studs'],4)
        self.assertEqual(result['component_totals']['jack_studs'],6)
        self.assertEqual(result['pending'],[])

    def test_exterior_and_wide_garage_use_distinct_confirmed_supports(self):
        openings=[{'id':kind,'source':'reviewed plan','classification':kind} for kind in
                  ('ordinary_exterior_opening','wide_garage_opening')]
        result=calculate(self.profile,openings,[])
        self.assertEqual([c['quantities'] for c in result['components']],
                         [{'king_studs':2,'jack_studs':2},{'king_studs':2,'jack_studs':4}])
        self.assertEqual(len(result['pending']),2)
        self.assertFalse(result['purchase_order_released'])

    def test_old_profile_does_not_guess_exterior_supports(self):
        profile={'version':1,'rules':[]}
        result=calculate(profile,[{'id':'E1','source':'plan','classification':'ordinary_exterior_opening'}],[])
        self.assertEqual(result['components'],[])
        self.assertEqual(len(result['pending']),1)

    def test_exterior_override_wins_and_invalid_counts_are_rejected(self):
        opening={'id':'E1','source':'detail','classification':'wide_garage_opening',
                 'studs_per_side':{'king':2,'jack':3},'bearing_verified':True}
        self.assertEqual(calculate(self.profile,[opening],[])['component_totals']['jack_studs'],6)
        for bad in ({'king':True,'jack':1},{'king':1,'jack':-1},{'king':1.5,'jack':1}):
            opening['studs_per_side']=bad
            with self.assertRaises(ValueError):calculate(self.profile,[opening],[])

    def test_same_physical_junction_cannot_be_counted_from_two_views(self):
        j={'id':'J1','source':'sheet 2','classification':'T_intersection','backing':'solid_stud_backing'}
        with self.assertRaises(ValueError):calculate(self.profile,[],[j,j])

    def test_cross_includes_both_branch_ends_once(self):
        result=calculate(self.profile,[],[{'id':'J1','source':'sheet 2','classification':'cross_intersection','backing':'solid_stud_backing'}])
        self.assertEqual(result['component_totals']['junction_studs'],5)

    def test_clips_do_not_inherit_solid_backing_quantity(self):
        result=calculate(self.profile,[],[{'id':'J1','source':'sheet 2','classification':'L_corner','backing':'drywall_clips'}])
        self.assertEqual(result['components'],[])
        self.assertEqual(len(result['pending']),1)

    def test_reviewed_special_openings_do_not_inherit_ordinary_jambs(self):
        schedule={'openings':[{'opening_id':str(i),'opening_type':kind} for i,kind in enumerate(
            ['hinged','pocket','bypass','open_passage','garage_entry','unrecognized'])]}
        openings=openings_from_schedule(schedule,'reviewed schedule',schedule_scope='interior_and_garage_entries')
        result=calculate(self.profile,openings,[])
        self.assertEqual(result['component_totals'],{'king_studs':2,'jack_studs':2,'junction_studs':0,'pocket_frame_kits':1})
        self.assertEqual({p['id'] for p in result['pending']},{'0','1','2','3','4','5'})
        self.assertFalse(result['purchase_order_released'])

    def test_schedule_requires_scope_source_and_unique_physical_ids(self):
        schedule={'openings':[{'opening_id':'D1','opening_type':'hinged'}]*2}
        with self.assertRaisesRegex(ValueError,'scope'):openings_from_schedule(schedule,'sheet',schedule_scope='unreviewed')
        with self.assertRaisesRegex(ValueError,'source'):openings_from_schedule(schedule,'',schedule_scope='interior_and_garage_entries')
        with self.assertRaisesRegex(ValueError,'Unique'):openings_from_schedule(schedule,'sheet',schedule_scope='interior_and_garage_entries')

    def test_schedule_preserves_explicit_stud_override_without_claiming_bearing_review(self):
        schedule={'openings':[{'opening_id':'D1','opening_type':'hinged','studs_per_side':{'king':2,'jack':2}}]}
        openings=openings_from_schedule(schedule,'detail',schedule_scope='interior_and_garage_entries')
        result=calculate(self.profile,openings,[])
        self.assertEqual(result['component_totals']['king_studs'],4)
        self.assertEqual(result['component_totals']['jack_studs'],4)
        self.assertEqual(len(result['pending']),1)

    def test_special_openings_only_receive_explicit_documented_allowances(self):
        for kind in ('bypass_door','garage_entry','open_passage'):
            opening={'id':'S1','source':'schedule','classification':kind}
            self.assertEqual(calculate(self.profile,[opening],[])['components'],[])
            opening['estimating_allowance']={'source':'reviewed header','basis':'One king and jack per side for estimating',
                'studs_per_side':{'king':1,'jack':1}}
            result=calculate(self.profile,[opening],[])
            self.assertEqual(result['component_totals']['king_studs'],2)
            self.assertEqual(result['component_totals']['jack_studs'],2)
            self.assertEqual(result['components'][0]['basis']['source'],'reviewed header')
            self.assertEqual(len(result['pending']),1)
            self.assertFalse(result['purchase_order_released'])

    def test_special_allowance_requires_evidence_and_integer_counts(self):
        for source,basis,rule in [('', 'basis', {'king':1,'jack':1}),('source','',{'king':1,'jack':1}),
                ('source','basis',{'king':True,'jack':1}),('source','basis',{'king':-1,'jack':1}),
                ('source','basis',{'king':1.5,'jack':1})]:
            opening={'id':'S1','source':'schedule','classification':'bypass_door',
                'estimating_allowance':{'source':source,'basis':basis,'studs_per_side':rule}}
            with self.assertRaises(ValueError):calculate(self.profile,[opening],[])

    def test_schedule_carries_special_allowance_without_changing_classification(self):
        allowance={'source':'header','basis':'Estimating only','studs_per_side':{'king':2,'jack':1}}
        schedule={'openings':[{'opening_id':'S1','opening_type':'open_passage','estimating_allowance':allowance}]}
        openings=openings_from_schedule(schedule,'schedule',schedule_scope='interior_and_garage_entries')
        self.assertEqual(openings[0]['classification'],'open_passage')
        result=calculate(self.profile,openings,[])
        self.assertEqual(result['component_totals']['king_studs'],4)
        self.assertEqual(result['component_totals']['jack_studs'],2)

    def test_group_allowance_counts_each_assembly_once_and_keeps_unknowns(self):
        settings={'framing.tight_door_corner_quantity_basis':'documented_estimating_allowances'}
        components={'components':[{'id':'door','source':'door detail','quantities':{'king_studs':2,'jack_studs':2}},
            {'id':'corner','source':'corner detail','quantities':{'junction_studs':3}}],'pending':[]}
        result=documented_group_allowances(settings,components,[{'assemblies':['door','corner','unknown']}])
        group=result['groups'][0]
        self.assertEqual(group['component_allowances'],{'king_studs':2,'jack_studs':2,'junction_studs':3})
        self.assertEqual(group['unquantified_assemblies'],['unknown'])
        self.assertEqual(group['shared_member_credit'],0)
        self.assertIsNone(result['complete_order_quantity'])
        self.assertFalse(result['exact_combined_layout_required_for_estimating'])
        for groups in ([{'assemblies':['door','corner']},{'assemblies':['door']}],[{'assemblies':['door']}],
                [{'assemblies':['door','door','corner']}]):
            with self.assertRaises(ValueError):documented_group_allowances(settings,components,groups)
        with self.assertRaises(ValueError):documented_group_allowances({},components,[{'assemblies':['door','corner']}])

if __name__=='__main__':unittest.main()
