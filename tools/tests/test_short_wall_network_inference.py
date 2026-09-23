import copy
import unittest
from wall_classification_review import source_digest
from wall_network_inference import candidate, infer
from wall_run_candidates import from_state
from test_wall_network_inference import line, room


def short(identity='stub',axis='horizontal'):
    m=line(identity,[60,120],[63.5,120]) if axis=='horizontal' else line(identity,[0,60],[0,63.5])
    a,b,c,d=m['source_bounds_pt']
    m.update(kind='area',points=[[a,b],[c,b],[c,d],[a,d]])
    return m


def with_stub():
    state=room();del state['measurements']['top']
    state['measurements'].update(top_left=line('top_left',[0,120],[24,120]),
        top_right=line('top_right',[96,120],[120,120]),stub=short())
    return state


class ShortWallNetworkInference(unittest.TestCase):
    def test_equal_sides_use_native_face_direction_not_longest_side(self):
        for name,axis in [('horizontal',0),('vertical',1)]:
            m=short(axis=name);value=candidate(m)
            self.assertEqual(value['axis'],axis);self.assertTrue(value['short_piece'])
            self.assertEqual(m['kind'],'area')

    def test_supported_short_outline_enters_run_without_changing_saved_polygon(self):
        state=with_stub();before=copy.deepcopy(state);result=from_state(state)
        decision=result['classification_decisions']['stub']
        self.assertEqual(decision['axis'],'horizontal')
        self.assertTrue(decision['inferred']);self.assertTrue(decision['requires_review'])
        run=next(r for r in result['run_candidates'] if 'stub' in r['source_measurement_ids'])
        self.assertAlmostEqual(run['visible_union_lf'],(24+3.5+24)/12)
        self.assertEqual(state,before)
        self.assertIsNone(result['purchase_quantity'])

    def test_two_native_face_axes_remain_ambiguous(self):
        m=short();a,b,c,d=m['source_bounds_pt']
        m['source_edges'] += [{'path':20,'points_pt':[[a,b],[a,d]]},
                              {'path':21,'points_pt':[[c,b],[c,d]]}]
        self.assertIsNone(candidate(m))
        state=with_stub();state['measurements']['stub']=m
        self.assertNotIn('stub',infer(state,{})['decisions'])

    def test_edited_outline_is_withheld_and_restore_recovers_direction(self):
        state=with_stub();before=copy.deepcopy(state)
        state['measurements']['stub']['points'][1][0]+=.5
        self.assertIsNone(candidate(state['measurements']['stub']))
        self.assertNotIn('stub',infer(state,{})['decisions'])
        self.assertEqual(infer(before,{})['decisions']['stub']['axis'],'horizontal')

    def test_no_depth_missing_face_and_crossed_polygon_do_not_supply_an_axis(self):
        for change in [lambda m:m.pop('wall_depth_basis'),lambda m:m['source_edges'].pop(),
                       lambda m:m.update(points=[m['points'][i] for i in [0,2,1,3]])]:
            m=short();change(m);self.assertIsNone(candidate(m))

    def test_stale_or_uncertain_review_is_not_replaced(self):
        state=with_stub();m=state['measurements']['stub']
        for decision,sha in [('uncertain',source_digest(m)),('wall_faces','stale')]:
            review={'plan_sha256':state['plan_sha256'],'reviewer':'reviewer','decisions':[
                {'measurement_id':'stub','decision':decision,'source_sha256':sha,'basis':'Explicit review'}]}
            result=from_state(state,review)
            self.assertNotIn('stub',result['wall_network_inference']['decisions'])

    def test_isolated_short_pieces_do_not_become_walls_from_direction_alone(self):
        state=room();state['measurements']={'stub':short()}
        self.assertTrue(candidate(state['measurements']['stub']))
        self.assertEqual(infer(state,{})['decisions'],{})


if __name__=='__main__':unittest.main()
