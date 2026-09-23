import base64
import json
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from case_service import CaseAccess, make_server


class CaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'cases.sqlite3'
        self.server = make_server(self.path, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.store, self.access = self.server.store, self.server.access
        self.case = self.store.create_case('Synthetic homeowner')
        self.other = self.store.create_case('Separate homeowner')
        self.home = self.access.issue(self.case, 'homeowner-one')
        self.reviewer = self.access.issue(self.case, 'reviewer-one', 'reviewer')
        self.other_token = self.access.issue(self.other, 'homeowner-two')

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, payload=None, token=None, headers=None):
        request_headers = {'Authorization': 'Bearer ' + (self.home if token is None else token)}
        if payload is not None:
            request_headers['Content-Type'] = 'application/json'
        request_headers.update(headers or {})
        request = Request(self.base + path,
                          data=None if payload is None else json.dumps(payload).encode(), headers=request_headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return response.status, (json.loads(body) if response.headers.get_content_type() == 'application/json' else body)

    def publish(self, stage='pre_bid'):
        report = {'meta': {'report_type': stage}, 'questions': ['Are permit fees included?'],
                  'findings': [{'title': 'Clarify permit fees', 'detail': 'Written scope is needed.'}]}
        status, response = self.request('/api/reports', {'report': report}, self.reviewer)
        self.assertEqual(status, 201)
        return response['report_id']

    def test_session_discloses_only_the_authenticated_role(self):
        self.assertEqual(self.request('/api/session'),(200,{'role':'homeowner'}))
        self.assertEqual(self.request('/api/session',token=self.reviewer),(200,{'role':'reviewer'}))
        self.assertEqual(self.request('/api/session',token='invalid')[0],401)

    def test_two_stage_return_visit_upload_answer_review_and_reopen(self):
        initial = self.publish()
        content = b'Synthetic bid addendum: permit fees included.'
        status, evidence = self.request('/api/evidence', {
            'filename': 'builder-addendum.txt', 'content_base64': base64.b64encode(content).decode()})
        self.assertEqual(status, 201)
        bid = self.publish('bid_gap')
        status, case = self.request('/api/case')
        self.assertEqual(status, 200)
        self.assertEqual([r['stage'] for r in case['reports']], ['pre_bid', 'bid_gap'])
        question = case['reports'][1]['questions'][0]['id']
        status, answer = self.request('/api/answers', {'report_id': bid, 'question_id': question,
            'text': 'Included in the addendum', 'evidence_refs': [evidence['reference']]})
        self.assertEqual(status, 201)
        self.assertFalse(self.request('/api/reports/' + bid)[1]['return_visit']['questions'][0]['resolved'])
        status, _ = self.request('/api/reviews', {'report_id': bid, 'answer_id': answer['answer_id'],
            'decision': 'accepted', 'rationale': 'Read the written inclusion',
            'evidence_refs': [evidence['reference']], 'reviewer_id': 'spoofed'}, self.reviewer)
        self.assertEqual(status, 201)
        updated = self.request('/api/reports/' + bid)[1]
        self.assertEqual(updated['questions'], [])
        self.assertEqual(updated['return_visit']['questions'][0]['answer']['reviews'][0]['reviewer_id'], 'reviewer-one')
        self.assertFalse(updated['return_visit']['estimate_released'])
        self.assertEqual(self.request('/api/reports/' + initial)[1]['questions'], ['Are permit fees included?'])
        self.request('/api/answers', {'report_id': bid, 'question_id': question, 'text': 'Builder changed the scope'})
        self.assertEqual(self.request('/api/reports/' + bid)[1]['questions'], ['Are permit fees included?'])
        reopened_store = AnswerStore(self.path)
        self.assertEqual(len(reopened_store.read_case(self.case)['reports'][1]['questions'][0]['answers']), 2)
        self.assertEqual(CaseAccess(reopened_store).authenticate(self.home)['case_id'], self.case)
        file_id = evidence['reference'].split(':')[1]
        self.assertEqual(self.request('/api/evidence/' + file_id), (200, content))

    def test_cross_case_report_answer_review_and_file_access_denied(self):
        report = self.publish()
        qid = self.store.read_case(self.case)['reports'][0]['questions'][0]['id']
        evidence = self.store.attach_evidence(self.case, 'private.txt', b'private')
        for path, payload in [('/api/reports/' + report, None),
                              ('/api/answers', {'report_id': report, 'question_id': qid, 'text': 'Other user'}),
                              ('/api/reviews', {'report_id': report, 'answer_id': 1}),
                              ('/api/evidence/' + evidence['reference'].split(':')[1], None)]:
            self.assertEqual(self.request(path, payload, self.other_token)[0], 404)
        other_case = self.request('/api/case', token=self.other_token)[1]
        self.assertEqual(other_case['reports'], [])
        self.assertEqual(other_case['documents'], [])

    def test_homeowner_cannot_publish_reports_or_approve_answers(self):
        report = self.publish()
        self.assertEqual(self.request('/api/reports', {'report': {'meta': {'report_type': 'bid_gap'}}})[0], 403)
        self.assertEqual(self.request('/api/reviews', {'report_id': report, 'answer_id': 1, 'role': 'reviewer'})[0], 403)

    def test_revocation_expiration_and_invalid_credentials(self):
        self.assertEqual(self.request('/api/case', token='')[0], 401)
        self.assertEqual(self.request('/api/case', token='wrong')[0], 401)
        self.access.revoke(self.home)
        self.assertEqual(self.request('/api/case')[0], 401)
        with self.store.connect() as db, db:
            db.execute('UPDATE case_access SET expires_at=?', (time.time() - 1,))
        self.assertEqual(self.request('/api/case', token=self.reviewer)[0], 401)
        self.assertNotIn(self.home.encode(), self.path.read_bytes())

    def test_cross_origin_host_and_url_credentials_refused(self):
        self.assertEqual(self.request('/api/case', headers={'Origin': 'https://other.invalid'})[0], 403)
        self.assertEqual(self.request('/api/case', headers={'Host': 'other.invalid'})[0], 403)
        self.assertEqual(self.request('/api/case?token=secret')[0], 400)

    def test_bad_uploads_and_other_case_evidence_cannot_be_attached_to_answer(self):
        for value in ('!bad-base64!', '', 22):
            self.assertEqual(self.request('/api/evidence', {'filename': 'file', 'content_base64': value})[0], 400)
        report = self.publish()
        qid = self.store.read_case(self.case)['reports'][0]['questions'][0]['id']
        evidence = self.store.attach_evidence(self.other, 'secret.txt', b'other case')
        self.assertEqual(self.request('/api/answers', {'report_id': report, 'question_id': qid,
            'text': 'Included', 'evidence_refs': [evidence['reference']]})[0], 400)

    def test_changed_file_blocks_updated_report(self):
        report = self.publish()
        qid = self.store.read_case(self.case)['reports'][0]['questions'][0]['id']
        evidence = self.store.attach_evidence(self.case, 'scope.txt', b'original')
        self.store.record_answer(report, qid, 'Included', [evidence['reference']])
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=?', (b'altered',))
        self.assertEqual(self.request('/api/reports/' + report)[0], 400)

    def test_malformed_identities_and_oversized_requests_rejected_without_breaking_service(self):
        for value in ([], {}, None, 12, ''):
            self.assertEqual(self.request('/api/answers', {'report_id': value})[0], 400)
            self.assertEqual(self.request('/api/answers', {'question_id': value})[0], 400)
            self.assertEqual(self.request('/api/reviews', {'answer_id': value}, self.reviewer)[0], 400)
        self.assertEqual(self.request('/api/answers', {}, headers={'Content-Length': str(1024 * 1024 + 1)})[0], 413)
        self.assertEqual(self.request('/api/evidence', {}, headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request('/api/case')[0], 200)

    def test_only_portal_assets_are_public(self):
        for path in ('/', '/portal.css', '/portal.js'):
            status, body = self.request(path, token='')
            self.assertEqual(status, 200)
            self.assertNotIn(self.case.encode(), body)
            self.assertNotIn(self.home.encode(), body)
        self.assertEqual(self.request('/api/case', token='')[0], 401)
        self.assertEqual(self.request('/../case_service.py', token='')[0], 401)
        self.assertEqual(self.request('/?token=secret', token='')[0], 400)

    def test_upload_is_processed_automatically_without_publishing_a_report(self):
        raw = b'Scope for review\nTotal: $1,400.00\nGrand total: $1,600.00\n'
        status, evidence = self.request('/api/evidence', {'filename': 'bid.txt',
            'content_base64': base64.b64encode(raw).decode()})
        self.assertEqual(status, 201)
        path = '/api/document-processing/' + evidence['reference'].split(':')[1]
        deadline = time.monotonic() + 5
        while True:
            status, processed = self.request(path)
            self.assertEqual(status, 200)
            if processed['status'] not in ('queued', 'processing'):
                break
            if time.monotonic() >= deadline:
                self.fail('Live server did not process the uploaded document')
            time.sleep(.1)
        self.assertEqual(processed['status'], 'text_extracted')
        self.assertEqual([c['value'] for c in processed['result']['field_candidates']], ['1400.00', '1600.00'])
        case = self.request('/api/case')[1]
        self.assertEqual(case['documents'][0]['processing_status'], 'text_extracted')
        self.assertEqual(case['reports'], [])
        self.assertEqual(self.request(path, token=self.other_token)[0], 404)

    def test_report_download_preserves_both_stages_and_current_answer_review(self):
        initial = self.publish()
        bid = self.publish('bid_gap')
        path = '/api/reports/' + bid + '/download'
        def read_download():
            status, raw = self.request(path)
            self.assertEqual(status, 200)
            self.assertNotIn(self.home.encode(), raw)
            embedded = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', raw.decode(), re.S)
            return json.loads(embedded.group(1))
        report = read_download()
        self.assertEqual(report['meta']['report_type'], 'bid_gap')
        self.assertFalse(report['return_visit']['estimate_released'])
        qid = report['return_visit']['questions'][0]['id']
        answer = self.store.record_answer(bid, qid, 'Builder says included')
        report = read_download()
        self.assertEqual(report['return_visit']['questions'][0]['status'], 'answer_received_needs_review')
        self.store.review_answer(bid, answer['answer_id'], 'reviewer-one', 'accepted', 'Written scope checked', ['Addendum page 2'])
        accepted = read_download()
        self.assertEqual(accepted['questions'], [])
        self.assertEqual(accepted['return_visit']['questions'][0]['answer']['reviews'][-1]['rationale'], 'Written scope checked')
        self.assertEqual(accepted['findings'], report['findings'])
        self.store.record_answer(bid, qid, 'The builder now excludes permits')
        self.assertEqual(read_download()['questions'], ['Are permit fees included?'])
        status, raw = self.request('/api/reports/' + initial + '/download')
        self.assertEqual(status, 200)
        self.assertIn(b'pre_bid', raw)
        self.assertEqual(self.store.read_case(self.case)['reports'][0]['questions'][0]['answers'], [])
        request = Request(self.base + path, headers={'Authorization': 'Bearer ' + self.home})
        with urlopen(request) as response:
            self.assertEqual(response.headers['Content-Disposition'], 'attachment; filename="level-ground-review.html"')
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.request(path, token=self.other_token)[0], 404)
        self.assertEqual(self.request(path, token='invalid')[0], 401)
        self.assertEqual(self.request(path, headers={'Origin':'https://other.invalid'})[0], 403)

    def test_report_download_refuses_changed_source_or_evidence(self):
        report = self.publish()
        path = '/api/reports/' + report + '/download'
        evidence = self.store.attach_evidence(self.case, 'clarification.txt', b'Original clarification')
        qid = self.store.read_case(self.case)['reports'][0]['questions'][0]['id']
        self.store.record_answer(report, qid, 'Included', [evidence['reference']])
        self.assertEqual(self.request(path)[0], 200)
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=? WHERE case_id=?', (b'Changed', self.case))
        self.assertEqual(self.request(path)[0], 400)
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=? WHERE case_id=?', (b'Original clarification', self.case))
            db.execute('UPDATE reports SET body=? WHERE id=?', ('{}', report))
        self.assertEqual(self.request(path)[0], 400)

    def test_reviewer_can_initialize_uploaded_plan_without_exposing_private_defaults(self):
        with fitz.open() as pdf:
            pdf.new_page().insert_text((30, 30), 'MAIN FLOOR PLAN')
            raw = pdf.tobytes()
        evidence = self.store.attach_evidence(self.case, 'plan.pdf', raw)
        self.server.processing.process_next()
        jurisdiction={'state':'GA','authority_id':'GA-JASPER-COUNTY','authority_verified':False}
        payload = {'source_reference': evidence['reference'], 'reviewer_id': 'spoofed','jurisdiction':jurisdiction}
        self.assertEqual(self.request('/api/plan-workspaces', payload)[0], 403)
        status, result = self.request('/api/plan-workspaces', payload, self.reviewer)
        self.assertEqual(status, 200)
        self.assertEqual(result['page_count'], 1)
        self.assertFalse(result['estimate_released'])
        self.assertNotIn('settings', result)
        path = '/api/plan-workspaces/' + result['workspace_id']
        self.assertEqual(self.request(path)[1], result)
        self.assertEqual(self.request(path, token=self.other_token)[0], 404)
        self.assertEqual(self.request('/api/plan-workspaces', payload, self.reviewer)[1], result)
        manifest = json.loads((self.path.parent / 'plan_workspaces' / self.case / result['workspace_id'] / 'case_workspace.json').read_text())
        self.assertEqual(manifest['selected_by'], 'reviewer-one')
        local=self.path.parent/'plan_workspaces'/self.case/result['workspace_id']/'local_requirements.json'
        self.assertEqual(json.loads(local.read_bytes())['project_basis'],jurisdiction)
        original=local.read_bytes()
        changed={**payload,'jurisdiction':{**jurisdiction,'authority_verified':True}}
        self.assertEqual(self.request('/api/plan-workspaces',changed,self.reviewer)[0],400)
        self.assertEqual(local.read_bytes(),original)
        corrections=path+'/permit-inputs'
        self.assertEqual(self.request(corrections)[0],403)
        self.assertEqual(self.request(corrections,token=self.reviewer)[1]['revision'],0)
        correction={'expected_revision':0,'jurisdiction':{'state':'GA','authority_id':'GA-JASPER-CITY'},
            'rationale':'Synthetic jurisdiction correction','evidence_refs':[evidence['reference']]}
        self.assertEqual(self.request(corrections,correction)[0],403)
        foreign=self.access.issue(self.other,'other-reviewer','reviewer')
        self.assertEqual(self.request(corrections,correction,foreign)[0],400)
        self.assertEqual(self.request(corrections,{**correction,'reviewer_id':'spoofed'},self.reviewer)[0],400)
        code,saved=self.request(corrections,correction,self.reviewer)
        self.assertEqual(code,201);self.assertEqual(saved['records'][0]['reviewer_id'],'reviewer-one')
        self.assertEqual(self.request(corrections,correction,self.reviewer)[0],400)
        current=self.request(corrections,token=self.reviewer)[1]
        self.assertEqual(current['project_basis'],correction['jurisdiction'])
        self.assertEqual(current['initial_project_basis'],jurisdiction)
        self.assertEqual(local.read_bytes(),original)


if __name__ == '__main__':
    unittest.main()
