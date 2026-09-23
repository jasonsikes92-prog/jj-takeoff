import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exterior_junction_allowances import reconcile
from company_profile import DEFAULT_PROFILE,resolve


class ExteriorJunctionAllowances(unittest.TestCase):
    def setUp(self):
        self.settings=resolve(json.loads(DEFAULT_PROFILE.read_text()))['settings']
        self.corners=[{'id':'C1','point_pt':[0,0],'wall_runs':['W1','W2'],'type':'reentrant'}]
        self.aliases=[{'id':'EC1','run':'IR1','exterior_walls':['W1','W2']}]

    def test_corner_and_interior_alias_form_one_whole_assembly(self):
        result=reconcile(self.corners,[],self.aliases,{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        self.assertEqual(len(result['assemblies']),1)
        self.assertEqual(result['known_junction_stud_allowance'],4)
        self.assertEqual(result['assemblies'][0]['aliases'],['C1','EC1'])

    def test_two_aliases_for_same_branch_do_not_add_a_branch(self):
        aliases=self.aliases+[{**self.aliases[0],'id':'EC2'}]
        result=reconcile(self.corners,[],aliases,{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        self.assertEqual(result['known_junction_stud_allowance'],4)

    def test_nearby_source_corner_connection_is_merged_but_distant_one_is_unresolved(self):
        connection={'id':'EJ1','kind':'corner_connection','exterior_wall':'W1','interior_run':'IR1','point_pt':[2,2]}
        result=reconcile(self.corners,[connection],[],{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        self.assertEqual(result['known_junction_stud_allowance'],4)
        connection['point_pt']=[50,50]
        result=reconcile(self.corners,[connection],[],{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        self.assertEqual(result['known_junction_stud_allowance'],3)
        self.assertEqual(result['unresolved'][0]['id'],'EJ1')

    def test_clear_T_and_plain_outside_corner_remain_separate(self):
        corners=copy.deepcopy(self.corners);corners[0]['type']='outside_convex'
        connection={'id':'EJ1','kind':'T_connection','interior_run':'IR1','point_pt':[30,0]}
        result=reconcile(corners,[connection],[],{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        self.assertEqual(result['known_junction_stud_allowance'],7)
        self.assertFalse(result['purchase_order_released'])

    def test_bad_source_assignment_does_not_silently_count(self):
        for aliases in ([{**self.aliases[0],'exterior_walls':['missing','wall']}],
                [{**self.aliases[0],'id':'C1'}]):
            with self.assertRaises(ValueError):reconcile(self.corners,[],aliases,{'IR1':{}},self.settings,12,'sheet',wall_depth_inches=3.5)
        with self.assertRaises(ValueError):reconcile(self.corners,[],self.aliases,{},self.settings,12,'sheet',wall_depth_inches=3.5)


if __name__=='__main__':unittest.main()
