import unittest
import fitz
from elevation_gable_pitch import candidates


class GablePitchTests(unittest.TestCase):
    def page(self):
        doc=fitz.open();self.addCleanup(doc.close)
        return doc.new_page(width=400,height=400)

    def gable(self,page,**options):
        page.draw_line((40,100),(100,50),**options)
        page.draw_line((100,50),(160,100),**options)

    def test_visible_pair_retains_source_and_inferred_status(self):
        p=self.page();self.gable(p,color=(.2,.4,.8),width=2)
        result=candidates(p,[20,20,180,120])
        self.assertFalse(result['pitch_certified'])
        self.assertEqual(len(result['candidates']),1)
        row=result['candidates'][0]
        self.assertAlmostEqual(row['rise_per_12'],10)
        self.assertEqual(row['source_cad_paths'],[0,1])
        self.assertEqual(row['page'],1)
        self.assertEqual(row['apex_pt'],[100,50])
        self.assertTrue(row['pitch_is_inferred'])
        self.assertFalse(row['pitch_certified'])
        self.assertNotIn('quantity',row)

    def test_pitch_is_not_rounded_to_a_nominal_specification(self):
        p=self.page()
        p.draw_line((40,100),(100,49.8));p.draw_line((100,49.8),(160,100))
        row=candidates(p,[20,20,180,120])['candidates'][0]
        self.assertAlmostEqual(row['rise_per_12'],10.04,places=5)
        self.assertNotEqual(row['rise_per_12'],10)

    def test_hidden_dashed_and_mismatched_styles_are_not_paired(self):
        for options in ({'stroke_opacity':0},{'dashes':'[3 2] 0'}):
            p=self.page();self.gable(p,**options)
            self.assertEqual(candidates(p,[20,20,180,120])['candidates'],[])
        p=self.page()
        p.draw_line((40,100),(100,50),color=(1,0,0))
        p.draw_line((100,50),(160,100),color=(0,0,1))
        self.assertEqual(candidates(p,[20,20,180,120])['candidates'],[])

    def test_different_slopes_or_disconnected_apex_are_not_paired(self):
        for start,end in (((100,50),(160,105)),((100,51),(160,101))):
            p=self.page();p.draw_line((40,100),(100,50));p.draw_line(start,end)
            self.assertEqual(candidates(p,[20,20,180,120])['candidates'],[])

    def test_view_does_not_clip_edges_or_import_nearby_pitch_label(self):
        p=self.page();self.gable(p);p.insert_text((50,90),'7 : 12')
        self.assertAlmostEqual(candidates(p,[20,20,180,120])['candidates'][0]['rise_per_12'],10)
        self.assertEqual(candidates(p,[60,20,180,120])['candidates'],[])

    def test_parallel_fascia_lines_remain_separate_ambiguous_candidates(self):
        p=self.page();self.gable(p)
        p.draw_line((40,104),(100,54));p.draw_line((100,54),(160,104))
        rows=candidates(p,[20,20,180,120])['candidates']
        self.assertEqual(len(rows),2)
        self.assertTrue(all(not row['pitch_certified'] for row in rows))

    def test_invalid_bounds_are_rejected(self):
        p=self.page()
        for bounds in ([0,0,500,400],[0,0,0,200],[0,0,float('nan'),200],[False,0,200,200],[0,0,200]):
            with self.assertRaises(ValueError):candidates(p,bounds)


if __name__=='__main__':unittest.main()
