import math
import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_face_candidates import candidates
from measurement_store import calculate


class RoofCandidates(unittest.TestCase):
    def page(self,color=(.3,.2,.7),pitch='8 : 12',closed=True):
        doc=fitz.open();self.addCleanup(doc.close);p=doc.new_page(width=400,height=400)
        points=[(20,20),(120,20),(120,120),(20,120)]
        if closed:points.append(points[0])
        p.draw_polyline(points,color=color)
        p.insert_text((45,75),pitch,fontsize=10)
        return p

    def test_closed_loop_has_pitch_and_scale_without_color_or_path_indices(self):
        for color in [(0,0,0),(.3,.2,.7)]:
            r=candidates(self.page(color=color),10)
            self.assertEqual(len(r['measurements']),1)
            m=r['measurements'][0]
            self.assertAlmostEqual(calculate(m)['quantity'],100*math.hypot(12,8)/12)
            self.assertTrue(m['engine_line_ids']);self.assertFalse(r['certified'])

    def test_open_loop_and_non_pitch_text_are_not_faces(self):
        self.assertEqual(candidates(self.page(closed=False),10)['measurements'],[])
        self.assertEqual(candidates(self.page(pitch='812'),10)['measurements'],[])

    def test_conflicting_pitch_labels_within_one_loop_are_not_guessed(self):
        p=self.page();p.insert_text((45,95),'12 : 12',fontsize=10)
        r=candidates(p,10)
        self.assertEqual(r['measurements'],[])
        self.assertEqual(len(r['unmatched_or_ambiguous_pitch_labels']),2)

    def test_unlabeled_source_outline_is_retained_without_physical_quantity(self):
        p=self.page(pitch='ROOF')
        result=candidates(p,10)
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['unresolved_source_outlines']),1)
        outline=result['unresolved_source_outlines'][0]
        self.assertEqual(outline['reason'],'No embedded pitch label')
        self.assertEqual(outline['pitch_labels'],[])
        self.assertEqual(outline['source_cad_paths'],[0])
        self.assertIsNone(outline['physical_quantity'])
        self.assertNotIn('surface_factor',outline)

    def test_conflicting_outline_is_retained_even_when_its_labels_have_other_faces(self):
        p=self.page(pitch='6 : 12')
        p.insert_text((75,95),'8 : 12',fontsize=10)
        p.draw_rect((30,50,75,80),color=(1,0,0))
        p.draw_rect((65,80,115,105),color=(0,0,1))
        result=candidates(p,10)
        self.assertEqual(len(result['measurements']),2)
        self.assertEqual(result['unmatched_or_ambiguous_pitch_labels'],[])
        self.assertEqual(len(result['unresolved_source_outlines']),1)
        outline=result['unresolved_source_outlines'][0]
        self.assertEqual(outline['reason'],'Conflicting embedded pitch labels')
        self.assertEqual({l['rise'] for l in outline['pitch_labels']},{6,8})
        self.assertIsNone(outline['physical_quantity'])

    def test_reviewed_styles_exclude_unrelated_unresolved_underlay(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.draw_rect((200,200,300,300),color=(.6,.6,.6))
        raw=candidates(p,10,[10,10,350,350])
        selected=candidates(p,10,[10,10,350,350],[{'color':[0,0,0],'width_pt':1}])
        self.assertEqual(len(raw['unresolved_source_outlines']),1)
        self.assertEqual(selected['unresolved_source_outlines'],[])

    def test_scale_must_be_valid(self):
        for scale in [0,-1,float('nan'),True]:
            with self.assertRaises(ValueError):candidates(self.page(),scale)

    def test_selected_view_excludes_other_geometry_and_pitch_labels(self):
        p=self.page()
        p.draw_rect((200,200,300,300),color=(.1,.7,.1))
        p.insert_text((230,250),'4 : 12',fontsize=10)
        result=candidates(p,10,[10,10,150,150])
        self.assertEqual(len(result['measurements']),1);self.assertEqual(len(result['pitch_labels']),1)
        self.assertEqual(result['measurements'][0]['pitch_candidate']['rise'],8)
        self.assertEqual(result['measurements'][0]['source_view_bounds_pt'],[10,10,150,150])
        self.assertFalse(result['certified'])

    def test_view_does_not_clip_crossing_geometry_into_a_new_face(self):
        p=self.page()
        result=candidates(p,10,[30,30,110,110])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),1)

    def test_invalid_view_rectangles_are_rejected(self):
        p=self.page()
        for bounds in ([0,0,500,500],[100,0,10,100],[0,0,float('nan'),100],[True,0,100,100],[0,0,100]):
            with self.assertRaises(ValueError):candidates(p,10,bounds)

    def test_shared_edge_recovers_two_faces_only_in_selected_view(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.draw_line((120,20),(220,20));p.draw_line((220,20),(220,120))
        p.draw_line((220,120),(120,120));p.insert_text((145,75),'8 : 12',fontsize=10)
        self.assertEqual(candidates(p,10)['measurements'],[])
        result=candidates(p,10,[10,10,240,140])
        self.assertEqual(len(result['measurements']),2)
        self.assertEqual(result['unmatched_or_ambiguous_pitch_labels'],[])
        self.assertAlmostEqual(sum(calculate(m)['quantity'] for m in result['measurements']),
            100*(math.hypot(12,6)+math.hypot(12,8))/12)
        self.assertTrue(all(0 in m['source_cad_paths'] for m in result['measurements']))
        self.assertFalse(result['certified'])

    def test_nested_ring_withholds_outer_area_even_without_branch_nodes(self):
        p=self.page(color=(0,0,0))
        p.draw_rect((80,85,100,105))
        result=candidates(p,10,[10,10,140,140])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['complex_face_candidates']),1)
        face=result['complex_face_candidates'][0]
        self.assertEqual(len(face['holes']),1)
        self.assertIsNone(face['physical_quantity'])
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),1)

    def test_dangling_line_preserves_face_and_reports_open_edge(self):
        p=self.page(color=(0,0,0));p.draw_line((120,20),(170,10))
        result=candidates(p,10,[5,5,190,140])
        self.assertEqual(len(result['measurements']),1)
        self.assertEqual(result['edge_network_diagnostics'][0]['dangling_edges'],1)
        self.assertEqual(result['measurements'][0]['source_cad_paths'],[0])

    def test_intervening_annotation_does_not_hide_dormer_ring(self):
        p=self.page(color=(0,0,0))
        p.draw_line((25,130),(100,130),color=(0,0,1))
        p.draw_rect((80,85,100,105))
        result=candidates(p,10,[10,10,140,140])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['complex_face_candidates']),1)
        self.assertEqual(result['complex_face_candidates'][0]['source_cad_paths'],[0,2])

    def test_other_style_simple_outline_cannot_bypass_cutout(self):
        p=self.page(color=(0,0,0))
        p.draw_rect((80,85,100,105))
        p.draw_rect((21,21,119,119),color=(0,0,1))
        result=candidates(p,10,[10,10,140,140])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['complex_face_candidates']),1)
        self.assertEqual(len(result['cutout_conflicting_outlines']),2)
        self.assertTrue(all(row['physical_quantity'] is None for row in result['cutout_conflicting_outlines']))
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),1)

    def test_selected_view_does_not_bridge_gap_or_guess_conflicting_pitch(self):
        p=self.page(color=(0,0,0),closed=False)
        p.draw_line((20,120),(20,20.1))
        self.assertEqual(candidates(p,10,[10,10,140,140])['measurements'],[])
        p=self.page(color=(0,0,0));p.draw_line((120,20),(170,10))
        p.insert_text((45,95),'10 : 12',fontsize=10)
        result=candidates(p,10,[5,5,190,140])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),2)

    def test_overlapping_closed_source_faces_are_not_trimmed_by_network(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.draw_line((25,140),(190,140),color=(0,0,1))
        p.draw_rect((100,20,200,120))
        p.insert_text((145,75),'8 : 12',fontsize=10)
        result=candidates(p,10,[10,10,220,160])
        self.assertEqual(len(result['measurements']),2)
        for row in result['measurements']:
            self.assertAlmostEqual(calculate(row)['quantity']/row['surface_factor'],100)
            self.assertEqual(row['source_method'],'style-run closed CAD loop and embedded pitch text')
        self.assertEqual(len(result['overlapping_face_candidates']),1)
        self.assertAlmostEqual(result['overlapping_face_candidates'][0]['overlap_area_pt2'],2000)
        self.assertEqual(len(result['network_alternatives']),2)
        self.assertFalse(result['certified'])

    def test_two_explicit_outlines_for_one_pitch_remain_ambiguous(self):
        p=self.page(color=(0,0,0))
        p.draw_line((25,140),(190,140),color=(0,0,1))
        p.draw_rect((30,30,140,130))
        result=candidates(p,10,[10,10,160,160])
        self.assertEqual(len(result['measurements']),2)
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),1)

    def test_style_selection_preserves_separate_closed_source_outlines(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.draw_line((25,140),(190,140),color=(0,0,1))
        p.draw_rect((100,20,200,120))
        p.insert_text((145,75),'8 : 12',fontsize=10)
        raw=candidates(p,10,[10,10,220,160])
        selected=candidates(p,10,[10,10,220,160],[{'color':[0,0,0],'width_pt':1}])
        self.assertEqual(selected['measurements'],raw['measurements'])
        self.assertEqual(selected['overlapping_face_candidates'],raw['overlapping_face_candidates'])

    def test_repeated_agreeing_labels_preserve_closed_face_and_all_evidence(self):
        p=self.page(pitch='6 : 12')
        p.insert_text((45,95),'6 : 12',fontsize=10)
        for bounds in (None,[10,10,150,150]):
            result=candidates(p,10,bounds)
            self.assertEqual(len(result['measurements']),1)
            m=result['measurements'][0]
            self.assertEqual(len(m['pitch_candidates']),2)
            self.assertAlmostEqual(calculate(m)['quantity'],100*math.hypot(12,6)/12)
            self.assertEqual(result['multiple_pitch_label_candidates'][0]['candidate_id'],m['id'])
            self.assertFalse(result['certified'])
            self.assertIsNone(result['multiple_pitch_label_candidates'][0]['physical_quantity'])

    def test_shared_network_retains_agreeing_labels_but_never_conflicting_slopes(self):
        for extra,expected in [('6 : 12',2),('10 : 12',1)]:
            p=self.page(color=(0,0,0),pitch='6 : 12')
            p.insert_text((45,95),extra,fontsize=10)
            p.draw_line((120,20),(220,20));p.draw_line((220,20),(220,120))
            p.draw_line((220,120),(120,120));p.insert_text((145,75),'8 : 12',fontsize=10)
            result=candidates(p,10,[10,10,240,140])
            self.assertEqual(len(result['measurements']),expected)
            if extra=='6 : 12':
                self.assertEqual(len(result['multiple_pitch_label_candidates']),1)
                self.assertAlmostEqual(sum(calculate(m)['quantity'] for m in result['measurements']),
                    100*(math.hypot(12,6)+math.hypot(12,8))/12)

    def test_repeated_labels_do_not_bypass_roof_hole(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.insert_text((45,95),'6 : 12',fontsize=10)
        p.draw_rect((85,85,105,105))
        result=candidates(p,10,[10,10,140,140])
        self.assertEqual(result['measurements'],[])
        self.assertEqual(len(result['complex_face_candidates']),1)
        self.assertEqual(len(result['complex_face_candidates'][0]['pitch_candidates']),2)

    def test_shared_pitch_label_between_source_outlines_stays_ambiguous(self):
        p=self.page(color=(0,0,0),pitch='6 : 12')
        p.insert_text((45,95),'6 : 12',fontsize=10)
        p.draw_line((25,140),(190,140),color=(0,0,1))
        p.draw_rect((30,30,140,130))
        result=candidates(p,10,[10,10,160,160])
        self.assertEqual(len(result['measurements']),2)
        self.assertEqual(len(result['unmatched_or_ambiguous_pitch_labels']),2)
        self.assertEqual(len(result['multiple_pitch_label_candidates']),2)

    def test_repeated_label_evidence_reaches_unsent_bid(self):
        from roof_partition_review import audit_faces
        from roof_bid_scope import build_scope,render_markdown
        p=self.page(pitch='6 : 12');p.insert_text((45,95),'6 : 12',fontsize=10)
        m=candidates(p,10)['measurements'][0]
        audit={'plan_sha256':'test','measurement_version':1,'measurements_sha256':'source',**audit_faces([m])}
        bid=build_scope(audit)
        self.assertEqual(bid['items'][0]['pitch_candidates'],m['pitch_candidates'])
        self.assertIn('Repeated agreeing labels; face ownership unresolved',render_markdown(bid))
        self.assertFalse(bid['sent']);self.assertFalse(bid['ready_to_order'])

    def test_repeated_label_changes_invalidate_complex_face_source_identity(self):
        import copy
        from roof_cutout_candidates import component_candidates
        p=self.page(color=(0,0,0),pitch='6 : 12');p.insert_text((45,95),'6 : 12',fontsize=10)
        p.draw_rect((85,85,105,105))
        face=candidates(p,10,[10,10,140,140])['complex_face_candidates'][0]
        before=component_candidates(face,10,400,400)
        changed=copy.deepcopy(face);changed['pitch_candidates'][1]['point_pt'][0]+=1
        after=component_candidates(changed,10,400,400)
        self.assertNotEqual(before['source_complex_face_sha256'],after['source_complex_face_sha256'])
        self.assertEqual(before['measurements'][0]['pitch_candidates'],face['pitch_candidates'])

if __name__=='__main__':unittest.main()
