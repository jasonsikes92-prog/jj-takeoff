import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from arrow_dimension_scale import arrow_dimension_scale
from sheet_scale_labels import scale_labels


class ArrowDimensionScale(unittest.TestCase):
    def page(self,scales=(18,18,18,18),axes=(0,0,1,1),arrows=True,color=(0,0,.5),inward=True,opacity=1):
        doc=fitz.open();self.addCleanup(doc.close);page=doc.new_page(width=600,height=600)
        self.arrow_sets=[]
        for index,(scale,axis) in enumerate(zip(scales,axes)):
            page.insert_text((100+200*(index%2),100+200*(index//2)),"1'-8\"",fontsize=8,
                color=(0,0,.5),rotate=90 if axis else 0)
            line=[line for block in page.get_text('dict')['blocks'] for line in block.get('lines',[])][-1]
            box=line['bbox'];center=(box[axis]+box[axis+2])/2;fixed=box[3-axis]+8
            tips=[]
            for side in (-1,1):
                tip=[0,0];tip[axis]=center+side*(5/3)*scale/2;tip[1-axis]=fixed
                tips.append(tip)
                for wing in (-1,1):
                    tail=tip.copy();tail[axis]-=side*6*(1 if inward else -1);tail[1-axis]+=wing*1.5
                    if arrows:page.draw_line(tip,tail,color=color,width=.5,stroke_opacity=opacity)
            self.arrow_sets.append((tips,axis))
        page.insert_text((30,550),'1/4 in = 1 ft',fontsize=8)
        return page

    def read(self,page,bounds=None):
        bounds=bounds or [0,0,600,600]
        return arrow_dimension_scale(page,bounds,scale_labels(page,bounds))

    def test_four_two_axis_arrow_dimensions_corroborate_printed_scale(self):
        result=self.read(self.page())
        self.assertTrue(result['usable_candidate']);self.assertAlmostEqual(result['points_per_foot'],18)
        self.assertEqual(len(result['controls']),4);self.assertFalse(result['certified'])
        self.assertTrue(all(len(c['cad_paths'])==4 for c in result['controls']))

    def test_labels_without_arrows_wrong_ink_and_outward_arrows_are_not_controls(self):
        for options in ({'arrows':False},{'color':(0,0,0)},{'inward':False},{'opacity':0}):
            with self.subTest(options=options):
                result=self.read(self.page(**options))
                self.assertEqual(result['controls'],[]);self.assertFalse(result['usable_candidate'])

    def test_disagreement_or_insufficient_axes_cannot_calibrate(self):
        for options in ({'scales':(18,18,18,19)},{'scales':(18,18,18)},
                {'axes':(0,0,0,0)},{'axes':(0,0,0,1)},{'scales':(10,10,10,10)}):
            with self.subTest(options=options):
                result=self.read(self.page(**options))
                self.assertFalse(result['usable_candidate']);self.assertIsNone(result['points_per_foot'])

    def test_view_cannot_borrow_missing_controls_or_printed_scale(self):
        page=self.page()
        for bounds in ([0,0,600,200],[0,0,200,600],[0,0,600,400]):
            with self.subTest(bounds=bounds):self.assertFalse(self.read(page,bounds)['usable_candidate'])

    def test_mixed_or_not_to_scale_view_is_not_calibrated(self):
        for label in ('1 in = 1 ft','NOT TO SCALE'):
            page=self.page();page.insert_text((300,550),label,fontsize=8)
            self.assertFalse(self.read(page)['usable_candidate'])

    def test_duplicate_labels_do_not_supply_an_extra_control(self):
        page=self.page(scales=(18,18,18))
        line=[line for block in page.get_text('dict')['blocks'] for line in block.get('lines',[])
            if line['spans'][0]['text']=="1'-8\""][0]
        page.insert_text(line['spans'][0]['origin'],"1'-8\"",fontsize=8,color=(0,0,.5))
        result=self.read(page)
        self.assertEqual(len(result['controls']),3);self.assertFalse(result['usable_candidate'])

    def test_competing_arrow_pairs_remain_ambiguous(self):
        page=self.page();tips,axis=self.arrow_sets[0]
        for side,point in zip((-1,1),tips):
            tip=point.copy();tip[1-axis]+=2
            for wing in (-1,1):
                tail=tip.copy();tail[axis]-=side*6;tail[1-axis]+=wing*1.5
                page.draw_line(tip,tail,color=(0,0,.5),width=.5)
        result=self.read(page)
        self.assertTrue(result['ambiguous_labels']);self.assertFalse(result['usable_candidate'])


if __name__=='__main__':unittest.main()
