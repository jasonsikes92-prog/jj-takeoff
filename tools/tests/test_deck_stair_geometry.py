import unittest
from deck_stair_geometry import straight_stair_reference


class StairGeometryTests(unittest.TestCase):
    def calc(self,rise=82.5,width=42,going=10):
        return straight_stair_reference(rise,width,max_riser_in=7.75,
                                       going_in=going,landing_depth_in=36)

    def test_owner_dimensions_and_upper_landing(self):
        r=self.calc()
        self.assertEqual((r['riser_count'],r['separate_tread_count']), (11,10))
        self.assertEqual(r['equal_riser_height_in'],7.5)
        self.assertEqual(r['horizontal_run_in'],100)
        self.assertEqual(r['bottom_landing_reference_sf'],10.5)
        self.assertFalse(r['stock_order_released'])

    def test_riser_boundary_and_changed_going(self):
        self.assertEqual(self.calc(93)['riser_count'],12)
        self.assertEqual(self.calc(93.01)['riser_count'],13)
        self.assertEqual(self.calc(going=11)['horizontal_run_in'],110)

    def test_missing_negative_and_nonfinite_inputs(self):
        for x in (None,0,-1,float('nan'),float('inf'),True,'82.5'):
            with self.subTest(x=x), self.assertRaises(ValueError):self.calc(x)


if __name__=='__main__':unittest.main()
