import unittest
from tools.panel_cut_stock import allocate


class PanelCuts(unittest.TestCase):
    def test_reuse_and_kerf_prevent_false_exact_fit(self):
        parts = [{'id': 'A', 'width': 30, 'height': 36}, {'id': 'B', 'width': 30, 'height': 36}]
        self.assertEqual(allocate(parts, 60, 36, 0)['sheet_count'], 1)
        self.assertEqual(allocate(parts, 60, 36, .125)['sheet_count'], 2)
        parts[1]['width'] = 29.875
        self.assertEqual(allocate(parts, 60, 36, .125)['sheet_count'], 1)

    def test_rotation_must_be_allowed_and_oversize_rejected(self):
        parts = [{'id': 'A', 'width': 36, 'height': 60}]
        with self.assertRaises(ValueError):allocate(parts, 60, 36, .125)
        self.assertTrue(allocate(parts, 60, 36, .125, True)['placements'][0]['rotated'])
        with self.assertRaises(ValueError):allocate([{'id': 'X', 'width': 61, 'height': 37}], 60, 36, 0, True)

    def test_every_cut_once_in_bounds_and_separated(self):
        parts = [{'id': str(i), 'width': 7+i, 'height': 13+i%4} for i in range(25)]
        result = allocate(parts, 60, 36, .125, True)
        self.assertEqual({p['id'] for p in result['placements']}, {p['id'] for p in parts})
        self.assertEqual(len(result['placements']), len(parts))
        for i, p in enumerate(result['placements']):
            x, y, r, t = p['bounds']
            self.assertTrue(0 <= x < r <= 60 and 0 <= y < t <= 36)
            for q in result['placements'][i+1:]:
                if p['sheet'] != q['sheet']:continue
                a, b, c, d = q['bounds']
                self.assertTrue(r+.125 <= a+1e-8 or c+.125 <= x+1e-8 or t+.125 <= b+1e-8 or d+.125 <= y+1e-8)

    def test_invalid_sizes_and_duplicate_identity(self):
        with self.assertRaises(ValueError):allocate([{'id': 'A', 'width': float('nan'), 'height': 3}], 60, 36, 0)
        with self.assertRaises(ValueError):allocate([{'id': 'A', 'width': 1, 'height': 1}]*2, 60, 36, 0)


if __name__ == '__main__':unittest.main()
