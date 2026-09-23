import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from linear_stock import lapped_cuts,pack_cuts


class LinearStockTests(unittest.TestCase):
    def test_exact_piece_and_zero_need_no_extra_joint(self):
        result=lapped_cuts([{'id':'a','length_ft':10},{'id':'b','length_ft':0}],10,2/12)
        self.assertEqual(result['cut_length_ft'],10)
        self.assertEqual([r['joint_count'] for r in result['runs']],[0,0])
        self.assertEqual(pack_cuts(result['cuts'],10)['quantity'],1)

    def test_lap_is_added_at_each_joint_only(self):
        r=lapped_cuts([{'id':'a','length_ft':20}],10,.5,.25)['runs'][0]
        self.assertEqual(r['cuts_ft'],[10,10,1.25])
        self.assertEqual(sum(r['cuts_ft'])-r['joint_count']*.5,20.25)

    def test_short_offcuts_are_reused_with_traceable_allocation(self):
        cuts=lapped_cuts([{'id':str(i),'length_ft':n} for i,n in enumerate([6,4,6,4])],10,0)['cuts']
        result=pack_cuts(cuts,10)
        self.assertEqual(result['quantity'],2)
        self.assertEqual(result['unused_length_ft'],0)
        self.assertEqual(sum(len(s['cuts']) for s in result['stocks']),4)
        self.assertFalse(result['optimality_proven'])

    def test_long_roll_run_and_material_conservation(self):
        result=lapped_cuts([{'id':'a','length_ft':67},{'id':'b','length_ft':35}],20,.5,1)
        packed=pack_cuts(result['cuts'],66.7)
        self.assertAlmostEqual(packed['purchased_length_ft']-packed['unused_length_ft'],result['cut_length_ft'])
        for r in result['runs']:
            self.assertAlmostEqual(sum(r['cuts_ft'])-r['joint_count']*.5,r['net_length_ft']+1)

    def test_invalid_inputs_fail(self):
        for stock,lap,allowance in [(0,0,0),(10,10,0),(10,-1,0),(10,0,-1),(math.nan,0,0)]:
            with self.assertRaises(ValueError):lapped_cuts([],stock,lap,allowance)
        for length in [-1,math.inf,True]:
            with self.assertRaises(ValueError):lapped_cuts([{'id':'a','length_ft':length}],10,0)
        with self.assertRaises(ValueError):lapped_cuts([{'id':'a','length_ft':1}]*2,10,0)
        with self.assertRaises(ValueError):pack_cuts([{'run_id':'a','piece':1,'length_ft':11}],10)

if __name__=='__main__':unittest.main()
