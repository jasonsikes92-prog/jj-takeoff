import unittest
from above_opening_stock import calculate


class UpperOpeningStockTests(unittest.TestCase):
    def setUp(self):
        self.field = {'points_per_foot': 12, 'field_studs': [],
            'reserved_stations': [{'id': f'S{i}', 'run': 'R1', 'along_pt': x,
                'point_pt': [x, 0], 'assembly_owners': ['D1']} for i, x in enumerate([0, 16, 32, 48])],
            'zones': [{'assembly': 'D1', 'run': 'R1'}]}
        self.openings = [{'id': 'D1', 'points': [[0, 0], [36, 0]],
            'wall_top_inches': 109.125, 'minimum_head_inches': 80, 'header_depth_inches': 5.5}]
        self.stock = {'sku': 'precut', 'length_inches': 104.625}

    def test_height_bound_and_station_ownership(self):
        result = calculate(self.field, self.openings, self.stock)
        self.assertEqual(result['member_count'], 2)
        self.assertEqual(result['candidate_whole_sticks'], 1)
        self.assertEqual([p['cut_inches'] for p in result['pieces']], [20.625, 20.625])
        self.assertFalse(result['installed_cut_lengths_verified'])

    def test_width_edit_recalculates_and_higher_head_reduces_cut(self):
        self.openings[0]['points'][1][0] = 60
        self.openings[0]['minimum_head_inches'] = 82.5
        result = calculate(self.field, self.openings, self.stock)
        self.assertEqual(result['member_count'], 3)
        self.assertEqual(result['pieces'][0]['cut_inches'], 18.125)

    def test_shared_station_is_pending_not_double_counted(self):
        self.field['reserved_stations'][1]['assembly_owners'].append('corner')
        result = calculate(self.field, self.openings, self.stock)
        self.assertEqual(result['member_count'], 1)
        self.assertEqual(len(result['pending']), 1)

    def test_nonpositive_gap_and_bad_geometry_withheld(self):
        self.openings[0]['header_depth_inches'] = 30
        self.assertEqual(len(calculate(self.field, self.openings, self.stock)['pending']), 1)
        self.openings[0]['points'][1][1] = 1
        with self.assertRaises(ValueError):
            calculate(self.field, self.openings, self.stock)

    def test_duplicate_opening_and_oversized_piece_rejected(self):
        with self.assertRaises(ValueError):
            calculate(self.field, self.openings * 2, self.stock)
        self.stock['length_inches'] = 10
        with self.assertRaises(ValueError):
            calculate(self.field, self.openings, self.stock)


if __name__ == '__main__':
    unittest.main()
