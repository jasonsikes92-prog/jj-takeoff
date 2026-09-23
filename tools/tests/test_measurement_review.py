import hashlib
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_review import make_server
from measurement_store import MeasurementStore

class ReviewHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();folder=Path(self.tmp.name)
        doc=fitz.open();doc.new_page(width=500,height=500);doc.save(folder/'plan.pdf');doc.close()
        self.sha=hashlib.sha256((folder/'plan.pdf').read_bytes()).hexdigest()
        self.line={'id':'wall','page':1,'kind':'length','width_pt':500,'height_pt':500,'points_per_foot':10,
            'points':[[0,0],[100,0]],'dependent_rows':['100'],'color':'#d97706','label':'Wall'}
        (folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[self.line]}))
        self.rules_path=folder/'quantity_rules.json'
        self.rules_path.write_text(json.dumps({'plan_sha256':self.sha,'rules':[
            {'id':'wall-length','label':'Wall length','measurement_ids':['wall'],'unit':'LF','rounding':'none',
             'template_rows':['100'],'use':'assembly_input','basis':'Gross wall length','remaining':['Stud and plate layouts']}]}))
        self.template_path=folder/'template_rows.json'
        self.template_path.write_text(json.dumps({'rows':[{'row_id':'row100','excel_row':'100','name':'Framing',
            'unit':'ft2','cost_type':'MATERIAL','markup_pct':'15','completion_status':'evidence_in_progress'}]}))
        self.server=make_server(MeasurementStore(folder));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def post(self,path,body,origin=None):
        request=urllib.request.Request(self.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin or self.url})
        with urllib.request.urlopen(request) as response:return json.load(response)
    def test_preview_does_not_save_and_save_survives_read(self):
        result=self.post('/api/preview',{'measurement_id':'wall','points':[[0,0],[200,0]]})
        self.assertEqual(result['quantity'],20)
        with urllib.request.urlopen(self.url+'/api/state') as response:self.assertEqual(json.load(response)['version'],1)
        saved=self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[200,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend wall'})
        with urllib.request.urlopen(self.url+'/api/state') as response:self.assertEqual(json.load(response),saved)
    def test_area_check_recalculates_saved_edits_and_rejects_wrong_plan(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        parent=Path(self.tmp.name);folder=parent/'draft_takeoff';folder.mkdir()
        (folder/'plan.pdf').write_bytes((parent/'plan.pdf').read_bytes())
        area={**self.line,'id':'floor','kind':'area','source_area_label':'HEATED AREA',
              'points':[[0,0],[100,0],[100,100],[0,100]],'dependent_rows':[]}
        (folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[area]}))
        inventory={'plan_sha256':self.sha,'area_schedule_references':[
            {'page':1,'rows':[{'label':'HEATED AREA','sqft':100}]}]}
        inventory_path=parent/'plan_inventory.json'
        inventory_path.write_text(json.dumps(inventory))
        self.server=make_server(MeasurementStore(folder))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.url+'/api/area-schedule-check') as response:first=json.load(response)
        self.assertEqual(first['status'],'within_tolerance')
        self.post('/api/save',{'measurement_id':'floor','points':[[0,0],[120,0],[120,100],[0,100]],
            'base_version':1,'plan_sha256':self.sha,'note':'Correct boundary'})
        with urllib.request.urlopen(self.url+'/api/area-schedule-check') as response:second=json.load(response)
        self.assertEqual(second['measurement_version'],2)
        self.assertEqual(second['rows'][0]['status'],'discrepancy')
        self.assertAlmostEqual(second['rows'][0]['difference_percent'],20)
        self.assertFalse(second['certified'])
        self.assertNotEqual(first['input_sha256'],second['input_sha256'])
        inventory['plan_sha256']='different-plan'
        inventory_path.write_text(json.dumps(inventory))
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.url+'/api/area-schedule-check')
        self.assertEqual(error.exception.code,400)
    def test_wall_runs_recalculate_gap_from_saved_geometry(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        folder=self.template_path.parent
        native={**self.line,'source_method':'native_filled_wall_rectangles_v1'}
        second={**native,'id':'wall2','points':[[150,0],[200,0]],'dependent_rows':[]}
        (folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[native,second]}))
        (folder/'measurement_edits.sqlite3').unlink()
        self.server=make_server(MeasurementStore(folder))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.url+'/api/wall-runs') as response:first=json.load(response)
        self.assertEqual(first['run_candidates'][0]['gaps'][0]['length_lf'],5)
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[120,0]],
            'base_version':1,'plan_sha256':self.sha,'note':'Extend source wall two feet'})
        with urllib.request.urlopen(self.url+'/api/wall-runs') as response:second=json.load(response)
        self.assertEqual(second['measurement_version'],2)
        self.assertEqual(second['run_candidates'][0]['gaps'][0]['length_lf'],3)
        self.assertEqual(second['run_candidates'][0]['visible_union_lf'],17)
        self.assertNotEqual(first['measurement_inputs_sha256'],second['measurement_inputs_sha256'])
        self.assertIsNone(second['purchase_quantity'])
        self.assertFalse(second['certified'])
        with urllib.request.urlopen(self.url+'/api/wall-gap-labels') as response:tags=json.load(response)
        self.assertEqual(tags['measurement_version'],2)
        self.assertEqual(tags['measurement_inputs_sha256'],second['measurement_inputs_sha256'])
        self.assertEqual(tags['gaps'][0]['drawn_gap_lf'],3)
        self.assertEqual(tags['gaps'][0]['status'],'no_aligned_tag')
    def test_opening_headers_follow_saved_edits_and_reject_changed_evidence(self):
        folder=self.template_path.parent
        config={'plan_sha256':self.sha,'bindings':[{'opening_id':'EO1','measurement_id':'wall',
            'measurement_page':1,'header_id':'H1','source':'reviewed header mapping'}]}
        for key,data in [('headers',{'sha256':self.sha,'headers':[{'id':'H1','length_inches':135}]}),
                ('products',{'openings':[{'opening_id':'EO1','rough_opening_width_in':120,'source':'supplier'}]})]:
            raw=json.dumps(data).encode();(folder/(key+'.json')).write_bytes(raw)
            config[key]={'path':key+'.json','sha256':hashlib.sha256(raw).hexdigest()}
        (folder/'opening_header_review.json').write_text(json.dumps(config))
        with urllib.request.urlopen(self.url+'/api/opening-headers') as response:first=json.load(response)
        self.assertEqual(first['openings'][0]['length_remaining_for_both_supports_inches'],15)
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[150,0]],'base_version':1,
            'plan_sha256':self.sha,'note':'Widen test opening'})
        with urllib.request.urlopen(self.url+'/api/opening-headers') as response:edited=json.load(response)
        self.assertEqual(edited['measurement_version'],2)
        self.assertEqual(edited['openings'][0]['length_remaining_for_both_supports_inches'],-45)
        (folder/'headers.json').write_text('{}')
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/opening-headers')
        self.assertEqual(error.exception.code,400)

    def test_other_origin_and_stale_version_refused(self):
        body={'measurement_id':'wall','points':[[0,0],[200,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'}
        with self.assertRaises(urllib.error.HTTPError) as error:self.post('/api/save',body,origin='https://example.com')
        self.assertEqual(error.exception.code,403)
        self.post('/api/save',body)
        with self.assertRaises(urllib.error.HTTPError) as error:self.post('/api/save',body)
        self.assertEqual(error.exception.code,409)
    def test_sheet_route_is_bounded_and_page_loads(self):
        with urllib.request.urlopen(self.url+'/sheet/1.png') as response:self.assertTrue(response.read().startswith(b'\x89PNG'))
        with urllib.request.urlopen(self.url+'/') as response:self.assertIn(b'Done editing',response.read())
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.url+'/../plan.pdf')
    def test_export_snapshot_binds_rows_and_readiness_to_same_revision(self):
        from estimate_export_snapshot import verify_snapshot
        with urllib.request.urlopen(self.url+'/api/export-snapshot') as response:first=json.load(response)
        verify_snapshot(first)
        self.assertEqual(first['draft']['measurement_version'],first['readiness']['measurement_version'])
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[200,0]],
            'base_version':1,'plan_sha256':self.sha,'note':'Extend wall'})
        with urllib.request.urlopen(self.url+'/api/export-snapshot') as response:second=json.load(response)
        self.assertNotEqual(first['snapshot_sha256'],second['snapshot_sha256'])
        self.assertEqual(second['draft']['measurement_version'],2)
        self.assertEqual(second['readiness']['measurement_version'],2)
        second['draft']['rows'][0]['line_price']=100
        with self.assertRaisesRegex(ValueError,'content changed'):verify_snapshot(second)
    def test_estimate_draft_tracks_edits_and_refuses_changed_template(self):
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[205,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'})
        with urllib.request.urlopen(self.url+'/api/estimate-draft') as response:
            value=json.load(response)
            self.assertEqual(value['measurement_version'],2)
            self.assertEqual(value['rows'][0]['assembly_inputs'][0]['quantity'],20.5)
            self.assertIsNone(value['rows'][0]['draft_quantity'])
            self.assertEqual(value['rows'][0]['markup_pct'],'15')
        self.template_path.write_text('{}')
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/estimate-draft')
        self.assertEqual(error.exception.code,409)

    def test_http_price_reads_source_and_rejects_changed_measurement_revision(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        folder=self.template_path.parent
        rules=json.loads(self.rules_path.read_text());rules['rules'][0]['use']='template_quantity'
        self.rules_path.write_text(json.dumps(rules))
        template=json.loads(self.template_path.read_text());template['rows'][0]['unit']='LF'
        self.template_path.write_text(json.dumps(template))
        evidence=folder/'price_evidence';evidence.mkdir()
        raw=b'Synthetic quote: $2 per LF';(evidence/'quote.txt').write_bytes(raw)
        today=date.today().isoformat()
        (folder/'reviewed_prices.json').write_text(json.dumps({'plan_sha256':self.sha,'measurement_version':1,'rates':[{
            'row_id':'row100','unit':'LF','currency':'USD','unit_price':2,'date':today,'valid_through':today,
            'source':'Synthetic supplier quote','source_file':'quote.txt','source_sha256':hashlib.sha256(raw).hexdigest(),
            'scope_reviewed':True,'evidence_kind':'current_supplier_quote','pricing_basis':'unit_rate'}]}))
        self.server=make_server(MeasurementStore(folder))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.url+'/api/estimate-draft') as response:
            value=json.load(response);self.assertEqual(value['rows'][0]['line_price'],23)
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[205,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/estimate-draft')
        self.assertEqual(error.exception.code,400)
        with urllib.request.urlopen(self.url+'/api/quantities') as response:
            self.assertEqual(json.load(response)['quantities'][0]['quantity'],20.5)

    def test_quantity_mapping_recalculates_after_save_and_detects_rule_change(self):
        with urllib.request.urlopen(self.url+'/api/quantities') as response:
            self.assertEqual(json.load(response)['quantities'][0]['quantity'],10)
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[205,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'})
        with urllib.request.urlopen(self.url+'/api/quantities') as response:
            value=json.load(response)
            self.assertEqual(value['quantities'][0]['quantity'],20.5)
            self.assertEqual(value['measurement_version'],2)
        self.rules_path.write_text('{}')
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/quantities')
        self.assertEqual(error.exception.code,409)

    def test_scope_decision_persists_and_edit_invalidates_it(self):
        with urllib.request.urlopen(self.url+'/api/scope-reviews') as response:context=json.load(response)
        body={'rule_id':'wall-length','measurement_id':'wall','decision':'approved_for_draft',
              'scope':'Gross wall line only','reviewer':'Test reviewer','base_version':1,
              'plan_sha256':self.sha,'rules_sha256':context['rules_sha256']}
        with self.assertRaises(urllib.error.HTTPError) as error:self.post('/api/scope-review',body,origin='https://example.com')
        self.assertEqual(error.exception.code,403)
        review=self.post('/api/scope-review',body)
        self.assertEqual(review['review_id'],1)
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[205,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/quantities')
        self.assertEqual(error.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as error:self.post('/api/scope-review',body)
        self.assertEqual(error.exception.code,409)
        self.post('/api/scope-review',{**body,'base_version':2})
        with urllib.request.urlopen(self.url+'/api/quantities') as response:
            self.assertEqual(json.load(response)['quantities'][0]['quantity'],20.5)

    def test_reviewed_package_price_served_and_geometry_change_blocks_it(self):
        from measurement_estimate import template_draft
        from bid_comparison import scope_digest
        self.server.shutdown();self.server.server_close();self.thread.join()
        folder=self.template_path.parent
        template=json.loads(self.template_path.read_text())
        template['rows'][0].update(unit='each',cost_type='SUBCONTRACTOR')
        self.template_path.write_text(json.dumps(template))
        store=MeasurementStore(folder);rules=json.loads(self.rules_path.read_text())
        draft=template_draft(store.read(),rules,template)
        draft['template_sha256']=hashlib.sha256(self.template_path.read_bytes()).hexdigest()
        draft['rules_sha256']=hashlib.sha256(self.rules_path.read_bytes()).hexdigest()
        evidence=folder/'price_evidence';evidence.mkdir();raw=b'Synthetic complete framing quote'
        (evidence/'quote.txt').write_bytes(raw)
        today=date.today().isoformat()
        scope={'plan_sha256':self.sha,'measurement_version':1,'items':[{'id':'work','label':'Complete fixture scope'}]}
        quote={'id':'q','supplier':'Synthetic supplier','source_file':'quote.txt',
            'source_sha256':hashlib.sha256(raw).hexdigest(),'date':today,'valid_through':today,
            'currency':'USD','total':'2000.00','reviewed':True,'reviewed_scope_sha256':scope_digest(scope),
            'evidence_kind':'current_subcontractor_quote','scope_items':[{'scope_id':'work','status':'included','source_ref':'page 1'}]}
        package={'scope':scope,'quotes':[quote],'quote_id':'q','row_id':'row100',
            'covered_row_ids':['row100'],'scope_mapping_reviewed':True,'reviewed_draft_sha256':scope_digest(draft)}
        (folder/'reviewed_packages.json').write_text(json.dumps([package]))
        self.server=make_server(store);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.url+'/api/estimate-draft') as response:
            value=json.load(response);self.assertEqual(value['rows'][0]['line_price'],2300)
            self.assertIsNone(value['whole_house_total']);self.assertFalse(value['estimate_released'])
        self.post('/api/save',{'measurement_id':'wall','points':[[0,0],[205,0]],'base_version':1,'plan_sha256':self.sha,'note':'Extend'})
        with urllib.request.urlopen(self.url+'/api/estimate-draft') as response:
            changed=json.load(response)
        self.assertIsNone(changed['rows'][0]['line_cost'])
        self.assertIsNone(changed['rows'][0]['line_price'])
        self.assertIn('withheld',changed['rows'][0]['price_status'])
        self.assertEqual(changed['pending_packages'],[{'row_id':'row100',
            'reason':'Estimate changed; package scope review required'}])
        self.assertIsNone(changed['whole_house_total']);self.assertFalse(changed['estimate_released'])
        self.post('/api/save',{'measurement_id':'wall','points':self.line['points'],'base_version':2,
            'plan_sha256':self.sha,'note':'Restore geometry; package review remains stale'})
        with urllib.request.urlopen(self.url+'/api/estimate-draft') as response:restored=json.load(response)
        self.assertIsNone(restored['rows'][0]['line_price'])
        self.assertEqual(restored['pending_packages'],changed['pending_packages'])

if __name__=='__main__':unittest.main()
