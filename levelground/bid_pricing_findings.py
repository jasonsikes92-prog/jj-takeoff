"""Turn extracted pricing discrepancies into sourced questions, never new costs."""
PRICING_FINDINGS_METHOD='native_pricing_questions_v2'


def pricing_findings(extraction,reference,filename):
    if not extraction:return []
    groups={'pricing_arithmetic':[],'pricing_quantity_basis':[],'pricing_extraction_incomplete':[]}
    for index,row in enumerate(extraction['pricing_candidates']):
        source={'desc':row['source_text'],'amount':None,
            'source_ref':f'{reference}, page {row["page"]}, pricing row {index+1}',
            'page':row['page'],'bbox':row['bbox'],'pricing_candidate_index':index,
            'source_quantity':row['quantity'],'source_rate':row['unit_rate'],
            'source_amount':row['amount'],'calculated_amount':row['calculated_amount'],
            'source_unit':row.get('quantity_unit_as_printed'),'quantity_role':row.get('quantity_role')}
        if row['arithmetic_matches'] is False:groups['pricing_arithmetic'].append(source)
        if row['quantity'] is not None and (row['quantity_unit'] is None or row.get('billing_basis') is None):
            groups['pricing_quantity_basis'].append(source)
    for row in extraction['unparsed_table_rows']:
        groups['pricing_extraction_incomplete'].append({'desc':row['source_text'],'amount':None,
            'source_ref':f'{reference}, page {row["page"]}, unparsed pricing row',
            'page':row['page'],'bbox':row['bbox'],'extraction_issue':row['reason']})
    wording={
        'pricing_arithmetic':('Line arithmetic needs clarification',
            'Please reconcile the extracted quantity times rate with the printed line amount. '
            'Confirm any discount, credit, rounding or extraction error before accepting a correction.'),
        'pricing_quantity_basis':('Confirm the quantity units',
            'Please identify the units and billing basis for the listed quantities. '
            'If billed by area, specify floor, wall or ceiling area and whether waste or other adjustments are included.'),
        'pricing_extraction_incomplete':('Some pricing rows need source review',
            'Please check the identified rows against the original document and provide a readable itemized schedule '
            'where needed. The automatic reader could not fully interpret these rows.')}
    return [{'category':kind,'title':wording[kind][0]+': '+filename,
        'detail':filename+': '+wording[kind][1],'evidence_lines':sources,
        'confidence':'needs_confirmation','scope_status':'unverified',
        'bid_amount':None,'realistic_low':None,'realistic_high':None,
        'basis':'Source-positioned extraction questions. No overcharge, missing construction scope, current price or added cost is established.'}
        for kind,sources in groups.items() if sources]
