import copy
import unittest
import test_area_overlap
from test_area_overlap import box
from measurement_quantities import rollup


class MixedSurfaceOverlapTests(unittest.TestCase):
    def setUp(self):
        self.state,self.rules=test_area_overlap.AreaOverlapTests().fixture()
        self.rule=self.rules['rules'][0]
        self.rule.pop('disjoint_areas')
        self.rule['disjoint_area_components']=True
        self.rule['surface_components']=[{'id':i,'measurement_id':i,'kind':'area','operation':'add'} for i in ['a','b']]
        self.state['measurements']['width']={**self.state['measurements']['a'],'id':'width','kind':'length','points':[[0,0],[30,0]]}
        self.rule['measurement_ids'].append('width')
        self.rule['surface_components'].extend({'id':i,'measurement_id':'width','kind':'length_wall',
            'height_ft':8,'height_source':'Reviewed distinct return faces','operation':'add'} for i in ['return-left','return-right'])

    def test_shared_dimensions_do_not_duplicate_area(self):
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],248)

    def test_overlap_withholds_and_correction_recovers(self):
        self.state['measurements']['b']['points']=box(90,0,100,100)
        result=rollup(self.state,self.rules)
        self.assertEqual(result['quantities'],[])
        self.assertEqual(result['pending_quantities'][0]['overlapping_measurement_ids'],[['a','b']])
        self.state['measurements']['b']['points']=box(100,0,100,100)
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],248)

    def test_different_pages_are_distinct_surfaces(self):
        self.state['measurements']['b'].update(page=2,points=box(0,0,100,100))
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],248)

    def test_same_page_scale_conflict_is_not_silently_skipped(self):
        self.state['measurements']['b']['points_per_foot']=20
        with self.assertRaisesRegex(ValueError,'same calibrated'):rollup(self.state,self.rules)

    def test_repeated_added_area_rejected(self):
        term=copy.deepcopy(self.rule['surface_components'][0]);term['id']='duplicate-area'
        self.rule['surface_components'].append(term)
        with self.assertRaisesRegex(ValueError,'unique added area'):rollup(self.state,self.rules)

    def test_no_area_or_no_assembly_rejected(self):
        self.rule.pop('surface_components')
        self.rule['measurement_ids'].remove('width')
        with self.assertRaisesRegex(ValueError,'surface assembly'):rollup(self.state,self.rules)


if __name__=='__main__':unittest.main()
