"""Durable local upload preparation; no automatic bid coverage or price approval."""
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from quote_intake import extract_document_pages, total_candidates
from quote_table_candidates import extract_tables
from quote_measurement_terms import extract_terms
from answer_store import encode


class DocumentProcessing:
    def __init__(self, store):
        self.store = store
        with store.connect() as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS document_processing (
                evidence_id TEXT PRIMARY KEY REFERENCES evidence_objects(id),
                source_sha256 TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                lease_token TEXT, lease_until REAL, result TEXT, result_sha256 TEXT,
                error TEXT, updated_at REAL NOT NULL)''')

    def discover(self):
        """Recover uploads even if the server stopped immediately after saving bytes."""
        with self.store.connect() as db, db:
            db.execute('''INSERT OR IGNORE INTO document_processing
                (evidence_id,source_sha256,status,updated_at)
                SELECT id,sha256,'queued',? FROM evidence_objects''', (time.time(),))

    def process_next(self):
        self.discover()
        lease = str(uuid.uuid4())
        with self.store.connect() as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('''SELECT p.*,e.case_id FROM document_processing p
                JOIN evidence_objects e ON e.id=p.evidence_id
                WHERE p.status='queued' OR (p.status='processing' AND p.lease_until<?)
                ORDER BY p.updated_at,p.evidence_id LIMIT 1''', (time.time(),)).fetchone()
            if row is None:
                return False
            job = dict(row)
            db.execute('''UPDATE document_processing SET status='processing',attempts=attempts+1,
                lease_token=?,lease_until=?,updated_at=? WHERE evidence_id=?''',
                (lease, time.time() + 300, time.time(), job['evidence_id']))
        result = None
        error = None
        try:
            evidence = self.store.read_evidence(job['case_id'], 'evidence:' + job['evidence_id'])
            if evidence['sha256'] != job['source_sha256']:
                raise ValueError('Source changed after upload was queued')
            pages = extract_document_pages(evidence['body'], Path(evidence['filename']).suffix)
            missing = [page['page'] for page in pages if not page['text'].strip()]
            result = {
                'source_sha256': evidence['sha256'], 'pages': pages,
                'pages_needing_visual_or_ocr_review': missing,
                'field_candidates': total_candidates(pages),
                'pricing_extraction': extract_tables(pages),
                'measurement_terms': extract_terms(pages),
                'method': 'native_document_text_pricing_and_terms_v3',
                'extractor_sha256': hashlib.sha256(Path(sys.modules[extract_document_pages.__module__].__file__).read_bytes()).hexdigest(),
                'pricing_extractor_sha256': hashlib.sha256(Path(sys.modules[extract_tables.__module__].__file__).read_bytes()).hexdigest(),
                'measurement_terms_extractor_sha256': hashlib.sha256(Path(sys.modules[extract_terms.__module__].__file__).read_bytes()).hexdigest(),
                'document_kind': 'unclassified', 'complete_document_review': False,
                'automatic_scope_assertions': 0, 'report_published': False,
            }
            status = 'needs_visual_review' if missing else 'text_extracted'
        except (ValueError, RuntimeError, UnicodeError):
            status = 'needs_manual_review'
            # Keep parser messages out of customer output; original bytes are retained.
            error = 'Source integrity or automatic extraction could not be verified. Review the original document.'
        body = None if result is None else encode(result)
        with self.store.connect() as db, db:
            db.execute('''UPDATE document_processing SET status=?,result=?,result_sha256=?,error=?,
                lease_token=NULL,lease_until=NULL,updated_at=? WHERE evidence_id=? AND lease_token=?''',
                (status, body, None if body is None else hashlib.sha256(body.encode()).hexdigest(),
                 error, time.time(), job['evidence_id'], lease))
        return True

    def read(self, case_id, evidence_id):
        with self.store.connect() as db:
            row = db.execute('''SELECT p.* FROM document_processing p
                JOIN evidence_objects e ON e.id=p.evidence_id WHERE e.case_id=? AND p.evidence_id=?''',
                (case_id, evidence_id)).fetchone()
        if row is None:
            raise ValueError('Document processing record not found')
        record = dict(row)
        evidence = self.store.read_evidence(case_id, 'evidence:' + evidence_id)
        if evidence['sha256'] != record['source_sha256']:
            raise ValueError('Processed source changed')
        body = record.pop('result')
        if body is not None and hashlib.sha256(body.encode()).hexdigest() != record['result_sha256']:
            raise ValueError('Document extraction changed')
        record['result'] = None if body is None else json.loads(body)
        record.pop('lease_token')
        record.pop('lease_until')
        return record
