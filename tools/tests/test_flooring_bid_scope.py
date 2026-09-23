import copy
import unittest
from flooring_bid_scope import build_scope,render_markdown
from bid_comparison import scope_digest,required_scope_items


class FlooringBidTests(unittest.TestCase):
    def setUp(self):
        self.region={'id':'room','page':1,'points_per_foot':10,
            'points':[[0,0],[100,0],[100,100],[0,100]],'holes':[],
            'printed_labels':[{'text':'LIVING'},{'text':'KITCHEN'}]}
        self.rooms={'plan_sha256':'plan','measurement_version':1,'source_sha256':'source','regions':[self.region]}

    def test_multiple_labels_remain_one_area_without_invented_selection(self):
        scope=build_scope(self.rooms);item,=scope['items']
        self.assertEqual(item['reference_quantity'],100)
        self.assertEqual(item['room_name'],'LIVING / KITCHEN')
        self.assertIsNone(item['finish_selection']);self.assertIsNone(item['purchase_quantity'])
        self.assertIsNone(item['quoted_quantity']);self.assertIsNone(item['unit_price'])
        self.assertEqual(scope_digest(scope),scope['scope_sha256'])
        self.assertEqual(len(required_scope_items(scope)),8)
        self.assertIn('Do not infer material selections',render_markdown(scope))

    def test_holes_are_deducted_and_geometry_changes_scope(self):
        first=build_scope(self.rooms)
        self.region['holes']=[[[20,20],[40,20],[40,40],[20,40]]]
        second=build_scope(self.rooms)
        self.assertEqual(second['items'][0]['reference_quantity'],96)
        self.assertNotEqual(first['scope_sha256'],second['scope_sha256'])

    def test_bad_boundary_withheld_empty_scope_unknown_and_overlap_rejected(self):
        self.region['boundary_source_issues']=[{'id':'wall'}]
        scope=build_scope(self.rooms)
        self.assertIsNone(scope['items'][0]['reference_quantity'])
        self.assertEqual(scope['unmeasured_region_ids'],['room'])
        self.rooms['regions'].append(dict(copy.deepcopy(self.region),id='overlap'))
        with self.assertRaises(ValueError):build_scope(self.rooms)
        self.rooms['regions']=[];scope=build_scope(self.rooms)
        self.assertIsNone(scope['whole_house_flooring_quantity'])
        self.assertIn('does not mean zero flooring',render_markdown(scope))

    def test_reviewed_name_and_frozen_practices_retained_without_applying_waste(self):
        self.region.update(room_use_confirmed=True,room_use_review={'name':'Open living area'})
        practice={'tile.material_waste_percent':{'value':10,'provenance':{'basis':'test'},'intake_sha256':'test'}}
        scope=build_scope(self.rooms,practice)
        self.assertEqual(scope['items'][0]['room_name'],'Open living area')
        self.assertEqual(scope['items'][0]['reference_quantity'],100)
        self.assertEqual(scope['estimating_practices'],practice)
        self.assertFalse(scope['ready_to_order']);self.assertFalse(scope['sent'])


if __name__=='__main__':unittest.main()
