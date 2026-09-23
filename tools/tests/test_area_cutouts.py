import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_cutout_candidates import component_candidates
from measurement_quantities import geometry_digest,rollup


class AreaCutouts(unittest.TestCase):
    def setUp(self):
        self.face={'page':1,'points':[[20,20],[220,20],[220,220],[20,220]],
            'holes':[[[40,40],[60,40],[60,60],[40,60]],[[120,120],[140,120],[140,140],[120,140]]],
            'pitch_candidate':{'text':'9 : 12','rise':9,'point_pt':[80,80]},'source_cad_paths':[3,4]}
        self.components=component_candidates(self.face,10,500,500)
        self.ids=[m['id'] for m in self.components['measurements']]
        self.state={'plan_sha256':'test','version':1,
            'measurements':{m['id']:copy.deepcopy(m) for m in self.components['measurements']}}
        self.rule={'id':'roof','label':'Roof net candidate','measurement_ids':self.ids,
            'unit':'SF','rounding':'none','use':'assembly_input','template_rows':['100'],
            'basis':'Synthetic source fixture','remaining':['Roof scope'],'defer_pending_scope':True,
            'surface_components':self.components['surface_components']}
        self.rules={'plan_sha256':'test','rules':[self.rule]};self.review()

    def review(self):
        self.rule['geometry_reviews']={identity:{'decision':'approved_for_draft',
            'geometry_sha256':geometry_digest(m),'scope':'Synthetic cutout arithmetic fixture'}
            for identity,m in self.state['measurements'].items()}

    def test_gross_deductions_and_net_apply_slope_once(self):
        value=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(value['surface_assembly']['gross_sf'],500)
        self.assertEqual(value['surface_assembly']['deductions_sf'],10)
        self.assertEqual(value['quantity'],490)
        self.assertFalse(value['order_released']);self.assertFalse(self.components['scope_certified'])
        self.assertEqual(len({m['color'] for m in self.state['measurements'].values()}),3)

    def test_cutout_edit_invalidates_review_then_recalculates(self):
        self.state['measurements'][self.ids[1]]['points']=[[40,40],[80,40],[80,60],[40,60]]
        result=rollup(self.state,self.rules)
        self.assertEqual(result['quantities'],[])
        self.assertEqual(result['pending_quantities'][0]['unreviewed_measurement_ids'],[self.ids[1]])
        self.review()
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],485)

    def test_outside_touching_and_overlapping_cutouts_are_pending_even_after_scope_review(self):
        for points in ([[230,30],[250,30],[250,50],[230,50]],
                [[20,40],[40,40],[40,60],[20,60]],
                [[110,110],[150,110],[150,150],[110,150]],
                [[100,100],[120,100],[120,120],[100,120]]):
            with self.subTest(points=points):
                self.state['measurements'][self.ids[1]]['points']=points;self.review()
                result=rollup(self.state,self.rules)
                self.assertEqual(result['quantities'],[])
                self.assertTrue(result['pending_quantities'][0]['cutout_issues'])

    def test_mismatched_scale_page_and_slope_cannot_be_subtracted(self):
        original=copy.deepcopy(self.state['measurements'][self.ids[1]])
        for field,value in [('page',2),('points_per_foot',20),('surface_factor',1.5),('width_pt',600)]:
            with self.subTest(field=field):
                self.state['measurements'][self.ids[1]]={**original,field:value};self.review()
                self.assertTrue(rollup(self.state,self.rules)['pending_quantities'][0]['cutout_issues'])

    def test_invalid_parent_duplicate_deduction_and_wrong_operation_are_rejected(self):
        for mode in ('missing','self','duplicate','add'):
            rules=copy.deepcopy(self.rules);terms=rules['rules'][0]['surface_components']
            if mode=='missing':terms[1]['cutout_of']='missing'
            elif mode=='self':terms[1]['cutout_of']=self.ids[1]
            elif mode=='duplicate':terms.append({**terms[1],'id':'duplicate'})
            else:terms[1]['operation']='add'
            with self.subTest(mode=mode),self.assertRaises(ValueError):rollup(self.state,rules)

    def test_source_geometry_change_changes_identity_and_invalid_source_rings_fail(self):
        altered=copy.deepcopy(self.face);altered['holes'][0][0][0]+=1
        other=component_candidates(altered,10,500,500)
        self.assertNotEqual(other['source_complex_face_sha256'],self.components['source_complex_face_sha256'])
        for holes in ([],[self.face['holes'][0],self.face['holes'][0]],
                [[[230,30],[250,30],[250,50],[230,50]]]):
            with self.subTest(holes=holes),self.assertRaises(ValueError):
                component_candidates({**self.face,'holes':holes},10,500,500)


if __name__=='__main__':unittest.main()
