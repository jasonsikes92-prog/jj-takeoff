import hashlib
import json
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from document_processing import DocumentProcessing
from quote_intake import extract_document_pages


class DocumentProcessingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cases.sqlite3'
        self.store = AnswerStore(self.path)
        self.case = self.store.create_case('Synthetic document case')
        self.processor = DocumentProcessing(self.store)

    def upload(self, name, body):
        return self.store.attach_evidence(self.case, name, body)['reference'].split(':')[1]

    def test_recovered_upload_extracts_conflicting_totals_with_page_and_line(self):
        raw = b'\xef\xbb\xbfSubtotal: $900.00\nTotal: $1,000.00\nGrand total: $1,100.00\n'
        identity = self.upload('bid.txt', raw)
        reopened = DocumentProcessing(AnswerStore(self.path))
        self.assertTrue(reopened.process_next())
        result = reopened.read(self.case, identity)
        self.assertEqual(result['status'], 'text_extracted')
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        candidates = result['result']['field_candidates']
        self.assertEqual([c['value'] for c in candidates], ['1000.00', '1100.00'])
        self.assertEqual([c['line'] for c in candidates], [2, 3])
        self.assertTrue(all(not c['reviewed'] for c in candidates))
        self.assertFalse(result['result']['complete_document_review'])
        self.assertFalse(result['result']['report_published'])
        self.assertEqual(self.store.read_case(self.case)['reports'], [])
        self.assertFalse(reopened.process_next())
        self.assertEqual(reopened.read(self.case, identity)['attempts'], 1)

    def test_pdf_blank_page_requires_visual_review(self):
        with fitz.open() as doc:
            doc.new_page().insert_text((30, 40), 'Total: $1,200.00')
            doc.new_page()
            raw = doc.tobytes()
        identity = self.upload('proposal.PDF', raw)
        self.processor.process_next()
        result = self.processor.read(self.case, identity)
        self.assertEqual(result['status'], 'needs_visual_review')
        self.assertEqual(result['result']['pages_needing_visual_or_ocr_review'], [2])
        self.assertEqual(result['result']['field_candidates'][0]['page'], 1)
        self.assertEqual(self.store.read_evidence(self.case, 'evidence:' + identity)['body'], raw)
        with self.assertRaisesRegex(ValueError, 'page limit'):
            extract_document_pages(raw, '.pdf', max_pages=1)

    def test_failed_or_unsupported_upload_does_not_block_later_work(self):
        for filename, raw in [('broken.pdf', b'not PDF'), ('photo.png', b'image'), ('invalid.txt', b'\xff')]:
            identity = self.upload(filename, raw)
            self.assertTrue(self.processor.process_next())
            record = self.processor.read(self.case, identity)
            self.assertEqual(record['status'], 'needs_manual_review')
            self.assertIsNone(record['result'])
        identity = self.upload('good.txt', b'Scope supplied by homeowner')
        self.assertTrue(self.processor.process_next())
        self.assertEqual(self.processor.read(self.case, identity)['status'], 'text_extracted')

    def test_other_case_and_altered_results_are_refused(self):
        identity = self.upload('source.txt', b'Original source')
        self.processor.process_next()
        other = self.store.create_case('Other case')
        with self.assertRaises(ValueError):
            self.processor.read(other, identity)
        with self.store.connect() as db, db:
            db.execute('UPDATE document_processing SET result=?', ('{}',))
        with self.assertRaisesRegex(ValueError, 'extraction changed'):
            self.processor.read(self.case, identity)

    def test_changed_source_cannot_be_processed_or_read_as_verified(self):
        identity = self.upload('source.txt', b'Original')
        self.processor.discover()
        with self.store.connect() as db, db:
            db.execute('UPDATE evidence_objects SET body=?', (b'Changed',))
        self.processor.process_next()
        with self.store.connect() as db:
            row = db.execute('SELECT status,result FROM document_processing').fetchone()
        self.assertEqual(row['status'], 'needs_manual_review')
        self.assertIsNone(row['result'])
        with self.assertRaisesRegex(ValueError, 'content changed'):
            self.processor.read(self.case, identity)

    def test_expired_worker_claim_can_resume_without_duplicate_results(self):
        identity = self.upload('bid.txt', b'Total: $12.00')
        self.processor.discover()
        with self.store.connect() as db, db:
            db.execute("UPDATE document_processing SET status='processing',attempts=1,lease_token='lost-worker',lease_until=?", (time.time() + 60,))
        self.assertFalse(self.processor.process_next())
        with self.store.connect() as db, db:
            db.execute('UPDATE document_processing SET lease_until=0')
        self.assertTrue(DocumentProcessing(AnswerStore(self.path)).process_next())
        self.assertEqual(self.processor.read(self.case, identity)['attempts'], 2)
        self.assertFalse(self.processor.process_next())

    def test_two_workers_claim_a_document_only_once(self):
        identity = self.upload('bid.txt', b'Total: $99.00')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.processor.process_next(), range(2)))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.processor.read(self.case, identity)['attempts'], 1)

    def test_text_limit_is_enforced_without_truncating_a_successful_result(self):
        with self.assertRaisesRegex(ValueError, 'text limit'):
            extract_document_pages(b'Long text', '.txt', max_text_characters=3)


if __name__ == '__main__':
    unittest.main()
