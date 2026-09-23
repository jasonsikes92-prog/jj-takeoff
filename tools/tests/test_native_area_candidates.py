import copy
import unittest
import fitz
from native_area_candidates import registered_scale,filled_regions
from measurement_store import calculate


class NativeAreaCandidates(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.doc.new_page(width=500,height=500);self.doc.new_page(width=500,height=500)
        self.addCleanup(self.doc.close)
        lines=[[(40,y),(440,y)] for y in range(40,441,40)]+[[(x,40),(x,440)] for x in range(40,441,40)]
        for a,b in lines:
            self.doc[0].draw_line(a,b)
            self.doc[1].draw_line(tuple(v*.5+t for v,t in zip(a,[100,200])),tuple(v*.5+t for v,t in zip(b,[100,200])))
        self.cal={'points_per_foot':18,'usable_candidate':True,'controls':[{'axis':'horizontal'},{'axis':'vertical'}]}
        self.anchors=[{'reference':{'path':i,'item':0},'target':{'path':i,'item':0}} for i in [0,11]]
        self.args=[self.doc[0],self.doc[1],self.cal,self.anchors,[0,0,500,500],[80,180,350,450]]

    def test_scale_transfer_uses_broad_two_axis_line_evidence(self):
        result=registered_scale(*self.args)
        self.assertAlmostEqual(result['points_per_foot'],9)
        self.assertEqual(len(result['matched_segments']),22)
        self.assertLess(result['maximum_endpoint_residual_pt'],1e-8)
        self.assertFalse(result['certified'])

    def test_scale_and_anchor_disagreement_are_rejected(self):
        for changes in ({'usable_candidate':False},{'mixed_view_scales':True},{'controls':[{'axis':'horizontal'}]}):
            with self.assertRaises(ValueError):registered_scale(*[self.doc[0],self.doc[1],{**self.cal,**changes},*self.args[3:]])
        with self.assertRaisesRegex(ValueError,'Two-axis'):registered_scale(*self.args[:3],self.anchors[:1],*self.args[4:])
        changed=copy.deepcopy(self.anchors);changed[1]['target']['path']=12
        with self.assertRaises(ValueError):registered_scale(*self.args[:3],changed,*self.args[4:])

    def test_blank_view_margins_do_not_reduce_linework_coverage(self):
        args=[*self.args[:4],[0,0,5000,5000],[0,0,5000,5000]]
        result=registered_scale(*args)
        self.assertAlmostEqual(result['points_per_foot'],9)
        self.assertEqual(result['source_linework_coverage_by_axis'],[1.,1.])

    def test_small_matching_cluster_cannot_register_larger_linework(self):
        self.doc[0].draw_line((40,40),(4400,4400))
        with self.assertRaisesRegex(ValueError,'spatial coverage'):
            registered_scale(*self.args[:4],[0,0,5000,5000],[0,0,5000,5000])

    def triangle(self,page,points,color):
        shape=page.new_shape();shape.draw_polyline(points+[points[0]]);shape.finish(fill=color,color=None);shape.commit()

    def test_union_counts_native_triangles_once_and_excludes_legend(self):
        p=self.doc[1]
        self.triangle(p,[(100,100),(190,100),(190,190)],(0,1,0))
        self.triangle(p,[(100,100),(190,190),(100,190)],(0,1,0))
        self.triangle(p,[(100,100),(190,100),(190,190)],(0,1,0))
        self.triangle(p,[(10,10),(19,10),(19,19)],(0,1,0))
        result=filled_regions(p,[90,90,200,200],[{'fill':[0,1,0],'label':'Heated'}],{'points_per_foot':9})
        self.assertEqual(len(result),1)
        self.assertEqual(calculate(result[0])['quantity'],100)
        self.assertEqual(len(result[0]['source_cad_paths']),3)
        self.assertEqual(result[0]['page'],2)
        self.assertEqual(result[0]['label'],'Heated')

    def test_missing_color_and_cut_view_are_rejected(self):
        p=self.doc[1];self.triangle(p,[(100,100),(190,100),(190,190)],(0,1,0))
        with self.assertRaisesRegex(ValueError,'crosses'):filled_regions(p,[110,90,200,200],[{'fill':[0,1,0],'label':'Heated'}],{'points_per_foot':9})
        with self.assertRaisesRegex(ValueError,'no geometry'):filled_regions(p,[90,90,200,200],[{'fill':[1,0,0],'label':'Garage'}],{'points_per_foot':9})

if __name__=='__main__':unittest.main()
