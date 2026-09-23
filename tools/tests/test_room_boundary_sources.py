import copy
import unittest
from room_region_candidates import associate
from room_use_candidates import apply as infer
from room_use_review import apply as review,binding
import test_room_region_candidates as fixtures


class RoomBoundarySources(unittest.TestCase):
    def setUp(self):
        f=fixtures.RoomRegions();f.setUp();self.enclosures=f.enclosures
        self.labels=[f.label('bed','BEDROOM',[20,20,50,30])]
        self.issue={'measurement_id':'edited','page':1,'points_per_foot':10,
            'current_bounds_pt':[150,0,154,100],'original_bounds_pt':[98,0,102,100],'reason':'Classification stale'}

    def test_original_footprint_conflict_blocks_label_inference(self):
        self.enclosures['unresolved_wall_sources']=[self.issue]
        r=infer(associate(self.enclosures,self.labels))['regions'][0]
        self.assertEqual(r['boundary_source_issues'],[self.issue])
        self.assertIsNone(r['room_use_inference']['room_use'])
        self.assertEqual(r['room_use_inference']['status'],'region_boundary_source_requires_review')

    def test_room_review_binding_changes_even_when_derived_polygon_stays_same(self):
        initial=associate(self.enclosures,self.labels);region=initial['regions'][0]
        record={'plan_sha256':'plan','reviewer':'Fixture','decisions':[{'region_id':'one','room_use':'bedroom',
            'name':'Bedroom','basis':'Reviewed source','source_sha256':binding('plan',region)}]}
        self.enclosures['unresolved_wall_sources']=[self.issue]
        changed=associate(self.enclosures,self.labels)
        self.assertEqual(changed['regions'][0]['points'],region['points'])
        self.assertNotEqual(binding('plan',changed['regions'][0]),binding('plan',region))
        checked=infer(review(changed,record))
        self.assertFalse(checked['regions'][0]['room_use_confirmed'])
        self.assertIsNone(checked['regions'][0]['room_use_inference']['room_use'])

    def test_other_page_scale_or_nonboundary_issues_do_not_block_room(self):
        for key,value in [('page',2),('points_per_foot',12),('original_bounds_pt',[110,0,114,100])]:
            enclosures=copy.deepcopy(self.enclosures);issue={**self.issue,key:value}
            enclosures['unresolved_wall_sources']=[issue]
            r=infer(associate(enclosures,self.labels))['regions'][0]
            self.assertNotIn('boundary_source_issues',r)
            self.assertEqual(r['room_use_inference']['room_use'],'bedroom')


if __name__=='__main__':unittest.main()
