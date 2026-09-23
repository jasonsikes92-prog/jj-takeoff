"""Locate bid wording for review, without deciding contract scope or dollar exposure."""
import hashlib
import json
import re

CLAUSE_METHOD = 'source_clause_candidates_v3'

_RULES = {
    'allowance': (r'\ballowances?\b|\bprovisional sums?\b',
        'Review allowance wording',
        'For the cited allowances, confirm quantities, product levels, labor, tax, delivery, overage markups and unused-balance credits.'),
    'exclusion': (r'\bnot included\b|\bexclud(?:ed|es|ing)\b|\bby others\b',
        'Review exclusion wording',
        'Confirm exactly what the cited exclusions cover, who will provide that work and whether another incorporated document includes it.'),
    'owner_supply': (r'\b(?:owner|homeowner|customer|client)[ -](?:supplied|provided|furnished)\b|\b(?:owner|homeowner|customer|client)\s+(?:(?:to|shall|will|must)\s+)?(?:supply|provide|purchase)\b|\b(?:owner|homeowner|customer|client)\s+(?:is\s+)?responsible for\b',
        'Review owner-supplied scope',
        'For the cited owner responsibilities, confirm purchasing, delivery, storage, installation, hookups, warranty and damage responsibility.'),
    'extra_charge': (r'\b(?:additional|extra) (?:cost|charge|fee)s?\b|\b(?:billed|charged|priced) separately\b|\btime (?:and|&) materials\b|\bT&M\b',
        'Review additional-charge wording',
        'What triggers each cited extra charge, how is it measured and priced, and what written authorization is required before work proceeds?'),
    'price_change': (r'\b(?:price|prices|pricing|cost|costs)\s+(?:(?:is|are)\s+)?subject to change\b|\b(?:price|material|materials|cost|labor) escalation\b|\bescalation clause\b|\btariffs?\b[^.;\n]{0,100}\b(?:passed (?:on|through)|charged|added)\b',
        'Review price-change wording',
        'For the cited price-change terms, confirm the trigger, timing, supporting evidence, limits and approval process before committing to the bid.'),
    'quote_validity': (r'\b(?:quotes?|quotations?|proposals?|bids?|prices?|pricing)\s+(?:(?:is|are|will be|remain|remains)\s+)?(?:valid|honored|held|guaranteed)\s+(?:for|until|through)\b|\b(?:quotes?|quotations?|proposals?|bids?|prices?|pricing)\s+expires?\b',
        'Review quote validity',
        'Check the cited price-validity period and whether the supplier still honors the quoted amount. A passed date alone does not establish a refusal or price increase. Record any confirmed price changes and exceptions.'),
    'attachment': (r'\b(?:see|per|subject to|as (?:shown|defined|specified) in)\s+(?:the\s+)?(?:attached\s+)?(?:attachments?|addenda|addendum|exhibits?|specifications?|scope schedule)\b',
        'Review referenced documents',
        'Obtain each cited document, identify its revision and confirm whether it is incorporated into the bid before resolving scope or price.'),
}
_PATTERNS = {key: re.compile(value[0], re.I) for key, value in _RULES.items()}
_HEADINGS = {'exclusions': 'exclusion', 'excluded work': 'exclusion', 'not included': 'exclusion',
             'allowances': 'allowance', 'provisional sums': 'allowance',
             'owner supplied': 'owner_supply', 'owner supplied items': 'owner_supply',
             'owner responsibilities': 'owner_supply'}
_RESET_HEADINGS = {'included', 'inclusions', 'included work', 'scope', 'scope of work',
                   'pricing', 'price', 'total', 'payment', 'payment terms', 'terms',
                   'schedule', 'warranty', 'signatures', 'acceptance'}


def clause_candidates(lines):
    """Return lexical/context candidates, retaining original page/line evidence.

    Heading context stops at page boundaries, blank-line gaps, known neutral
    headings or another colon-ended heading. It never establishes an exclusion.
    """
    candidates = []
    context = None
    previous = None
    for line in lines:
        text = line['source_text']
        if previous and (line['page'] != previous['page'] or line['line'] > previous['line'] + 1):
            context = None
        previous = line
        heading = re.sub(r'^\s*(?:\d+[.)]|[-*])\s*', '', text).strip().rstrip(':').lower().replace('-', ' ')
        if heading in _HEADINGS:
            context = (_HEADINGS[heading], line)
            continue
        if (heading in _RESET_HEADINGS or text.rstrip().endswith(':')
                or heading.rstrip('.') in ('none', 'n/a', 'not applicable', 'no exclusions', 'no allowances')):
            context = None
            continue
        for kind, pattern in _PATTERNS.items():
            matches = []
            for match in pattern.finditer(text):
                # These common negations should not be presented as positive risk cues.
                prefix = text[:match.start()]
                if re.search(r'\b(?:no|not|without)\s+$', prefix, re.I):
                    continue
                matches.append({'text':match.group(), 'start':match.start(), 'end':match.end()})
            heading_line = context[1] if context and context[0] == kind and re.search(r'[A-Za-z]', text) else None
            if not matches and heading_line is None:
                continue
            sources = ([heading_line] if heading_line else []) + [line]
            identity = json.dumps({'kind':kind, 'sources':[(s['source_ref'],s['source_text']) for s in sources]}, sort_keys=True)
            candidates.append({
                'id':hashlib.sha256(identity.encode()).hexdigest()[:20], 'kind':kind,
                'title':_RULES[kind][1], 'question':_RULES[kind][2],
                'status':'needs_source_review', 'page':line['page'], 'line':line['line'],
                'source_text':text, 'source_ref':line['source_ref'], 'matched_wording':matches,
                'section_context':None if heading_line is None else {
                    k:heading_line[k] for k in ('page','line','source_text','source_ref')},
                'money_text':[m.group() for m in re.finditer(r'\$\s*\d+(?:,\d+)*(?:\.\d+)?',text)],
                'evidence_lines':[{'desc':s['source_text'],'amount':None,'source_ref':s['source_ref']} for s in sources],
                'scope_status':'unclear', 'dollar_exposure':None,
            })
    return candidates


def clause_findings(candidates):
    """Group related candidates into a bounded set of sourced report questions."""
    findings = []
    for kind, (_, title, question) in _RULES.items():
        related = [c for c in candidates if c['kind'] == kind]
        if not related:
            continue
        lines = {line['source_ref']:line for c in related for line in c['evidence_lines']}
        findings.append({'category':'contract_wording_review', 'title':title, 'detail':question,
            'bid_amount':None, 'realistic_low':None, 'realistic_high':None,
            'confidence':'needs_confirmation', 'scope_status':'unverified',
            'candidate_ids':[c['id'] for c in related], 'evidence_lines':list(lines.values()),
            'basis':'Machine-located wording or section context. Review surrounding clauses, plans and attachments; no scope decision, legal conclusion or added cost is established.'})
    return findings
