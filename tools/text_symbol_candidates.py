"""Located text-symbol candidates, with explicit legend/note exclusion regions."""
import hashlib
import json
import math


def plan_symbol_candidates(document, config, plan_sha256):
    """Extract configured legends only from the drawing revision they describe."""
    if config.get('plan_sha256') != plan_sha256:
        raise ValueError('Symbol definitions belong to another drawing')
    pages = config.get('pages', [])
    if not pages:
        raise ValueError('Symbol extraction needs explicit page definitions')
    seen = set(); measurements = []; page_results = []
    for definition in pages:
        page = definition['page']
        if type(page) is not int or not 1 <= page <= len(document) or page in seen:
            raise ValueError('Symbol page must be unique and inside this drawing')
        seen.add(page)
        result = symbol_candidates(document[page-1], definition['symbols'], definition['exclusions'])
        measurements.extend(result['measurements'])
        page_results.append({'page': page, 'excluded_labels': result['excluded_labels'],
                             'missing_symbol_tokens': result['missing_symbol_tokens']})
    return {'plan_sha256': plan_sha256, 'measurements': measurements, 'pages': page_results,
            'definitions_sha256': hashlib.sha256(json.dumps(config, sort_keys=True, allow_nan=False).encode()).hexdigest(),
            'scope_review_required': True, 'coverage_certified': False, 'estimate_released': False}


def symbol_candidates(page, symbols, exclusions):
    if not symbols or any(not k.strip() or not v.get('label') or not v.get('meaning_source') for k,v in symbols.items()):
        raise ValueError('Explicit symbol meanings and source references required')
    for exclusion in exclusions:
        box=exclusion['bbox_pt']
        if len(box)!=4 or not all(type(v) in (int,float) and math.isfinite(v) for v in box) or box[0]>=box[2] or box[1]>=box[3] or not exclusion.get('source'):
            raise ValueError('Exclusion needs bounds and source')
    found={k:[] for k in symbols};excluded={k:[] for k in symbols};seen=set()
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=''.join(s['text'] for s in line['spans']).strip()
            if text not in symbols:continue
            box=list(line['bbox']);point=[(box[0]+box[2])/2,(box[1]+box[3])/2]
            key=(text,tuple(round(v,3) for v in box))
            if key in seen:continue
            seen.add(key)
            hits=[e['source'] for e in exclusions if box[0]<=e['bbox_pt'][2] and box[2]>=e['bbox_pt'][0] and box[1]<=e['bbox_pt'][3] and box[3]>=e['bbox_pt'][1]]
            record={'text':text,'point_pt':point,'bbox_pt':box}
            if hits:excluded[text].append({**record,'exclusions':hits})
            else:found[text].append(record)
    measurements=[]
    for token,locations in found.items():
        if not locations:continue
        identity='symbol-'+hashlib.sha256(json.dumps([page.number,token,locations],sort_keys=True).encode()).hexdigest()[:16]
        measurements.append({'id':identity,'label':symbols[token]['label'],'page':page.number+1,
            'kind':'count','points':[s['point_pt'] for s in locations],'width_pt':page.rect.width,
            'height_pt':page.rect.height,'color':symbols[token].get('color','#0369a1'),
            'dependent_rows':[],'engine_line_ids':[identity],'symbol_token':token,
            'source_labels':locations,'meaning_source':symbols[token]['meaning_source'],
            'scope_status':'Located text labels; verify physical symbol meaning, redlines and coverage before pricing'})
    return {'measurements':measurements,'excluded_labels':excluded,'certified':False,
        'missing_symbol_tokens':[k for k,v in found.items() if not v]}
