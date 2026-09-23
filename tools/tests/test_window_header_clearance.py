import copy
import unittest
from window_header_clearance_review import calculate


class WindowHeaderClearanceTests(unittest.TestCase):
    def setUp(self):
        self.windows=[{'opening_id':'W','run':'wall','head_datum_inches':96,'base_offset_inches':0}]
        self.scenarios=[{'id':'exact','wall_height_inches':108},{'id':'precut','wall_height_inches':109.125}]
        self.alternatives={'W':[{'id':'plan','depth_inches':9,'source':'plan'},
            {'id':'supplier','depth_inches':11.25,'source':'supplier'}]}

    def calc(self):return calculate(self.windows,self.scenarios,self.alternatives,3)

    def test_deeper_alternative_overlaps_both_heights_and_never_becomes_a_zero_quantity(self):
        result=self.calc();rows=result['comparisons']
        self.assertEqual([r['gap_inches'] for r in rows],[0,-2.25,1.125,-1.125])
        self.assertEqual([r['status'] for r in rows],['zero_clearance','vertical_overlap',
            'positive_gap_unresolved','vertical_overlap'])
        self.assertTrue(all(r['short_stud_quantity'] is None for r in rows))
        self.assertIsNone(result['purchase_quantity']);self.assertIsNone(result['selected_scenario'])

    def test_garage_offset_changes_both_elevations_and_not_gap(self):
        original=self.calc()['comparisons'];self.windows[0]['base_offset_inches']=10.71875
        rows=self.calc()['comparisons']
        self.assertEqual([r['gap_inches'] for r in rows],[r['gap_inches'] for r in original])
        self.assertEqual(rows[0]['head_above_base_inches'],106.71875)
        self.assertEqual(rows[0]['wall_top_above_base_inches'],118.71875)

    def test_lvl_alternative_changes_from_overlap_to_unresolved_positive_gap(self):
        self.alternatives['W'][1]['depth_inches']=9.5
        rows=self.calc()['comparisons'];self.assertEqual(rows[1]['gap_inches'],-.5)
        self.assertEqual(rows[3]['gap_inches'],.625)
        self.assertFalse(rows[3]['detail_approved'])

    def test_missing_depth_remains_pending(self):
        self.alternatives={};result=self.calc()
        self.assertEqual(result['comparisons'],[]);self.assertEqual(result['pending'][0]['id'],'W')

    def test_owner_height_selection_does_not_select_header_or_approve_overlap(self):
        result=calculate(self.windows,self.scenarios,self.alternatives,3,selected_scenario='precut')
        self.assertEqual(result['selected_scenario'],'precut')
        selected=[r for r in result['comparisons'] if r['selected_wall_height']]
        self.assertEqual([r['gap_inches'] for r in selected],[1.125,-1.125])
        self.assertTrue(all(r['purchase_quantity'] is None and not r['detail_approved'] for r in selected))
        self.assertIsNone(result['selected_header_alternative'])
        with self.assertRaises(ValueError):calculate(self.windows,self.scenarios,self.alternatives,3,selected_scenario='missing')

    def test_unsupported_or_duplicate_inputs_rejected(self):
        baseline=copy.deepcopy(self.windows)
        self.windows*=2
        with self.assertRaisesRegex(ValueError,'Duplicate window'):self.calc()
        self.windows=baseline;self.scenarios.append(self.scenarios[0])
        with self.assertRaisesRegex(ValueError,'Unique'):self.calc()
        self.scenarios.pop();self.alternatives['W'][0]['depth_inches']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):self.calc()
        self.alternatives['W'][0]['depth_inches']=9;self.alternatives['W'][0]['source']=''
        with self.assertRaisesRegex(ValueError,'source'):self.calc()


if __name__=='__main__':unittest.main()
