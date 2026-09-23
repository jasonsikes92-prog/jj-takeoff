import copy
import math
import unittest
from roof_junction_quantities import calculate
from roof_panel_review import junction_allowance


class RoofJunctionQuantities(unittest.TestCase):
    def setUp(self):
        self.faces=[{'id':i,'kind':'area','page':1,'width_pt':100,'height_pt':100,
            'points_per_foot':1,'surface_factor':math.sqrt(2),'points':points} for i,points in [
                ('a',[[0,0],[10,0],[10,10],[0,10]]),('b',[[10,0],[20,0],[20,10],[10,10]])]]
        self.gradients={'a':[1,0],'b':[-1,0]}

    def test_shared_ridge_counted_once_not_once_per_face(self):
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_length_by_kind_lf'],{'ridge':10})
        self.assertEqual(result['exact_shared_projected_lf'],10)
        self.assertEqual(result['unmatched_boundary_by_face_lf'],{'a':30,'b':30})
        self.assertEqual(len(result['candidate_segments']),1)
        self.assertFalse(result['certified']);self.assertIsNone(result['complete_member_quantity'])

    def test_valley_uses_inward_rising_slopes(self):
        self.gradients={'a':[-1,0],'b':[1,0]}
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_length_by_kind_lf'],{'valley':10})

    def test_hip_length_uses_along_edge_rise_not_full_pitch_multiplier(self):
        self.gradients={'a':[1,.5],'b':[-1,.5]}
        for f in self.faces:f['surface_factor']=1.5
        result=calculate(self.faces,self.gradients)
        self.assertAlmostEqual(result['candidate_length_by_kind_lf']['hip'],math.sqrt(125))
        self.assertFalse(result['candidate_segments'][0]['absolute_elevations_verified'])

    def test_incompatible_adjacent_slopes_withhold_length(self):
        self.gradients['b']=[-1,.5];self.faces[1]['surface_factor']=1.5
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_segments'],[])
        self.assertTrue(any('disagree' in x['reason'] for x in result['unresolved_junctions']))

    def test_small_gap_is_not_closed(self):
        self.faces[1]['points']=[[x+.0001,y] for x,y in self.faces[1]['points']]
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_segments'],[])
        self.assertEqual(result['exact_shared_projected_lf'],0)

    def test_overlapping_roofs_do_not_create_member_orders(self):
        self.faces[1]['points']=[[5,0],[15,0],[15,10],[5,10]]
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_segments'],[])
        self.assertTrue(any('overlap' in x['reason'].lower() for x in result['unresolved_junctions']))

    def test_three_face_boundary_is_not_counted_twice(self):
        self.faces.append({**copy.deepcopy(self.faces[0]),'id':'c'})
        self.gradients['c']=self.gradients['a']
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_segments'],[])
        self.assertTrue(any('More than two' in x['reason'] for x in result['unresolved_junctions']))

    def test_reversed_vertex_order_does_not_flip_ridge_into_valley(self):
        before=calculate(self.faces,self.gradients)
        for f in self.faces:f['points'].reverse()
        after=calculate(self.faces,self.gradients)
        self.assertEqual(before['candidate_length_by_kind_lf'],after['candidate_length_by_kind_lf'])

    def test_partial_shared_edge_only_counts_shared_length(self):
        self.faces[1]['points']=[[10,3],[20,3],[20,7],[10,7]]
        self.assertEqual(calculate(self.faces,self.gradients)['candidate_length_by_kind_lf'],{'ridge':4})

    def test_invalid_gradient_or_frame_rejected(self):
        for field,value in [('points_per_foot',2),('page',2),('surface_factor',1)]:
            bad=copy.deepcopy(self.faces);bad[1][field]=value
            with self.assertRaises(ValueError):calculate(bad,self.gradients)
        with self.assertRaises(ValueError):calculate(self.faces,{'a':[1,0]})

    def test_same_slope_is_a_seam_not_a_roof_member(self):
        self.gradients['b']=[1,0]
        result=calculate(self.faces,self.gradients)
        self.assertEqual(result['candidate_segments'],[])
        self.assertTrue(any('Slope break' in x['reason'] for x in result['unresolved_junctions']))

    def test_numerical_slope_noise_retains_explicit_length_bounds(self):
        self.gradients['b']=[-1,1e-7]
        result=calculate(self.faces,self.gradients)
        row=result['candidate_segments'][0]
        self.assertEqual(row['kind'],'ridge')
        self.assertLessEqual(row['length_bounds_lf'][0],row['quantity_lf'])
        self.assertEqual(row['length_bounds_lf'][1],row['quantity_lf'])
        self.assertEqual(result['numerical_tolerance_inches'],.0001)

    def test_reviewed_approximation_retains_difference_and_conservative_length(self):
        self.gradients={'a':[-1,.2],'b':[1,.2005]}
        for face in self.faces:face['surface_factor']=math.hypot(1,*self.gradients[face['id']])
        self.assertEqual(calculate(self.faces,self.gradients)['candidate_segments'],[])
        result=calculate(self.faces,self.gradients,rise_allowance_inches=.125)
        row,=result['candidate_segments']
        self.assertEqual(row['kind'],'valley')
        self.assertTrue(row['uses_reviewed_slope_approximation'])
        self.assertAlmostEqual(row['rise_difference_inches'],.06)
        self.assertAlmostEqual(row['length_bounds_lf'][0],math.hypot(10,2))
        self.assertAlmostEqual(row['quantity_lf'],math.hypot(10,2.005))
        self.assertIsNone(result['complete_member_quantity'])
        self.assertFalse(result['purchase_authorized'])
        self.assertFalse(row['absolute_elevations_verified'])

    def test_over_limit_difference_is_still_unresolved(self):
        self.gradients['b']=[-1,.0011]
        self.faces[1]['surface_factor']=math.hypot(1,*self.gradients['b'])
        result=calculate(self.faces,self.gradients,rise_allowance_inches=.125)
        self.assertEqual(result['candidate_segments'],[])
        self.assertAlmostEqual(result['unresolved_junctions'][0]['rise_difference_inches'],.132)

    def test_allowance_does_not_close_gaps_or_accept_overlaps(self):
        self.faces[1]['points']=[[x+.01,y] for x,y in self.faces[1]['points']]
        self.assertEqual(calculate(self.faces,self.gradients,rise_allowance_inches=.125)['candidate_segments'],[])
        self.faces[1]['points']=[[5,0],[15,0],[15,10],[5,10]]
        self.assertEqual(calculate(self.faces,self.gradients,rise_allowance_inches=.125)['candidate_segments'],[])

    def test_invalid_allowance_rejected(self):
        for value in (True,-1,0,float('nan'),float('inf'),'0.125'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                calculate(self.faces,self.gradients,rise_allowance_inches=value)

    def test_review_requires_current_geometry_gradient_and_plan(self):
        review={'plan_sha256':'plan','gradient_sha256':'gradient','source_geometry_sha256':{'a':'first'},
            'maximum_rise_difference_inches':.125,'reviewer':'Estimator','basis':'Source drawing comparison'}
        self.assertEqual(junction_allowance(review,'plan','gradient',{'a':'first'}),(.125,'current_estimating_review'))
        self.assertEqual(junction_allowance(review,'plan','gradient',{'a':'changed'}),(None,'stale_source_review'))
        self.assertEqual(junction_allowance(review,'plan','changed',{'a':'first'}),(None,'stale_source_review'))
        with self.assertRaises(ValueError):junction_allowance(review,'other','gradient',{'a':'first'})
        review['basis']=''
        with self.assertRaises(ValueError):junction_allowance(review,'plan','gradient',{'a':'first'})


if __name__=='__main__':unittest.main()
