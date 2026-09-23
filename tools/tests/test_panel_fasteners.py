import unittest
from shapely.geometry import Polygon, Point, box
from tools.panel_fasteners import positions


class PanelFasteners(unittest.TestCase):
    def test_full_sheet_has_54_positions_with_half_inch_edge_distance(self):
        r = positions(box(0, 0, 60, 36), 8, .5)
        self.assertEqual(r['count'], 54)
        self.assertFalse(r['needs_review'])
        self.assertEqual(len({(p['x'], p['y']) for p in r['points']}), 54)
        for p in r['points']:
            if p['role'] == 'perimeter':self.assertAlmostEqual(p['edge_distance'], .5)

    def test_irregular_cut_has_no_screws_outside_material(self):
        poly = Polygon([(0,0),(60,0),(60,15),(20,15),(20,36),(0,36)])
        r = positions(poly, 8, .5)
        self.assertTrue(r['needs_review'])
        self.assertTrue(all(poly.covers(Point(p['x'], p['y'])) for p in r['points']))

    def test_unfastenable_strip_is_not_zero_quantity(self):
        r = positions(box(0,0,.75,30), 8, .5)
        self.assertIsNone(r['count'])
        self.assertTrue(r['needs_review'])

    def test_changes_recalculate_and_invalid_inputs_rejected(self):
        self.assertGreater(positions(box(0,0,60,36),8,.5)['count'], positions(box(0,0,30,36),8,.5)['count'])
        with self.assertRaises(ValueError):positions(box(0,0,60,36),0,.5)


if __name__ == '__main__':unittest.main()
