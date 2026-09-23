import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from wall_boundary_surfaces import wall_surface,WallBoundaryReviewRequired
from measurement_quantities import rollup


def area(points):
    return {'kind':'area','points':points,'page':1,'width_pt':100,'height_pt':100,'points_per_foot':1}


class WallFaces(unittest.TestCase):
    def setUp(self):
        self.m={'room':area([[10,10],[10,20],[30,20],[30,10]]),
                'combined':area([[10,10],[10,30],[30,30],[30,10]])}
        self.term={'id':'face','measurement_id':'room','kind':'rectangular_wall_faces','faces':['min_x','max_y'],
                   'height_ft':9,'height_source':'plan height','scope_source':'reviewed interior faces','operation':'add'}

    def exposed(self):
        return {**self.term,'measurement_id':'combined','kind':'exposed_boundary_wall','exclude_measurement_id':'room'}

    def test_selected_interior_faces_and_reordered_vertices(self):
        result=wall_surface(self.m,self.term)
        self.assertEqual((result['selected_length_lf'],result['surface_sf']),(30,270))
        self.m['room']['points'].reverse()
        self.assertEqual(wall_surface(self.m,self.term),result)
        self.m['room']['points']=[[10,10],[10,22],[30,22],[30,10]]
        self.assertEqual(wall_surface(self.m,self.term)['surface_sf'],288)

    def test_exposed_boundary_removes_house_faces_not_divider(self):
        result=wall_surface(self.m,self.exposed())
        self.assertEqual((result['selected_length_lf'],result['surface_sf']),(40,360))
        self.assertEqual(sum(x['length_lf'] for x in result['wall_segments']),40)
        # Collinear break points do not change selected length.
        self.m['combined']['points'].insert(1,[10,15])
        self.assertEqual(wall_surface(self.m,self.exposed())['surface_sf'],360)

    def test_wrong_frames_outside_house_and_nonrectangle_require_review(self):
        for field,value in [('page',2),('points_per_foot',2),('surface_factor',2)]:
            m=copy.deepcopy(self.m);m['room'][field]=value
            with self.assertRaises(WallBoundaryReviewRequired):wall_surface(m,self.exposed())
        self.m['room']['points'][0]=[9,10]
        with self.assertRaises(WallBoundaryReviewRequired):wall_surface(self.m,self.exposed())
        with self.assertRaises(WallBoundaryReviewRequired):wall_surface(self.m,self.term)

    def test_height_and_duplicate_faces_are_not_silently_accepted(self):
        for key,value in [('faces',['min_x','min_x']),('faces',['unknown']),('height_ft',0),('height_ft',float('nan')),('scope_source','')]:
            term={**self.term,key:value}
            with self.assertRaises(ValueError):wall_surface(self.m,term)

    def test_surface_rollup_keeps_opening_deductions_and_withholds_changed_topology(self):
        self.m['door']={'kind':'length','points':[[10,12],[10,15]],'page':1,'width_pt':100,'height_pt':100,'points_per_foot':1}
        rule={'id':'sound','label':'sound wall','measurement_ids':['room','door'],'unit':'SF','rounding':'none',
              'template_rows':['217'],'use':'assembly_input','basis':'test','remaining':['cavities'],
              'surface_components':[self.term,{'id':'door','measurement_id':'door','kind':'length_wall','height_ft':7,'height_source':'plan','operation':'deduct',
                                              'wall_face_of':'face','alignment_source':'same wall','alignment_tolerance_ft':0.25}]}
        state={'plan_sha256':'p','version':1,'measurements':self.m};rules={'plan_sha256':'p','rules':[rule]}
        result=rollup(state,rules)
        self.assertEqual(result['quantities'][0]['quantity'],249)
        self.m['door']['points']=[[9.8,12],[9.8,15]]
        self.assertEqual(rollup(state,rules)['quantities'][0]['quantity'],249)
        self.m['door']['points']=[[8,12],[8,15]]
        self.assertEqual(rollup(state,rules)['quantities'],[])
        self.m['door']['points']=[[10,12],[10,15]]
        duplicate={**rule['surface_components'][1],'id':'duplicate'}
        rule['surface_components'].append(duplicate)
        self.assertEqual(rollup(state,rules)['quantities'],[])
        rule['surface_components'].pop()
        self.m['room']['points'][0]=[9,10]
        result=rollup(state,rules)
        self.assertEqual(result['quantities'],[])
        self.assertEqual(result['pending_quantities'][0]['quantity'],None)


if __name__=='__main__':unittest.main()
