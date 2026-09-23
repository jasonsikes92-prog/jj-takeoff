import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from vault_wall_surface import vault_upper_wall_area


class VaultWallSurfaceTests(unittest.TestCase):
    def boundary(self, points):
        return {'id':'room', 'kind':'area', 'page':1, 'points':points,
            'points_per_foot':10, 'width_pt':1000, 'height_pt':1000}

    def measure(self, points, direction=(0, 1)):
        return vault_upper_wall_area(self.boundary(points), direction, 8, 12, 'Synthetic roof section')

    def test_rectangle_is_two_triangular_ends_with_zero_at_low_sides(self):
        result = self.measure([[100,100],[300,100],[300,260],[100,260]])
        self.assertAlmostEqual(result['gross_upper_wall_sf'], 2 * 16 * (8 * 8/12) / 2)
        self.assertEqual([e['upper_wall_sf'] for e in result['edges']][::2], [0, 0])
        self.assertIsNone(result['low_side_height_ft'])
        self.assertIsNone(result['purchase_quantity'])

    def test_centered_chase_adds_only_two_upper_returns(self):
        # Twenty-by-sixteen room, two-foot-deep chase six feet wide.
        points = [[100,100],[300,100],[300,150],[280,150],[280,210],[300,210],[300,260],[100,260]]
        result = self.measure(points)
        projected_ends = 16 * (8 * 8/12)
        return_height = 5 * 8/12
        self.assertAlmostEqual(result['gross_upper_wall_sf'], projected_ends + 2 * 2 * return_height)
        self.assertAlmostEqual(result['edges'][3]['upper_wall_sf'], 26)  # Two trapezoids across the ridge.

    def test_diagonal_end_crossing_ridge_uses_sloped_wall_length(self):
        points = [[100,100],[200,100],[300,260],[100,260]]
        result = self.measure(points)
        rise = 8 * 8/12
        expected = (math.hypot(10,16) + 16) * rise / 2
        self.assertAlmostEqual(result['gross_upper_wall_sf'], expected)

    def test_rotation_translation_and_scale_preserve_physical_result(self):
        points = [[100,100],[300,100],[300,260],[100,260]]
        original = self.measure(points)
        angle = math.pi/5
        rotate = lambda p:[p[0]*math.cos(angle)-p[1]*math.sin(angle)+350,
                          p[0]*math.sin(angle)+p[1]*math.cos(angle)+50]
        rotated = self.measure([rotate(p) for p in points], (-math.sin(angle), math.cos(angle)))
        self.assertAlmostEqual(rotated['gross_upper_wall_sf'], original['gross_upper_wall_sf'])
        scaled = self.boundary([[v*2 for v in p] for p in points])
        scaled['points_per_foot'] = 20
        self.assertAlmostEqual(vault_upper_wall_area(scaled, [0,1], 8,12,'section')['gross_upper_wall_sf'], original['gross_upper_wall_sf'])

    def test_source_geometry_is_preserved_and_changed_depth_recalculates(self):
        boundary = self.boundary([[100,100],[300,100],[300,150],[280,150],[280,210],[300,210],[300,260],[100,260]])
        before = copy.deepcopy(boundary)
        first = vault_upper_wall_area(boundary, [0,1], 8,12,'section')
        self.assertEqual(boundary, before)
        boundary['points'][3][0] -= 10
        boundary['points'][4][0] -= 10
        second = vault_upper_wall_area(boundary, [0,1], 8,12,'section')
        self.assertAlmostEqual(second['gross_upper_wall_sf']-first['gross_upper_wall_sf'], 2 * 5 * 8/12)

    def test_invalid_geometry_pitch_and_direction_rejected(self):
        boundary = self.boundary([[100,100],[300,100],[300,260],[100,260]])
        for direction,rise,run,source in [([0,0],8,12,'section'),([0,float('nan')],8,12,'section'),
            ([0,1],0,12,'section'),([0,1],8,True,'section'),([0,1],8,12,''),([1],8,12,'section')]:
            with self.subTest(direction=direction,rise=rise,run=run), self.assertRaises(ValueError):
                vault_upper_wall_area(boundary,direction,rise,run,source)
        boundary['points'] = [[100,100],[300,260],[300,100],[100,260]]
        with self.assertRaises(ValueError):
            vault_upper_wall_area(boundary,[0,1],8,12,'section')


if __name__ == '__main__':
    unittest.main()
