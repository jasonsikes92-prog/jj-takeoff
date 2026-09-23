"""Compare reviewed bid documents without treating every quote as contracted scope."""
import hashlib
from datetime import date

from answer_store import encode
from jnj_takeoff import ingest_bid, report_from_takeoff, review_bid_scopes
from levelground_scope import CHECKLIST_VERSION
from bid_pricing_findings import PRICING_FINDINGS_METHOD,pricing_findings


def package_sources_current(reviews, case_id, report):
    """A changed attachment invalidates the entire combined review, not just itself."""
    sources = report['source_documents']
    if not isinstance(sources, list) or not sources:
        return False
    for source in sources:
        current = reviews.latest(case_id, source['reference'].removeprefix('evidence:'))
        if (current is None or current['id'] != source['review_id']
                or current['review_sha256'] != source['review_sha256']
                or current['source_sha256'] != source['sha256']
                or current['extraction_sha256'] != source['extraction_sha256']):
            return False
    return report.get('scope_checklist_version') == CHECKLIST_VERSION


def prepare_bid_package(reviews, case_id, reviewer_id, payload):
    primary_id, attachments = payload['primary_review_id'], payload['attachments']
    if not isinstance(primary_id, str) or not primary_id.strip():
        raise ValueError('Select the governing builder bid review')
    if not isinstance(attachments, list) or not 1 <= len(attachments) <= 20:
        raise ValueError('Select one to twenty related document reviews')
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError('Reviewer identity required')
    selections = [{'review_id':primary_id, 'relationship':'primary', 'rationale':'Selected governing builder bid'}]
    for attachment in attachments:
        if (not isinstance(attachment, dict) or not isinstance(attachment.get('review_id'), str)
                or not attachment['review_id'].strip()
                or attachment.get('relationship') not in ('incorporated', 'unconfirmed')
                or not isinstance(attachment.get('rationale'), str) or not attachment['rationale'].strip()):
            raise ValueError('Each attachment needs a review, relationship and source-based rationale')
        selections.append({key:attachment[key].strip() for key in ('review_id','relationship','rationale')})
    if len({s['review_id'] for s in selections}) != len(selections):
        raise ValueError('Do not count a document review twice')
    records = [reviews.read(case_id, s['review_id']) for s in selections]
    if len({r['evidence_id'] for r in records}) != len(records):
        raise ValueError('Select only the current review of each document')
    if records[0]['document_kind'] != 'builder_bid':
        raise ValueError('The primary review must be a builder bid')
    if any(r['document_kind'] == 'builder_bid' for r in records[1:]):
        raise ValueError('Alternative builder bids need separate comparisons')
    sources, lines, comparisons, pricing_questions = [], [], [], []
    home = {key:None for key in ('heated_sf','stories','foundation','garage','finish_level')}
    for selection, record in zip(selections, records):
        if reviews.latest(case_id, record['evidence_id']) != record:
            raise ValueError('Document review changed; select its current version')
        included = selection['relationship'] in ('primary', 'incorporated')
        if included and not record['document_review_complete']:
            raise ValueError('Governing bid and incorporated documents require complete source review')
        evidence = reviews.store.read_evidence(case_id, 'evidence:' + record['evidence_id'])
        source = {**selection, 'reference':'evidence:' + record['evidence_id'], 'filename':evidence['filename'],
            'sha256':record['source_sha256'], 'extraction_sha256':record['extraction_sha256'],
            'review_sha256':record['review_sha256'], 'document_kind':record['document_kind'],
            'reviewed_pages':record['reviewed_pages'], 'document_review_complete':record['document_review_complete'],
            'document_total':record['bid']['total'], 'currency':record['currency']}
        sources.append(source)
        extraction=reviews.processing.read(case_id,record['evidence_id'])['result']
        findings=pricing_findings(extraction.get('pricing_extraction'),source['reference'],source['filename'])
        pricing_questions.extend([{**finding,'document_relationship':selection['relationship']} for finding in findings])
        comparisons.append({'source':source, 'scope_checks':review_bid_scopes(record['bid'], home)})
        if included:
            lines.extend(record['bid']['lines'])
    identity = hashlib.sha256(encode({'sources':sources, 'reviewer':reviewer_id.strip(),
        'checklist':CHECKLIST_VERSION, 'method':'bid_package_v1',
        'pricing_findings_method':PRICING_FINDINGS_METHOD}).encode()).hexdigest()
    report = report_from_takeoff({'lines':[], 'not_measured':[]}, home, {}, bid=ingest_bid(lines),
        property_label='Combined bid review: ' + sources[0]['filename'],
        report_id='LG-PACKAGE-' + identity[:16], date=date.today().isoformat())
    report['meta'].update(bid_total=None, primary_bid_total=records[0]['bid']['total'],
        primary_bid_currency=records[0]['currency'], package_total=None,
        verdict_note='Combined reviewer draft. Only the governing bid and explicitly incorporated attachments establish bid scope. '
        'Conflicting wording remains unresolved; no document automatically overrides another. '
        'The primary bid amount and individual document amounts are references, not a reconciled package total.')
    report['findings']+=pricing_questions
    report['questions']+=[finding['detail'] for finding in pricing_questions]
    report['pricing_findings_method']=PRICING_FINDINGS_METHOD
    # Related, unincorporated quotes can reveal disagreements but cannot close a
    # builder-scope question merely by offering the work themselves.
    differences = []
    for topic in report['scope_checks']:
        evidence_lines, included_docs, excluded_docs = [], set(), set()
        for document in comparisons:
            check = next(c for c in document['scope_checks'] if c['id'] == topic['id'])
            for line in check['evidence_lines']:
                if topic['title'] not in line.get('confirmed_scopes', []):
                    continue
                if line['scope_status'] == 'included':
                    included_docs.add(document['source']['review_id'])
                elif line['scope_status'] == 'excluded':
                    excluded_docs.add(document['source']['review_id'])
                evidence_lines.append(line)
        if any(a != b for a in included_docs for b in excluded_docs):
            detail = 'The reviewed documents differ about ' + topic['title'] + '. Confirm the governing scope, responsibility and any price change in writing.'
            differences.append({'scope_id':topic['id'], 'title':topic['title'], 'evidence_lines':evidence_lines})
            report['findings'].append({'category':'document_scope_difference', 'title':topic['title'] + ': documents differ',
                'detail':detail, 'basis':'A difference between documents is not proof of omitted work or an automatic addendum override.',
                'bid_amount':None, 'realistic_low':None, 'realistic_high':None,
                'confidence':'needs_confirmation', 'evidence_lines':evidence_lines})
            report['questions'].append(detail)
    for source in sources[1:]:
        if source['relationship'] == 'unconfirmed':
            question = 'Is ' + source['filename'] + ' incorporated in the builder bid? Confirm the referenced revision, covered scope and effect on price.'
            report['questions'].append(question)
    report.update(report_status='reviewer_draft', source_documents=sources,
        document_comparison=comparisons, document_scope_differences=differences,
        package_review={'method':'bid_package_v1', 'reviewer_id':reviewer_id.strip(), 'sha256':identity},
        complete_home_bid_review=False, homeowner_release_approved=False, measurements_certified=False,
        permit_compliance_verified=False, estimate_released=False, package_total_confirmed=False)
    report['unknowns'] += ['Only the selected documents were compared. Referenced but unsupplied attachments, plan quantities, current local requirements and pricing adequacy still need review.',
        'The package total is unknown. Do not add quote or addendum totals to the primary bid without reconciling inclusions, credits and revisions.']
    if not package_sources_current(reviews, case_id, report):
        raise ValueError('Package sources changed during report generation')
    return report
