import copy
import math
import unittest
from roof_dormer_candidates import component_candidates


class DormerCandidates(unittest.TestCase):
    def setUp(self):
        self.group={'interior_ring_points':[[0,0],[-60,100],[-60,240],[60,240],[60,100]],
            'faces':[{'points':[[0,0],[-60,100],[-60,240],[0,240]],'source_cad_paths':[1,2,3]},
                {'points':[[0,0],[0,240],[60,240],[60,100]],'source_cad_paths':[3,4,5]}]}
        self.parent={'rise':6,'downslope':[0,1],'source':'Synthetic 6:12 label and downward arrow'}
        self.frame={'page':1,'points_per_foot':10,'width_pt':600,'height_pt':600,'plan_sha256':'a'*64}
        self.transform(lambda x,y:(x+200,y+100))

    def transform(self,fn):
        self.group['interior_ring_points']=[list(fn(*p)) for p in self.group['interior_ring_points']]
        for face in self.group['faces']:face['points']=[list(fn(*p)) for p in face['points']]

    def test_intersection_derives_different_pitch_without_inheriting_parent(self):
        original=copy.deepcopy(self.group)
        result=component_candidates(self.group,self.parent,self.frame)
        self.assertEqual(self.group,original)
        self.assertEqual(len(result['measurements']),2)
        for row in result['measurements']:
            evidence=row['source_pitch_evidence']
            self.assertAlmostEqual(evidence['inferred_rise_per_12'],10)
            self.assertAlmostEqual(row['surface_factor'],math.hypot(12,10)/12)
            self.assertTrue(evidence['pitch_is_inferred']);self.assertFalse(evidence['pitch_certified'])
            self.assertTrue(row['source_cad_paths']);self.assertFalse(row['dependent_rows'])
        self.assertFalse(result['scope_certified'])

    def test_rotating_and_uniformly_scaling_plan_does_not_change_pitch(self):
        self.transform(lambda x,y:(600-y,x))
        self.parent['downslope']=[-1,0]
        self.transform(lambda x,y:(x/2,y/2))
        result=component_candidates(self.group,self.parent,self.frame)
        for e in result['pitch_evidence']:self.assertAlmostEqual(e['inferred_rise_per_12'],10)

    def test_uphill_or_cross_ridge_parent_arrow_is_rejected(self):
        for down in ([0,-1],[1,0],[1,1]):
            with self.assertRaises(ValueError):
                component_candidates(self.group,{**self.parent,'downslope':down},self.frame)

    def test_missing_or_invalid_pitch_and_provenance_are_rejected(self):
        for patch in ({'rise':None},{'rise':True},{'rise':float('nan')},{'rise':0},
                      {'downslope':[0,0]},{'downslope':[float('inf'),1]},{'source':''}):
            with self.assertRaises(ValueError):component_candidates(self.group,{**self.parent,**patch},self.frame)
        with self.assertRaises(ValueError):component_candidates(self.group,self.parent,{**self.frame,'plan_sha256':'wrong'})

    def test_missing_face_or_unfilled_footprint_is_rejected(self):
        group=copy.deepcopy(self.group);group['faces'].pop()
        with self.assertRaises(ValueError):component_candidates(group,self.parent,self.frame)
        group=copy.deepcopy(self.group);group['faces'][0]['points'][1][0]+=2
        with self.assertRaises(ValueError):component_candidates(group,self.parent,self.frame)

    def test_changed_source_pitch_or_geometry_changes_identity(self):
        base=component_candidates(self.group,self.parent,self.frame)['source_geometry_sha256']
        changed=component_candidates(self.group,{**self.parent,'rise':7},self.frame)['source_geometry_sha256']
        self.assertNotEqual(base,changed)
        self.transform(lambda x,y:(x+1,y))
        self.assertNotEqual(base,component_candidates(self.group,self.parent,self.frame)['source_geometry_sha256'])


if __name__=='__main__':unittest.main()
