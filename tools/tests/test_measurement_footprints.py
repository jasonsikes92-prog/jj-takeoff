import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from footprint_area import footprint_area


def box(x0,y0,x1,y1):
    return {'kind':'area','page':1,'points_per_foot':10,'width_pt':500,'height_pt':500,
        'points':[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]}


class FootprintTests(unittest.TestCase):
    def test_union_counts_overlap_once_and_exclusions_only_where_intersecting(self):
        m={'house':box(0,0,100,100),'porch':box(50,50,150,150)}
        self.assertEqual(footprint_area(m,['house','porch'],[]),175)
        self.assertEqual(footprint_area(m,['porch'],['house']),75)
        m['porch']=box(50,50,200,150)
        self.assertEqual(footprint_area(m,['house','porch'],[]),225)
        self.assertEqual(footprint_area(m,['porch'],['house']),125)

    def test_incompatible_geometry_and_unassigned_boundaries_refused(self):
        m={'a':box(0,0,100,100),'b':box(50,50,150,150)}
        for key,value in [('page',2),('points_per_foot',20),('surface_factor',1.5)]:
            bad=copy.deepcopy(m);bad['b'][key]=value
            with self.assertRaises(ValueError):footprint_area(bad,['a','b'],[])
        with self.assertRaises(ValueError):footprint_area(m,['a'],[])
        with self.assertRaises(ValueError):footprint_area(m,['a','b'],['b'])
        m['b']['points']=[[50,50],[150,150],[150,50],[50,150]]
        with self.assertRaises(ValueError):footprint_area(m,['a','b'],[])

    def test_angled_floor_clips_deductions_and_counts_overlaps_once(self):
        triangle=box(0,0,100,100)
        triangle['points']=[[0,0],[100,0],[0,100]]
        self.assertEqual(footprint_area({'a':triangle},['a'],[]),50)
        m={'a':triangle,'left':box(0,0,50,100),'nested':box(0,0,25,50),
           'outside':box(100,100,150,150)}
        self.assertEqual(footprint_area(m,['a'],['left','nested','outside']),12.5)
        m['duplicate']=copy.deepcopy(triangle)
        self.assertEqual(footprint_area(m,['a','duplicate'],['left','nested','outside']),12.5)


if __name__=='__main__':unittest.main()
