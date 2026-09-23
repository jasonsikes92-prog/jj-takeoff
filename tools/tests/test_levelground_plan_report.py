import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
import plan_report
from measurement_store import MeasurementStore
from measurement_scope_reviews import ScopeReviews


class PlanReportTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = AnswerStore(self.root / 'cases.sqlite3')
        self.case = self.store.create_case('Synthetic homeowner')
        self.workspaces = PlanWorkspaces(self.store, self.root / 'workspaces')
        with fitz.open() as pdf:
            for title in ('COVER', 'MAIN FLOOR PLAN', 'ROOF PLAN'):
                pdf.new_page().insert_text((30, 30), title)
            raw = pdf.tobytes()
        evidence = self.store.attach_evidence(self.case, 'test-plan.pdf', raw)
        DocumentProcessing(self.store).process_next()
        result = self.workspaces.initialize(self.case, evidence['reference'], 'private-reviewer')
        self.sha = result['workspace_id']
        self.job = self.workspaces.root / self.case / self.sha
        pages = []
        with fitz.open(self.job / 'plan.pdf') as pdf:
            for index, role in enumerate(('cover', 'floor_plan', 'roof_plan')):
                view = self.job / f'page{index}.png'
                pdf[index].get_pixmap().save(view)
                pages.append({'page':index + 1, 'role':role, 'view':view.name,
                              'view_sha256':hashlib.sha256(view.read_bytes()).hexdigest()})
        review = {'plan_sha256':self.sha, 'reviewer':'private-reviewer',
                  'cover_index':[[1,'Main Floor Plan'], [2,'Roof Plan'], [3,'Site Plan']],
                  'pages':pages, 'unresolved_issues':[]}
        self.review_path = self.job / 'sheet_review.json'
        self.review_path.write_text(json.dumps(review))
        status = self.workspaces.read(self.case, self.sha)
        review['partial_measurement_review'] = {'role_pages':{'floor':2, 'roof':3},
            'basis':'Private review rationale', 'missing_roles':status['sheet_review']['missing_roles'], 'unresolved_issues':[]}
        self.review_path.write_text(json.dumps(review))
        status = self.workspaces.read(self.case, self.sha)
        self.folder = self.job / 'draft_takeoff'
        self.folder.mkdir()
        shutil.copy2(self.job / 'plan.pdf', self.folder / 'plan.pdf')
        measurements = [{'id':identity, 'kind':'area', 'page':3, 'width_pt':612, 'height_pt':792,
            'points_per_foot':10, 'points':[[x,10],[x+100,10],[x+100,110],[x,110]],
            'engine_line_ids':[identity], 'dependent_rows':['104','105','106'], 'color':'#123456'}
            for identity,x in [('roof-a',10),('roof-b',110),('unmapped',210)]]
        (self.folder / 'measurements.json').write_text(json.dumps({'plan_sha256':self.sha, 'measurements':measurements}))
        self.rules = {'plan_sha256':self.sha, 'private_unit_price':98765, 'rules':[{
            'id':'roof', 'label':'Roof surfaces', 'measurement_ids':['roof-a','roof-b'],
            'template_rows':['104','105','106'], 'unit':'SF', 'rounding':'none', 'use':'assembly_input',
            'basis':'Drawing', 'remaining':['Resolve material allocation'], 'defer_pending_scope':True}]}
        (self.folder / 'quantity_rules.json').write_text(json.dumps(self.rules))
        (self.folder / 'summary.json').write_text(json.dumps({'plan_sha256':self.sha,
            'sheet_review_sha256':status['sheet_review']['review_sha256'],
            'editable_region_candidates':3, 'editable_count_candidates':0}))
        self.measurements = MeasurementStore(self.folder)
        self.reviews = ScopeReviews(self.measurements, self.rules)

    def approve(self):
        for identity in ('roof-a', 'roof-b'):
            self.reviews.save('roof', identity, 'approved_for_draft', 'Partial roof only', 'private-reviewer',
                              self.measurements.read()['version'], self.sha, self.reviews.rules_sha256)

    def test_pending_then_approved_rule_is_one_draft_reference_without_prices_or_publication(self):
        pending = self.workspaces.prebid_draft(self.case, self.sha)
        self.assertEqual(pending['quantities'], [])
        self.assertTrue(any('quantity withheld' in text for text in pending['unknowns']))
        self.approve()
        before = self.measurements.read()
        result = self.workspaces.prebid_draft(self.case, self.sha)
        self.assertEqual(len(result['quantities']), 1)
        quantity = result['quantities'][0]
        self.assertEqual(quantity['qty'], 200)
        self.assertEqual(quantity['confidence'], 'needs_confirmation')
        self.assertIsNone(quantity['purchase_quantity'])
        self.assertFalse(result['sheet_coverage_passed'])
        self.assertIn('site', result['findings'][0]['detail'])
        self.assertTrue(any('unmapped' in item for item in result['unknowns']))
        self.assertIsNone(result['meta']['our_range'])
        self.assertIsNone(result['meta']['home']['heated_sf'])
        self.assertIsNone(result['meta']['home']['stories'])
        for key in ('homeowner_release_approved','estimate_released','measurements_certified','complete_home_review'):
            self.assertFalse(result[key])
        for private in ('98765', 'private-reviewer', 'Private review rationale', str(self.root), 'markup_pct'):
            self.assertNotIn(private, json.dumps(result))
        self.assertEqual(self.measurements.read(), before)
        self.assertEqual(self.store.read_case(self.case)['reports'], [])
        self.assertEqual(self.workspaces.prebid_draft(self.case,self.sha)['meta']['report_id'], result['meta']['report_id'])

    def test_geometry_edit_withholds_prior_review_and_changes_snapshot_identity(self):
        self.approve()
        old = self.workspaces.prebid_draft(self.case, self.sha)
        self.measurements.save('roof-a', [[10,10],[90,10],[90,110],[10,110]], 1, self.sha, 'Test change')
        changed = self.workspaces.prebid_draft(self.case, self.sha)
        self.assertEqual(changed['quantities'], [])
        self.assertNotEqual(changed['meta']['report_id'], old['meta']['report_id'])

    def test_http_preview_uses_authenticated_case_and_reviewer_role(self):
        from case_service import make_server
        self.approve()
        server = make_server(self.root / 'cases.sqlite3', 0)
        server.workspaces.root = self.workspaces.root
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            reviewer = server.access.issue(self.case, 'operator', 'reviewer')
            homeowner = server.access.issue(self.case, 'homeowner')
            other = self.store.create_case('Other')
            other_reviewer = server.access.issue(other, 'other-operator', 'reviewer')
            url = f'http://127.0.0.1:{server.server_port}/api/plan-workspaces/{self.sha}/prebid-draft'
            for credential, expected in [(homeowner,403), ('invalid',401), (other_reviewer,400), (reviewer,200)]:
                try:
                    response = urlopen(Request(url, headers={'Authorization':'Bearer ' + credential}), timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    body = json.load(response)
                    self.assertEqual(response.status, expected)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    if expected == 200:
                        self.assertEqual(body['quantities'][0]['qty'], 200)
                        self.assertFalse(body['homeowner_release_approved'])
            self.assertEqual(self.store.read_case(self.case)['reports'], [])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_other_case_changed_review_and_changed_during_generation_are_refused(self):
        other = self.store.create_case('Other homeowner')
        with self.assertRaises(ValueError):
            self.workspaces.prebid_draft(other, self.sha)
        original = plan_report.report_from_takeoff
        def mutate(*args, **kwargs):
            self.measurements.save('roof-a', [[10,10],[90,10],[90,110],[10,110]], 1, self.sha, 'Concurrent edit')
            return original(*args, **kwargs)
        with patch.object(plan_report, 'report_from_takeoff', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed while preparing'):
                self.workspaces.prebid_draft(self.case, self.sha)
        review = json.loads(self.review_path.read_text())
        review['partial_measurement_review']['basis'] += ' changed'
        self.review_path.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, 'current, sheet-reviewed'):
            self.workspaces.prebid_draft(self.case, self.sha)

    def test_reviewed_openings_join_draft_without_loading_or_exposing_company_policy(self):
        from test_levelground_opening_references import fixture
        source=fixture();source['plan_sha256']=self.sha
        (self.folder/'opening_schedule_review.json').write_text('{}')
        with patch.object(plan_report,'opening_schedule',return_value=source) as reader:
            result=self.workspaces.prebid_draft(self.case,self.sha)
            reader.assert_called_once_with(self.folder,self.measurements.read(),include_company_policy=False)
        self.assertEqual([q['qty'] for q in result['quantities']],[3,1,1,1])
        self.assertFalse(result['homeowner_release_approved']);self.assertIsNone(result['meta']['our_range'])
        self.assertIn('opening_references_sha256',result['source_workspace'])
        for private in ('private-core','private-source','private-defaults','98765','markup_pct','door_core_review'):
            self.assertNotIn(private,json.dumps(result))
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_opening_review_change_during_report_generation_is_refused(self):
        from test_levelground_opening_references import fixture
        path=self.folder/'opening_schedule_review.json';path.write_text('{}')
        original=plan_report.report_from_takeoff
        def mutate(*args,**kwargs):
            path.write_text('{"changed":true}')
            return original(*args,**kwargs)
        with patch.object(plan_report,'opening_schedule',return_value=fixture()),patch.object(plan_report,'report_from_takeoff',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed while preparing'):
                self.workspaces.prebid_draft(self.case,self.sha)

    def bind_test_permit_basis(self):
        path=self.job/'local_requirements.json';context=json.loads(path.read_bytes())
        context['project_basis']={'state':'GA','code_basis_date':'2026-09-19',
            'authority_id':'GA-JASPER-COUNTY','authority_verified':True,'private_notes':'PRIVATE PERMIT NOTE',
            'conditions':{'agricultural_zoning':False,'crawlspace':True,'residential_new_construction':True}}
        path.write_text(json.dumps(context))
        inventory_path=self.job/'plan_inventory.json';inventory=json.loads(inventory_path.read_bytes())
        inventory['local_requirements_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        inventory_path.write_text(json.dumps(inventory))
        manifest_path=self.job/'case_workspace.json';manifest=json.loads(manifest_path.read_bytes())
        manifest['initial_file_sha256']['plan_inventory.json']=hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))

    def test_permit_findings_recheck_sources_without_prices_or_private_inputs(self):
        from datetime import date
        self.bind_test_permit_basis()
        with patch.object(plan_report,'date') as clock:
            clock.today.return_value=date(2026,9,19)
            report=self.workspaces.prebid_draft(self.case,self.sha)
            clock.today.return_value=date(2026,10,20)
            stale=self.workspaces.prebid_draft(self.case,self.sha)
        local=report['permit_review']['needs_review'];self.assertEqual(len(local),6)
        findings=[f for f in report['findings'] if f['title'].startswith('Permit review:')]
        self.assertEqual(len(findings),7) # State adoption plus six conditional local topics.
        self.assertTrue(all(f['bid_amount'] is None and f['realistic_low'] is None and f['realistic_high'] is None for f in findings))
        self.assertTrue(all('https://' in f['basis'] for f in findings))
        self.assertNotIn('PRIVATE PERMIT NOTE',json.dumps(report));self.assertNotIn('project_basis',json.dumps(report))
        self.assertFalse(report['permit_compliance_verified']);self.assertFalse(report['homeowner_release_approved'])
        self.assertNotEqual(report['meta']['report_id'],stale['meta']['report_id'])
        self.assertTrue(all('Refresh official source' in r['review_issues'] for r in stale['permit_review']['needs_review']))
        self.assertTrue(any('Refresh official source' in s for s in stale['unknowns']))
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_revised_property_facts_change_report_without_exposing_private_history(self):
        self.bind_test_permit_basis()
        before=self.workspaces.prebid_draft(self.case,self.sha)
        ref=self.store.attach_evidence(self.case,'correction.txt',b'Synthetic city jurisdiction')['reference']
        payload={'expected_revision':0,'jurisdiction':{'state':'GA','authority_id':'GA-JASPER-CITY',
            'authority_verified':True,'private_notes':'PRIVATE CORRECTION'},
            'rationale':'PRIVATE REASON','evidence_refs':[ref]}
        self.workspaces.revise_permit_inputs(self.case,self.sha,'PRIVATE REVIEWER',payload)
        after=self.workspaces.prebid_draft(self.case,self.sha)
        self.assertNotEqual(before['meta']['report_id'],after['meta']['report_id'])
        self.assertEqual(before['quantities'],after['quantities'])
        self.assertEqual(after['permit_review']['input_revision'],1)
        self.assertFalse(any(i.get('authority_id')=='GA-JASPER-COUNTY' for i in
            after['permit_review']['candidates']+after['permit_review']['needs_review']))
        for private in ('PRIVATE CORRECTION','PRIVATE REASON','PRIVATE REVIEWER',ref):
            self.assertNotIn(private,json.dumps(after))
        self.assertFalse(after['homeowner_release_approved']);self.assertIsNone(after['meta']['our_range'])
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_permit_revision_during_report_generation_is_refused(self):
        ref=self.store.attach_evidence(self.case,'correction.txt',b'Synthetic correction')['reference']
        original=plan_report.report_from_takeoff
        def mutate(*args,**kwargs):
            self.workspaces.revise_permit_inputs(self.case,self.sha,'operator',{
                'expected_revision':0,'jurisdiction':{'state':'GA'},'rationale':'Correct state','evidence_refs':[ref]})
            return original(*args,**kwargs)
        with patch.object(plan_report,'report_from_takeoff',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed while preparing'):
                self.workspaces.prebid_draft(self.case,self.sha)

    def test_permit_file_change_during_generation_is_refused(self):
        original=plan_report.report_from_takeoff
        def mutate(*args,**kwargs):
            (self.job/'official_requirements_snapshot.json').write_text('[]')
            return original(*args,**kwargs)
        with patch.object(plan_report,'report_from_takeoff',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'changed while preparing'):
                self.workspaces.prebid_draft(self.case,self.sha)


if __name__ == '__main__':
    unittest.main()
