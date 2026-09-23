import copy
import unittest
from room_use_review import apply,binding


class RoomUses(unittest.TestCase):
    def setUp(self):
        self.region={'id':'room','page':1,'points_per_foot':10,'points':[[0,0],[10,0],[10,10],[0,10]],
            'holes':[],'printed_labels':[],'room_use_confirmed':False,'finish_selection':None,'floor_finish_quantity':None}
        self.result={'plan_sha256':'plan','source_sha256':'geometry','regions':[self.region]}
        self.review={'plan_sha256':'plan','reviewer':'Source reviewer','decisions':[{'region_id':'room',
            'source_sha256':binding('plan',self.region),'room_use':'closet','name':'Bedroom closet',
            'basis':'Original plan shelving and bypass door'}]}

    def test_current_source_review_supplies_use_but_no_finish_or_owner_approval(self):
        result=apply(self.result,self.review);room=result['regions'][0]
        self.assertTrue(room['room_use_confirmed']);self.assertEqual(room['room_use_review']['room_use'],'closet')
        self.assertFalse(room['room_use_review']['owner_approved']);self.assertIsNone(room['floor_finish_quantity'])
        self.assertFalse(self.region['room_use_confirmed']);self.assertEqual(result['room_use_review']['unreviewed_region_ids'],[])

    def test_changed_geometry_scale_labels_and_missing_region_withhold_use(self):
        for changes in ({'points':[[0,0],[11,0],[11,10],[0,10]]},{'page':2},
                        {'points_per_foot':12},{'printed_labels':[{'text':'BATH'}]},{'id':'new'}):
            source=copy.deepcopy(self.result);source['regions'][0].update(changes)
            result=apply(source,self.review)
            self.assertFalse(result['regions'][0]['room_use_confirmed'])
            self.assertEqual(len(result['room_use_review']['unresolved_decisions']),1)

    def test_cosmetic_change_does_not_invalidate_source_and_restore_recovers(self):
        source=copy.deepcopy(self.result);source['regions'][0]['color']='blue'
        self.assertTrue(apply(source,self.review)['regions'][0]['room_use_confirmed'])
        source['regions'][0]['points'][0][0]=1
        self.assertFalse(apply(source,self.review)['regions'][0]['room_use_confirmed'])
        source['regions'][0]['points'][0][0]=0
        self.assertTrue(apply(source,self.review)['regions'][0]['room_use_confirmed'])

    def test_invalid_reviews_fail_and_no_review_preserves_unknowns(self):
        for changes in ({'plan_sha256':'other'},{'reviewer':''},{'decisions':None},
                        {'decisions':self.review['decisions']*2}):
            with self.assertRaises(ValueError):apply(self.result,{**self.review,**changes})
        r=copy.deepcopy(self.review);r['decisions'][0]['basis']=''
        with self.assertRaises(ValueError):apply(self.result,r)
        self.assertEqual(apply(self.result,None),self.result)

    def test_changed_review_changes_result_fingerprint(self):
        first=apply(self.result,self.review)
        self.review['decisions'][0]['name']='Office closet'
        self.assertNotEqual(first['source_sha256'],apply(self.result,self.review)['source_sha256'])


if __name__=='__main__':unittest.main()
