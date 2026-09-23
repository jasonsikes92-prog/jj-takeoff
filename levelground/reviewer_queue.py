"""Read the current case's outstanding work without approving or publishing it."""
import hashlib
from collections import Counter

from answer_store import encode
from bid_document_reviews import BidDocumentReviews
from bid_package_review import package_sources_current
from levelground_scope import CHECKLIST_VERSION
from case_trade_quote import sources_current


def case_review_queue(store, processing, workspaces, case_id):
    case = store.read_case(case_id)
    bid_reviews = BidDocumentReviews(store, processing)
    items = []
    # Previous report versions remain available in history, but their unanswered
    # questions must not create duplicate work beside the current stage version.
    current = {report['stage']:report for report in case['reports']}
    for report in current.values():
        source=report['source_report']
        if 'trade_quote_review' in source and not sources_current(bid_reviews,workspaces,case_id,source):
            items.append({'id':'trade-quote:'+report['id'],'kind':'trade_quote_revision_review','owner':'reviewer',
                'report_id':report['id'],'action':'Reconcile the trade quote with the current plan and document review, then regenerate the report.'})
    for stage in ('pre_bid', 'bid_gap'):
        report = current.get(stage)
        if report is None:
            items.append({'id':'stage:' + stage, 'kind':'report_not_prepared', 'owner':'reviewer',
                          'stage':stage, 'action':'Determine whether the documents needed for this stage are available and prepare the review.'})
            continue
        for question in report['questions']:
            if question['resolved']:
                continue
            answer = question['answers'][-1] if question['answers'] else None
            needs_review = question['status'] == 'answer_received_needs_review'
            items.append({'id':'question:' + question['id'],
                'kind':'answer_needs_review' if needs_review else 'homeowner_response_needed',
                'owner':'reviewer' if needs_review else 'homeowner', 'stage':stage,
                'report_id':report['id'], 'source_report_sha256':report['source_sha256'],
                'question_id':question['id'], 'question':question['text'], 'status':question['status'],
                'answer_id':None if answer is None else answer['id'],
                'answer_revision':None if answer is None else answer['revision'],
                'action':'Review the latest answer and its evidence.' if needs_review else 'Obtain the missing answer or clarification.'})
    with store.connect() as db:
        documents = [dict(row) for row in db.execute(
            '''SELECT e.id,e.filename,e.sha256,p.status FROM evidence_objects e
               LEFT JOIN document_processing p ON e.id=p.evidence_id
               WHERE e.case_id=? ORDER BY e.created_at,e.id''', (case_id,))]
    for document in documents:
        identity = document['id']
        item = {'id':'document:' + identity, 'evidence_id':identity,
                'source_reference':'evidence:' + identity, 'filename':document['filename'],
                'source_sha256':document['sha256'], 'owner':'reviewer'}
        try:
            store.read_evidence(case_id, item['source_reference'])
            prepared = processing.read(case_id, identity) if document['status'] else None
            status = prepared['status'] if prepared else 'queued'
        except ValueError:
            items.append({**item, 'kind':'source_verification_failed',
                          'action':'Inspect the original upload and extraction; source integrity could not be verified.'})
            continue
        item['processing_status'] = status
        if status in ('text_extracted', 'needs_visual_review'):
            item['bid_preparation_url'] = '/api/document-processing/' + identity + '/bid-preparation'
        if status in ('queued', 'processing'):
            items.append({**item, 'kind':'document_preparation_pending', 'owner':'worker',
                          'action':'Wait for automatic preparation or inspect the worker if it fails to advance.'})
            continue
        if status in ('needs_visual_review', 'needs_manual_review'):
            items.append({**item, 'kind':'document_manual_review',
                'pages_needing_visual_or_ocr_review':(prepared['result'] or {}).get('pages_needing_visual_or_ocr_review', []),
                'action':'Review the original document; automatic extraction is incomplete or unavailable.'})
            continue
        folder = workspaces.root / case_id / document['sha256']
        if not folder.exists():
            try:
                reviewed_bid = bid_reviews.latest(case_id, identity)
            except ValueError:
                items.append({**item, 'kind':'bid_review_verification_failed',
                              'action':'Recheck the saved document review against its source and extraction.'})
                continue
            if reviewed_bid is not None:
                linked = any(r['source_report'].get('source_document',{}).get('review_sha256') == reviewed_bid['review_sha256']
                             and r['source_report'].get('scope_checklist_version') == CHECKLIST_VERSION
                             for r in current.values())
                for report in current.values():
                    source = report['source_report']
                    if 'package_review' not in source:
                        continue
                    try:
                        if package_sources_current(bid_reviews, case_id, source):
                            linked = linked or any(s['review_sha256'] == reviewed_bid['review_sha256']
                                and s['relationship'] in ('primary','incorporated') for s in source['source_documents'])
                    except (ValueError, KeyError, TypeError):
                        pass  # A stale or altered package cannot clear its document work.
                if reviewed_bid['document_review_complete'] and linked:
                    continue
                items.append({**item, 'review_id':reviewed_bid['id'],
                    'kind':'bid_report_review' if reviewed_bid['document_review_complete'] else 'bid_document_review_incomplete',
                    'action':'Review the current generated bid draft and prepare the case report.' if reviewed_bid['document_review_complete'] else 'Complete the document review before confirming scope.'})
                continue
            items.append({**item, 'kind':'document_scope_review',
                          'action':'Classify this upload and review its scope. Extracted text is not a completed bid or plan review.'})
            continue
        try:
            workspace = workspaces.read(case_id, document['sha256'])
        except (ValueError, OSError, KeyError):
            items.append({**item, 'kind':'workspace_verification_failed',
                          'action':'Inspect the saved intake and its source or sheet review before using measurements.'})
            continue
        item['workspace_id'] = workspace['workspace_id']
        review = workspace['sheet_review']
        if not review or not review['coverage_passed']:
            items.append({**item, 'id':item['id'] + ':sheets', 'kind':'sheet_coverage_review',
                'missing_roles':[] if not review else review['missing_roles'],
                'unresolved_issues':[] if not review else review['unresolved_issues'],
                'action':'Review every supplied sheet and resolve missing drawings or revision conflicts.'})
        if workspace['measurement_status'] == 'preparation_incomplete':
            kind, action = 'measurement_preparation_incomplete', 'Inspect any running preparation and retained partial output before retrying or creating a new revision.'
        elif workspace['measurement_status'] == 'source_or_review_changed':
            kind, action = 'measurement_revision_review', 'Regenerate and review measurements against the current source and sheet review.'
        elif workspace['measurement_status'] == 'candidates_require_review':
            kind, action = 'measurement_scope_review', 'Review candidate boundaries, unmapped trades and remaining takeoff scope; candidates do not certify a complete estimate.'
        elif workspace.get('failed_preparation_attempts'):
            kind, action = 'measurement_preparation_retry', 'Previous preparation failed; its evidence is retained separately. Retry using the current reviewed sheet scope.'
        else:
            kind, action = 'measurement_not_prepared', 'Complete the sheet review, then generate measurements for the supported scope.'
        measurement_item={**item, 'id':item['id'] + ':measurements', 'kind':kind, 'action':action}
        if workspace['measurement_status']=='not_measured' and (workspace.get('sheet_review') or {}).get('measurement_allowed'):
            measurement_item['measurement_request']={'method':'POST',
                'url':'/api/plan-workspaces/'+workspace['workspace_id']+'/measure',
                'body':{'sheet_review_sha256':workspace['sheet_review']['review_sha256']}}
        if workspace['measurement_status']=='candidates_require_review':
            measurement_item['trade_bid_drafts_request']={'method':'GET',
                'url':'/api/plan-workspaces/'+workspace['workspace_id']+'/trade-bid-drafts'}
        items.append(measurement_item)
    counts = Counter(item['owner'] for item in items)
    return {'case_id':case_id, 'current_report_ids':{stage:r['id'] for stage,r in current.items()},
            'items':items, 'counts':{owner:counts[owner] for owner in ('reviewer','homeowner','worker')},
            'snapshot_sha256':hashlib.sha256(encode(items).encode()).hexdigest(),
            'historical_reports_omitted':len(case['reports']) - len(current),
            'complete_home_review':False, 'estimate_released':False,
            'notice':'This queue tracks pending work only. An empty queue does not certify completeness, prices, permits or readiness to build.'}
