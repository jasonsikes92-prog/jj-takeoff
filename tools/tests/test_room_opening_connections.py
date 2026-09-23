import copy
import unittest
from room_opening_connections import connections


def region(identity,points,page=1,ppf=10):
    return {'id':identity,'points':points,'holes':[],'page':page,'points_per_foot':ppf,
        'printed_labels':[{'id':identity+'-label','text':'BEDROOM'}]}


class OpeningConnections(unittest.TestCase):
    def setUp(self):
        self.regions=[region('left',[[0,0],[40,0],[40,100],[0,100]]),
            region('right',[[45,0],[100,0],[100,100],[45,100]])]
        self.source={'candidate_enclosures':[{'id':'house','page':1,'points_per_foot':10,
            'points':[[0,0],[100,0],[100,100],[0,100]]}],
            'gap_closures':[{'gap_id':'gap','opening_id':'door','axis':'vertical',
                'bounds_pt':[40,20,45,60],'page':1,'points_per_foot':10}]}

    def test_two_full_faces_link_regions_without_confirming_use(self):
        for horizontal in (False,True):
            s=copy.deepcopy(self.source);r=copy.deepcopy(self.regions)
            if horizontal:
                for item in r:item['points']=[p[::-1] for p in item['points']]
                s['gap_closures'][0].update(axis='horizontal',bounds_pt=[20,40,60,45])
            value=connections(s,r)[0]
            self.assertEqual(value['status'],'two_region_boundaries')
            self.assertEqual([side['region_id'] for side in value['sides']],['left','right'])
            self.assertFalse(value['room_use_confirmed']);self.assertIsNone(value['finish_selection'])

    def test_external_side_requires_measured_outer_boundary(self):
        self.source['gap_closures'][0]['bounds_pt']=[-5,20,0,60]
        outer=self.source['candidate_enclosures'][0];outer['points']=[[-5,0],[100,0],[100,100],[-5,100]]
        self.assertEqual(connections(self.source,self.regions)[0]['status'],'region_and_exterior_boundary')
        self.source['candidate_enclosures']=[]
        self.assertEqual(connections(self.source,self.regions)[0]['status'],'unresolved')

    def test_partial_face_or_point_contact_does_not_assign_room(self):
        for end in (20,40):
            self.regions[0]['points']=[[0,0],[40,0],[40,end],[0,end]]
            self.assertIsNone(connections(self.source,self.regions)[0]['sides'][0]['region_id'])

    def test_wrong_page_scale_and_overlapping_regions_remain_unresolved(self):
        for key,value in [('page',2),('points_per_foot',20)]:
            r=copy.deepcopy(self.regions);r[0][key]=value
            self.assertEqual(connections(self.source,r)[0]['status'],'unresolved')
        duplicate=copy.deepcopy(self.regions[0]);duplicate['id']='duplicate'
        self.assertIsNone(connections(self.source,self.regions+[duplicate])[0]['sides'][0]['region_id'])

    def test_nonopening_closures_are_excluded_and_edits_recompute(self):
        before=connections(self.source,self.regions)
        r=copy.deepcopy(self.regions);r[0]['points'][1][0]-=1
        self.assertNotEqual(connections(self.source,r),before)
        self.assertEqual(connections(self.source,self.regions),before)
        self.source['gap_closures'][0]['opening_id']=None
        self.assertEqual(connections(self.source,self.regions),[])

    def test_hole_boundary_is_a_region_boundary_not_a_filled_space(self):
        r=region('surround',[[0,0],[100,0],[100,100],[0,100]])
        r['holes']=[[[40,20],[60,20],[60,60],[40,60]]]
        self.assertEqual(connections(self.source,[r])[0]['sides'][0]['region_id'],'surround')
        self.assertIsNone(connections(self.source,[r])[0]['sides'][1]['region_id'])


if __name__=='__main__':unittest.main()
