import copy
import unittest
from roof_partition_state import audit_state


class RoofPartitionState(unittest.TestCase):
    def setUp(self):
        self.measurement={'id':'roof','kind':'area','points':[[10,10],[110,10],[110,110],[10,110]],
            'surface_factor':1.25,'page':1,'width_pt':500,'height_pt':500,'points_per_foot':10}
        self.state={'plan_sha256':'plan','version':1,'measurements':{'roof':self.measurement}}
        self.config={'plan_sha256':'plan','measurement_ids':['roof'],
            'cutout_terms':[{'measurement_id':'roof','kind':'area','operation':'add'}]}
        self.coverage={'plan_sha256':'plan','page':1,'points':copy.deepcopy(self.measurement['points']),
            'review_sha256':'source-review'}

    def test_latest_geometry_updates_coverage_and_digest_without_certification(self):
        before=audit_state(self.state,self.config,self.coverage)
        self.measurement['points']=[[10,10],[100,10],[100,110],[10,110]];self.state['version']=2
        after=audit_state(self.state,self.config,self.coverage)
        self.assertEqual(before['coverage']['missing_projected_sf'],0)
        self.assertEqual(after['coverage']['missing_projected_sf'],10)
        self.assertNotEqual(before['measurements_sha256'],after['measurements_sha256'])
        self.assertEqual(after['measurement_version'],2)
        self.assertFalse(after['certified']);self.assertFalse(after['order_released'])

    def test_without_independent_outline_coverage_is_unknown(self):
        result=audit_state(self.state,self.config)
        self.assertIsNone(result['coverage']);self.assertIsNone(result['coverage_review_sha256'])

    def test_wrong_source_outline_and_missing_or_repeated_measurements_are_rejected(self):
        for config in ({**self.config,'plan_sha256':'other'},
                       {**self.config,'measurement_ids':['missing']},
                       {**self.config,'measurement_ids':['roof','roof']}):
            with self.assertRaises(ValueError):audit_state(self.state,config,self.coverage)
        for change in ({'page':2},{'plan_sha256':'other'}):
            with self.assertRaises(ValueError):audit_state(self.state,self.config,{**self.coverage,**change})


if __name__=='__main__':unittest.main()
