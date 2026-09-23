"""Bind reviewed bid wording to an uploaded source and generate a report draft."""
import hashlib
import json
import math
from datetime import date
from pathlib import Path
import sys
import uuid

from answer_store import encode, now
from bid_clause_candidates import CLAUSE_METHOD, clause_candidates, clause_findings
from bid_pricing_findings import PRICING_FINDINGS_METHOD,pricing_findings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from jnj_takeoff import PRE_BID_SCOPE_CHECKLIST, ingest_bid, report_from_takeoff
from levelground_scope import CHECKLIST_VERSION
from quote_measurement_terms import extract_terms,term_findings


class BidDocumentReviews:
    def __init__(self, store, processing):
        self.store, self.processing = store, processing
        with store.connect() as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS bid_document_reviews (
                id TEXT PRIMARY KEY, evidence_id TEXT NOT NULL REFERENCES evidence_objects(id),
                body TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL)''')

    def latest(self, case_id, evidence_id):
        self.store.read_evidence(case_id, 'evidence:' + evidence_id)
        with self.store.connect() as db:
            row = db.execute('SELECT id FROM bid_document_reviews WHERE evidence_id=? ORDER BY rowid DESC LIMIT 1',
                             (evidence_id,)).fetchone()
        return None if row is None else self.read(case_id, row['id'])

    def prepare(self, case_id, evidence_id):
        """Prepare source-linked review wording without inventing an operator review."""
        prepared = self.processing.read(case_id, evidence_id)
        result = prepared['result']
        if result is None or prepared['status'] not in ('text_extracted', 'needs_visual_review'):
            raise ValueError('Bid preparation needs extracted document text')
        evidence = self.store.read_evidence(case_id, 'evidence:' + evidence_id)
        prior = self.latest(case_id, evidence_id)
        lines = []
        source_line_count = 0
        omitted_pages = set()
        for page in result['pages']:
            for number, text in enumerate(page['text'].splitlines(), 1):
                if not text.strip():
                    continue
                source_line_count += 1
                if len(lines) == 1000:
                    omitted_pages.add(page['page'])
                    continue
                lines.append({'page':page['page'], 'line':number, 'source_text':text,
                    'source_ref':f'evidence:{evidence_id}, page {page["page"]}, line {number}',
                    'suggested_scopes':[c['title'] for c in PRE_BID_SCOPE_CHECKLIST
                                        if any(k in text.lower() for k in c.get('scope_keys', []))],
                    'scope_status':'unclear', 'confirmed_scopes':[]})
        if not lines:
            raise ValueError('No extracted wording; review the original document visually')
        clauses = clause_candidates(lines)
        terms=result.get('measurement_terms') or extract_terms(result['pages'])
        bid = ingest_bid([{'desc':line['source_text'], 'amount':None,
                           'source_ref':line['source_ref']} for line in lines])
        home = {key:None for key in ('heated_sf','stories','foundation','garage','finish_level')}
        identity = hashlib.sha256(encode({'source':prepared['source_sha256'],
            'extraction':prepared['result_sha256'], 'checklist':CHECKLIST_VERSION,
            'method':'source_line_preparation_v2', 'clause_method':CLAUSE_METHOD,
            'pricing_findings_method':PRICING_FINDINGS_METHOD,'measurement_terms_method':terms['method']}).encode()).hexdigest()
        report = report_from_takeoff({'lines':[], 'not_measured':[]}, home, {}, bid=bid,
            property_label='Unreviewed document: ' + evidence['filename'],
            report_id='LG-PREP-' + identity[:16], date=date.today().isoformat())
        report['meta']['verdict_note'] = ('Automatically prepared review questions from extracted text. '
            'Related wording is a search aid, not confirmation that a trade is included or excluded. '
            'Review the complete original document and referenced attachments.')
        source = {'reference':'evidence:' + evidence_id, 'filename':evidence['filename'],
            'sha256':prepared['source_sha256'], 'extraction_sha256':prepared['result_sha256'],
            'document_kind':'unclassified', 'reviewed_pages':[], 'document_review_complete':False}
        report.update(report_status='machine_preparation', source_document=source,
            complete_home_bid_review=False, homeowner_release_approved=False,
            measurements_certified=False, permit_compliance_verified=False, estimate_released=False)
        report['unknowns'] += ['Document type, all scope interpretations, currency and totals need review. No plan quantities or pricing adequacy are established.']
        findings = clause_findings(clauses)+pricing_findings(result.get('pricing_extraction'),
            'evidence:'+evidence_id,evidence['filename'])+term_findings(terms,'evidence:'+evidence_id,evidence['filename'])
        report['findings'] += findings
        report['questions'] += [finding['detail'] for finding in findings]
        report['clause_candidates'] = clauses
        report['clause_detection_method'] = CLAUSE_METHOD
        report['pricing_findings_method'] = PRICING_FINDINGS_METHOD
        report['measurement_terms']=terms
        report['unknowns'].append(terms['limitations'])
        report['unknowns'].append('Clause detection uses explicit English wording and adjacent section headings. It can miss wrapped phrases, tables, unfamiliar wording and context across blank lines or pages; no candidates does not establish a complete or risk-free bid.')
        if omitted_pages:
            report['unknowns'].append('Preparation includes only the first 1,000 nonblank source lines; review omitted wording on pages ' + ', '.join(map(str, sorted(omitted_pages))) + '.')
        missing = result['pages_needing_visual_or_ocr_review']
        if missing:
            report['unknowns'].append('Visual or OCR review is required for pages ' + ', '.join(map(str, missing)) + '.')
        return {'evidence_id':evidence_id, 'source_sha256':prepared['source_sha256'],
            'extraction_sha256':prepared['result_sha256'], 'scope_checklist_version':CHECKLIST_VERSION,
            'method':'source_line_preparation_v2', 'lines':lines,
            'clause_detection_method':CLAUSE_METHOD, 'clause_candidates':clauses,
            'source_line_count':source_line_count, 'omitted_line_count':source_line_count-len(lines),
            'pages_with_omitted_lines':sorted(omitted_pages), 'pages_needing_visual_or_ocr_review':missing,
            'total_candidates':[{'candidate_index':i, **c} for i,c in enumerate(result['field_candidates'])],
            'pricing_extraction':result.get('pricing_extraction'),
            'measurement_terms':terms,
            'review_template':{'evidence_id':evidence_id, 'source_sha256':prepared['source_sha256'],
                'extraction_sha256':prepared['result_sha256'], 'document_kind':None,
                'reviewed_pages':[], 'document_review_complete':False, 'rationale':'',
                'base_review_id':None if prior is None else prior['id'], 'currency':None,
                'total_candidate_index':None,
                'lines':[{k:line[k] for k in ('page','source_text','scope_status','confirmed_scopes')} for line in lines]},
            'report_draft':report, 'automatic_scope_assertions':0, 'report_published':False}

    def save(self, case_id, reviewer_id, payload):
        evidence_id = payload['evidence_id']
        prepared = self.processing.read(case_id, evidence_id)
        result = prepared['result']
        if (result is None or prepared['status'] not in ('text_extracted','needs_visual_review')
                or payload['source_sha256'] != prepared['source_sha256']
                or payload['extraction_sha256'] != prepared['result_sha256']):
            raise ValueError('Review needs the current source and extraction')
        if payload['document_kind'] not in ('builder_bid','trade_quote','scope_addendum'):
            raise ValueError('Unsupported bid document kind')
        if not isinstance(reviewer_id,str) or not reviewer_id.strip():
            raise ValueError('Reviewer identity is required')
        if not isinstance(payload['rationale'],str) or not payload['rationale'].strip():
            raise ValueError('Describe the review basis and limits')
        pages = {p['page']:p['text'] for p in result['pages']}
        reviewed = payload['reviewed_pages']
        if (not isinstance(reviewed,list) or not reviewed or any(type(p) is not int for p in reviewed)
                or len(set(reviewed)) != len(reviewed) or set(reviewed)-set(pages)):
            raise ValueError('Identify unique source pages reviewed')
        complete = payload['document_review_complete']
        if type(complete) is not bool or (complete and (set(reviewed) != set(pages) or prepared['status'] != 'text_extracted')):
            raise ValueError('Complete review requires all pages and resolved extraction')
        lines = payload['lines']
        if not isinstance(lines,list) or not 1 <= len(lines) <= 1000:
            raise ValueError('Provide reviewed source lines')
        titles = {c['title'] for c in PRE_BID_SCOPE_CHECKLIST}
        normalized, source_lines = [], []
        for line in lines:
            page, text = line['page'], line['source_text']
            if (type(page) is not int or page not in reviewed or not isinstance(text,str)
                    or not text.strip() or text not in pages[page]):
                raise ValueError('Reviewed wording must occur on the cited source page')
            status = line.get('scope_status','unclear')
            scopes = line.get('confirmed_scopes',[])
            if (not isinstance(scopes,list) or any(not isinstance(s,str) for s in scopes)
                    or len(set(scopes)) != len(scopes) or set(scopes)-titles):
                raise ValueError('Use existing scope checklist identities')
            if not complete and (scopes or status != 'unclear'):
                raise ValueError('Partial document review cannot establish an inclusion or exclusion')
            lump = line.get('is_lump',False)
            if type(lump) is not bool:
                raise ValueError('Lump-sum classification must be explicit')
            reference = f'evidence:{evidence_id}, page {page}'
            normalized.append({'desc':text, 'amount':None, 'scope_status':status,
                               'source_ref':reference, 'confirmed_scopes':scopes, 'is_lump':lump})
            source_lines.append({'page':page,'source_text':text})
        bid = ingest_bid(normalized)
        candidate_index = payload.get('total_candidate_index')
        bid['total'] = None
        total_source = None
        if candidate_index is not None:
            candidates = result['field_candidates']
            if (not complete or type(candidate_index) is not int or not 0 <= candidate_index < len(candidates)
                    or payload.get('currency') != 'USD'):
                raise ValueError('Total selection requires a complete review and confirmed currency')
            total_source = candidates[candidate_index]
            if total_source['page'] not in reviewed:
                raise ValueError('Total source page was not reviewed')
            bid['total'] = float(total_source['value'])
            if not math.isfinite(bid['total']) or bid['total'] < 0:
                raise ValueError('Invalid document total')
        prior = self.latest(case_id,evidence_id)
        previous_id = None if prior is None else prior['id']
        if payload.get('base_review_id') != previous_id:
            raise ValueError('Document review changed; reload before revising')
        identity = str(uuid.uuid4())
        record = {'id':identity,'evidence_id':evidence_id,'source_sha256':prepared['source_sha256'],
            'extraction_sha256':prepared['result_sha256'],'document_kind':payload['document_kind'],
            'reviewer_id':reviewer_id.strip(),'rationale':payload['rationale'].strip(),
            'reviewed_pages':sorted(reviewed),'document_review_complete':complete,
            'previous_review_id':previous_id,'source_lines':source_lines,'bid':bid,
            'total_source':total_source,'currency':'USD' if total_source else None,'created_at':now()}
        body = encode(record)
        with self.store.connect() as db, db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT id FROM bid_document_reviews WHERE evidence_id=? ORDER BY rowid DESC LIMIT 1',
                                (evidence_id,)).fetchone()
            if (None if latest is None else latest['id']) != previous_id:
                raise ValueError('Document review changed during save')
            db.execute('INSERT INTO bid_document_reviews VALUES (?,?,?,?,?)',
                       (identity,evidence_id,body,hashlib.sha256(body.encode()).hexdigest(),record['created_at']))
        return self.read(case_id,identity)

    def read(self, case_id, identity):
        with self.store.connect() as db:
            row = db.execute('''SELECT r.* FROM bid_document_reviews r JOIN evidence_objects e ON e.id=r.evidence_id
                                WHERE r.id=? AND e.case_id=?''',(identity,case_id)).fetchone()
        if row is None or hashlib.sha256(row['body'].encode()).hexdigest() != row['sha256']:
            raise ValueError('Review unavailable or source record changed')
        record = json.loads(row['body'])
        prepared = self.processing.read(case_id,record['evidence_id'])
        if (record['source_sha256'] != prepared['source_sha256']
                or record['extraction_sha256'] != prepared['result_sha256']):
            raise ValueError('Review belongs to an earlier source or extraction')
        return {**record,'review_sha256':row['sha256']}

    def draft(self, case_id, identity):
        record = self.read(case_id,identity)
        if self.latest(case_id,record['evidence_id'])['id'] != identity:
            raise ValueError('A newer document review exists')
        evidence = self.store.read_evidence(case_id,'evidence:' + record['evidence_id'])
        home = {key:None for key in ('heated_sf','stories','foundation','garage','finish_level')}
        report = report_from_takeoff({'lines':[],'not_measured':[]},home,{},bid=record['bid'],
            property_label='Bid document review: ' + evidence['filename'],
            report_id='LG-BID-DRAFT-' + record['review_sha256'][:16], date=date.today().isoformat())
        report['meta']['verdict_note'] = ('Reviewer draft of the selected ' + record['document_kind'].replace('_',' ') +
            '. Scope statements are tied to reviewed source wording. This is not a complete comparison against plans, attachments or local requirements.')
        report['meta']['document_total'] = record['bid']['total']
        report['meta']['document_currency'] = record['currency']
        if record['document_kind'] != 'builder_bid':
            report['meta']['bid_total'] = None
        report.update(report_status='reviewer_draft',source_document={
            'reference':'evidence:' + record['evidence_id'],'filename':evidence['filename'],
            'sha256':record['source_sha256'],'extraction_sha256':record['extraction_sha256'],
            'review_id':identity,'review_sha256':record['review_sha256'],'document_kind':record['document_kind'],
            'reviewed_pages':record['reviewed_pages'],'document_review_complete':record['document_review_complete']},
            complete_home_bid_review=False,homeowner_release_approved=False,
            measurements_certified=False,permit_compliance_verified=False,estimate_released=False)
        report['unknowns'] += ['Plan quantities, complete trade scope, referenced attachments, current local requirements and pricing adequacy have not been established by this document review.']
        if not record['document_review_complete']:
            report['unknowns'].append('This document review is partial; no sourced inclusion or exclusion has been approved.')
        extraction=self.processing.read(case_id,record['evidence_id'])['result']
        terms=extraction.get('measurement_terms') or extract_terms(extraction['pages'])
        findings=pricing_findings(extraction.get('pricing_extraction'),'evidence:'+record['evidence_id'],evidence['filename'])+term_findings(terms,'evidence:'+record['evidence_id'],evidence['filename'])
        report['findings']+=findings
        report['questions']+=[finding['detail'] for finding in findings]
        report['pricing_findings_method']=PRICING_FINDINGS_METHOD
        report['measurement_terms']=terms
        report['unknowns'].append(terms['limitations'])
        if self.latest(case_id,record['evidence_id']) != record:
            raise ValueError('Document review changed during report generation')
        return report
