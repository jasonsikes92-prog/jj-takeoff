import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import fitz
from window_symbol_candidates import recognize,apply_from_plan
from native_door_interpretation import interpret


def opening():
    return {'opening_id':'window','page':1,'tag':'3050SH','points':[[50,50],[86,50]],
        'points_per_foot':12,'printed_nominal_size':{'width_inches':36,'height_inches':60,'type_code':'SH'},
        'source_sha256':'opening-source','review_status':'role_unreviewed','role':None,
        'window_component_count':None,'door_configuration':None,'drawn_panel_count':None}


def segments():
    return [[[51,50],[85,50]],[[51,50.75],[85,50.75]]]+[
        [[x,48],[x,52]] for x in (50,51,85,86)]


def drawings(lines=None):
    return [{'type':'s','color':(0,0,0),'stroke_opacity':1,'dashes':'[] 0',
             'items':[('l',fitz.Point(*a),fitz.Point(*b))]} for a,b in (lines or segments())]


class WindowSymbols(unittest.TestCase):
    def test_coded_tag_and_glazing_frame_support_window_without_unit_count(self):
        result=recognize([opening()],{1:drawings()},'plan')
        c,=result['candidates'];self.assertEqual(c['status'],'candidate_requires_review')
        self.assertIsNone(c['window_component_count']);self.assertFalse(c['product_fit_verified'])

    def test_rotated_symbol_uses_its_gap_frame(self):
        o=opening();o['points']=[p[::-1] for p in o['points']]
        lines=[[p[::-1] for p in pair] for pair in segments()]
        self.assertEqual(len(recognize([o],{1:drawings(lines)},'plan')['candidates']),1)

    def test_bare_or_unsupported_tag_wrong_width_missing_jamb_and_rectangle_only_are_not_windows(self):
        for code in (None,'DH','MUL'):
            o=opening();o['printed_nominal_size']['type_code']=code
            self.assertEqual(recognize([o],{1:drawings()},'plan')['candidates'],[])
        o=opening();o['points'][1][0]+=3
        self.assertEqual(recognize([o],{1:drawings()},'plan')['candidates'],[])
        self.assertEqual(recognize([opening()],{1:drawings(segments()[:-1])},'plan')['candidates'],[])
        rectangle=[[[50,50],[86,50]],[[50,50.75],[86,50.75]],[[50,48],[50,52]],[[86,48],[86,52]]]
        self.assertEqual(recognize([opening()],{1:drawings(rectangle)},'plan')['candidates'],[])

    def test_hidden_white_fill_and_other_page_strokes_are_ignored(self):
        for changes in ({'stroke_opacity':0},{'color':(1,1,1)},{'type':'f'},{'dashes':'[3 2] 0'}):
            ds=[{**d,**changes} for d in drawings()]
            self.assertEqual(recognize([opening()],{1:ds},'plan')['candidates'],[])
        self.assertEqual(recognize([opening()],{2:drawings()},'plan')['candidates'],[])

    def test_duplicate_strokes_are_deduplicated_but_different_glazing_pairs_are_ambiguous(self):
        ds=drawings();self.assertEqual(len(recognize([opening()],{1:ds+ds},'plan')['candidates'][0]['evidence']['matches']),1)
        ds+=drawings([[[51,49],[85,49]]])
        self.assertEqual(recognize([opening()],{1:ds},'plan')['candidates'][0]['status'],'ambiguous_symbols')

    def test_actual_pdf_roles_preserve_review_and_propagate_window_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan=Path(tmp)/'plan.pdf'
            with fitz.open() as doc:
                p=doc.new_page(width=200,height=200)
                for a,b in segments():p.draw_line(a,b,color=(0,0,0))
                doc.save(plan)
            sha=hashlib.sha256(plan.read_bytes()).hexdigest()
            base={'plan_sha256':sha,'measurement_version':1,'openings':[opening()],
                'reviewed_role_counts':{'window':0,'interior_door':0},'unresolved_opening_ids':['window'],
                'stale_or_missing_label_ids':[],'unlocated_opening_tags':[],'enumerated_window_unit_count':None}
            original=copy.deepcopy(base);result=apply_from_plan(plan,base)
            self.assertEqual(base,original);self.assertEqual(result['openings'][0]['role'],'window')
            self.assertEqual(result['inferred_role_counts']['window'],1)
            self.assertIsNone(result['enumerated_window_unit_count'])
            rooms={'plan_sha256':sha,'measurement_version':1,'opening_connections':[],'regions':[]}
            self.assertEqual(interpret(result,rooms)['inferred_opening_ids'],['window'])
            base['openings'][0].update(review_status='current_source_review',role='window',window_component_count=2)
            base['enumerated_window_unit_count']=2
            reviewed=apply_from_plan(plan,base)
            self.assertEqual(reviewed['openings'][0]['window_component_count'],2)
            self.assertEqual(reviewed['openings'][0]['review_status'],'current_source_review')
            base['openings'][0].update(role='interior_door')
            conflict=apply_from_plan(plan,base)['openings'][0]
            self.assertEqual(conflict['review_status'],'symbol_conflict_requires_review');self.assertIsNone(conflict['role'])
            base['openings'][0].update(review_status='stale_source_review',role=None)
            self.assertEqual(apply_from_plan(plan,base)['openings'][0]['review_status'],'stale_source_review')
            plan.write_bytes(plan.read_bytes()+b' ')
            with self.assertRaises(ValueError):apply_from_plan(plan,original)

    def test_source_binding_changes_with_tag_gap_and_drawing_evidence(self):
        o=opening();ds=drawings();before=recognize([o],{1:ds},'plan')['candidates'][0]['source_sha256']
        for changed in ('tag','source_sha256'):
            value=copy.deepcopy(o);value[changed]+=' changed'
            self.assertNotEqual(recognize([value],{1:ds},'plan')['candidates'][0]['source_sha256'],before)

    def test_window_closure_is_a_source_bound_hypothesis_and_not_added_material(self):
        import test_wall_enclosure_candidates as fixtures
        from wall_enclosure_candidates import candidates
        fixture=fixtures.WallEnclosures();fixture.setUp()
        fixture.state['measurements']['top']['points'][1][0]=48
        fixture.add('top2',[[72,2],[116,2]])
        runs,gaps,openings=fixture.sources(True)
        row=openings['openings'][0]
        row.update(role='window',review_status='native_symbol_inference',source_sha256='opening',
            native_interpretation={'kind':'window','evidence':{'plan_sha256':'plan','opening_source_sha256':'opening'}})
        result=candidates(fixture.state,runs,gaps,openings)
        self.assertEqual(result['candidate_enclosures'][0]['gross_boundary_sf'],100)
        self.assertIn('hypothesis',result['gap_closures'][0]['basis'])
        self.assertNotIn(row['gap_id'],result['unresolved_gap_ids'])
        self.assertIsNone(result['purchase_quantity']);self.assertIsNone(result['whole_floor_area'])
        row['native_interpretation']['evidence']['opening_source_sha256']='old'
        self.assertEqual(candidates(fixture.state,runs,gaps,openings)['candidate_enclosures'],[])


if __name__=='__main__':unittest.main()
