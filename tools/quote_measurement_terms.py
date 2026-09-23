"""Extract explicit measurement-term candidates without assigning them to price lines."""
import hashlib
import json
import re
from decimal import Decimal

TERMS_METHOD='explicit_measurement_terms_v1'
OBJECTS=r'(?:windows?\s+(?:and|or)\s+doors?|window\s+and\s+door\s+openings|openings)'
NO_DEDUCTIONS=re.compile(rf'(?:no opening deductions?|no deductions? (?:for|of) {OBJECTS}|do not deduct {OBJECTS}|'
    rf'{OBJECTS} (?:are )?not deducted|opening deductions?\s*[:=]\s*(?:none|no))',re.I)
DEDUCTIONS=re.compile(rf'(?:deduct {OBJECTS}|{OBJECTS} (?:are )?deducted|'
    r'opening deductions?\s*[:=]\s*yes)',re.I)
PERCENT=r'(?P<percent>\d+(?:\.\d+)?)\s*%'


def extract_terms(pages):
    candidates=[]
    for page in pages:
        for number,text in enumerate(page['text'].splitlines(),1):
            normalized=' '.join(text.split()).rstrip('.').strip()
            lower=normalized.lower()
            deduction_cue='deduct' in lower and any(word in lower for word in ('window','door','opening'))
            waste_cue='waste' in lower and any(word in lower for word in ('%','billing','material','cutting','allowance'))
            if not deduction_cue and not waste_cue:continue
            field=None;value=None
            if NO_DEDUCTIONS.fullmatch(normalized):field='deduct_window_door_openings';value=False
            elif DEDUCTIONS.fullmatch(normalized):field='deduct_window_door_openings';value=True
            else:
                for label,key in [('billing','billing_waste_percent'),('material','material_purchase_waste_percent'),
                                  ('cutting','material_purchase_waste_percent')]:
                    if re.fullmatch(rf'no (?:added )?{label} waste',normalized,re.I):
                        field=key;value='0';break
                    match=re.fullmatch(rf'(?:added )?{label} waste(?: allowance)?\s*[:=]\s*{PERCENT}',normalized,re.I)
                    if match is None:match=re.fullmatch(rf'{PERCENT} (?:added )?{label} waste',normalized,re.I)
                    if match:
                        field=key;value=format(Decimal(match['percent']).normalize(),'f');break
            source={'page':page['page'],'line':number,'source_text':text}
            identity=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()[:20]
            candidates.append({'id':identity,**source,'source_ref':f'page {page["page"]}, line {number}',
                'field':field,'value':value,'reviewed':False,'status':'needs_source_review',
                'scope_ids':[],'pricing_line_ids':[],
                'interpretation':'explicit_wording_candidate' if field is not None else 'wording_requires_interpretation'})
    varying=[]
    for field in sorted({c['field'] for c in candidates if c['field'] is not None}):
        selected=[c for c in candidates if c['field']==field]
        if len({json.dumps(c['value']) for c in selected})>1:
            varying.append({'field':field,'candidate_ids':[c['id'] for c in selected],
                'reason':'Different source values; affected price lines and scope are not assigned'})
    return {'method':TERMS_METHOD,'candidates':candidates,'fields_with_multiple_values':varying,
        'automatic_pricing_assertions':0,'complete_document_review':False,
        'limitations':'Explicit single-line English wording only. Conditions, thresholds, generic waste, wrapped terms and scanned text require source review. No candidates does not prove terms are absent.'}


def term_findings(extraction,reference,filename):
    if not extraction or not extraction['candidates']:return []
    sources=[{'desc':c['source_text'],'amount':None,'source_ref':reference+', '+c['source_ref'],
        'page':c['page'],'line':c['line'],'measurement_term_candidate_id':c['id']}
        for c in extraction['candidates']]
    return [{'category':'pricing_measurement_terms','title':'Confirm measurement adjustments: '+filename,
        'detail':filename+': Confirm the cited opening deductions and waste terms, which price lines they cover, '
            'and whether they affect billing quantities, material purchasing or both. Resolve conditional or differing terms in writing.',
        'evidence_lines':sources,'confidence':'needs_confirmation','scope_status':'unverified',
        'bid_amount':None,'realistic_low':None,'realistic_high':None,
        'basis':'Unreviewed source wording; no approved adjustment, scope inclusion or added cost is established.'}]
