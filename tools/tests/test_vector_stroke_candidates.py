import copy
import math
import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vector_stroke_candidates import plan_stroke_candidates


def draw_symbol(page,x,y,scale=1,angle=0,reverse=False,incomplete=False):
    angle=math.radians(angle)
    def point(a,b):return (x+scale*(a*math.cos(angle)-b*math.sin(angle)),y+scale*(a*math.sin(angle)+b*math.cos(angle)))
    a,b=point(0,-20),point(0,20)
    page.draw_line(b if reverse else a,a if reverse else b,color=(1,0,0))
    shape=page.new_shape()
    shape.draw_polyline([point(*p) for p in [(6,-12),(0,-16),(-6,-12),(-6,-6),(0,0),(6,6),(6,12),(0,16),(-6,12)]][:(4 if incomplete else 9)])
    shape.finish(color=(1,0,0));shape.commit()


class VectorStrokes(unittest.TestCase):
    def setup_plan(self):
        doc=fitz.open();self.addCleanup(doc.close);p=doc.new_page(width=500,height=500)
        draw_symbol(p,50,50)
        c={'plan_sha256':'plan','pages':[{'page':1,'id':'switch','label':'Ordinary switch','meaning_source':'Synthetic legend',
            'bbox_pt':[35,25,65,75],'ink':'red','scale_range':[.4,.6],'maximum_error_ratio':.02,
            'exclusions':[{'bbox_pt':[20,20,80,80],'source':'Synthetic legend'}],
            'qualifying_labels':{'3':{'label':'Three way','meaning_source':'Synthetic qualifier'}}}]}
        return doc,c

    def test_rotated_reversed_and_clustered_symbols_with_qualifier(self):
        doc,c=self.setup_plan();p=doc[0]
        draw_symbol(p,200,200,.5,45,True);draw_symbol(p,220,200,.5,90)
        draw_symbol(p,350,300,.5);draw_symbol(p,360,300,.5)
        p.insert_text((348,319),'3',fontsize=6)
        r=plan_stroke_candidates(doc,c,'plan');self.assertEqual(r['pages'][0]['matched_shapes'],4)
        self.assertEqual(len(r['measurements'][0]['points']),3)
        self.assertEqual(len(r['pages'][0]['qualified_shapes']),1);self.assertEqual(r['pages'][0]['unresolved_labels'],[])
        self.assertTrue(r['measurements'][0]['source_shapes'][0]['support_path_sequence_numbers'])
        self.assertFalse(r['coverage_certified']);self.assertFalse(r['estimate_released'])

    def test_missing_strokes_and_plain_lines_are_not_symbols(self):
        doc,c=self.setup_plan();p=doc[0]
        draw_symbol(p,200,200,.5,incomplete=True);p.draw_line((300,190),(300,210),color=(1,0,0))
        self.assertEqual(plan_stroke_candidates(doc,c,'plan')['measurements'],[])

    def test_tied_label_withholds_both_symbols(self):
        doc,c=self.setup_plan();p=doc[0]
        draw_symbol(p,300,300,.5);draw_symbol(p,310,300,.5)
        p.insert_text((303.332,319),'3',fontsize=6)
        r=plan_stroke_candidates(doc,c,'plan');self.assertEqual(r['measurements'],[])
        self.assertEqual(len(r['pages'][0]['qualified_shapes']),2);self.assertEqual(len(r['pages'][0]['unresolved_labels']),1)

    def test_wrong_source_invalid_settings_and_missing_legend(self):
        doc,c=self.setup_plan()
        with self.assertRaisesRegex(ValueError,'another drawing'):plan_stroke_candidates(doc,c,'other')
        for change in ({'scale_range':[0,1]},{'maximum_error_ratio':float('nan')},
                       {'bbox_pt':[400,400,450,450]},{'meaning_source':''}):
            bad=copy.deepcopy(c);bad['pages'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):plan_stroke_candidates(doc,bad,'plan')


if __name__=='__main__':unittest.main()
