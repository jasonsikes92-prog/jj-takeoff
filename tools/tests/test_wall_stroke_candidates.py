import sys
import unittest
from pathlib import Path
import fitz
import math
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_stroke_candidates import candidates


class WallStrokeCandidates(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.addCleanup(self.doc.close)
        self.page=self.doc.new_page(width=600,height=600)

    def line(self,a,b,**kwargs):self.page.draw_line(a,b,width=1,**kwargs)
    def extract(self):return candidates(self.page,12,[10,10,400,400])

    def test_visible_overlap_only_and_view_excludes_details(self):
        self.line((20,20),(140,20));self.line((30,23.5),(160,23.5))
        self.line((450,20),(550,20));self.line((450,23.5),(550,23.5))
        found=self.extract()['measurements'];self.assertEqual(len(found),1)
        self.assertEqual(found[0]['points'],[[30,21.75],[140,21.75]])
        self.assertEqual(found[0]['source_cad_paths'],[0,1]);self.assertEqual(found[0]['dependent_rows'],[])
        self.assertFalse(found[0]['certified'])

    def test_competing_faces_are_withheld_not_arbitrarily_selected(self):
        for y in [20,23,26]:self.line((20,y),(140,y))
        result=self.extract();self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['ambiguous_pairs']),2)
        self.assertEqual(len(result['blocked_intervals']),1)

    def test_intervening_face_removes_outer_pair_without_inventing_wall_width(self):
        for y in [20,20.5,24]:self.line((20,y),(140,y))
        result=self.extract();self.assertEqual(len(result['measurements']),1)
        self.assertEqual(result['measurements'][0]['points'],[[20,22.25],[140,22.25]])
        self.assertEqual(result['measurements'][0]['drawn_thickness_inches'],3.5)
        self.assertEqual(result['blocked_intervals'][0]['intervening_segment_indices'],[1])

    def test_partial_intervening_face_partitions_instead_of_erasing_whole_pair(self):
        self.line((20,20),(200,20));self.line((20,24),(200,24))
        self.line((80,20.5),(140,20.5))
        result=self.extract()
        self.assertEqual({tuple(map(tuple,m['points'])) for m in result['measurements']},
            {((20,22),(80,22)),((80,22.25),(140,22.25)),((140,22),(200,22))})
        self.assertEqual([(p['low'],p['high']) for p in result['blocked_intervals']],[(80,140)])

    def test_short_intervening_face_still_blocks_the_affected_interval(self):
        self.line((20,20),(200,20));self.line((20,24),(200,24))
        self.line((80,20.5),(85,20.5))
        result=self.extract()
        self.assertEqual([(p['low'],p['high']) for p in result['blocked_intervals']],[(80,85)])
        self.assertEqual(len(result['measurements']),3)

    def test_deduplicate_edges_keep_provenance_and_allow_nonoverlapping_pairs(self):
        self.line((20,20),(200,20));self.line((20,20),(200,20))
        self.line((20,23.5),(80,23.5));self.line((100,23.5),(200,23.5))
        found=self.extract()['measurements'];self.assertEqual(len(found),2)
        self.assertEqual(found[0]['source_cad_paths'],[0,1,2])

    def test_vertical_clipping_uses_original_edge_evidence(self):
        self.line((20,0),(20,500));self.line((23.5,0),(23.5,500))
        found=self.extract()['measurements'][0]
        self.assertEqual(found['points'],[[21.75,10],[21.75,400]])
        self.assertEqual(found['source_edges'][0]['points_pt'],[[20,0],[20,500]])

    def test_same_geometry_in_two_styles_has_one_identity(self):
        for color in [(0,0,0),(1,0,0)]:
            self.line((20,20),(140,20),color=color)
            self.line((20,23.5),(140,23.5),color=color)
        found=self.extract()['measurements'];self.assertEqual(len(found),1)
        self.assertEqual(found[0]['source_cad_paths'],[0,1,2,3])

    def test_nonmatching_styles_dashes_and_short_edges_excluded(self):
        self.line((20,20),(140,20));self.line((20,23.5),(140,23.5),color=(1,0,0))
        self.line((20,40),(140,40),dashes='[2 2]');self.line((20,43.5),(140,43.5),dashes='[2 2]')
        self.line((20,60),(22,60));self.line((20,63.5),(22,63.5))
        self.assertEqual(self.extract()['measurements'],[])

    def diagonal(self,angle,offset=0,start=0,end=120):
        u=(math.cos(angle),math.sin(angle));v=(-u[1],u[0])
        point=lambda t:(200+t*u[0]+offset*v[0],200+t*u[1]+offset*v[1])
        self.line(point(start),point(end))

    def test_diagonal_length_uses_parallel_face_overlap_and_normal_depth(self):
        self.diagonal(math.pi/6);self.diagonal(math.pi/6,3.5,20,160)
        result=self.extract();self.assertEqual(len(result['measurements']),1)
        m=result['measurements'][0]
        self.assertAlmostEqual(math.dist(*m['points']),100,places=3)
        self.assertAlmostEqual(m['drawn_thickness_inches'],3.5,places=3)
        self.assertEqual(m['orientation'],'diagonal')
        self.assertEqual(m['dependent_rows'],[]);self.assertFalse(m['certified'])

    def test_diagonal_intervening_faces_and_competing_layers_stay_unresolved(self):
        for offset in (0,3,6):self.diagonal(-math.pi/4,offset)
        result=self.extract()
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['ambiguous_pairs']),2)
        self.assertEqual(len(result['blocked_intervals']),1)

    def test_diagonal_clipping_respects_original_view_and_keeps_original_edges(self):
        self.diagonal(math.pi/4,0,-400,400);self.diagonal(math.pi/4,3.5,-400,400)
        result=self.extract();self.assertEqual(len(result['measurements']),1)
        m=result['measurements'][0]
        self.assertTrue(all(10<=x<=400 and 10<=y<=400 for x,y in m['source_outline_pt']))
        self.assertTrue(any(x<10 or y<10 for edge in m['source_edges'] for x,y in edge['points_pt']))

    def test_diagonal_short_piece_remains_rotated_outline(self):
        self.diagonal(math.pi/4,0,0,3.5);self.diagonal(math.pi/4,3.5,0,3.5)
        result=self.extract();self.assertEqual(result['short_piece_candidates'],1)
        m=result['measurements'][0]
        self.assertEqual(m['kind'],'area');self.assertEqual(len(m['points']),4)
        from measurement_store import calculate
        self.assertAlmostEqual(calculate(m)['quantity'],3.5*3.5/144,places=5)

    def test_rotated_corner_detected_from_both_axes_is_one_piece(self):
        u=math.sqrt(.5)
        points=[(200,200),(200+3.5*u,200+3.5*u),(200,200+7*u),(200-3.5*u,200+3.5*u)]
        for a,b in zip(points,points[1:]+points[:1]):self.line(a,b)
        result=self.extract();self.assertEqual(result['short_piece_candidates'],1)
        self.assertEqual(result['measurements'][0]['source_cad_paths'],[0,1,2,3])

    def test_diagonal_duplicate_edges_preserve_one_quantity_and_sources(self):
        self.diagonal(math.pi/6);self.diagonal(math.pi/6,0,120,0)
        self.diagonal(math.pi/6,3.5)
        result=self.extract();self.assertEqual(len(result['measurements']),1)
        self.assertEqual(result['measurements'][0]['source_cad_paths'],[0,1,2])

    def test_diagonal_is_reported_as_unresolved_in_run_analysis(self):
        self.diagonal(math.pi/6);self.diagonal(math.pi/6,3.5)
        m=self.extract()['measurements'][0]
        m['wall_depth_basis']={'depth_inches':3.5};m['expected_depth_inches']=3.5
        from wall_run_candidates import from_state
        r=from_state({'plan_sha256':'test','version':1,'measurements':{m['id']:m}})
        self.assertEqual(r['source_wall_candidates'],1)
        self.assertEqual(len(r['unresolved_measurements']),1)
        self.assertEqual(r['wall_network_inference']['decisions'],{})
        self.assertEqual(r['run_candidates'],[]);self.assertIsNone(r['purchase_quantity'])

    def test_near_horizontal_noise_and_nonparallel_lines_are_not_paired(self):
        self.line((20,20),(300,20.002));self.line((20,23.5),(300,23.502))
        self.line((200,100),(300,200));self.line((203,100),(307,200))
        self.assertEqual(self.extract()['measurements'],[])

    def test_invalid_scale_and_region_rejected(self):
        for scale in [True,0,-1,float('nan')]:
            with self.assertRaises(ValueError):candidates(self.page,scale,[0,0,100,100])
        for region in [[0,0,700,100],[10,10,5,20],[0,0,float('inf'),100]]:
            with self.assertRaises(ValueError):candidates(self.page,12,region)

    def test_style_filter_is_explicit_not_a_global_wall_width(self):
        self.line((20,20),(140,20));self.line((20,23.5),(140,23.5))
        self.page.draw_line((20,60),(140,60),width=.2)
        self.page.draw_line((20,63.5),(140,63.5),width=.2)
        self.assertEqual(len(self.extract()['measurements']),2)
        result=candidates(self.page,12,[10,10,400,400],[{'color':[0,0,0],'width_pt':1}])
        self.assertEqual(len(result['measurements']),1)
        self.assertEqual(result['measurements'][0]['source_cad_paths'],[0,1])

    def test_expected_depth_keeps_mismatched_layer_evidence(self):
        for y in [20,23.5,28]:self.line((20,y),(140,y))
        self.assertEqual(len(self.extract()['ambiguous_pairs']),2)
        result=candidates(self.page,12,[10,10,400,400],expected_depth_inches=3.5)
        self.assertEqual(len(result['measurements']),1)
        self.assertEqual(result['measurements'][0]['points'],[[20,21.75],[140,21.75]])
        self.assertEqual(result['depth_mismatched_intervals'][0]['thickness'],4.5)
        self.assertFalse(result['coverage_certified'])

    def test_project_depth_changes_candidates_and_no_match_stays_empty(self):
        for y in [20,23.5,60,65.5]:self.line((20,y),(140,y))
        result=candidates(self.page,12,[10,10,400,400],expected_depth_inches=5.5)
        self.assertEqual(result['measurements'][0]['points'],[[20,62.75],[140,62.75]])
        result=candidates(self.page,12,[10,10,400,400],expected_depth_inches=4.5)
        self.assertEqual(result['measurements'],[]);self.assertEqual(len(result['depth_mismatched_intervals']),2)

    def test_invalid_expected_depth_rejected(self):
        for value in [True,0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):candidates(self.page,12,[10,10,400,400],expected_depth_inches=value)

    def test_short_return_retains_visible_length_and_square_retains_outline(self):
        self.line((20,20),(28,20));self.line((20,23.5),(28,23.5))
        for a,b in [((50,20),(53.5,20)),((50,23.5),(53.5,23.5)),
                    ((50,20),(50,23.5)),((53.5,20),(53.5,23.5))]:self.line(a,b)
        result=self.extract()
        self.assertEqual(result['length_candidates'],1)
        self.assertEqual(result['short_piece_candidates'],1)
        segment=next(m for m in result['measurements'] if m['kind']=='length')
        outline=next(m for m in result['measurements'] if m['kind']=='area')
        self.assertEqual(segment['points'],[[20,21.75],[28,21.75]])
        self.assertEqual(outline['points'],[[50,20],[53.5,20],[53.5,23.5],[50,23.5]])
        self.assertEqual(len(outline['source_edges']),4)
        self.assertEqual(outline['orientation'],'unresolved_short_piece')

    def test_short_competing_pairs_are_withheld_and_subminimum_not_invented(self):
        for y in [20,23,26]:self.line((20,y),(25,y))
        self.line((50,20),(52,20));self.line((50,23.5),(52,23.5))
        result=self.extract()
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['ambiguous_pairs']),2)


if __name__=='__main__':unittest.main()
