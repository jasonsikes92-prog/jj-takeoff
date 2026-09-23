import sys
import unittest
from pathlib import Path
import fitz
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dimension_scale import split_dimension_scale


class DimensionScale(unittest.TestCase):
    def make_page(self,scales=(16.67,16.67,16.67),vertical=True,filled_arrows=False,witnesses=True):
        doc=fitz.open();self.addCleanup(doc.close);p=doc.new_page(width=1000,height=1000)
        specs=[('10\'-6 1/2"',10+6.5/12,(250,100),0),
               ('20\'-4 3/4"',20+4.75/12,(250,220),0),
               ('15\'-0"',15,(700,400),90 if vertical else 0)]
        for (text,feet,location,rotation),scale in zip(specs,scales):
            p.insert_text(location,text,fontsize=10,rotate=rotation)
            line=[l for b in p.get_text('dict')['blocks'] for l in b.get('lines',[])
                  if ''.join(s['text'] for s in l['spans'])==text][-1]
            axis=1 if rotation else 0;box=line['bbox'];lo,hi=box[axis],box[axis+2]
            fixed=(box[1-axis]+box[3-axis])/2;center=(lo+hi)/2
            for a,b in [(center-feet*scale/2,lo-2),(hi+2,center+feet*scale/2)]:
                if filled_arrows:
                    tip=a if a<lo else b;sign=1 if a<lo else -1
                    coords=[(tip,fixed),(tip+sign*7,fixed-1.2),(tip+sign*6,fixed),(tip+sign*7,fixed+1.2)]
                    if axis:coords=[(y,x) for x,y in coords]
                    p.draw_polyline(coords,color=None,fill=(.2,.4,.6),closePath=True)
                    if witnesses:
                        ends=[(tip,fixed-5),(tip,fixed+15)]
                        if axis:ends=[(y,x) for x,y in ends]
                        p.draw_line(*ends,color=(.2,.4,.6))
                    if a<lo:a=tip+6
                    else:b=tip-6
                points=[(a,fixed),(b,fixed)] if axis==0 else [(fixed,a),(fixed,b)]
                p.draw_line(*points,color=(.2,.4,.6))
        return p

    def test_filled_arrow_tips_at_witness_lines_recover_both_axes(self):
        r=split_dimension_scale(self.make_page(filled_arrows=True))
        self.assertTrue(r['usable_candidate'])
        self.assertAlmostEqual(r['points_per_foot'],16.67,places=4)
        self.assertTrue(all(c['endpoint_method']=='filled_arrow_tips_at_witness_lines' for c in r['controls']))

    def test_filled_arrows_without_witness_lines_do_not_supply_dimensions(self):
        r=split_dimension_scale(self.make_page(filled_arrows=True,witnesses=False))
        self.assertFalse(r['usable_candidate'])
        self.assertIsNone(r['points_per_foot'])

    def test_ambiguous_arrows_or_invisible_witnesses_are_not_used(self):
        for defect in ('duplicate_arrow','invisible_witness'):
            with self.subTest(defect=defect):
                page=self.make_page(filled_arrows=True);drawings=page.get_drawings()
                if defect=='duplicate_arrow':
                    drawings += [d for d in drawings if d['type']=='f']
                else:
                    for d in drawings:
                        if d['type']=='s' and abs(max(d['rect'].width,d['rect'].height)-20)<.01:
                            d['stroke_opacity']=0
                with patch.object(page,'get_drawings',return_value=drawings):
                    r=split_dimension_scale(page)
                self.assertFalse(r['usable_candidate'])

    def test_filled_arrows_keep_scale_disagreement_and_view_limits(self):
        self.assertFalse(split_dimension_scale(self.make_page(scales=(16,16,32),filled_arrows=True))['usable_candidate'])
        r=split_dimension_scale(self.make_page(filled_arrows=True),[0,0,600,900])
        self.assertFalse(r['usable_candidate'])
        self.assertEqual(len(r['controls']),2)

    def test_fractional_labels_and_split_lines_recover_nonstandard_scale(self):
        r=split_dimension_scale(self.make_page())
        self.assertTrue(r['usable_candidate']);self.assertAlmostEqual(r['points_per_foot'],16.67,places=4)
        self.assertEqual(r['agreeing_controls'],3)
        self.assertFalse(r['certified'])
        self.assertAlmostEqual(r['controls'][0]['feet'],10+6.5/12)

    def test_disagreeing_scales_and_single_axis_do_not_auto_select(self):
        self.assertFalse(split_dimension_scale(self.make_page(scales=(16,16,32)))['usable_candidate'])
        self.assertFalse(split_dimension_scale(self.make_page(vertical=False))['usable_candidate'])

    def test_empty_page_has_no_invented_scale(self):
        doc=fitz.open();self.addCleanup(doc.close)
        self.assertIsNone(split_dimension_scale(doc.new_page())['points_per_foot'])

    def test_view_excludes_other_axis_and_does_not_borrow_outside_controls(self):
        result=split_dimension_scale(self.make_page(),[0,0,600,900])
        self.assertFalse(result['usable_candidate'])
        self.assertEqual(len(result['controls']),2)
        self.assertEqual({c['axis'] for c in result['controls']},{'horizontal'})

if __name__=='__main__':unittest.main()
