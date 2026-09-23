import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from answer_store import AnswerStore
from document_processing import DocumentProcessing
from bid_document_reviews import BidDocumentReviews
from bid_package_review import prepare_bid_package
from bid_pricing_findings import pricing_findings
from quote_intake import extract_document_pages
from quote_table_candidates import extract_tables
from test_quote_table_candidates import pdf,ruled_pdf


class BidPricingFindings(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=AnswerStore(Path(tmp.name)/'cases.sqlite3');self.case=self.store.create_case('Pricing fixture')
        self.processing=DocumentProcessing(self.store);self.reviews=BidDocumentReviews(self.store,self.processing)

    def prepare(self,raw,filename='fixture.pdf'):
        source=self.store.attach_evidence(self.case,filename,raw)
        self.processing.process_next()
        return self.reviews.prepare(self.case,source['reference'].split(':')[1])

    def review(self,prepared,kind='trade_quote',complete=True):
        payload=prepared['review_template']
        payload.update(document_kind=kind,reviewed_pages=[1],document_review_complete=complete,
            rationale='Synthetic test: source wording read, units and price discrepancy remain unresolved.')
        return self.reviews.save(self.case,'test-reviewer',payload)

    def pricing(self,report):return [f for f in report['findings'] if f['category'].startswith('pricing_')]

    def test_math_discrepancy_is_a_source_question_not_a_cost_adjustment(self):
        prepared=self.prepare(pdf([('Drywall','$10.00','10','$110.00')]))
        report=prepared['report_draft'];findings=self.pricing(report)
        self.assertEqual({f['category'] for f in findings},{'pricing_arithmetic','pricing_quantity_basis'})
        finding=next(f for f in findings if f['category']=='pricing_arithmetic')
        source=finding['evidence_lines'][0]
        self.assertEqual(source['source_amount'],'110.00');self.assertEqual(source['calculated_amount'],'100.00')
        self.assertIn(prepared['evidence_id'],source['source_ref']);self.assertEqual(len(source['bbox']),4)
        self.assertIn(finding['detail'],report['questions'])
        self.assertIsNone(finding['bid_amount']);self.assertIsNone(finding['realistic_high'])
        self.assertIsNone(report['meta']['bid_total']);self.assertFalse(report['homeowner_release_approved'])
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_correct_math_still_needs_quantity_basis_without_false_mismatch(self):
        report=self.prepare(pdf([('Drywall','$10.00','10','$100.00')]))['report_draft']
        self.assertEqual([f['category'] for f in self.pricing(report)],['pricing_quantity_basis'])

    def test_package_amounts_do_not_invent_rates_or_math_errors(self):
        self.assertEqual(self.pricing(self.prepare(ruled_pdf())['report_draft']),[])

    def test_incomplete_rows_create_reading_question_not_missing_construction_claim(self):
        report=self.prepare(pdf([('Drywall','$10.00','','$100.00')]))['report_draft']
        findings=self.pricing(report)
        self.assertEqual([f['category'] for f in findings],['pricing_extraction_incomplete'])
        self.assertEqual(findings[0]['scope_status'],'unverified')
        self.assertIn('original document',findings[0]['detail'])

    def test_legacy_extraction_without_pricing_does_not_claim_verification(self):
        self.assertEqual(pricing_findings(None,'evidence:test','old.txt'),[])
        prepared=self.prepare(b'Gutters included.','old.txt')
        self.assertEqual(self.pricing(prepared['report_draft']),[])
        self.assertFalse(prepared['report_draft']['complete_home_bid_review'])

    def test_partial_and_complete_source_review_do_not_erase_pricing_questions(self):
        prepared=self.prepare(pdf([('Drywall','$10.00','10','$110.00')]))
        for complete in (False,True):
            current=self.reviews.prepare(self.case,prepared['evidence_id'])
            record=self.review(current,complete=complete)
            report=self.reviews.draft(self.case,record['id'])
            self.assertEqual({f['category'] for f in self.pricing(report)},
                {'pricing_arithmetic','pricing_quantity_basis'})
            self.assertIsNone(report['meta']['bid_total']);self.assertFalse(report['homeowner_release_approved'])

    def test_unincorporated_attachment_keeps_source_questions_without_adding_to_bid(self):
        primary=self.review(self.prepare(b'Builder proposal\nTotal: $300,000.00','builder.txt'),kind='builder_bid')
        trade=self.review(self.prepare(pdf([('Drywall','$10.00','10','$110.00')])))
        report=prepare_bid_package(self.reviews,self.case,'test-reviewer',{
            'primary_review_id':primary['id'],'attachments':[{'review_id':trade['id'],
                'relationship':'unconfirmed','rationale':'Fixture quote was not incorporated in builder proposal.'}]})
        findings=self.pricing(report)
        self.assertEqual(len(findings),2)
        self.assertTrue(all(f['document_relationship']=='unconfirmed' for f in findings))
        self.assertTrue(all(trade['evidence_id'] in f['evidence_lines'][0]['source_ref'] for f in findings))
        self.assertIsNone(report['meta']['package_total']);self.assertIsNone(report['meta']['bid_total'])
        self.assertFalse(report['package_total_confirmed'])


if __name__=='__main__':unittest.main()
