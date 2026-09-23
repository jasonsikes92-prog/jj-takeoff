import math
import unittest
from collections import Counter
from shapely.geometry import Polygon
from tools.subfloor_panel_layout import calculate


class SubfloorPanels(unittest.TestCase):
    def check_pieces(self,result):
        ids=result['dedicated_sheet_modules']+[c['piece_id'] for s in result['reuse_sheets'] for c in s['cuts']]
        self.assertEqual(Counter(ids),Counter(p['id'] for p in result['pieces']))
        self.assertGreaterEqual(result['candidate_sheets'],math.ceil(result['gross_surface_sf']/32-1e-9))
        self.assertTrue(all(s['remaining_inches']>=0 for s in result['reuse_sheets']))

    def test_whole_sheet_and_translated_reversed_polygon(self):
        points=[[0,0],[8,0],[8,4],[0,4]];a=calculate(points,1)
        b=calculate([[x+12,y+20] for x,y in reversed(points)],1)
        self.assertEqual(a['candidate_sheets'],1);self.assertEqual(a['gross_surface_sf'],32)
        self.assertEqual(a['candidate_sheets'],b['candidate_sheets'])
        self.assertEqual(a['pieces'][0]['module_bounds_ft'],b['pieces'][0]['module_bounds_ft'])
        self.assertTrue(Polygon(a['pieces'][0]['footprint_polygons_ft'][0]).equals(
            Polygon(b['pieces'][0]['footprint_polygons_ft'][0])))
        self.check_pieces(a)

    def test_unrotated_full_width_reuse_and_kerf(self):
        a=calculate([[0,0],[3,0],[3,8],[0,8]],1)
        self.assertEqual(a['modules_before_reuse'],2);self.assertEqual(a['candidate_sheets'],1)
        self.check_pieces(a)
        b=calculate([[0,0],[4,0],[4,8],[0,8]],1,stagger_inches=48)
        self.assertEqual(b['candidate_sheets'],2);self.check_pieces(b)

    def test_concave_footprint_exact_area_and_no_irregular_reuse(self):
        a=calculate([[0,0],[12,0],[12,4],[4,4],[4,12],[0,12]],1)
        self.assertAlmostEqual(a['gross_surface_sf'],80);self.check_pieces(a)
        for p in a['pieces']:
            if p['full_width_strip_reusable']:
                self.assertEqual(len(p['footprint_polygons_ft']),1)

    def test_narrow_course_sensitivity_has_no_invented_tongue_groove(self):
        a=calculate([[0,0],[3,0],[3,8],[0,8]],1,course_inches=47.5)
        self.assertFalse(a['reuse_sheets']);self.check_pieces(a)

    def test_product_face_width_preserves_full_width_reuse(self):
        height=2*47.5/12
        points=[[0,0],[3,0],[3,height],[0,height]]
        a=calculate(points,1,course_inches=47.5,panel_width_inches=47.5)
        self.assertEqual(a['modules_before_reuse'],2)
        self.assertEqual(a['candidate_sheets'],1)
        self.assertEqual(a['panel_width_inches'],47.5)
        self.assertTrue(all(p['full_width_strip_reusable'] for p in a['pieces']))
        self.check_pieces(a)
        # Ripping a nominal 48-inch panel to the same course cannot claim intact T&G.
        b=calculate(points,1,course_inches=47.5)
        self.assertEqual(b['candidate_sheets'],2)
        with self.assertRaises(ValueError):
            calculate(points,1,course_inches=47.625,panel_width_inches=47.5)

    def test_invalid_geometry_scale_and_modules_rejected(self):
        square=[[0,0],[8,0],[8,4],[0,4]]
        for points in [[[0,0],[8,1],[8,4],[0,4]],[[0,0],[8,4],[8,0],[0,4]]]:
            with self.assertRaises(ValueError):calculate(points,1)
        for values in [{'points_per_foot':0},{'points_per_foot':float('nan')},
                       {'points_per_foot':1,'course_inches':49},{'points_per_foot':1,'stagger_inches':96},
                       {'points_per_foot':1,'panel_width_inches':float('nan')},
                       {'points_per_foot':1,'panel_width_inches':49}]:
            with self.assertRaises(ValueError):calculate(square,**values)


if __name__=='__main__':unittest.main()
