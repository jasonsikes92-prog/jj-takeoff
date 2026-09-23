import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from floor_obstructions import net_floor_area


class FloorObstructionTests(unittest.TestCase):
    def setUp(self):
        def m(x,y,w,h):return {'kind':'area','page':1,'points_per_foot':1,'width_pt':100,'height_pt':100,
            'points':[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]}
        self.state={'plan_sha256':'p','version':3,'measurements':{'room':m(0,0,20,10)}}
        self.cuts={'plan_sha256':'p','version':1,'measurements':{'cab':m(0,0,5,2),'island':m(4,0,4,2)}}
    def result(self):return net_floor_area(self.state,['room'],self.cuts,['cab','island'])
    def test_union_not_sum_and_no_mutation(self):
        before=copy.deepcopy(self.state);r=self.result()
        self.assertEqual((r['gross_sf'],r['deducted_sf'],r['net_sf']),(200,16,184))
        self.assertEqual(self.state,before)
    def test_live_room_and_footprint_changes(self):
        self.state['measurements']['room']['points']=[[0,0],[21,0],[21,10],[0,10]]
        self.assertEqual(self.result()['net_sf'],194)
        self.cuts['measurements']['island']['points']=[[4,0],[9,0],[9,2],[4,2]]
        self.assertEqual(self.result()['net_sf'],192)
    def test_boundary_clip_disclosed(self):
        self.state['measurements']['room']['points']=[[1,0],[20,0],[20,10],[1,10]]
        r=self.result();self.assertEqual(r['net_sf'],176)
        self.assertEqual(r['footprints'][0]['outside_floor_sf'],2)
    def test_wrong_source_scale_page_and_outside_rejected(self):
        original=copy.deepcopy(self.cuts)
        for key,value in [('page',2),('points_per_foot',2),('surface_factor',1.1),
                          ('points',[[30,30],[35,30],[35,35],[30,35]])]:
            self.cuts=copy.deepcopy(original);self.cuts['measurements']['cab'][key]=value
            with self.assertRaises(ValueError):self.result()
        self.cuts=original;self.cuts['plan_sha256']='other'
        with self.assertRaises(ValueError):self.result()
    def test_room_overlap_and_duplicate_ids_rejected(self):
        self.state['measurements']['second']=copy.deepcopy(self.state['measurements']['room'])
        with self.assertRaises(ValueError):net_floor_area(self.state,['room','second'],self.cuts,['cab'])
        with self.assertRaises(ValueError):net_floor_area(self.state,['room'],self.cuts,['cab','cab'])

if __name__=='__main__':unittest.main()
