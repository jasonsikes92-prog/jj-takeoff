import math
from pathlib import Path
import sys
import unittest
from shapely.geometry import box
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_panel_layout import panel_modules,pack_blanks


class RoofPanelTests(unittest.TestCase):
    def face(self,points):
        return {'id':'R','points_per_foot':1,'surface_factor':math.sqrt(2),'points':points}

    def test_slope_area_and_rotation_invariant(self):
        points=[[0,0],[8,0],[8,4/math.sqrt(2)],[0,4/math.sqrt(2)]]
        a=panel_modules(self.face(points),[0,1])
        self.assertAlmostEqual(a['surface_sf'],32)
        b=panel_modules(self.face([[-y+10,x+20] for x,y in points]),[-1,0])
        self.assertAlmostEqual(b['surface_sf'],a['surface_sf'])
        self.assertEqual(len(a['pieces']),len(b['pieces']))
        self.assertEqual(len(a['pieces']),1)

    def test_concave_face_partition_and_stagger(self):
        a=panel_modules(self.face([[0,0],[16,0],[16,3],[7,3],[7,8],[0,8]]),[0,1])
        self.assertAlmostEqual(sum(p['covered_sf'] for p in a['pieces']),a['surface_sf'])
        self.assertLess(a['uncovered_module_sf'],1e-7)
        self.assertTrue(any(p['course']==2 for p in a['pieces']))

    def test_kerf_prevents_two_half_blanks_but_exact_full_sheet_fits(self):
        p=lambda i,w,h:{'id':i,'width_inches':w,'height_inches':h}
        self.assertEqual(len(pack_blanks([p('a',48,48),p('b',48,48)])),2)
        self.assertEqual(len(pack_blanks([p('a',48,48),p('b',47.875,48)])),1)
        self.assertEqual(len(pack_blanks([p('a',96,48)])),1)

    def test_all_blanks_fit_once_without_overlap_or_rotation(self):
        pieces=[{'id':str(i),'width_inches':w,'height_inches':h}
                for i,(w,h) in enumerate([(60,24),(30,24),(20,12),(80,12),(96,8),(10,40)])]
        sheets=pack_blanks(pieces)
        self.assertCountEqual([c['piece_id'] for s in sheets for c in s['cuts']],[p['id'] for p in pieces])
        for sheet in sheets:
            rectangles=[]
            for c in sheet['cuts']:
                r=box(c['x_inches'],c['y_inches'],c['x_inches']+c['width_inches'],c['y_inches']+c['height_inches'])
                self.assertTrue(box(0,0,96,48).covers(r));self.assertFalse(c['rotated'])
                self.assertTrue(all(r.intersection(other).area<1e-8 for other in rectangles))
                rectangles.append(r)

    def test_invalid_geometry_and_oversized_or_duplicate_blank_rejected(self):
        with self.assertRaises(ValueError):panel_modules(self.face([[0,0],[3,3],[0,3],[3,0]]),[0,1])
        with self.assertRaises(ValueError):panel_modules(self.face([[0,0],[3,0],[3,3]]),[0,.5])
        for w,h in [(97,48),(48,96),(0,1),(float('nan'),1)]:
            with self.assertRaises(ValueError):pack_blanks([{'id':'a','width_inches':w,'height_inches':h}])
        p={'id':'a','width_inches':20,'height_inches':20}
        with self.assertRaises(ValueError):pack_blanks([p,p])


if __name__=='__main__':unittest.main()
