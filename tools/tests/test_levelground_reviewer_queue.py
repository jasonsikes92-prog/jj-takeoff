import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from case_service import make_server
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
from reviewer_queue import case_review_queue


class ReviewerQueueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = AnswerStore(self.root / 'cases.sqlite3')
        self.case = self.store.create_case('Synthetic owner')
        self.processing = DocumentProcessing(self.store)
        self.workspaces = PlanWorkspaces(self.store, self.root / 'plan_workspaces')

    def queue(self):
        return case_review_queue(self.store, self.processing, self.workspaces, self.case)

    def report(self, stage='pre_bid'):
        return self.store.attach_report(self.case, {'meta':{'report_type':stage}, 'questions':['Who pays for permits?']})

    def test_latest_stage_answer_review_and_revision_drive_queue(self):
        self.report()
        report = self.report()
        bid = self.report('bid_gap')
        original = self.store.read_case(self.case)
        queue = self.queue()
        self.assertEqual(queue['historical_reports_omitted'], 1)
        self.assertEqual(queue['current_report_ids'], {'pre_bid':report, 'bid_gap':bid})
        self.assertEqual(queue['counts'], {'reviewer':0, 'homeowner':2, 'worker':0})
        self.assertEqual(original, self.store.read_case(self.case))
        question = next(i for i in queue['items'] if i['report_id'] == report)['question_id']
        first = self.store.record_answer(report, question, 'Builder includes permit fees')
        self.assertEqual(self.queue()['counts']['reviewer'], 1)
        self.store.review_answer(report, first['answer_id'], 'operator', 'accepted', 'Written confirmation', ['contract page 3'])
        self.assertEqual(self.queue()['counts']['reviewer'], 0)
        self.assertEqual(len(self.queue()['items']), 1)
        second = self.store.record_answer(report, question, 'Builder now says fees are extra')
        task = next(i for i in self.queue()['items'] if i.get('report_id') == report)
        self.assertEqual(task['answer_id'], second['answer_id'])
        self.assertEqual(task['answer_revision'], 2)
        self.store.review_answer(report, second['answer_id'], 'operator', 'needs_clarification', 'Need addendum', ['contract page 3'])
        task = next(i for i in self.queue()['items'] if i.get('report_id') == report)
        self.assertEqual(task['owner'], 'homeowner')
        self.assertFalse(self.queue()['complete_home_review'])

    def test_upload_preparation_manual_review_and_tampering(self):
        upload = self.store.attach_evidence(self.case, 'bid.txt', b'Total: $12,000.00')
        queue = self.queue()
        self.assertEqual(queue['counts']['worker'], 1)
        self.processing.process_next()
        task = next(i for i in self.queue()['items'] if i.get('source_reference') == upload['reference'])
        self.assertEqual(task['kind'], 'document_scope_review')
        self.assertNotIn('12000', json.dumps(task))
        self.store.attach_evidence(self.case, 'unknown.bin', b'unsupported')
        self.processing.process_next()
        self.assertIn('document_manual_review', [i['kind'] for i in self.queue()['items']])
        with self.store.connect() as db, db:
            db.execute('UPDATE document_processing SET result=? WHERE evidence_id=?', ('{}', upload['reference'].split(':')[1]))
        self.assertIn('source_verification_failed', [i['kind'] for i in self.queue()['items']])
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=? WHERE id=?', (b'changed', upload['reference'].split(':')[1]))
        self.assertIn('source_verification_failed', [i['kind'] for i in self.queue()['items']])

    def test_selected_plan_queue_and_interrupted_workspace(self):
        with fitz.open() as pdf:
            pdf.new_page().insert_text((30,30), 'SYNTHETIC FLOOR PLAN')
            raw = pdf.tobytes()
        upload = self.store.attach_evidence(self.case, 'plan.pdf', raw)
        self.processing.process_next()
        workspace = self.workspaces.initialize(self.case, upload['reference'], 'operator')
        kinds = [i['kind'] for i in self.queue()['items']]
        self.assertIn('sheet_coverage_review', kinds)
        self.assertIn('measurement_not_prepared', kinds)
        self.assertNotIn('document_scope_review', kinds)
        manifest = self.workspaces.root / self.case / workspace['workspace_id'] / 'case_workspace.json'
        manifest.unlink()
        self.assertIn('workspace_verification_failed', [i['kind'] for i in self.queue()['items']])

    def test_http_reviewer_role_case_isolation_and_no_mutation(self):
        server = make_server(self.store.path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            other = self.store.create_case('Other case')
            self.report()
            before = self.store.read_case(self.case)
            reviewer = server.access.issue(self.case, 'operator', 'reviewer')
            home = server.access.issue(self.case, 'owner')
            other_reviewer = server.access.issue(other, 'other operator', 'reviewer')
            def request(token):
                try:
                    response = urlopen(Request(f'http://127.0.0.1:{server.server_port}/api/reviewer-queue',
                        headers={'Authorization':'Bearer ' + token}), timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    return response.status, json.load(response)
            status, queue = request(reviewer)
            self.assertEqual(status, 200)
            self.assertEqual(queue, self.queue())
            self.assertEqual(request(home)[0], 403)
            self.assertEqual(request('invalid')[0], 401)
            other_queue = request(other_reviewer)[1]
            self.assertEqual(other_queue['case_id'], other)
            self.assertEqual(other_queue['current_report_ids'], {})
            self.assertNotIn(self.case, json.dumps(other_queue))
            self.assertEqual(before, self.store.read_case(self.case))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
