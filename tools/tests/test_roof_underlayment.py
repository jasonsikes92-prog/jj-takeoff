import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_underlayment import feltbuster_courses


def face(slope=.25):
    return {'id':'roof','points_per_foot':1,'surface_factor':math.sqrt(1+slope*slope),
            'points':[[0,0],[20,0],[20,10],[0,10]]}


class UnderlaymentTests(unittest.TestCase):
    def test_double_coverage_includes_bottom_and_top(self):
        result=feltbuster_courses(face(),[0,.25])
        self.assertEqual(result['less_than_double_coverage_sf'],0)
        self.assertEqual(result['courses'][0]['kind'],'starter')
        self.assertGreater(result['uncut_stock_area_sf'],2*result['surface_sf'])

    def test_four_in_twelve_uses_single_coverage(self):
        result=feltbuster_courses(face(4/12),[0,4/12])
        self.assertFalse(result['low_slope_double_coverage'])
        self.assertEqual(result['uncovered_sf'],0)
        self.assertTrue(all(c['kind']=='course' for c in result['courses']))

    def test_calibration_translation_and_reflection_preserve_quantity(self):
        original=face(1);a=feltbuster_courses(original,[0,1])
        changed=copy.deepcopy(original);changed['points']=[[2*x+50,-2*y+90] for x,y in original['points']]
        changed['points_per_foot']=2;b=feltbuster_courses(changed,[0,-1])
        self.assertAlmostEqual(a['cut_length_ft'],b['cut_length_ft'])
        self.assertAlmostEqual(a['surface_sf'],b['surface_sf'])

    def test_mismatch_low_pitch_and_unplanned_splice_fail(self):
        for item,gradient in [(face(),[0,1]),(face(.1),[0,.1])]:
            with self.assertRaises(ValueError):feltbuster_courses(item,gradient)
        item=face(1);item['points']=[[0,0],[300,0],[300,10],[0,10]]
        with self.assertRaisesRegex(ValueError,'splice'):feltbuster_courses(item,[0,1])

if __name__=='__main__':unittest.main()
