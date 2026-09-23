import copy
import sys
import unittest
from pathlib import Path
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_segment_candidates import candidates, rectangle_bounds


class WallSegmentCandidates(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.addCleanup(self.doc.close)
        self.page=self.doc.new_page(width=600,height=600)

    def rect(self, bounds, fill=(.7,.7,0)):
        self.page.draw_rect(bounds,fill=fill,color=None)

    def test_horizontal_vertical_and_short_pieces_keep_source_geometry(self):
        self.rect((20,20,140,23.5));self.rect((200,20,205.5,140));self.rect((250,20,253.5,23.5))
        result=candidates(self.page,12)
        self.assertEqual((result['length_candidates'],result['short_piece_candidates']),(2,1))
        a,b,c=result['measurements']
        self.assertEqual(a['points'],[[20,21.75],[140,21.75]])
        self.assertEqual(b['points'],[[202.75,20],[202.75,140]])
        self.assertEqual(c['orientation'],'unresolved_short_piece')
        self.assertEqual(c['kind'],'area')
        self.assertEqual(a['source_cad_paths'],[0])
        self.assertEqual(b['drawn_thickness_inches'],5.5)
        self.assertTrue(all(not m['certified'] and not m['dependent_rows'] for m in result['measurements']))

    def test_white_masks_outlines_and_nonwall_widths_are_not_candidates(self):
        self.rect((20,20,140,23.5),fill=(1,1,1))
        self.page.draw_rect((20,30,140,33.5),color=(0,0,0))
        self.rect((20,40,140,41));self.rect((20,50,140,70))
        self.assertEqual(candidates(self.page,12)['measurements'],[])

    def test_identical_geometry_deduplicates_but_keeps_both_source_paths(self):
        self.rect((20,20,140,23.5));self.rect((20,20,140,23.5),fill=(0,0,1))
        found=candidates(self.page,12)['measurements']
        self.assertEqual(len(found),1);self.assertEqual(found[0]['source_cad_paths'],[0,1])

    def test_four_edges_must_reproduce_rectangle_not_a_diagonal_or_retraced_path(self):
        a,b,c,d=[fitz.Point(*p) for p in [(20,20),(140,20),(140,23.5),(20,23.5)]]
        shape={'rect':fitz.Rect(20,20,140,23.5),'items':[('l',a,b),('l',b,c),('l',c,d),('l',d,a)]}
        self.assertEqual(rectangle_bounds(shape),[20,20,140,23.5])
        wrong=copy.deepcopy(shape);wrong['items']=[('l',a,c),('l',c,b),('l',b,d),('l',d,a)]
        self.assertIsNone(rectangle_bounds(wrong))
        wrong['items']=[('l',a,b)]*4
        self.assertIsNone(rectangle_bounds(wrong))

    def test_repeated_extraction_is_stable_and_scale_changes_measured_length(self):
        self.rect((20,20,140,23.5))
        first=candidates(self.page,12)
        self.assertEqual(first,candidates(self.page,12))
        revised=candidates(self.page,14)['measurements'][0]
        self.assertEqual(first['measurements'][0]['id'],revised['id'])
        self.assertEqual(revised['points_per_foot'],14)

    def test_invalid_scale_does_not_create_measurements(self):
        for value in (0,-1,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):candidates(self.page,value)


if __name__=='__main__':unittest.main()
