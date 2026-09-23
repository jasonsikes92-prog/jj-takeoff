import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from bid_document_reviews import BidDocumentReviews
from bid_package_review import prepare_bid_package
from case_service import make_server
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
from reviewer_queue import case_review_queue


class BidPackageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = AnswerStore(self.root / 'cases.sqlite3')
        self.case = self.store.create_case('Synthetic package')
        self.other = self.store.create_case('Other case')
        self.processing = DocumentProcessing(self.store)
        self.reviews = BidDocumentReviews(self.store, self.processing)
        self.primary = self.review('builder_bid', 'Gutters excluded.', 'excluded', 300000)
        self.quote = self.review('trade_quote', 'Gutters included.', 'included', 2000)
        self.payload = {'primary_review_id':self.primary['id'], 'attachments':[
            {'review_id':self.quote['id'], 'relationship':'unconfirmed', 'rationale':'No incorporation statement in the supplied bid.'}]}

    def review(self, kind, wording, status, amount=None, complete=True):
        text = wording + (f'\nTotal: ${amount:,.2f}' if amount is not None else '')
        evidence = self.store.attach_evidence(self.case, kind + '.txt', text.encode())
        self.processing.process_next()
        payload = self.reviews.prepare(self.case, evidence['reference'].split(':')[1])['review_template']
        payload.update(document_kind=kind, reviewed_pages=[1], document_review_complete=complete,
            rationale='Synthetic fixture: complete source read.' if complete else 'Partial fixture.',
            currency='USD' if amount is not None else None, total_candidate_index=0 if amount is not None else None)
        payload['lines'][0].update(scope_status=status, confirmed_scopes=['Gutters & downspouts'] if status != 'unclear' else [])
        return self.reviews.save(self.case, 'operator', payload)

    def draft(self, payload=None):
        return prepare_bid_package(self.reviews, self.case, 'operator', payload or self.payload)

    def test_unincorporated_quote_cannot_close_bid_exclusion_or_inflate_total(self):
        before = self.store.read_case(self.case)
        report = self.draft()
        gutter = next(c for c in report['scope_checks'] if c['id'] == 'gutters')
        self.assertEqual(gutter['status'], 'excluded_per_source_review')
        self.assertEqual(len(gutter['evidence_lines']), 1)
        self.assertEqual(report['meta']['primary_bid_total'], 300000)
        self.assertIsNone(report['meta']['bid_total'])
        self.assertIsNone(report['meta']['package_total'])
        self.assertEqual([s['document_total'] for s in report['source_documents']], [300000, 2000])
        self.assertEqual([d['scope_id'] for d in report['document_scope_differences']], ['gutters'])
        refs = [l['source_ref'] for l in report['document_scope_differences'][0]['evidence_lines']]
        self.assertEqual(set(refs), {f"evidence:{r['evidence_id']}, page 1" for r in (self.primary, self.quote)})
        self.assertTrue(any('incorporated' in q for q in report['questions']))
        self.assertEqual(report['quantities'], [])
        self.assertFalse(report['complete_home_bid_review'])
        self.assertFalse(report['homeowner_release_approved'])
        self.assertEqual(before, self.store.read_case(self.case))

    def test_incorporated_addendum_preserves_conflict_instead_of_overriding_bid(self):
        addendum = self.review('scope_addendum', 'Gutters included.', 'included', 1000)
        payload = {'primary_review_id':self.primary['id'], 'attachments':[
            {'review_id':addendum['id'], 'relationship':'incorporated', 'rationale':'Fixture bid references the attached scope revision.'}]}
        report = self.draft(payload)
        self.assertEqual(next(c for c in report['scope_checks'] if c['id'] == 'gutters')['status'], 'conflicting_wording')
        self.assertIsNone(report['meta']['bid_total'])
        self.assertEqual(report['meta']['primary_bid_total'], 300000)
        self.assertEqual(len(report['source_documents']), 2)

    def test_primary_unknown_total_remains_unknown_with_priced_quote(self):
        primary = self.review('builder_bid', 'Gutters included.', 'included')
        report = self.draft({**self.payload, 'primary_review_id':primary['id']})
        self.assertIsNone(report['meta']['primary_bid_total'])
        self.assertIsNone(report['meta']['bid_total'])

    def test_invalid_selections_partial_incorporation_and_other_case_rejected(self):
        variants = [
            {**self.payload, 'primary_review_id':self.quote['id']},
            {**self.payload, 'attachments':[]},
            {**self.payload, 'attachments':self.payload['attachments'] * 2},
            {**self.payload, 'attachments':[dict(self.payload['attachments'][0], relationship='incorporated', rationale='')]},
            {**self.payload, 'attachments':[dict(self.payload['attachments'][0], relationship=True)]},
            {**self.payload, 'attachments':[dict(self.payload['attachments'][0], review_id=self.primary['id'])]},
        ]
        for payload in variants:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.draft(payload)
        other_bid = self.review('builder_bid', 'Gutters included.', 'included')
        with self.assertRaises(ValueError):
            self.draft({**self.payload, 'attachments':[dict(self.payload['attachments'][0], review_id=other_bid['id'])]})
        partial = self.review('trade_quote', 'Gutters included.', 'unclear', complete=False)
        attachment = dict(self.payload['attachments'][0], review_id=partial['id'])
        self.assertFalse(self.draft({**self.payload, 'attachments':[attachment]})['source_documents'][1]['document_review_complete'])
        with self.assertRaises(ValueError):
            self.draft({**self.payload, 'attachments':[dict(attachment, relationship='incorporated')]})
        with self.assertRaises(ValueError):
            prepare_bid_package(self.reviews, self.other, 'operator', self.payload)

    def revise_quote(self):
        payload = self.reviews.prepare(self.case, self.quote['evidence_id'])['review_template']
        payload.update(document_kind='trade_quote', reviewed_pages=[1], document_review_complete=True,
            rationale='New review without scope confirmation.', total_candidate_index=None)
        return self.reviews.save(self.case, 'operator', payload)

    def test_changed_attachment_reopens_whole_package_and_preserves_history(self):
        payload = copy.deepcopy(self.payload)
        payload['attachments'][0]['relationship'] = 'incorporated'
        report = self.draft(payload)
        self.store.attach_report(self.case, report)
        workspaces = PlanWorkspaces(self.store, self.root / 'workspaces')
        queue = lambda:case_review_queue(self.store, self.processing, workspaces, self.case)
        self.assertFalse(any(i['kind'] == 'bid_report_review' for i in queue()['items']))
        saved = self.store.read_case(self.case)['reports']
        self.revise_quote()
        with self.assertRaises(ValueError):
            self.draft(payload)
        reopened = {i['evidence_id'] for i in queue()['items'] if i['kind'] == 'bid_report_review'}
        self.assertEqual(reopened, {self.primary['evidence_id'], self.quote['evidence_id']})
        self.assertEqual(saved, self.store.read_case(self.case)['reports'])

    def test_unconfirmed_attachment_remains_in_queue_after_report_attachment(self):
        self.store.attach_report(self.case, self.draft())
        queue = case_review_queue(self.store, self.processing, PlanWorkspaces(self.store, self.root / 'workspaces'), self.case)
        pending = [i['evidence_id'] for i in queue['items'] if i['kind'] == 'bid_report_review']
        self.assertEqual(pending, [self.quote['evidence_id']])

    def test_tampered_source_and_concurrent_revision_cannot_generate_package(self):
        with patch('bid_package_review.package_sources_current', return_value=False):
            with self.assertRaises(ValueError):
                self.draft()
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=? WHERE id=?', (b'changed', self.quote['evidence_id']))
        with self.assertRaises(ValueError):
            self.draft()

    def test_http_role_case_attachment_revalidation_and_return_visit(self):
        server = make_server(self.store.path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            operator = server.access.issue(self.case, 'operator', 'reviewer')
            owner = server.access.issue(self.case, 'owner')
            other = server.access.issue(self.other, 'other-operator', 'reviewer')
            def request(path, payload=None, token=operator):
                headers = {'Authorization':'Bearer ' + token}
                if payload is not None:
                    headers['Content-Type'] = 'application/json'
                req = Request(f'http://127.0.0.1:{server.server_port}' + path,
                    data=None if payload is None else json.dumps(payload).encode(), headers=headers)
                try:
                    response = urlopen(req, timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    return response.status, json.load(response)
            endpoint = '/api/bid-package-draft'
            self.assertEqual(request(endpoint, self.payload, owner)[0], 403)
            self.assertEqual(request(endpoint, self.payload, other)[0], 400)
            status, draft = request(endpoint, {**self.payload, 'reviewer_id':'spoofed'})
            self.assertEqual(status, 200)
            self.assertEqual(draft, self.draft())
            self.assertEqual(self.store.read_case(self.case)['reports'], [])
            for sources in ([], None, {}, draft['source_documents'][:1]):
                self.assertEqual(request('/api/reports', {'report':{**draft, 'source_documents':sources}})[0], 400)
            altered = copy.deepcopy(draft)
            altered['meta']['bid_total'] = 302000
            self.assertEqual(request('/api/reports', {'report':altered})[0], 400)
            status, saved = request('/api/reports', {'report':draft})
            self.assertEqual(status, 201)
            report = self.store.read_case(self.case)['reports'][0]
            question = next(q for q in report['questions'] if 'incorporated' in q['text'])
            self.assertEqual(request('/api/answers', {'report_id':saved['report_id'], 'question_id':question['id'],
                'text':'The builder says this quote is included.'}, owner)[0], 201)
            status, updated = request('/api/reports/' + saved['report_id'], token=owner)
            self.assertEqual(status, 200)
            self.assertIsNone(updated['meta']['bid_total'])
            self.assertEqual(updated['source_documents'][1]['relationship'], 'unconfirmed')
            self.revise_quote()
            self.assertEqual(request('/api/reports', {'report':draft})[0], 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
