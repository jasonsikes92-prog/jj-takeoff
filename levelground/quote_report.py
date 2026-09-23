"""Turn source-checked trade quote comparisons into homeowner questions."""
import copy
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from bid_comparison import compare_quotes,scope_digest


def report_from_quote(scope, quotes, quote_id, as_of, evidence_root, metadata):
    comparison=compare_quotes(scope,quotes,as_of,evidence_root)
    matches=[q for q in quotes if q['id']==quote_id]
    if len(matches)!=1:raise ValueError('Select one existing quote')
    quote=matches[0]
    result=next(q for q in comparison['quotes'] if q['id']==quote_id)
    reviewed=quote.get('reviewed') is True and quote.get('reviewed_scope_sha256')==scope_digest(scope)
    findings=[];questions=[]
    for item in result['scope_matrix']:
        status=item['status'];label=item['label']
        if status=='included' and reviewed:continue
        category='scope_confirmation';confidence='needs_confirmation'
        if not reviewed and status!='unknown':
            detail=f'The extracted quote marks {label} as {status}, but that interpretation has not been reviewed against the current scope.'
            question=f'Please confirm in writing whether {label} is included, excluded or an allowance in this quote.'
        elif status=='excluded':
            category='excluded_scope';confidence='fact'
            detail=f'The reviewed quote excludes {label}. Responsibility and any separate cost remain to be established.'
            question=f'Who will supply and pay for {label}, which this quote excludes?'
        elif status=='allowance':
            detail=f'The quote treats {label} as an allowance. Its adequacy has not been established.'
            question=f'For {label}, confirm the allowance amount, covered quantity and specification, labor/tax/delivery inclusions, and how differences are charged.'
        else:
            detail=f'Coverage of {label} has not been established from the reviewed information. This does not prove it is omitted.'
            question=f'Please confirm in writing whether {label} is included and identify the quote section that covers it.'
        findings.append({'category':category,'title':label,'detail':detail,
            'confidence':confidence,'basis':f"Quote {quote_id}; {item['source_ref'] or 'source location not established'}"+(f". Review note: {item['note']}" if item['note'] else ''),
            'bid_amount':None,'realistic_low':None,'realistic_high':None,
            'source':{'quote_id':quote_id,'file':result['source_file'],'sha256':result['source_sha256'],
                      'reference':item['source_ref'],'scope_id':item['scope_id']}})
        questions.append(question)
    pricing_issues=(result.get('pricing_review') or {}).get('issues',[])
    if pricing_issues:
        findings.append({'category':'pricing_confirmation','title':'Quote pricing needs clarification',
            'detail':' '.join(pricing_issues),'confidence':'needs_confirmation',
            'basis':'Source-linked pricing transcription; clarify these checks against the written quote.',
            'bid_amount':None,'realistic_low':None,'realistic_high':None,
            'source':{'quote_id':quote_id,'file':result['source_file'],'sha256':result['source_sha256']}})
        questions.append('Please reconcile the pricing discrepancies and confirm the billing units, quantity basis, opening deductions, billing waste, line amounts, and whether component charges are included in the package total.')
        if scope.get('required_work')=='complete':
            questions.append('Please identify the written quote items covering material supply and installation labor for every requested surface. If either is outside this price, identify who provides it and its separate cost; do not add a second charge for work already included.')
    meta=copy.deepcopy(metadata)
    meta.update(report_type='bid_gap',date=as_of,bid_total=None,our_range=None,
        verdict_note='This is a review of one trade quote, not a complete home bid. Missing scope costs and the whole-home price have not been established.',
        quote_id=quote_id,trade_quote_total=result['quoted_total'],trade_quote_currency=result['currency'])
    return {'meta':meta,'findings':findings,'questions':questions,'quantities':[],
        'unknowns':list(result['comparison_issues']),
        'source_plan_sha256':scope['plan_sha256'],'measurement_version':scope['measurement_version'],
        'scope_sha256':comparison['scope_sha256'],'quote_comparison':result,
        'complete_home_bid_review':False,'estimate_released':False,'permit_compliance_verified':False}
