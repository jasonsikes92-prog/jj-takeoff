import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from new_plan_measure import measure_job
from measurement_store import MeasurementStore


class NewPlanMeasure(unittest.TestCase):
    def test_reviewed_cross_view_candidates_are_published_without_count_approval(self):
        with fitz.open() as doc:
            doc.new_page().insert_text((50,50),'3062SH')
            doc.new_page().insert_text((50,50),'3050FX')
            doc.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory.update(plan_sha256=self.sha,role_candidates={'floor':[1],'elevations':[2]})
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}):
            summary=measure_job(self.job)
        self.assertEqual(summary['window_cross_view_candidate_count'],1)
        from window_cross_view_review import from_folder
        result=from_folder(self.job/'draft_takeoff')
        self.assertEqual(result['unrepresented_elevation_tags'][0]['tag'],'3050FX')
        self.assertFalse(result['certified']);self.assertIsNone(result['whole_building_count'])
        self.assertFalse(summary['estimate_released'])

    def test_new_measurement_automatically_writes_company_trade_scope_additions(self):
        from company_profile import initialize
        scale=self.prepare_floor()
        initialize(self.job/'plan.pdf',self.job,facts={'attic_HVAC':True})
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['company_scope_bid_files'],[
            'company_bid_scopes/framing_DRAFT.md','company_bid_scopes/plumbing_DRAFT.md','company_bid_scopes/tile_DRAFT.md'])
        self.assertFalse(summary['company_scope_bids_sent'])
        area_check=json.loads((self.job/'draft_takeoff'/summary['initial_area_schedule_check_file']).read_text())
        self.assertEqual(area_check['status'],summary['initial_area_schedule_check_status'])
        self.assertFalse(area_check['certified'])
        self.assertFalse(area_check['estimate_released'])
        folder=self.job/'draft_takeoff/company_bid_scopes'
        framing=json.loads((folder/'framing.json').read_text())
        plumbing=json.loads((folder/'plumbing.json').read_text())
        self.assertEqual(framing['items'][0]['applicability'],'included')
        self.assertIsNone(framing['items'][0]['reference_quantity'])
        self.assertEqual(plumbing['items'][0]['reference_quantity'],4)
        tile=json.loads((folder/'tile.json').read_text())
        self.assertEqual({i['source_rule']:i['specification'] for i in tile['items']}, {
            'tile.material_waste_percent':10,
            'tile.floor_underlayment_by_substrate':{'concrete_slab':'none_direct_to_slab','wood_floor':'cement_board',
                                                   'wood_floor_board_thickness_inches':.25},
            'tile.shower_wall_backer':{'supplier':'Floor and Decor','type':'waterproof_composite_board',
                                      'seal_joints_and_fasteners':True,'exact_product':None,
                                      'owner_product_name':'Sentinal fiber board'},
            'tile.shower_floor':'mortar_bed','tile.edge_finish':'Schluter_trim'})
        self.assertTrue(all((self.job/'draft_takeoff'/p).is_file() for p in summary['company_scope_bid_files']))
        from company_scope_review import read_decisions
        from drywall_bid_scope import estimating_practice
        config=json.loads((self.job/'draft_takeoff/drywall_practice_review.json').read_text())
        practice=estimating_practice(read_decisions(self.job/'draft_takeoff',config,self.sha))
        self.assertIs(practice['deduct_window_door_openings'],False)
        self.assertEqual(practice['billing_waste_percent'],0)
        from wall_plate_reference import from_folder as plate_reference
        reference=plate_reference(self.job/'draft_takeoff',MeasurementStore(self.job/'draft_takeoff').read())
        self.assertEqual(reference['plate_courses'],{'top':2,'bottom':1})
        self.assertIsNone(reference['purchase_quantity'])

    def prepare_stroke_view(self,short_pieces=False):
        scale=self.prepare_floor()
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            for a,b in [((20,20),(140,20)),((20,23.5),(140,23.5)),
                        ((200,20),(200,140)),((203.5,20),(203.5,140))]:page.draw_line(a,b,width=1)
            for y in [60,63.5]:page.draw_line((20,y),(140,y),width=.2)
            if short_pieces:
                for a,b in [((20,100),(28,100)),((20,103.5),(28,103.5)),
                            ((50,100),(53.5,100)),((50,103.5),(53.5,103.5))]:page.draw_line(a,b,width=1)
            page.insert_text((20,200),'1/4 in = 1 ft',fontsize=8)
            page.insert_text((370,30),'1 in = 1 ft',fontsize=8)
            doc.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['plan_sha256']=self.sha
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        review={'plan_sha256':self.sha,'page':1,'reviewer':'Synthetic source review','basis':'Floor view and two wall faces',
            'view_bounds_pt':[10,10,350,350],'wall_face_examples':[
                {'path':0,'item':0,'points_pt':[[20,20],[140,20]]},
                {'path':2,'item':0,'points_pt':[[200,20],[200,140]]}]}
        (self.job/'floor_wall_view_review.json').write_text(json.dumps(review))
        return scale

    def test_reviewed_wall_view_and_styles_reach_store_without_price_mapping(self):
        scale=self.prepare_stroke_view()
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],2)
        self.assertEqual(summary['wall_extraction_status'],'candidates_require_review')
        self.assertTrue(summary['wall_view_review_sha256'])
        self.assertEqual(summary['wall_run_unresolved_pieces'],2)
        self.assertEqual(summary['wall_stroke_ambiguous_intervals'],0)
        self.assertEqual(summary['wall_stroke_blocked_intervals'],0)
        state=MeasurementStore(self.job/'draft_takeoff').read()
        self.assertTrue(all(m['source_method']=='native_parallel_wall_strokes_v3' and not m['dependent_rows'] for m in state['measurements'].values()))
        saved=json.loads((self.job/'draft_takeoff/wall_segment_candidates.json').read_text())
        self.assertFalse(saved['printed_scales']['mixed_view_scales'])
        self.assertEqual(saved['wall_view_review']['allowed_styles'],[{'color':[0,0,0],'width_pt':1}])

    def test_short_returns_and_outlines_reach_store_as_unmapped_candidates(self):
        scale=self.prepare_stroke_view(short_pieces=True)
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],3)
        self.assertEqual(summary['wall_short_piece_candidates'],1)
        self.assertEqual(summary['wall_run_unresolved_pieces'],4)
        measurements=MeasurementStore(self.job/'draft_takeoff').read()['measurements']
        self.assertEqual(sum(m['kind']=='area' for m in measurements.values()),1)
        self.assertTrue(all(not m['dependent_rows'] for m in measurements.values()))

    def test_invalid_wall_view_stops_before_measurement_output(self):
        self.prepare_stroke_view()
        path=self.job/'floor_wall_view_review.json';r=json.loads(path.read_text());r['plan_sha256']='other'
        path.write_text(json.dumps(r))
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'another drawing'):measure_job(self.job)
        engine.assert_not_called();self.assertFalse((self.job/'draft_takeoff').exists())

    def install_stud_size(self,size='2x4'):
        from company_profile import initialize
        profile=self.job/'source_profile.json'
        profile.write_text(json.dumps({'profile_id':'test','version':1,'rules':[
            {'key':'framing.stud_size','value':'2x4','source':'Owner test rule','when':{}}]}))
        initialize(self.job/'plan.pdf',self.job,profile,
            project_overrides={} if size=='2x4' else {'framing.stud_size':size})

    def test_project_stud_size_is_used_without_inventing_matching_walls(self):
        scale=self.prepare_stroke_view();self.install_stud_size('2x6')
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],0)
        self.assertEqual(summary['wall_extraction_status'],'no_wall_pairs_match_stud_depth')
        self.assertEqual(summary['wall_stroke_depth_mismatched_intervals'],2)
        self.assertEqual(summary['wall_depth_basis']['provenance']['basis'],'project_override')

    def test_default_provenance_reaches_each_candidate(self):
        scale=self.prepare_stroke_view();self.install_stud_size()
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            measure_job(self.job)
        state=MeasurementStore(self.job/'draft_takeoff').read()
        self.assertTrue(all(m['wall_depth_basis']['depth_inches']==3.5
            and m['wall_depth_basis']['provenance']['basis']=='company_default'
            and not m['wall_depth_basis']['drawing_verified'] for m in state['measurements'].values()))

    def test_changed_intake_during_extraction_rejected(self):
        scale=self.prepare_stroke_view();self.install_stud_size()
        def engine(*args,**kwargs):
            path=self.job/'estimate_intake.json';path.write_text(path.read_text()+'\n')
            return {**self.result,'lines':[]}
        with patch('jnj_takeoff.run_takeoff',side_effect=engine),patch('dimension_scale.split_dimension_scale',return_value=scale):
            with self.assertRaisesRegex(ValueError,'assumption changed during'):measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff/measurements.json').exists())

    def prepare_floor(self):
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            page.draw_rect((20,20,140,23.5),color=None,fill=(1,1,0))
            doc.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory.update(plan_sha256=self.sha,unique_role_pages={'floor':1},roles_requiring_disambiguation={})
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        return {'usable_candidate':True,'points_per_foot':12,'controls':[], 'method':'synthetic calibrated dimensions'}

    def test_floor_wall_segments_reach_editable_store_without_purchase_mapping(self):
        scale=self.prepare_floor()
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],1)
        self.assertEqual(summary['editable_length_candidates'],1)
        store=MeasurementStore(self.job/'draft_takeoff');state=store.read()
        wall=next(iter(state['measurements'].values()))
        self.assertEqual(wall['result']['quantity'],10)
        runs=json.loads((self.job/'draft_takeoff'/summary['wall_run_candidate_file']).read_text())
        self.assertEqual(summary['wall_run_candidates'],1)
        self.assertEqual(runs['measurement_version'],state['version'])
        self.assertEqual(runs['run_candidates'][0]['visible_union_lf'],10)
        self.assertFalse(runs['certified'])
        tags=json.loads((self.job/'draft_takeoff'/summary['wall_gap_label_candidate_file']).read_text())
        self.assertEqual(tags['measurement_inputs_sha256'],runs['measurement_inputs_sha256'])
        self.assertEqual(summary['wall_gap_tag_matches'],0)
        self.assertEqual(tags['gaps'],[])
        revised=store.save(wall['id'],[[20,21.75],[152,21.75]],1,self.sha,'Synthetic one-foot extension')
        self.assertEqual(revised['measurements'][wall['id']]['result']['quantity'],11)
        self.assertEqual(wall['dependent_rows'],[])
        self.assertEqual(json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())['rules'],[])
        self.assertFalse(summary['wall_coverage_certified'])

    def test_floor_without_calibration_does_not_guess_wall_scale(self):
        scale=self.prepare_floor();scale.update(usable_candidate=False,points_per_foot=None)
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],0)
        self.assertEqual(summary['wall_extraction_status'],'scale_unresolved')

    def test_ambiguous_auto_area_view_preserves_other_candidates_and_records_reason(self):
        scale=self.prepare_floor();self.inventory['unique_role_pages']['area_schedule']=1
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), \
             patch('dimension_scale.split_dimension_scale',return_value=scale), \
             patch('native_area_discovery.discover',side_effect=ValueError('Ambiguous duplicate views')):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],1)
        self.assertEqual(summary['native_area_candidates'],0)
        review=json.loads((self.job/'draft_takeoff/native_area_candidates.json').read_text())
        self.assertEqual(review['reason'],'Ambiguous duplicate views')
        self.assertEqual(review['plan_sha256'],self.sha)
        self.assertFalse(summary['estimate_released'])

    def test_explicit_area_view_has_priority_over_automatic_discovery(self):
        scale=self.prepare_floor();self.inventory['unique_role_pages']['area_schedule']=1
        explicit={'review_sha256':'explicit-review','measurements':[]}
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), \
             patch('dimension_scale.split_dimension_scale',return_value=scale), \
             patch('native_area_candidates.from_review',return_value=explicit), \
             patch('native_area_discovery.discover') as automatic:
            summary=measure_job(self.job)
        automatic.assert_not_called()
        self.assertEqual(summary['native_area_review_sha256'],'explicit-review')

    def test_floor_with_mixed_views_does_not_apply_page_scale_to_walls(self):
        scale=self.prepare_floor()
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), patch('dimension_scale.split_dimension_scale',return_value=scale), patch('sheet_scale_labels.scale_labels',return_value={'labels':[],'mixed_view_scales':True}):
            summary=measure_job(self.job)
        self.assertEqual(summary['wall_segment_candidates'],0)
        self.assertEqual(summary['wall_extraction_status'],'view_scale_assignment_required')

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.job=Path(self.tmp.name)
        doc=fitz.open();doc.new_page(width=500,height=500);doc.save(self.job/'plan.pdf');doc.close()
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory={'plan_sha256':self.sha,'unique_role_pages':{'foundation':1},'roles_requiring_disambiguation':{'floor':[1,2]}}
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        line={'id':'area','page':0,'method':'synthetic','geometry':{'kind':'polygon','points':[[10,10],[110,10],[110,110],[10,110],[10,10]]}}
        self.result={'status':'more_information_required','pages':{0:{'ppf':10}},'lines':[line,{**copy.deepcopy(line),'id':'perimeter'}]}
        # These tests isolate geometry conversion. Real review gating and reviewed
        # page routing are exercised without this mock in test_plan_sheet_review.
        review=patch('new_plan_measure.read_sheet_review',side_effect=lambda job: {
            **self.inventory,'coverage_passed':True,'review_sha256':'synthetic-review'})
        review.start();self.addCleanup(review.stop)

    def prepare_region_scale(self,scale=10):
        from test_dimension_scale import DimensionScale
        fixture=DimensionScale();self.addCleanup(fixture.doCleanups)
        page=fixture.make_page(scales=(scale,scale,scale))
        page.parent.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['plan_sha256']=self.sha
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))

    def test_engine_geometry_without_dimension_controls_is_withheld(self):
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['editable_region_candidates'],0)
        self.assertFalse(summary['editor_available'])
        self.assertFalse(summary['estimate_released'])

    def test_engine_geometry_with_conflicting_dimension_scale_is_withheld(self):
        self.prepare_region_scale(20)
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['editable_region_candidates'],0)
        self.assertFalse(summary['estimate_released'])

    def test_engine_geometry_becomes_one_editable_candidate_without_pricing(self):
        self.prepare_region_scale()
        with patch('jnj_takeoff.run_takeoff',return_value=self.result) as engine:
            summary=measure_job(self.job)
        self.assertEqual(engine.call_args.args[1],{'foundation':0})
        self.assertEqual(summary['editable_region_candidates'],1)
        self.assertEqual(summary['unresolved_page_roles'],{'floor':[1,2]})
        self.assertTrue(summary['template_draft_available'])
        self.assertEqual(summary['opening_quantity_mapped_template_rows'],7)
        mapping=json.loads((self.job/'draft_takeoff'/summary['opening_quantity_mapping_file']).read_text())
        self.assertEqual(mapping['mapping_method'],'exact_template_opening_scopes_v3')
        self.assertEqual(mapping['plan_sha256'],self.sha)
        self.assertNotIn('opening_schedule_review.json',[p.name for p in (self.job/'draft_takeoff').iterdir()])
        template=json.loads((self.job/'draft_takeoff/template_rows.json').read_text())
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        self.assertEqual(len(template['rows']),711)
        self.assertEqual(rules,{'plan_sha256':self.sha,'rules':[]})
        store=MeasurementStore(self.job/'draft_takeoff');state=store.read()
        item=next(iter(state['measurements'].values()))
        self.assertEqual(item['result']['quantity'],100)
        self.assertEqual(item['engine_line_ids'],['area','perimeter'])
        changed=store.save(item['id'],[[10,10],[210,10],[210,110],[10,110]],1,self.sha,'Synthetic boundary correction')
        self.assertEqual(changed['measurements'][item['id']]['result']['quantity'],200)
        self.assertFalse(summary['estimate_released']);self.assertIsNone(summary['whole_house_total'])
        self.assertEqual(summary['roof_extraction_status'],'page_unresolved')
        self.assertFalse(summary['roof_coverage_certified'])
        with self.assertRaises(FileExistsError):measure_job(self.job)

    def test_wrong_drawing_stroke_definitions_stop_before_engine(self):
        (self.job/'electrical_stroke_definitions.json').write_text(json.dumps({'plan_sha256':'wrong'}))
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'another drawing'):measure_job(self.job)
            engine.assert_not_called()
        self.assertFalse((self.job/'draft_takeoff').exists())

    def test_stroke_symbols_reach_editor_but_not_purchase_quantity(self):
        from test_vector_stroke_candidates import draw_symbol
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=500);draw_symbol(p,50,50);draw_symbol(p,200,200,.5)
            doc.save(self.job/'plan.pdf')
        digest=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['plan_sha256']=digest
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        definition={'plan_sha256':digest,'pages':[{'page':1,'id':'switch','label':'Switch','meaning_source':'Synthetic legend',
            'bbox_pt':[35,25,65,75],'ink':'red','scale_range':[.4,.6],'maximum_error_ratio':.02}]}
        (self.job/'electrical_stroke_definitions.json').write_text(json.dumps(definition))
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['editable_count_candidates'],1)
        self.assertEqual(summary['electrical_stroke_status'],'candidates_require_review')
        state=MeasurementStore(self.job/'draft_takeoff').read()
        counts=[m for m in state['measurements'].values() if m['kind']=='count']
        self.assertEqual(counts[0]['result']['quantity'],1)
        from measurement_quantities import rollup
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        quantities=rollup(state,rules)
        self.assertEqual(quantities['quantities'],[]);self.assertEqual(len(quantities['pending_quantities']),1)
        self.assertFalse(summary['estimate_released'])

    def test_changed_plan_refused_before_engine_run(self):
        (self.job/'plan.pdf').write_bytes(b'changed')
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaises(ValueError):measure_job(self.job)
            engine.assert_not_called()

    def test_electrical_definitions_are_source_bound_and_export_located_counts(self):
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            page.insert_text((30,30),'R');page.insert_text((300,300),'R')
            doc.save(self.job/'plan.pdf')
        digest=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['plan_sha256']=digest
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        definition={'plan_sha256':digest,'pages':[{'page':1,
            'symbols':{'R':{'label':'Recessed light','meaning_source':'Sheet legend'}},
            'exclusions':[{'bbox_pt':[280,280,330,330],'source':'Schedule example'}]}]}
        (self.job/'electrical_symbol_definitions.json').write_text(json.dumps(definition))
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        saved=json.loads((self.job/'draft_takeoff/electrical_symbol_candidates.json').read_text())
        self.assertEqual(len(saved['measurements'][0]['points']),1)
        self.assertEqual(summary['electrical_extraction_status'],'candidates_require_review')
        self.assertFalse(summary['electrical_coverage_certified'])
        self.assertEqual(saved['plan_sha256'],digest)
        self.assertEqual(summary['editable_count_candidates'],1)
        state=MeasurementStore(self.job/'draft_takeoff').read()
        counts=[m for m in state['measurements'].values() if m['kind']=='count']
        self.assertEqual(len(counts),1);self.assertEqual(counts[0]['dependent_rows'],['204'])
        from measurement_quantities import rollup
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        quantities=rollup(state,rules)
        self.assertEqual(quantities['quantities'],[])
        self.assertEqual(len(quantities['pending_quantities']),1)

    def test_wrong_drawing_symbol_definitions_stop_before_engine(self):
        (self.job/'electrical_symbol_definitions.json').write_text(json.dumps({'plan_sha256':'wrong'}))
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'another drawing'):measure_job(self.job)
            engine.assert_not_called()
        self.assertFalse((self.job/'draft_takeoff').exists())

    def test_wrong_drawing_template_definitions_stop_before_engine(self):
        (self.job/'electrical_template_definitions.json').write_text(json.dumps({'plan_sha256':'wrong'}))
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'another drawing'):measure_job(self.job)
            engine.assert_not_called()
        self.assertFalse((self.job/'draft_takeoff').exists())

    def test_wrong_drawing_vector_definitions_stop_before_engine(self):
        (self.job/'electrical_vector_definitions.json').write_text(json.dumps({'plan_sha256':'wrong'}))
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'another drawing'):measure_job(self.job)
            engine.assert_not_called()
        self.assertFalse((self.job/'draft_takeoff').exists())

    def test_vector_outlets_reach_editor_and_pending_package_rules(self):
        from measurement_quantities import rollup
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            for x,y in ((40,40),(150,150)):
                page.draw_circle((x,y),10,color=(1,0,0))
                for offset in (-6,6):page.draw_line((x+offset,y-8),(x+offset,y+16),color=(1,0,0))
            doc.save(self.job/'plan.pdf')
        digest=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest();self.inventory['plan_sha256']=digest
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        definition={'plan_sha256':digest,'pages':[{'page':1,'ink':'red',
            'exclusions':[{'bbox_pt':[0,0,80,80],'source':'Synthetic legend'}],
            'legends':[{'id':'duplex','label':'Duplex','meaning_source':'Synthetic legend',
                        'bbox_pt':[20,20,60,60],'diameter_scale_range':[.5,1.5]}]}]}
        (self.job/'electrical_vector_definitions.json').write_text(json.dumps(definition))
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}):summary=measure_job(self.job)
        self.assertEqual(summary['editable_count_candidates'],1)
        self.assertEqual(summary['electrical_vector_status'],'candidates_require_review')
        state=MeasurementStore(self.job/'draft_takeoff').read()
        self.assertEqual(next(iter(state['measurements'].values()))['result']['quantity'],1)
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        quantities=rollup(state,rules)
        self.assertEqual(quantities['quantities'],[]);self.assertEqual(len(quantities['pending_quantities']),1)

    def test_template_counts_are_editable_even_without_area_candidates(self):
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=500)
            for x,y in ((30,30),(150,150)):
                p.draw_circle((x,y),12,color=(1,0,0));p.draw_line((x-16,y),(x+16,y),color=(1,0,0))
            doc.save(self.job/'plan.pdf')
        digest=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['plan_sha256']=digest
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        definition={'plan_sha256':digest,'pages':[{'page':1,'templates':[{'id':'fixture','label':'Fixture',
            'meaning_source':'Synthetic legend','bbox_pt':[10,10,50,50],'ink':'red','scales':[1],'minimum_score':.9}]}]}
        (self.job/'electrical_template_definitions.json').write_text(json.dumps(definition))
        result={**self.result,'lines':[]}
        with patch('jnj_takeoff.run_takeoff',return_value=result):summary=measure_job(self.job)
        self.assertTrue(summary['editor_available']);self.assertEqual(summary['editable_region_candidates'],0)
        self.assertEqual(summary['editable_count_candidates'],1)
        state=MeasurementStore(self.job/'draft_takeoff').read()
        self.assertEqual(next(iter(state['measurements'].values()))['result']['quantity'],1)
        self.assertEqual(summary['electrical_template_status'],'candidates_require_review')
        self.assertFalse(summary['estimate_released'])

    def test_unresolved_scale_is_not_reported_as_complete_empty_roof(self):
        self.inventory['unique_role_pages']={'roof':1}
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        self.result['pages']={};self.result['lines']=[]
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['roof_extraction_status'],'scale_unresolved')
        self.assertFalse(summary['roof_coverage_certified'])

    def test_empty_extraction_with_scale_requires_other_method(self):
        self.inventory['unique_role_pages']={'roof':1}
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        self.result['lines']=[]
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['roof_extraction_status'],'no_faces_extracted')
        self.assertFalse(summary['roof_coverage_certified'])

    def test_invalid_geometry_is_recorded_not_silently_certified(self):
        self.prepare_region_scale()
        self.result['lines']=self.result['lines'][:1]
        self.result['lines'][0]['geometry']['points']=[[10,10],[110,110],[10,110],[110,10]]
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertFalse(summary['editor_available'])
        self.assertEqual(len(summary['rejected_editor_geometry']),1)
        self.assertTrue((self.job/'draft_takeoff/takeoff.json').exists())

    def test_mixed_view_scales_do_not_apply_one_legacy_scale_to_roof(self):
        with fitz.open() as doc:
            p=doc.new_page()
            p.insert_text((30,30),'1/4"=1\'')
            p.insert_text((30,60),'3/16"=1\'')
            doc.save(self.job/'plan.pdf')
        self.inventory['plan_sha256']=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory['unique_role_pages']={'roof':1}
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), patch('roof_face_candidates.candidates') as extract:
            summary=measure_job(self.job)
        extract.assert_not_called()
        self.assertEqual(summary['roof_extraction_status'],'view_scale_assignment_required')
        self.assertFalse(summary['roof_coverage_certified'])
        self.assertEqual(summary['editable_region_candidates'],0)
        self.assertEqual({r['line_id'] for r in summary['rejected_editor_geometry']},{'area','perimeter'})

    def prepare_roof_view(self,repeated_pitch=False):
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            page.draw_rect((20,60,200,200))
            page.insert_text((50,120),'6 : 12',fontsize=10)
            if repeated_pitch:page.insert_text((50,150),'6 : 12',fontsize=10)
            page.insert_text((30,40),'1/4 in = 1 ft',fontsize=8)
            page.insert_text((350,40),'1 in = 1 ft',fontsize=8)
            doc.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.inventory.update(plan_sha256=self.sha,unique_role_pages={'roof':1},roles_requiring_disambiguation={})
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        review={'plan_sha256':self.sha,'page':1,'reviewer':'Synthetic source review',
            'basis':'Main roof view; exclude the adjacent detail','view_bounds_pt':[10,10,250,250]}
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        return review

    def test_unlabelled_roof_uses_reviewed_elevation_pitch_through_full_import(self):
        from roof_face_candidates import candidates
        review=self.prepare_roof_view()
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=500)
            for a,b in [((20,60),(200,60)),((200,60),(200,200)),((200,200),(20,200)),((20,200),(20,60))]:
                page.draw_line(a,b,color=(1,0,0),width=2)
            page.insert_text((30,40),'1/4 in = 1 ft',fontsize=8)
            doc.new_page(width=500,height=500).insert_text((40,50),'6 : 12')
            raw=doc.tobytes()
        (self.job/'plan.pdf').write_bytes(raw);self.sha=hashlib.sha256(raw).hexdigest()
        self.inventory['plan_sha256']=self.sha;review['plan_sha256']=self.sha
        review['roof_edge_examples']=[{'path':0,'item':0,'points_pt':[[20,60],[200,60]]},
            {'path':1,'item':0,'points_pt':[[200,60],[200,200]]}]
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        with fitz.open(self.job/'plan.pdf') as doc:
            outline=candidates(doc[0],18,review['view_bounds_pt'],[{'color':[1,0,0],'width_pt':2}])['unresolved_source_outlines'][0]
            box=list(doc[1].get_text('dict')['blocks'][0]['lines'][0]['bbox'])
        pitch={'plan_sha256':self.sha,'reviewer':'Fixture reviewer','basis':'Cross-sheet source review',
            'outlines':[{'source_outline_sha256':outline['source_sha256'],'basis':'Elevation identifies this face',
                'pitch_label':{'page':2,'text':'6 : 12','bbox_pt':box}}]}
        (self.job/'roof_outline_pitch_review.json').write_text(json.dumps(pitch))
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],'method':'synthetic dimensions'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=scale):summary=measure_job(self.job)
        self.assertEqual(summary['roof_face_candidates'],1)
        self.assertEqual(summary['roof_extraction_status'],'candidates_require_review')
        self.assertEqual(summary['roof_unresolved_source_outlines'],0)
        bid=json.loads((self.job/'draft_takeoff/roof_bid_scope/roofing.json').read_text())
        self.assertEqual(bid['items'][0]['pitch_evidence']['label']['page'],2)
        self.assertFalse(bid['ready_to_order'])
        self.assertFalse(summary['estimate_released'])

    def test_uncalibrated_roof_preserves_repeated_pitch_evidence_without_area(self):
        self.prepare_roof_view(repeated_pitch=True)
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        saved=json.loads((self.job/'draft_takeoff/roof_face_candidates.json').read_text())
        self.assertEqual(summary['roof_extraction_status'],'geometry_requires_calibration')
        self.assertEqual(saved['measurements'],[])
        self.assertEqual(len(saved['uncalibrated_geometry'][0]['pitch_candidates']),2)
        self.assertNotIn('points_per_foot',saved['uncalibrated_geometry'][0])
        self.assertNotIn('result',saved['uncalibrated_geometry'][0])
        self.assertFalse(summary['estimate_released'])

    def test_roof_view_without_dimensions_keeps_geometry_without_borrowing_legacy_scale(self):
        self.prepare_roof_view()
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):summary=measure_job(self.job)
        self.assertEqual(summary['roof_extraction_status'],'geometry_requires_calibration')
        self.assertEqual(summary['roof_uncalibrated_geometry_candidates'],1)
        self.assertEqual(summary['editable_region_candidates'],0)
        self.assertEqual({r['line_id'] for r in summary['rejected_editor_geometry']},{'area','perimeter'})
        saved=json.loads((self.job/'draft_takeoff/roof_face_candidates.json').read_text())
        self.assertFalse(saved['printed_scales']['mixed_view_scales'])
        self.assertEqual(saved['measurements'],[])
        self.assertNotIn('points_per_foot',saved['uncalibrated_geometry'][0])
        self.assertNotIn('result',saved['uncalibrated_geometry'][0])
        self.assertFalse((self.job/'draft_takeoff/measurements.json').exists())
        self.assertFalse(summary['estimate_released'])
        self.assertNotIn('roof_bid_scope_files',summary)
        self.assertFalse((self.job/'draft_takeoff/roof_bid_scope').exists())

    def test_roof_view_uses_only_view_calibration_and_saves_review_evidence(self):
        self.prepare_roof_view()
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],
            'method':'synthetic independently calibrated dimensions'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=scale) as calibrate:
            summary=measure_job(self.job)
        self.assertEqual(calibrate.call_args.args[1],[10,10,250,250])
        self.assertEqual(summary['roof_face_candidates'],1)
        self.assertEqual(summary['roof_uncalibrated_geometry_candidates'],0)
        saved=json.loads((self.job/'draft_takeoff/roof_face_candidates.json').read_text())
        self.assertEqual(saved['roof_view_review']['review_sha256'],summary['roof_view_review_sha256'])
        self.assertEqual(saved['measurements'][0]['points_per_foot'],18)
        self.assertFalse(summary['roof_coverage_certified']);self.assertFalse(summary['estimate_released'])

    def test_reviewed_roof_edges_filter_underlay_through_full_import(self):
        review=self.prepare_roof_view()
        with fitz.open(self.job/'plan.pdf') as doc:
            p=doc[0]
            for a,b in [((20,60),(200,60)),((200,60),(110,210)),((110,210),(20,60))]:
                p.draw_line(a,b,color=(1,0,0),width=2)
            p.draw_line((20,220),(80,220),color=(.5,.5,.5))
            for a,b in [((210,80),(240,80)),((240,80),(220,120)),((220,120),(210,80))]:
                p.draw_line(a,b,color=(1,0,0),width=2)
            drawings=p.get_drawings()
            review['roof_edge_examples']=[{'path':n,'item':0,
                'points_pt':[list(v) for v in drawings[n]['items'][0][1:]]} for n in (1,2)]
            raw=doc.tobytes()
        (self.job/'plan.pdf').write_bytes(raw);digest=hashlib.sha256(raw).hexdigest()
        review['plan_sha256']=digest;self.inventory['plan_sha256']=digest
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],
            'method':'synthetic independently calibrated dimensions'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=scale):summary=measure_job(self.job)
        saved=json.loads((self.job/'draft_takeoff/roof_face_candidates.json').read_text())
        self.assertEqual(summary['roof_face_candidates'],1)
        self.assertEqual(saved['roof_view_review']['allowed_styles'],[{'color':[1,0,0],'width_pt':2}])
        self.assertEqual(saved['measurements'][0]['source_cad_paths'],[1,2,3])
        self.assertEqual(summary['roof_unresolved_source_outlines'],1)
        bid=json.loads((self.job/'draft_takeoff/roof_bid_scope/roofing.json').read_text())
        self.assertEqual(len(bid['items']),1)
        self.assertEqual(len(bid['source_exceptions']['unresolved_source_outlines']),1)
        self.assertIsNone(bid['source_exceptions']['unresolved_source_outlines'][0]['physical_quantity'])
        self.assertIn('Roof outlines still requiring measurement',
            (self.job/'draft_takeoff/roof_bid_scope/roofing_DRAFT.md').read_text())
        self.assertFalse(summary['roof_coverage_certified']);self.assertFalse(summary['estimate_released'])

    def test_cutout_only_roof_creates_deferred_net_assembly_not_gross_purchase_area(self):
        review=self.prepare_roof_view()
        with fitz.open(self.job/'plan.pdf') as doc:
            doc[0].draw_rect((100,90,130,130));raw=doc.tobytes()
        (self.job/'plan.pdf').write_bytes(raw);self.sha=hashlib.sha256(raw).hexdigest()
        self.inventory['plan_sha256']=self.sha;review['plan_sha256']=self.sha
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],'method':'synthetic dimensions'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=scale):summary=measure_job(self.job)
        self.assertEqual(summary['roof_face_candidates'],0)
        self.assertEqual(summary['roof_cutout_face_groups'],1)
        self.assertEqual(summary['roof_cutout_measurement_candidates'],2)
        self.assertEqual(summary['roof_unpitched_interior_face_candidates'],1)
        raw=json.loads((self.job/'draft_takeoff/roof_face_candidates.json').read_text())
        faces=[face for network in raw['edge_network_diagnostics']
            for group in network.get('unpitched_interior_faces',[]) for face in group['faces']]
        self.assertEqual(len(faces),1)
        self.assertIsNone(faces[0]['pitch_candidate']);self.assertIsNone(faces[0]['physical_quantity'])
        state=MeasurementStore(self.job/'draft_takeoff').read()
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        self.assertEqual(len(state['measurements']),2);self.assertEqual(len(rules['rules']),1)
        self.assertEqual([t['operation'] for t in rules['rules'][0]['surface_components']],['add','deduct'])
        from measurement_quantities import rollup
        result=rollup(state,rules)
        self.assertEqual(result['quantities'],[]);self.assertEqual(len(result['pending_quantities']),1)
        self.assertFalse(summary['roof_coverage_certified']);self.assertFalse(summary['estimate_released'])

    def prepare_dormer_review(self):
        from roof_face_candidates import candidates
        from roof_dormer_review import group_sha256
        review=self.prepare_roof_view()
        with fitz.open(self.job/'plan.pdf') as doc:
            p=doc[0]
            p.draw_polyline([(145,100),(135,120),(135,170),(155,170),(155,120),(145,100)])
            p.draw_line((145,100),(145,170))
            p.draw_line((80,130),(80,160),width=.5)
            p.draw_line((80,160),(77,154),width=.5)
            p.draw_line((83,154),(80,160),width=.5)
            data=doc.tobytes()
        (self.job/'plan.pdf').write_bytes(data);self.sha=hashlib.sha256(data).hexdigest()
        self.inventory['plan_sha256']=self.sha;review['plan_sha256']=self.sha
        (self.job/'plan_inventory.json').write_text(json.dumps(self.inventory))
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        with fitz.open(self.job/'plan.pdf') as doc:raw=candidates(doc[0],18,review['view_bounds_pt'])
        groups=[g for n in raw['edge_network_diagnostics'] for g in n.get('unpitched_interior_faces',[])]
        self.assertEqual(len(groups),1)
        pitch={'plan_sha256':self.sha,'page':1,'reviewer':'Synthetic reviewer','basis':'Test level ridge and valleys',
            'groups':[{'source_group_sha256':group_sha256(groups[0]),
                'parent':{'rise':6,'downslope':[0,1],'arrow_paths':[3,4,5],'source':'Synthetic parent arrow and label'}}]}
        (self.job/'roof_dormer_pitch_review.json').write_text(json.dumps(pitch))
        return pitch

    def test_reviewed_dormer_pitch_enters_intake_as_deferred_editable_faces(self):
        self.prepare_dormer_review()
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],'method':'synthetic dimensions'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=scale):summary=measure_job(self.job)
        self.assertEqual(summary['roof_inferred_dormer_face_candidates'],2)
        self.assertTrue(summary['roof_dormer_review_sha256'])
        state=MeasurementStore(self.job/'draft_takeoff').read()
        self.assertEqual(len(state['measurements']),4)
        inferred=[m for m in state['measurements'].values() if 'source_pitch_evidence' in m]
        self.assertEqual(len(inferred),2)
        for m in inferred:
            self.assertAlmostEqual(m['source_pitch_evidence']['inferred_rise_per_12'],12)
            self.assertFalse(m['source_pitch_review']['reviewer_identity_authenticated'])
        rules=json.loads((self.job/'draft_takeoff/quantity_rules.json').read_text())
        from measurement_quantities import rollup
        self.assertEqual(rollup(state,rules)['quantities'],[])
        self.assertFalse(summary['roof_coverage_certified']);self.assertFalse(summary['estimate_released'])

    def test_changed_dormer_review_during_extraction_does_not_publish_measurements(self):
        pitch=self.prepare_dormer_review()
        scale={'usable_candidate':True,'points_per_foot':18,'controls':[],'method':'synthetic dimensions'}
        def change(*args,**kwargs):
            pitch['basis']='Changed interpretation'
            (self.job/'roof_dormer_pitch_review.json').write_text(json.dumps(pitch))
            return self.result
        with patch('jnj_takeoff.run_takeoff',side_effect=change), \
             patch('dimension_scale.split_dimension_scale',return_value=scale):
            with self.assertRaisesRegex(ValueError,'Dormer pitch review changed'):measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff/measurements.json').exists())

    def test_dormer_review_cannot_supply_missing_scale(self):
        self.prepare_dormer_review()
        with patch('jnj_takeoff.run_takeoff',return_value=self.result):
            with self.assertRaisesRegex(ValueError,'calibrated'):measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff/measurements.json').exists())

    def test_dormer_review_rejects_stale_groups_wrong_pitch_and_source_arrow(self):
        pitch=self.prepare_dormer_review()
        from roof_face_candidates import candidates
        from roof_dormer_review import read_review,reviewed_candidates
        with fitz.open(self.job/'plan.pdf') as doc:raw=candidates(doc[0],18,[10,10,250,250])
        frame={'page':1,'plan_sha256':self.sha,'points_per_foot':18,'width_pt':500,'height_pt':500}
        review=read_review(self.job,self.sha)
        changes=[('source_group_sha256','changed'),('parent',{'rise':7}),
            ('parent',{'rise':6,'arrow_paths':[0,1,2]}),
            ('parent',{**pitch['groups'][0]['parent'],'downslope':[0,-1]})]
        for key,value in changes:
            changed=copy.deepcopy(review);changed['groups'][0][key]=value
            with self.assertRaises(ValueError):reviewed_candidates(self.job/'plan.pdf',raw,changed,frame)
        duplicate=copy.deepcopy(review);duplicate['groups']*=2
        with self.assertRaises(ValueError):reviewed_candidates(self.job/'plan.pdf',raw,duplicate,frame)
        pitch['plan_sha256']='old'
        (self.job/'roof_dormer_pitch_review.json').write_text(json.dumps(pitch))
        with self.assertRaises(ValueError):read_review(self.job,self.sha)

    def test_invalid_roof_view_fails_before_engine_or_output(self):
        review=self.prepare_roof_view()
        for key,value in [('plan_sha256','other'),('page',2),('reviewer',''),('basis',''),
                ('view_bounds_pt',[0,0,600,600]),('view_bounds_pt',[0,0,float('nan'),250]),
                ('view_bounds_pt',[True,0,250,250]),('view_bounds_pt',[0,0,250])]:
            (self.job/'roof_view_review.json').write_text(json.dumps({**review,key:value}))
            with self.subTest(key=key,value=value),patch('jnj_takeoff.run_takeoff') as engine:
                with self.assertRaises(ValueError):measure_job(self.job)
                engine.assert_not_called();self.assertFalse((self.job/'draft_takeoff').exists())

    def test_arrow_calibration_reaches_roof_measurements_when_split_lines_absent(self):
        self.prepare_roof_view()
        arrow={'usable_candidate':True,'points_per_foot':18,'controls':[{'source':'synthetic arrow fixture'}],
            'method':'synthetic four opposed-arrow controls'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('arrow_dimension_scale.arrow_dimension_scale',return_value=arrow) as calibrate:
            summary=measure_job(self.job)
        self.assertEqual(calibrate.call_args.args[1],[10,10,250,250])
        self.assertEqual(summary['roof_face_candidates'],1)
        self.assertEqual(summary['roof_scale_review']['method'],arrow['method'])
        self.assertEqual(summary['roof_scale_review']['split_line_review']['controls'],[])
        self.assertFalse(summary['estimate_released'])

    def test_arrow_fallback_does_not_override_unresolved_long_dimension_controls(self):
        self.prepare_roof_view()
        disputed={'usable_candidate':False,'points_per_foot':None,
            'controls':[{'axis':'horizontal','points_per_foot':12}],'method':'unresolved long controls'}
        with patch('jnj_takeoff.run_takeoff',return_value=self.result), \
             patch('dimension_scale.split_dimension_scale',return_value=disputed), \
             patch('arrow_dimension_scale.arrow_dimension_scale') as calibrate:
            summary=measure_job(self.job)
        calibrate.assert_not_called()
        self.assertEqual(summary['roof_extraction_status'],'geometry_requires_calibration')
        self.assertEqual(summary['roof_face_candidates'],0)

    def test_roof_view_changed_during_extraction_cannot_publish_measurements(self):
        review=self.prepare_roof_view()
        def change_review(*args,**kwargs):
            (self.job/'roof_view_review.json').write_text(json.dumps({**review,'basis':'Changed scope'}))
            return self.result
        with patch('jnj_takeoff.run_takeoff',side_effect=change_review):
            with self.assertRaisesRegex(ValueError,'Roof view review changed'):measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff/roof_face_candidates.json').exists())
        self.assertFalse((self.job/'draft_takeoff/measurements.json').exists())

    def test_roof_partition_audit_is_saved_without_approving_scope(self):
        self.inventory['unique_role_pages']={'roof':1}
        item={'id':'roof-test','label':'Roof','page':1,'kind':'area',
              'points':[[10,10],[110,10],[110,110],[10,110]],'points_per_foot':10,
              'surface_factor':1.25,'width_pt':500,'height_pt':500,'color':'#0e7490',
              'dependent_rows':[]}
        extracted={'measurements':[item],'unmatched_or_ambiguous_pitch_labels':[]}
        with patch('jnj_takeoff.run_takeoff',return_value={**self.result,'lines':[]}), \
             patch('roof_face_candidates.candidates',return_value=extracted):
            summary=measure_job(self.job)
        audit=json.loads((self.job/'draft_takeoff'/summary['roof_partition_file']).read_text())
        self.assertEqual(audit['plan_sha256'],self.sha)
        self.assertEqual(audit['projected_union_sf'],100)
        self.assertEqual(audit['covered_sloped_lower_sf'],125)
        self.assertEqual(audit['covered_sloped_upper_sf'],125)
        self.assertIsNone(audit['coverage'])
        self.assertFalse(audit['certified'])
        self.assertFalse(summary['estimate_released'])
        from roof_bid_scope import from_folder
        folder=self.job/'draft_takeoff'
        scope=json.loads((folder/'roof_bid_scope/roofing.json').read_text())
        self.assertEqual(scope,from_folder(folder))
        self.assertEqual(summary['roof_bid_scope_sha256'],scope['scope_sha256'])
        self.assertFalse(summary['roof_bid_scope_sent'])
        self.assertEqual(scope['items'][0]['reference_quantity'],125)
        self.assertEqual(scope['items'][0]['reference_roofing_squares'],1.25)
        self.assertTrue(all((folder/p).exists() for p in summary['roof_bid_scope_files']))
        self.assertIn('no independently reviewed outer contour',
            (folder/'roof_bid_scope/roofing_DRAFT.md').read_text())

if __name__=='__main__':unittest.main()
