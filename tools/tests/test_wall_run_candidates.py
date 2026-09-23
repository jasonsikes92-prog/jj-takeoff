import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_run_candidates import from_state, WALL_METHOD


def line(identity,a,b,page=1,ppf=1):
    return {'id':identity,'page':page,'kind':'length','points':[a,b],
            'points_per_foot':ppf,'source_method':WALL_METHOD}


def state(*items):
    return {'plan_sha256':'source-plan','version':1,'measurements':{m['id']:m for m in items}}


class WallRunCandidates(unittest.TestCase):
    def test_unclassified_stroke_candidates_are_visible_as_unresolved(self):
        stroke={**line('stroke',[0,0],[10,0]),'source_method':'native_parallel_wall_strokes_v1'}
        before=from_state(state(stroke))
        self.assertEqual(before['source_wall_candidates'],1)
        self.assertEqual(before['run_candidates'],[])
        self.assertEqual(before['unresolved_measurements'][0]['measurement_id'],'stroke')
        stroke['points'][1][0]=12
        self.assertNotEqual(before['measurement_inputs_sha256'],from_state(state(stroke))['measurement_inputs_sha256'])

    def test_union_overlap_and_gap_are_separate_quantities(self):
        result=from_state(state(line('a',[0,0],[10,0]),line('b',[8,0],[15,0]),line('c',[20,0],[25,0])))
        run=result['run_candidates'][0]
        self.assertEqual(run['visible_union_lf'],20)
        self.assertEqual(run['overlapping_piece_lf'],2)
        self.assertEqual(run['gross_alignment_span_lf'],25)
        self.assertEqual(run['gaps'][0]['length_lf'],5)
        self.assertIsNone(result['whole_wall_quantity']);self.assertIsNone(result['purchase_quantity'])

    def test_page_scale_and_perpendicular_segments_are_separate(self):
        result=from_state(state(line('a',[0,0],[10,0]),line('b',[0,0],[0,10]),
            line('c',[0,0],[10,0],page=2),line('d',[0,0],[10,0],ppf=2)))
        self.assertEqual(len(result['run_candidates']),4)

    def test_alignment_groups_do_not_drift_by_chained_tolerance(self):
        items=[line(str(i),[0,y],[10,y],ppf=12) for i,y in enumerate((0,.2,.4))]
        result=from_state(state(*items))
        self.assertEqual(len(result['run_candidates']),2)
        self.assertTrue(all(r['centerline_coordinate_range_pt'][1]-r['centerline_coordinate_range_pt'][0]<=.25 for r in result['run_candidates']))

    def test_short_pieces_diagonal_and_polyline_do_not_get_invented_axes(self):
        square={**line('square',[0,0],[3,0]),'kind':'area','points':[[0,0],[3,0],[3,3],[0,3]]}
        bent={**line('bent',[0,0],[10,0]),'points':[[0,0],[10,0],[10,10]]}
        result=from_state(state(square,bent,line('diagonal',[0,0],[10,10])))
        self.assertEqual(result['run_candidates'],[])
        self.assertEqual(len(result['unresolved_measurements']),3)

    def test_edit_recomputes_from_points_not_saved_bounds_or_orientation(self):
        original=state(line('a',[0,0],[10,0]),line('b',[15,0],[20,0]))
        edited=copy.deepcopy(original);edited['version']=2
        edited['measurements']['a'].update(points=[[0,0],[12,0]],source_bounds_pt=[0,0,10,1],orientation='vertical')
        before=from_state(original);after=from_state(edited)
        self.assertEqual(after['run_candidates'][0]['gaps'][0]['length_lf'],3)
        self.assertEqual(after['measurement_version'],2)
        self.assertNotEqual(before['measurement_inputs_sha256'],after['measurement_inputs_sha256'])
        self.assertEqual(original['measurements']['a']['points'],[[0,0],[10,0]])

    def test_order_is_deterministic_and_other_measurements_are_not_wall_pieces(self):
        a=line('a',[10,0],[0,0]);b=line('b',[15,0],[20,0])
        self.assertEqual(from_state(state(a,b)),from_state(state(b,a)))
        diagonal=line('diagonal',[0,0],[1,1])
        other_diagonal=line('another-diagonal',[0,0],[2,2])
        self.assertEqual(from_state(state(diagonal,other_diagonal)),from_state(state(other_diagonal,diagonal)))
        other={**a,'source_method':'unrelated-line'}
        self.assertEqual(from_state(state(other))['source_wall_candidates'],0)


if __name__=='__main__':unittest.main()
