import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_panel_layout import wall_modules
from roof_panel_layout import pack_blanks


class WallPanels(unittest.TestCase):
    def test_nine_foot_wall_has_top_course_and_exact_coverage(self):
        face=wall_modules('W',[[0,0],[8,0],[8,9],[0,9]])
        self.assertEqual(face['surface_sf'],72)
        self.assertEqual(sorted((p['width_inches'],p['height_inches']) for p in face['pieces']),
                         [(12,48),(12,48),(96,48),(96,48)])
        self.assertEqual(sum(p['covered_sf'] for p in face['pieces']),72)
        self.assertEqual(len(pack_blanks(face['pieces'])),3)

    def test_exact_stock_and_translation_do_not_add_panels(self):
        points=[[0,0],[4,0],[4,8],[0,8]];before=copy.deepcopy(points)
        a=wall_modules('W',points)
        b=wall_modules('W',[[x+100,y-80] for x,y in points])
        self.assertEqual(points,before)
        self.assertEqual(len(a['pieces']),1)
        self.assertEqual(pack_blanks(a['pieces']),pack_blanks(b['pieces']))

    def test_gable_clipping_does_not_bill_its_bounding_rectangle(self):
        face=wall_modules('G',[[0,0],[8,0],[4,4]])
        self.assertEqual(face['surface_sf'],16)
        self.assertEqual(sum(p['covered_sf'] for p in face['pieces']),16)
        self.assertEqual(len(face['pieces']),2)

    def test_changed_height_recomputes_blanks_without_mutating_original(self):
        a=wall_modules('W',[[0,0],[4,0],[4,8],[0,8]])
        b=wall_modules('W',[[0,0],[4,0],[4,10],[0,10]])
        self.assertEqual(a['surface_sf'],32)
        self.assertEqual(b['surface_sf'],40)
        self.assertEqual(len(pack_blanks(b['pieces'])),2)

    def test_invalid_faces_rejected(self):
        for points in [[[0,0],[4,4],[0,4],[4,0]],[[0,0],[0,0],[0,0]],
                       [[0,0],[4,0],[4,math.inf]],[[0,0],[4,0],[4,True]]]:
            with self.subTest(points=points),self.assertRaises(ValueError):wall_modules('W',points)

    def test_sloping_chase_face_matches_trapezoid_without_reflection_loss(self):
        a=wall_modules('C',[[0,0],[6,4],[6,7],[0,7]])
        b=wall_modules('C',[[0,4],[6,0],[6,7],[0,7]])
        self.assertEqual(a['surface_sf'],30)
        self.assertEqual(b['surface_sf'],30)
        self.assertAlmostEqual(sum(p['covered_sf'] for p in a['pieces']),30)
        self.assertAlmostEqual(sum(p['covered_sf'] for p in b['pieces']),30)

    def test_multiple_faces_keep_piece_ids_and_stock_coverage_separate(self):
        a=wall_modules('G1',[[0,0],[8,0],[4,4]])
        b=wall_modules('G2',[[0,0],[8,0],[4,4]])
        pieces=a['pieces']+b['pieces'];sheets=pack_blanks(pieces)
        self.assertEqual({c['piece_id'] for s in sheets for c in s['cuts']},{p['id'] for p in pieces})
        with self.assertRaisesRegex(ValueError,'Unique'):pack_blanks(a['pieces']+a['pieces'])
