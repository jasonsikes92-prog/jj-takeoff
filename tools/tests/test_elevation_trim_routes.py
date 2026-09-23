import copy
import math
import unittest
from elevation_trim_routes import calculate


class ElevationTrimRoutes(unittest.TestCase):
    def setUp(self):
        def m(identity,points,kind='area'):
            return {'id':identity,'page':9,'kind':kind,'points':points,'points_per_foot':10}
        self.sources={'wall':m('wall',[[0,100],[200,100],[200,200],[0,200]]),
            'gable':m('gable',[[40,100],[80,60],[120,100]]),
            'return':m('return',[[10,10],[10,60]],'length')}
        self.mapping={'horizontal':[{'measurement_id':'wall','kind':'area','point_count':4,'vertices':[0,1]}],
            'gables':[{'measurement_id':'gable','kind':'area','point_count':3,'edges':[[0,1],[1,2]],'parent_horizontal':'wall','same_wall_plane':True}],
            'returns':[{'measurement_id':'return','kind':'length','point_count':2}]}
    def result(self):return calculate(self.sources,self.mapping)
    def test_gable_replaces_horizontal_span_not_added_twice(self):
        r=self.result();self.assertAlmostEqual(r['group_lf']['horizontal_wall_top'],12)
        self.assertAlmostEqual(r['group_lf']['sloped_gable'],8*math.sqrt(2))
        self.assertEqual(r['group_lf']['gable_base_scope_pending'],8)
        self.assertEqual(r['group_lf']['recessed_porch_return'],5)
        self.assertIsNone(r['final_installed_quantity']);self.assertFalse(r['price_applied'])
    def test_overlapping_gable_projections_are_removed_once(self):
        self.sources['g2']=dict(self.sources['gable'],id='g2',points=[[100,100],[140,60],[180,100]])
        self.mapping['gables'].append(dict(self.mapping['gables'][0],measurement_id='g2'))
        r=self.result();self.assertEqual(r['group_lf']['gable_base_scope_pending'],14)
        self.assertEqual(r['group_lf']['horizontal_wall_top'],6)
    def test_edit_updates_geometry_and_restoring_recovers_result(self):
        first=self.result();old=copy.deepcopy(self.sources)
        self.sources['gable']['points'][1][1]=20
        self.assertGreater(self.result()['group_lf']['sloped_gable'],first['group_lf']['sloped_gable'])
        self.sources=old;self.assertEqual(self.result(),first)
    def test_topology_scale_page_and_orientation_changes_rejected(self):
        for change in ['topology','scale','page','horizontal','outside','slope_factor']:
            with self.subTest(change=change):
                self.setUp()
                if change=='topology':self.sources['wall']['points'].append([0,150])
                elif change=='scale':self.sources['gable']['points_per_foot']=20
                elif change=='page':self.sources['gable']['page']=10
                elif change=='horizontal':self.sources['wall']['points'][0][1]=99
                elif change=='outside':self.sources['gable']['points'][0][0]=-1
                else:self.sources['gable']['surface_factor']=1.4
                with self.assertRaises(ValueError):self.result()
    def test_duplicate_routes_and_unused_sources_are_rejected(self):
        self.mapping['horizontal']*=2
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.result()
        self.setUp();self.sources['unused']=copy.deepcopy(self.sources['wall'])
        with self.assertRaisesRegex(ValueError,'declared'):self.result()

    def test_porch_gable_does_not_remove_wall_trim_behind_it(self):
        self.mapping['gables'][0]['same_wall_plane']=False
        result=self.result()
        self.assertEqual(result['group_lf']['horizontal_wall_top'],20)
        self.assertEqual(result['group_lf']['gable_base_scope_pending'],0)
        self.assertEqual(result['separate_plane_gables'],['gable'])
        del self.mapping['gables'][0]['same_wall_plane']
        with self.assertRaisesRegex(ValueError,'physical wall-plane'):self.result()


if __name__=='__main__':unittest.main()
