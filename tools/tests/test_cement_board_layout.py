import unittest
from shapely.geometry import box
from cement_board_layout import calculate, material_allowance


class CementBoardLayoutTests(unittest.TestCase):
    def test_full_row_counts_shared_seam_once(self):
        result=calculate(box(0,0,10,3))
        self.assertEqual(result['candidate_sheets_without_reuse'],2)
        self.assertEqual(result['unique_seam_lf'],3)
        self.assertIsNone(result['purchase_quantity'])

    def test_shower_hole_never_gets_board(self):
        floor=box(0,0,10,9).difference(box(2,2,4,4))
        result=calculate(floor)
        self.assertAlmostEqual(sum(p['installed_sf'] for p in result['pieces']),86)
        self.assertTrue(result['nominal_coverage_verified'])

    def test_cut_piece_not_treated_as_reused_stock(self):
        result=calculate(box(0,0,5.1,3))
        self.assertEqual(result['candidate_sheets_without_reuse'],2)
        self.assertTrue(all(not p['offcut_reuse_assumed'] for p in result['pieces']))
        self.assertFalse(result['installation_gap_layout_verified'])

    def test_full_course_strips_share_stock_without_losing_cuts(self):
        floor=box(0,0,1,3).union(box(6,0,7,3))
        result=material_allowance(calculate(floor))
        self.assertEqual(result['candidate_sheets'],1)
        self.assertEqual(len(result['reused_strip_stock'][0]['cuts']),2)
        self.assertGreater(result['fastener_allowance'],0)
        self.assertFalse(result['order_released'])

    def test_kerf_prevents_two_exact_half_sheets_sharing_stock(self):
        floor=box(0,0,2.5,3).union(box(5,0,7.5,3))
        result=material_allowance(calculate(floor))
        self.assertEqual(result['candidate_sheets'],2)
        self.assertEqual(material_allowance(calculate(floor),kerf_inches=0)['candidate_sheets'],1)
