import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from baseboard_geometry import baseboard_runs


def measurement(identity, points, kind='area'):
    return {'id': identity, 'kind': kind, 'page': 1, 'points_per_foot': 12,
            'points': [[x+100,y+100] for x,y in points], 'surface_factor': 1,
            'width_pt': 1000, 'height_pt': 1000}


class BaseboardGeometryTests(unittest.TestCase):
    def setUp(self):
        self.state = {'plan_sha256': 'same', 'version': 1, 'measurements': {
            'room': measurement('room', [[0, 0], [120, 0], [120, 120], [0, 120]]),
            'door': measurement('door', [[36, -2], [72, -2]], 'length')}}
        self.cuts = {'plan_sha256': 'same', 'version': 1, 'measurements': {}}
        self.passages = [{'measurement_id': 'door', 'sides': [{'side': -1, 'room_id': None},
                                                               {'side': 1, 'room_id': 'room'}]}]

    def run_geometry(self):
        return baseboard_runs(self.state, ['room'], self.passages, .5, self.cuts, list(self.cuts['measurements']))

    def test_finish_offset_and_three_foot_door(self):
        result = self.run_geometry()
        self.assertAlmostEqual(result['remaining_wall_run_lf'], 4 * (10 - 1/12) - 3)
        self.assertEqual(result['rooms'][0]['door_gap_lf'], 3)
        self.assertIsNone(result['purchase_quantity'])

    def test_cabinet_overlap_and_door_union(self):
        # Two overlapping bases cover x=0..84 inches on the top wall and 24 inches of the side.
        # The three-foot door was already removed; it must not be deducted a second time.
        for identity, x0, x1 in [('a', 0, 60), ('b', 48, 84)]:
            self.cuts['measurements'][identity] = measurement(identity, [[x0,0],[x1,0],[x1,24],[x0,24]])
        result = self.run_geometry()['rooms'][0]
        self.assertAlmostEqual(result['fixed_footprint_lf'], (83.5 + 23.5) / 12 - 3)
        self.assertAlmostEqual(result['remaining_wall_run_lf'], 4 * (10 - 1/12) - 107/12)

    def test_freestanding_island_does_not_add_or_remove_wall_base(self):
        before = self.run_geometry()['remaining_wall_run_lf']
        self.cuts['measurements']['island'] = measurement('island', [[36,36],[60,36],[60,72],[36,72]])
        self.assertEqual(before, self.run_geometry()['remaining_wall_run_lf'])

    def test_bad_plan_scale_and_door_adjacency(self):
        original = copy.deepcopy(self.state)
        self.cuts['plan_sha256'] = 'different'
        with self.assertRaises(ValueError): self.run_geometry()
        self.cuts['plan_sha256'] = 'same'
        self.state['measurements']['door']['points_per_foot'] = 24
        with self.assertRaises(ValueError): self.run_geometry()
        self.state = original
        self.state['measurements']['door']['points'] = [[136, 80], [172, 80]]
        with self.assertRaises(ValueError): self.run_geometry()


if __name__ == '__main__': unittest.main()
