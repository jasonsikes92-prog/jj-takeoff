import copy
import unittest
from wall_finish_allocation import allocate
from wall_boundary_surfaces import WallBoundaryReviewRequired


def area(points):
    return {'kind':'area','page':1,'points':points,'points_per_foot':1,'width_pt':100,'height_pt':100}


class FinishAllocation(unittest.TestCase):
    def setUp(self):
        self.room=area([[10,10],[30,10],[30,30],[10,30]])
        self.m={'shower':area([[10,10],[14,10],[14,15],[10,15]])}
        self.term={'id':'tile','measurement_id':'shower','kind':'rectangular_wall_faces',
            'faces':['min_x','min_y'],'height_ft':9,'height_source':'owner','scope_source':'plan'}

    def test_solid_faces_only_not_whole_shower_perimeter(self):
        result=allocate(self.room,9,self.m,[self.term])
        self.assertEqual((result['gross_wall_sf'],result['excluded_wall_sf'],result['remaining_wall_reference_sf']),(720,81,639))
        self.assertFalse(result['paint_quantity_certified'])
        self.assertIsNone(result['purchase_quantity'])

    def test_overlapping_bands_are_unioned_not_added(self):
        band={**self.term,'id':'lower-band','height_ft':3,'faces':['min_x']}
        result=allocate(self.room,9,self.m,[self.term,band])
        self.assertEqual(result['excluded_wall_sf'],81)
        self.assertEqual(result['overlapping_exclusion_sf'],15)

    def test_adjacent_collinear_segments_and_reverse_winding(self):
        self.room['points'].insert(1,[12,10])
        a=allocate(self.room,9,self.m,[self.term])
        self.room['points'].reverse();self.m['shower']['points'].reverse()
        b=allocate(self.room,9,self.m,[self.term])
        self.assertEqual(a['excluded_wall_sf'],81)
        self.assertEqual(a['excluded_wall_sf'],b['excluded_wall_sf'])

    def test_alignment_tolerance_and_endpoint_clipping(self):
        self.m['shower']['points']=[[9.97,9.97],[14,9.97],[14,15],[9.97,15]]
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,self.m,[self.term])
        self.assertAlmostEqual(allocate(self.room,9,self.m,[self.term],0.04)['excluded_wall_sf'],81)
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,self.m,[self.term],0.02)

    def test_moved_finish_wrong_frame_and_height_require_review(self):
        for field,value in [('page',2),('points_per_foot',2)]:
            m=copy.deepcopy(self.m);m['shower'][field]=value
            with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,m,[self.term])
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,8,self.m,[self.term])
        self.m['shower']['points']=[[12,12],[16,12],[16,17],[12,17]]
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,self.m,[self.term],0.25)

    def test_unknown_glass_side_and_duplicate_id_rejected(self):
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,self.m,[{**self.term,'faces':['max_x']}])
        with self.assertRaises(ValueError):allocate(self.room,9,self.m,[self.term,self.term])
        for tolerance in [-1,float('nan'),0.3,True]:
            with self.assertRaises(ValueError):allocate(self.room,9,self.m,[self.term],tolerance)

    def test_wall_gap_cannot_be_filled_by_tolerance(self):
        room=area([[10,10],[30,10],[30,30],[20,30],[20,15],[15,15],[15,30],[10,30]])
        m={'shower':area([[10,25],[30,25],[30,30],[10,30]])}
        with self.assertRaises(WallBoundaryReviewRequired):
            allocate(room,9,m,[{**self.term,'faces':['max_y']}],0.25)

    def test_nearby_parallel_walls_are_ambiguous(self):
        room=area([[10,10],[30,10],[30,30],[15.1,30],[15.1,15],[15,15],[15,30],[10,30]])
        m={'shower':area([[15.05,20],[18,20],[18,25],[15.05,25]])}
        with self.assertRaises(WallBoundaryReviewRequired):
            allocate(room,9,m,[{**self.term,'faces':['min_x']}],0.1)

    def test_elevation_height_on_a_source_mapped_plan_span(self):
        m={'band':{**self.room,'kind':'length','points':[[10,10],[14.25,10]]}}
        term={'id':'band','measurement_id':'band','kind':'length_wall','height_ft':3.5,
              'height_source':'reviewed elevation','scope_source':'reviewed plan wall'}
        self.assertEqual(allocate(self.room,9,m,[term])['excluded_wall_sf'],14.875)
        m['band']['points'].append([15,11])
        with self.assertRaises(WallBoundaryReviewRequired):allocate(self.room,9,m,[term])


if __name__=='__main__':unittest.main()
