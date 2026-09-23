import copy
import unittest
from wall_classification_review import source_digest
from wall_network_inference import infer
from wall_run_candidates import from_state


def line(identity,a,b,depth=3.5,page=1):
    axis=0 if a[1]==b[1] else 1;half=depth/2
    bounds=[min(a[0],b[0]),a[1]-half,max(a[0],b[0]),a[1]+half] if axis==0 else [a[0]-half,min(a[1],b[1]),a[0]+half,max(a[1],b[1])]
    edges=[]
    for side in (bounds[1-axis],bounds[3-axis]):
        points=[[bounds[0],side],[bounds[2],side]] if axis==0 else [[side,bounds[1]],[side,bounds[3]]]
        edges.append({'path':len(edges),'item':0,'points_pt':points})
    return {'id':identity,'page':page,'kind':'length','points':[a,b],'points_per_foot':12,
        'source_method':'native_parallel_wall_strokes_v3','source_bounds_pt':bounds,
        'source_edges':edges,'drawn_thickness_inches':depth,'expected_depth_inches':depth,
        'wall_depth_basis':{'depth_inches':depth,'drawing_verified':False}}


def room():
    items=[line('bottom',[0,0],[120,0]),line('top',[0,120],[120,120]),
           line('left',[0,0],[0,120]),line('right',[120,0],[120,120])]
    return {'plan_sha256':'plan','version':1,'measurements':{m['id']:m for m in items}}


class WallNetworkInference(unittest.TestCase):
    def test_network_enters_runs_as_an_explicit_inference_not_a_purchase(self):
        value=from_state(room())
        self.assertEqual(len(value['wall_network_inference']['decisions']),4)
        self.assertEqual(len(value['run_candidates']),4)
        self.assertIsNone(value['classification_reviewer'])
        self.assertIsNone(value['whole_wall_quantity']);self.assertIsNone(value['purchase_quantity'])
        self.assertFalse(value['certified'])
        self.assertTrue(all(r['wall_interpretation_requires_review'] for r in value['run_candidates']))

    def test_explicit_uncertain_nonwall_and_stale_decisions_are_never_replaced(self):
        state=room()
        for decision,current in [('uncertain',True),('not_wall_faces',True),('wall_faces',False)]:
            value=infer(state,{'bottom':{'decision':decision,'current':current}})
            self.assertNotIn('bottom',value['decisions'])
            self.assertEqual(value['decisions'],{})

    def test_close_parallel_layer_blocks_both_sides_even_after_its_points_are_edited(self):
        state=room();state['measurements']['layer']=line('layer',[0,6],[120,6])
        result=infer(state,{})
        self.assertEqual(result['parallel_layer_ambiguities'],['bottom','layer'])
        self.assertNotIn('bottom',result['decisions'])
        state['measurements']['layer']['points'][0][0]+=20
        edited=infer(state,{})
        self.assertEqual(edited['parallel_layer_ambiguities'],['bottom','layer'])
        self.assertNotIn('layer',edited['decisions'])

    def test_editing_a_support_withholds_the_network_and_restoring_recovers_it(self):
        state=room();original=copy.deepcopy(state)
        state['measurements']['bottom']['points'][1][0]-=12
        self.assertEqual(infer(state,{})['decisions'],{})
        self.assertEqual(len(infer(original,{})['decisions']),4)

    def test_defaults_cad_faces_page_and_scale_are_required(self):
        for mutate in [lambda m:m.pop('wall_depth_basis'),lambda m:m.update(source_edges=[]),
                       lambda m:m.update(page=2),lambda m:m.update(points_per_foot=24),
                       lambda m:m.update(expected_depth_inches=5.5)]:
            state=room();mutate(state['measurements']['bottom'])
            self.assertNotIn('bottom',infer(state,{})['decisions'])

    def test_small_fixture_network_and_unconnected_lines_are_not_inferred(self):
        state=room()
        for m in state['measurements'].values():
            replacement=line(m['id'],[v/4 for v in m['points'][0]],[v/4 for v in m['points'][1]])
            m.update(replacement)
        self.assertEqual(infer(state,{})['decisions'],{})
        state=room();state['measurements']={'bottom':state['measurements']['bottom']}
        self.assertEqual(infer(state,{})['decisions'],{})

    def test_network_evidence_tracks_support_sources_and_input_order_is_irrelevant(self):
        state=room();before=infer(state,{})
        state['measurements']['bottom']['source_edges'][0]['path']=99
        after=infer(state,{})
        self.assertNotEqual(before['decisions']['top']['network_sha256'],after['decisions']['top']['network_sha256'])
        state['measurements']=dict(reversed(list(state['measurements'].items())))
        self.assertEqual(infer(state,{}),after)

    def test_explicit_reviewed_wall_remains_explicit(self):
        state=room();record={'measurement_id':'bottom','decision':'wall_faces',
            'source_sha256':source_digest(state['measurements']['bottom']),'basis':'Source reviewed'}
        value=from_state(state,{'plan_sha256':'plan','reviewer':'reviewer','decisions':[record]})
        self.assertNotIn('inferred',value['classification_decisions']['bottom'])
        self.assertEqual(len(value['wall_network_inference']['decisions']),3)

    def test_alignment_links_never_fill_an_unmeasured_gap(self):
        state=room();del state['measurements']['top']
        state['measurements']['top_left']=line('top_left',[0,120],[42,120])
        state['measurements']['top_right']=line('top_right',[78,120],[120,120])
        value=from_state(state)
        self.assertEqual(len(value['wall_network_inference']['decisions']),5)
        top=next(r for r in value['run_candidates'] if 'top_left' in r['source_measurement_ids'])
        self.assertEqual(top['visible_union_lf'],7)
        self.assertEqual(top['gaps'][0]['length_lf'],3)
        self.assertIsNone(value['purchase_quantity'])


if __name__=='__main__':unittest.main()
