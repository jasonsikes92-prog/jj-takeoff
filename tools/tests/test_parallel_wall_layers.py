"""Recover a connected wall outline without assuming an adjacent layer's scope."""
import copy
import unittest
from test_wall_network_inference import line,room
from wall_network_inference import infer
from wall_run_candidates import from_state


def layered_room():
    state=room();state['measurements']['layer']=line('layer',[3,6],[117,6])
    return state


class ParallelWallLayers(unittest.TestCase):
    def test_unique_physical_end_contacts_support_wall_but_leave_layer_unresolved(self):
        state=layered_room();original=copy.deepcopy(state);result=infer(state,{})
        self.assertEqual(set(result['decisions']),{'bottom','top','left','right'})
        self.assertEqual(result['parallel_layer_ambiguities'],['layer'])
        resolution,=result['parallel_layer_resolutions']
        self.assertEqual(resolution['selected_wall_id'],'bottom')
        self.assertEqual(resolution['endpoint_supports'],[['left'],['right']])
        self.assertTrue(resolution['requires_review']);self.assertEqual(state,original)
        runs=from_state(state)
        self.assertEqual([u['measurement_id'] for u in runs['unresolved_measurements']],['layer'])
        self.assertIsNone(runs['whole_wall_quantity']);self.assertIsNone(runs['purchase_quantity'])

    def test_two_physically_connected_layers_are_not_resolved_by_preference(self):
        state=layered_room();state['measurements']['layer']=line('layer',[0,6],[120,6])
        result=infer(state,{})
        self.assertEqual(result['parallel_layer_resolutions'],[])
        self.assertEqual(result['parallel_layer_ambiguities'],['bottom','layer'])
        self.assertNotIn('bottom',result['decisions'])

    def test_small_positive_gap_is_not_promoted_to_physical_contact(self):
        state=layered_room()
        state['measurements']['bottom']=line('bottom',[1.751,0],[118.249,0])
        self.assertEqual(infer(state,{})['parallel_layer_resolutions'],[])

    def test_layer_edit_or_explicit_decision_prevents_resolving_the_group(self):
        state=layered_room();state['measurements']['layer']['points'][0][0]+=1
        self.assertNotIn('bottom',infer(state,{})['decisions'])
        for decision,current in (('uncertain',True),('wall_faces',True),('wall_faces',False)):
            result=infer(layered_room(),{'layer':{'decision':decision,'current':current}})
            self.assertNotIn('bottom',result['decisions']);self.assertEqual(result['parallel_layer_resolutions'],[])
        # An explicit nonwall decision can remove its obstruction by the existing rule.
        result=infer(layered_room(),{'layer':{'decision':'not_wall_faces','current':True}})
        self.assertIn('bottom',result['decisions']);self.assertNotIn('layer',result['decisions'])

    def test_changed_perpendicular_support_is_not_reused_from_its_original_shape(self):
        state=layered_room();state['measurements']['left']['points'][0][1]+=1
        result=infer(state,{})
        self.assertNotIn('bottom',result['decisions']);self.assertEqual(result['parallel_layer_resolutions'],[])

    def test_dependency_hash_includes_unresolved_layer_source_and_is_order_independent(self):
        state=layered_room();before=infer(state,{})
        state['measurements']['layer']['source_edges'][0]['path']=99
        after=infer(state,{})
        for identity in before['decisions']:
            self.assertNotEqual(before['decisions'][identity]['network_sha256'],after['decisions'][identity]['network_sha256'])
        self.assertIn('layer',after['decisions']['bottom']['evidence']['layer_source_sha256'])
        state['measurements']=dict(reversed(list(state['measurements'].items())))
        self.assertEqual(infer(state,{}),after)

    def test_rotated_and_reversed_geometry_retains_face_contact_resolution(self):
        state=layered_room()
        for i,m in list(state['measurements'].items()):
            points=[[300-p[1],p[0]+50] for p in reversed(m['points'])]
            state['measurements'][i]=line(i,*points)
        result=infer(state,{})
        self.assertIn('bottom',result['decisions']);self.assertNotIn('layer',result['decisions'])

    def test_local_resolution_does_not_replace_minimum_network_evidence(self):
        state=layered_room()
        for i,m in list(state['measurements'].items()):
            state['measurements'][i]=line(i,*[[v/3 for v in p] for p in m['points']])
        self.assertEqual(infer(state,{})['decisions'],{})


if __name__=='__main__':unittest.main()
