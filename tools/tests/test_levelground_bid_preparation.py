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
from bid_document_reviews import BidDocumentReviews
from case_service import make_server
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
from reviewer_queue import case_review_queue


class BidPreparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = AnswerStore(self.root / 'cases.sqlite3')
        self.case = self.store.create_case('Preparation test')
        self.other = self.store.create_case('Other case')
        self.processing = DocumentProcessing(self.store)
        self.reviews = BidDocumentReviews(self.store, self.processing)

    def upload(self, text, filename='bid.txt'):
        evidence = self.store.attach_evidence(self.case, filename, text.encode() if isinstance(text, str) else text)
        self.processing.process_next()
        return evidence['reference'].split(':')[1]

    def test_ruled_prices_reach_review_preparation_without_approving_scope_or_total(self):
        from test_quote_table_candidates import ruled_pdf
        evidence=self.upload(ruled_pdf(),'trade-quote.pdf')
        prepared=self.reviews.prepare(self.case,evidence)
        extraction=self.processing.read(self.case,evidence)
        self.assertEqual(prepared['pricing_extraction'],extraction['result']['pricing_extraction'])
        self.assertEqual(len(prepared['pricing_extraction']['pricing_candidates']),2)
        self.assertTrue(extraction['result']['pricing_extractor_sha256'])
        self.assertIsNone(prepared['report_draft']['meta']['bid_total'])
        self.assertFalse(prepared['report_draft']['homeowner_release_approved'])
        self.assertEqual(prepared['automatic_scope_assertions'],0)
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_measurement_terms_reach_preparation_and_reviewed_draft_without_auto_acceptance(self):
        evidence=self.upload('No deductions for windows or doors.\nBilling waste: 0%\nMaterial waste: 10%')
        prepared=self.reviews.prepare(self.case,evidence)
        terms=prepared['measurement_terms']
        self.assertEqual([c['value'] for c in terms['candidates']],[False,'0','10'])
        self.assertEqual(terms,self.processing.read(self.case,evidence)['result']['measurement_terms'])
        self.assertEqual(prepared['report_draft']['measurement_terms'],terms)
        finding=next(f for f in prepared['report_draft']['findings'] if f['category']=='pricing_measurement_terms')
        self.assertIn('page 1, line 2',finding['evidence_lines'][1]['source_ref'])
        self.assertIsNone(finding['realistic_high'])
        payload=prepared['review_template']
        payload.update(document_kind='trade_quote',reviewed_pages=[1],rationale='Synthetic source review only')
        review=self.reviews.save(self.case,'operator',payload)
        draft=self.reviews.draft(self.case,review['id'])
        self.assertEqual(draft['measurement_terms'],terms)
        self.assertTrue(any(f['category']=='pricing_measurement_terms' for f in draft['findings']))
        self.assertFalse(draft['homeowner_release_approved']);self.assertFalse(draft['estimate_released'])
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_all_wording_retained_with_page_line_sources_and_unconfirmed_totals(self):
        text = 'INCLUDED\nGutters and downspouts\nEXCLUDED\nLandscaping\n\nSee revised scope attachment\nTotal: $100,000.00\nTotal: $110,000.00'
        evidence = self.upload(text)
        before = self.store.read_case(self.case)
        extraction = self.processing.read(self.case, evidence)
        prepared = self.reviews.prepare(self.case, evidence)
        self.assertEqual([line['source_text'] for line in prepared['lines']], [t for t in text.splitlines() if t])
        self.assertEqual(prepared['lines'][4]['line'], 6)
        self.assertEqual(prepared['lines'][1]['suggested_scopes'], ['Gutters & downspouts'])
        self.assertEqual([c['candidate_index'] for c in prepared['total_candidates']], [0, 1])
        self.assertEqual([c['value'] for c in prepared['total_candidates']], ['100000.00', '110000.00'])
        report = prepared['report_draft']
        self.assertIsNone(report['meta']['bid_total'])
        self.assertIsNone(report['meta']['our_range'])
        self.assertEqual(report['quantities'], [])
        self.assertTrue(all(s['status'] in ('unverified', 'selection_unconfirmed') for s in report['scope_checks']))
        gutter = next(s for s in report['scope_checks'] if s['id'] == 'gutters')
        self.assertIn('page 1, line 2', gutter['evidence_lines'][0]['source_ref'])
        self.assertEqual(report['source_document']['reviewed_pages'], [])
        self.assertFalse(report['homeowner_release_approved'])
        self.assertEqual(before, self.store.read_case(self.case))
        self.assertEqual(extraction, self.processing.read(self.case, evidence))
        self.assertIsNone(self.reviews.latest(self.case, evidence))

    def test_preparation_requires_real_review_before_scope_or_total_approval(self):
        evidence = self.upload('Gutters included.\nTotal: $10,000.00')
        prepared = self.reviews.prepare(self.case, evidence)
        payload = prepared['review_template']
        with self.assertRaises(ValueError):
            self.reviews.save(self.case, 'operator', payload)
        payload.update(document_kind='builder_bid', reviewed_pages=[1], rationale='Reviewed complete original and context.')
        review = self.reviews.save(self.case, 'operator', payload)
        self.assertIsNone(self.reviews.draft(self.case, review['id'])['meta']['bid_total'])
        revised = self.reviews.prepare(self.case, evidence)['review_template']
        self.assertEqual(revised['base_review_id'], review['id'])
        revised.update(document_kind='builder_bid', reviewed_pages=[1], document_review_complete=True,
                       rationale='Confirmed gutter scope and USD total against entire bid.', currency='USD', total_candidate_index=0)
        revised['lines'][0].update(scope_status='included', confirmed_scopes=['Gutters & downspouts'])
        approved = self.reviews.save(self.case, 'operator', revised)
        draft = self.reviews.draft(self.case, approved['id'])
        self.assertEqual(draft['meta']['bid_total'], 10000)
        self.assertEqual(next(s for s in draft['scope_checks'] if s['id'] == 'gutters')['status'], 'included_per_source_review')
        self.assertEqual(self.store.read_case(self.case)['reports'], [])

    def test_clause_candidates_reach_report_without_confirming_review_template(self):
        evidence = self.upload('EXCLUSIONS\nGutters\nALLOWANCES\nCabinets $8,000\nTERMS\nRock excavation charged separately.\nOwner to supply appliances.')
        before = self.store.read_case(self.case)
        prepared = self.reviews.prepare(self.case, evidence)
        self.assertEqual(prepared['method'], 'source_line_preparation_v2')
        candidates = prepared['clause_candidates']
        self.assertEqual({c['kind'] for c in candidates}, {'exclusion','allowance','extra_charge','owner_supply'})
        report = prepared['report_draft']
        self.assertEqual(report['clause_candidates'], candidates)
        findings = [f for f in report['findings'] if f['category']=='contract_wording_review']
        self.assertEqual(len(findings), 4)
        self.assertTrue(all(f['detail'] in report['questions'] for f in findings))
        self.assertTrue(all(l['scope_status']=='unclear' and not l['confirmed_scopes'] for l in prepared['review_template']['lines']))
        self.assertIsNone(report['meta']['bid_total'])
        self.assertEqual(prepared['automatic_scope_assertions'], 0)
        self.assertEqual(before, self.store.read_case(self.case))
        self.assertIsNone(self.reviews.latest(self.case, evidence))

    def test_large_document_does_not_hide_omitted_wording(self):
        evidence = self.upload('\n'.join(['Scope detail'] * 1000 + ['Gutters excluded.']))
        prepared = self.reviews.prepare(self.case, evidence)
        self.assertEqual(len(prepared['lines']), 1000)
        self.assertEqual(prepared['source_line_count'], 1001)
        self.assertEqual(prepared['omitted_line_count'], 1)
        self.assertEqual(prepared['pages_with_omitted_lines'], [1])
        self.assertTrue(any('1,000' in u for u in prepared['report_draft']['unknowns']))
        self.assertFalse(prepared['review_template']['document_review_complete'])

    def test_partial_pdf_retains_missing_page_requirement(self):
        with fitz.open() as pdf:
            pdf.new_page().insert_text((20, 20), 'Gutters included.')
            pdf.new_page()
            evidence = self.upload(pdf.tobytes(), 'partial.pdf')
        prepared = self.reviews.prepare(self.case, evidence)
        self.assertEqual(prepared['pages_needing_visual_or_ocr_review'], [2])
        self.assertTrue(any('OCR' in u for u in prepared['report_draft']['unknowns']))
        payload = prepared['review_template']
        payload.update(document_kind='builder_bid', reviewed_pages=[1, 2], document_review_complete=True, rationale='Trying to confirm missing page')
        with self.assertRaises(ValueError):
            self.reviews.save(self.case, 'operator', payload)
        blank = self.upload('   ')
        with self.assertRaises(ValueError):
            self.reviews.prepare(self.case, blank)

    def test_source_tampering_and_case_boundaries(self):
        evidence = self.upload('Gutters included.')
        with self.assertRaises(ValueError):
            self.reviews.prepare(self.other, evidence)
        with self.store.connect() as db, db:
            db.execute('UPDATE document_processing SET result=? WHERE evidence_id=?', ('{}', evidence))
        with self.assertRaises(ValueError):
            self.reviews.prepare(self.case, evidence)

    def test_queue_links_preparation_without_clearing_review_work(self):
        evidence = self.upload('Landscaping excluded.')
        workspaces = PlanWorkspaces(self.store, self.root / 'workspaces')
        before = case_review_queue(self.store, self.processing, workspaces, self.case)
        item = next(i for i in before['items'] if i.get('evidence_id') == evidence)
        self.assertEqual(item['bid_preparation_url'], f'/api/document-processing/{evidence}/bid-preparation')
        self.reviews.prepare(self.case, evidence)
        self.assertEqual(before, case_review_queue(self.store, self.processing, workspaces, self.case))

    def test_http_case_and_role_boundaries_and_no_implicit_review(self):
        evidence = self.upload('Garage door with opener.\nInstallation charged separately.\nTotal: $5,000.00')
        server = make_server(self.store.path, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            tokens = [server.access.issue(self.case, 'operator', 'reviewer'),
                      server.access.issue(self.case, 'owner'),
                      server.access.issue(self.other, 'other-operator', 'reviewer')]
            endpoint = f'http://127.0.0.1:{server.server_port}/api/document-processing/{evidence}/bid-preparation'
            responses = []
            for token in tokens:
                try:
                    response = urlopen(Request(endpoint, headers={'Authorization':'Bearer ' + token}), timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    responses.append((response.status, json.load(response)))
            self.assertEqual([s for s, _ in responses], [200, 403, 400])
            self.assertEqual(responses[0][1]['report_draft']['report_status'], 'machine_preparation')
            self.assertEqual(responses[0][1]['clause_candidates'][0]['kind'], 'extra_charge')
            self.assertIn('page 1, line 2', responses[0][1]['clause_candidates'][0]['source_ref'])
            self.assertEqual(self.store.read_case(self.case)['reports'], [])
            self.assertIsNone(self.reviews.latest(self.case, evidence))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
