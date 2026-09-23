"""Connect a reviewed case document to its current plan-derived trade scope."""
import copy
import hashlib
import tempfile
from datetime import date
from pathlib import Path
from answer_store import encode
from quote_report import report_from_quote


def sources_current(reviews, workspaces, case_id, report):
    binding=report['trade_quote_review'];request=binding['request']
    try:
        record=reviews.read(case_id,request['document_review_id'])
        if (record['review_sha256']!=binding['document_review_sha256'] or
                reviews.latest(case_id,record['evidence_id'])['id']!=record['id']):
            return False
        drafts=workspaces.trade_bid_drafts(case_id,request['workspace_id'])
        return any(d['scope']['scope_sha256']==request['scope_sha256'] for d in drafts['drafts'])
    except (ValueError,KeyError,TypeError,OSError):
        return False


def current_report_view(reviews, workspaces, case_id, report):
    if 'trade_quote_review' not in report:return report
    result=copy.deepcopy(report)
    current=sources_current(reviews,workspaces,case_id,result)
    result['trade_quote_sources_current']=current
    if not current:
        notice='The plan scope or reviewed quote has changed, or its source could not be verified. This saved comparison needs reviewer renewal before use; earlier answers do not confirm the revised work.'
        result['findings'].insert(0,{'category':'source_revision','title':'Trade quote review needs renewal',
            'detail':notice,'confidence':'needs_confirmation','basis':'Current case source verification',
            'bid_amount':None,'realistic_low':None,'realistic_high':None})
        result['unknowns'].append(notice)
        result['homeowner_release_approved']=False
    return result


def prepare_trade_quote(reviews, workspaces, case_id, reviewer_id, payload):
    record=reviews.read(case_id,payload['document_review_id'])
    if (record['document_kind']!='trade_quote' or not record['document_review_complete']
            or reviews.latest(case_id,record['evidence_id'])['id']!=record['id']):
        raise ValueError('Use the latest complete trade-document review')
    if not isinstance(reviewer_id,str) or not reviewer_id.strip():
        raise ValueError('Reviewer identity required')
    if not isinstance(payload.get('rationale'),str) or not payload['rationale'].strip():
        raise ValueError('Describe the source basis for the pricing transcription')
    drafts=workspaces.trade_bid_drafts(case_id,payload['workspace_id'])
    matches=[d['scope'] for d in drafts['drafts'] if d['scope']['scope_sha256']==payload['scope_sha256']]
    if len(matches)!=1:raise ValueError('Select one current case trade scope; changed measurements require review')
    scope=matches[0]
    supplied=payload['quote']
    allowed={'supplier','date','valid_through','evidence_kind','pricing_lines','scope_items'}
    if not isinstance(supplied,dict) or set(supplied)-allowed:
        raise ValueError('Only source-transcribed quote fields are accepted')
    references={f"evidence:{record['evidence_id']}, page {page}" for page in record['reviewed_pages']}
    for item in supplied.get('scope_items',[])+supplied.get('pricing_lines',[]):
        if item.get('source_ref') not in references:
            raise ValueError('Every quote scope and price line must cite a reviewed document page')
        for name in ('quantity_basis_source_ref',):
            if item.get(name) is not None and item[name] not in references:
                raise ValueError('Pricing quantity basis must cite a reviewed document page')
        adjustments=item.get('measurement_adjustments')
        if adjustments is not None and adjustments.get('source_ref') not in references:
            raise ValueError('Measurement adjustments must cite a reviewed document page')
    evidence=reviews.store.read_evidence(case_id,'evidence:'+record['evidence_id'])
    if hashlib.sha256(evidence['body']).hexdigest()!=record['source_sha256']:
        raise ValueError('Trade document bytes changed')
    request=copy.deepcopy(payload)
    identity=hashlib.sha256(encode({'request':request,'review_sha256':record['review_sha256'],
        'reviewer':reviewer_id,'method':'case_trade_quote_v1'}).encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='lg-trade-review-') as temp:
        root=Path(temp);(root/'quote-source').write_bytes(evidence['body'])
        quote={**supplied,'id':record['id'],'source_file':'quote-source','source_sha256':record['source_sha256'],
            'total':record['bid']['total'],'currency':record['currency'],'reviewed':True,
            'reviewed_scope_sha256':scope['scope_sha256']}
        report=report_from_quote(scope,[quote],quote['id'],date.today().isoformat(),root,
            {'report_id':'LG-TRADE-'+identity[:16],'property_label':'Trade quote: '+evidence['filename']})
    # The temporary filename is never an evidence link in the retained case report.
    for finding in report['findings']:
        finding['source']['file']=evidence['filename']
        finding['source']['reference']='evidence:'+record['evidence_id']
    report['quote_comparison']['source_file']=evidence['filename']
    report.update(report_status='reviewer_draft',homeowner_release_approved=False,
        trade_quote_review={'request':request,'reviewer_id':reviewer_id,'document_review_sha256':record['review_sha256'],
            'source_reference':'evidence:'+record['evidence_id'],'method':'case_trade_quote_v1'})
    if (reviews.latest(case_id,record['evidence_id'])['id']!=record['id']
            or workspaces.trade_bid_drafts(case_id,payload['workspace_id'])!=drafts):
        raise ValueError('Document or workspace changed during quote review; retry')
    return report
