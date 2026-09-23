import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup


class ProjectionContainment(unittest.TestCase):
    def setUp(self):
        outer={'id':'house','kind':'area','page':1,'width_pt':500,'height_pt':500,
               'points_per_foot':10,'points':[[0,0],[100,0],[100,100],[0,100]]}
        inner={**outer,'id':'vault','points':[[0,0],[40,0],[40,50],[0,50]],'surface_factor':1.25}
        self.state={'version':1,'plan_sha256':'test','measurements':{'house':outer,'vault':inner}}
        self.rule={'id':'ceiling','label':'Ceiling insulation','measurement_ids':['house','vault'],
            'unit':'SF','rounding':'whole_up','template_rows':['218'],'use':'template_quantity',
            'basis':'Synthetic horizontal and sloped ceiling fixture','remaining':['Product assembly remains separate'],
            'contained_projections':[{'parent':'house','child':'vault'}],
            'surface_components':[{'id':'gross','measurement_id':'house','kind':'projected_area','operation':'add'},
                {'id':'flat-deduction','measurement_id':'vault','kind':'projected_area','operation':'deduct'},
                {'id':'vault-slope','measurement_id':'vault','kind':'area','operation':'add'}]}
    def result(self):return rollup(self.state,{'plan_sha256':'test','rules':[self.rule]})

    def test_shared_edges_and_distinct_slopes_use_projection_once(self):
        result=self.result();self.assertEqual(result['pending_quantities'],[])
        self.assertEqual(result['quantities'][0]['quantity'],105)

    def test_same_size_vault_outside_withholds_quantity(self):
        points=copy.deepcopy(self.state['measurements']['vault']['points'])
        for dx,dy in ((80,0),(0,80)):
            with self.subTest(dx=dx,dy=dy):
                self.state['measurements']['vault']['points']=[[x+dx,y+dy] for x,y in points]
                result=self.result();self.assertEqual(result['quantities'],[])
                self.assertEqual(len(result['pending_quantities'][0]['containment_issues']),1)

    def test_frame_mismatch_is_pending(self):
        original=copy.deepcopy(self.state['measurements']['vault'])
        for field,value in [('page',2),('points_per_foot',20),('width_pt',600),('height_pt',600)]:
            with self.subTest(field=field):
                self.state['measurements']['vault']={**original,field:value}
                self.assertEqual(self.result()['quantities'],[])

    def test_invalid_relationships_are_rejected(self):
        for relation in ([],[{'parent':'house','child':'missing'}],[{'parent':'house','child':'house'}],
                         [{'parent':'house','child':'vault'}]*2,[{'parent':'house'}]):
            with self.subTest(relation=relation):
                self.rule['contained_projections']=relation
                with self.assertRaises(ValueError):self.result()

    def test_contained_resize_updates_flat_and_sloped_surfaces(self):
        self.state['measurements']['vault']['points']=[[0,0],[40,0],[40,40],[0,40]]
        q=self.result()['quantities'][0]
        self.assertTrue(math.isclose(q['measured_quantity'],104))
        self.assertEqual(q['quantity'],104)


if __name__=='__main__':unittest.main()
