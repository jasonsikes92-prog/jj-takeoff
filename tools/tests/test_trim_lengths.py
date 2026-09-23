import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trim_lengths import net_run


class TrimLengths(unittest.TestCase):
    def test_overlapping_door_casing_and_cabinet_deductions_count_once(self):
        result=net_run(20,[{'id':'door','start_ft':2,'end_ft':5},
                           {'id':'casing','start_ft':1.75,'end_ft':5.25},
                           {'id':'cabinet','start_ft':5,'end_ft':10}])
        self.assertEqual(result['net_lf'],11.75)
        self.assertEqual(result['retained'],[{'start_ft':0,'end_ft':1.75},{'start_ft':10,'end_ft':20}])
        self.assertEqual(set(result['deductions'][0]['deduction_ids']),{'door','casing','cabinet'})

    def test_touching_intervals_and_full_wall_coverage(self):
        result=net_run(10,[{'id':'a','start_ft':0,'end_ft':4},{'id':'b','start_ft':4,'end_ft':10}])
        self.assertEqual(result['net_lf'],0);self.assertEqual(result['retained'],[])
        self.assertIsNone(result['purchase_quantity'])

    def test_no_deduction_preserves_measured_length(self):
        self.assertEqual(net_run(17.125,[])['net_lf'],17.125)

    def test_invalid_locations_are_not_silently_clipped(self):
        for start,end in [(-1,3),(3,2),(0,11),(0,float('nan'))]:
            with self.assertRaises(ValueError):net_run(10,[{'id':'bad','start_ft':start,'end_ft':end}])
        with self.assertRaises(ValueError):net_run(10,[{'id':'a','start_ft':0,'end_ft':1}]*2)

if __name__=='__main__':unittest.main()
