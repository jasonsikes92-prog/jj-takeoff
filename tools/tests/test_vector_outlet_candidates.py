import copy
import math
import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vector_outlet_candidates import outlet_shapes,plan_vector_outlets


def draw_outlet(page,x,y,center=False,angle=0):
    page.draw_circle((x,y),10,color=(1,0,0))
    theta=math.radians(angle)
    def point(a,b):return (x+a*math.cos(theta)-b*math.sin(theta),y+a*math.sin(theta)+b*math.cos(theta))
    for a in (-6,6):page.draw_line(point(a,-8),point(a,16),color=(1,0,0))
    if center:page.draw_line(point(0,-18),point(0,10),color=(1,0,0))


class VectorOutlets(unittest.TestCase):
    def setup_plan(self):
        doc=fitz.open();self.addCleanup(doc.close);p=doc.new_page(width=800,height=600)
        draw_outlet(p,40,50);draw_outlet(p,100,50,True)
        draw_outlet(p,200,200,angle=45);draw_outlet(p,300,200,True,90)
        draw_outlet(p,400,200);p.draw_rect((388,187,412,215),color=(1,0,0))
        draw_outlet(p,500,200);p.insert_text((491,220),'GFCI',fontsize=7)
        config={'plan_sha256':'plan','pages':[{'page':1,'ink':'red',
            'exclusions':[{'bbox_pt':[0,0,160,100],'source':'Synthetic legend'}],
            'legends':[{'id':'duplex','label':'Duplex','meaning_source':'Synthetic duplex legend','bbox_pt':[20,25,60,75],'diameter_scale_range':[.5,1.5]},
                       {'id':'220v','label':'220V','meaning_source':'Synthetic 220V legend','bbox_pt':[80,25,120,75],'diameter_scale_range':[.5,1.5]}],
            'qualifying_labels':{'GFCI':{'label':'GFCI','meaning_source':'Synthetic GFCI legend'}}}]}
        return doc,config

    def test_rotation_center_line_and_special_qualifiers_partition_symbols(self):
        doc,config=self.setup_plan();result=plan_vector_outlets(doc,config,'plan')
        groups={m['label']:m for m in result['measurements']}
        self.assertEqual(groups['Duplex']['points'],[[200,200]])
        self.assertEqual(groups['220V']['points'],[[300,200]])
        self.assertEqual(len(result['pages'][0]['qualified_shapes']),2)
        self.assertEqual(result['pages'][0]['field_shapes'],4)
        self.assertEqual(result['pages'][0]['unassigned_shapes'],[])
        self.assertTrue(groups['Duplex']['engine_line_ids']);self.assertFalse(result['coverage_certified'])

    def test_circle_without_bars_and_ellipse_do_not_become_outlets(self):
        with fitz.open() as doc:
            p=doc.new_page();p.draw_circle((40,40),10,color=(1,0,0))
            p.draw_oval((80,30,130,50),color=(1,0,0));p.draw_line((90,20),(90,60),color=(1,0,0))
            p.draw_line((120,20),(120,60),color=(1,0,0))
            self.assertEqual(outlet_shapes(p),[])

    def test_source_validation_and_missing_vector_legend(self):
        doc,config=self.setup_plan()
        with self.assertRaisesRegex(ValueError,'another drawing'):plan_vector_outlets(doc,config,'other')
        for patch in ({'diameter_scale_range':[0,1]},{'diameter_scale_range':[True,1]},
                      {'diameter_scale_range':[1,float('nan')]},{'meaning_source':''},{'bbox_pt':[600,400,650,450]}):
            bad=copy.deepcopy(config);bad['pages'][0]['legends'][0].update(patch)
            with self.subTest(patch=patch),self.assertRaises(ValueError):plan_vector_outlets(doc,bad,'plan')

    def test_ambiguous_legends_are_not_silently_selected(self):
        doc,config=self.setup_plan();other=copy.deepcopy(config['pages'][0]['legends'][0]);other['id']='other'
        config['pages'][0]['legends'].append(other)
        result=plan_vector_outlets(doc,config,'plan')
        self.assertEqual([m['label'] for m in result['measurements']],['220V'])
        self.assertEqual(len(result['pages'][0]['unassigned_shapes']),1)

    def test_ambiguous_special_label_withholds_both_nearby_ordinary_candidates(self):
        doc,config=self.setup_plan();p=doc[0]
        draw_outlet(p,235,200);p.insert_text((210,220),'GFCI',fontsize=7)
        result=plan_vector_outlets(doc,config,'plan')
        self.assertEqual([m['label'] for m in result['measurements']],['220V'])
        self.assertEqual(len(result['pages'][0]['unresolved_labels']),1)
        ambiguous=[s for s in result['pages'][0]['qualified_shapes'] if any(q['type']=='ambiguous_label' for q in s['qualifiers'])]
        self.assertEqual(len(ambiguous),2)


if __name__=='__main__':unittest.main()
