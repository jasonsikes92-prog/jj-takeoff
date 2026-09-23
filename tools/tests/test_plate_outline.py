import copy
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
               str(Path(__file__).resolve().parents[1] / 'viewer')]
from measurement_store import calculate
from plate_stock_review import outline_runs


class PlateOutlineTests(unittest.TestCase):
    def setUp(self):
        self.original = {'id':'outline', 'kind':'area', 'page':5,
            'points':[[10,10],[110,10],[110,90],[10,90]],
            'width_pt':300, 'height_pt':300, 'points_per_foot':10}
        self.ids = ['N','E','S','W']

    def runs(self, measurement):
        calculate(measurement)
        return outline_runs(measurement, self.original, self.ids, 'source')

    def test_uses_perimeter_not_enclosed_area(self):
        runs = self.runs(self.original)
        self.assertEqual([r['length_inches'] for r in runs], [120,96,120,96])
        self.assertEqual(sum(r['length_inches'] for r in runs)/12, 36)
        self.assertEqual(calculate(self.original)['quantity'], 80)

    def test_wall_move_updates_both_adjoining_runs(self):
        edited = copy.deepcopy(self.original)
        edited['points'][1][0] += 20
        edited['points'][2][0] += 20
        runs = self.runs(edited)
        self.assertEqual([r['length_inches'] for r in runs], [144,96,144,96])
        self.assertEqual([r['id'] for r in runs], self.ids)

    def test_added_corner_requires_new_edge_mapping(self):
        edited = copy.deepcopy(self.original)
        edited['points'].insert(1,[60,10])
        with self.assertRaisesRegex(ValueError, 'topology'):
            self.runs(edited)

    def test_bent_wall_requires_review(self):
        edited = copy.deepcopy(self.original)
        edited['points'][1][0] += 5
        with self.assertRaisesRegex(ValueError, 'direction'):
            self.runs(edited)

    def test_reversed_outline_cannot_silently_reassign_runs(self):
        edited = copy.deepcopy(self.original)
        edited['points'].reverse()
        with self.assertRaisesRegex(ValueError, 'direction'):
            self.runs(edited)

    def test_self_crossing_outline_rejected(self):
        edited = copy.deepcopy(self.original)
        edited['points'][1],edited['points'][2] = edited['points'][2],edited['points'][1]
        with self.assertRaises(ValueError):
            self.runs(edited)

    def test_duplicate_edge_identity_rejected(self):
        self.ids[-1] = 'N'
        with self.assertRaisesRegex(ValueError, 'topology'):
            self.runs(self.original)
