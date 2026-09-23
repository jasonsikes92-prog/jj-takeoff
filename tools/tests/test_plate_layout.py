import unittest
from tools.plate_layout import layout, stock_study


class PlateLayoutTests(unittest.TestCase):
    def test_each_layer_covers_run_without_gaps(self):
        for length in [5.5, 96, 192, 193.5, 401.17, 900]:
            rows = layout('wall', length)
            for layer in ['top_lower', 'top_upper', 'bottom']:
                pieces = [p for p in rows if p['layer'] == layer]
                self.assertEqual(pieces[0]['from_inches'], 0)
                self.assertEqual(pieces[-1]['to_inches'], length)
                self.assertTrue(all(a['to_inches'] == b['from_inches'] for a,b in zip(pieces,pieces[1:])))
                self.assertTrue(all(p['cut_inches'] <= 192 for p in pieces))

    def test_top_joints_are_staggered(self):
        rows = layout('wall', 900)
        lower = [p['to_inches'] for p in rows if p['layer'] == 'top_lower' and p['to_inches'] < 900]
        upper = [p['to_inches'] for p in rows if p['layer'] == 'top_upper' and p['to_inches'] < 900]
        self.assertGreaterEqual(min(abs(a-b) for a in lower for b in upper), 24)

    def test_rejects_joint_spacing_below_reference(self):
        with self.assertRaises(ValueError):
            layout('wall', 400, stagger_inches=12)

    def test_lengths_round_up_to_eighth(self):
        self.assertEqual(layout('wall', 20.01)[0]['cut_inches'], 20.125)

    def test_rejects_nonfinite_and_nonincrement_stock(self):
        for value in [float('nan'), float('inf'), True, -1, 0]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                layout('wall', value)
        with self.assertRaises(ValueError):
            layout('wall', 400, stock_inches=191.99)

    def test_stock_preserves_material_groups_and_all_three_layers(self):
        result = stock_study([{'id':'wall', 'length_inches':96}], {'top':'T', 'bottom':'B'})
        self.assertEqual(result['summary']['three_layer_net_lf'], 24)
        self.assertEqual(len(result['pieces']), 3)
        self.assertEqual(len(result['boards']), 3)  # Two halves cannot share a board with saw kerf.
        self.assertEqual(result['summary']['stock_by_material_group'], {'T':2, 'B':1})
        self.assertIsNone(result['purchase_quantity'])
        self.assertFalse(result['price_applied'])

    def test_changed_length_recalculates_cuts_and_stock(self):
        groups = {'top':'T', 'bottom':'B'}
        before = stock_study([{'id':'wall', 'length_inches':50}], groups)
        after = stock_study([{'id':'wall', 'length_inches':400}], groups)
        self.assertGreater(after['summary']['candidate_whole_sticks'], before['summary']['candidate_whole_sticks'])
        for b in after['boards']:
            self.assertAlmostEqual(sum(c['consumed_inches'] for c in b['cuts']) + b['remaining_inches'], 192)

    def test_rejects_duplicate_runs_and_merged_material_groups(self):
        run = {'id':'wall', 'length_inches':50}
        with self.assertRaises(ValueError):
            stock_study([run, run], {'top':'T', 'bottom':'B'})
        with self.assertRaises(ValueError):
            stock_study([run], {'top':'T', 'bottom':'T'})
