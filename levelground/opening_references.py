"""Project source-reviewed opening geometry into a price-free homeowner reference."""
import hashlib
import json


def references(schedule):
    rows=schedule['openings'];identities=[r['opening_id'] for r in rows]
    if len(set(identities))!=len(identities):raise ValueError('Opening references require unique identities')
    current=(bool(rows) and not schedule['unresolved_opening_ids'] and not schedule['stale_or_missing_label_ids']
        and all(r['review_status']=='current_source_review' for r in rows))
    details=[];quantities=[];unknowns=[]
    for row in rows:
        reviewed=row['review_status']=='current_source_review';size=row.get('printed_nominal_size')
        details.append({'opening_id':row['opening_id'],'page':row['page'],'printed_tag':row['tag'],
            'location':row.get('location') if reviewed else None,'role':row['role'] if reviewed else None,
            'nominal_width_inches':size.get('width_inches') if size else None,
            'nominal_height_inches':size.get('height_inches') if size else None,
            'door_configuration':row.get('door_configuration') if reviewed else None,
            'drawn_panel_count':row.get('drawn_panel_count') if reviewed else None,
            'individual_window_units':row.get('window_component_count') if reviewed and row['role']=='window' else None,
            'source_review_current':reviewed,'purchase_quantity':None})
    groups=(('window','Individual window units'),('interior_door','Ordinary interior door assemblies'),
        ('special_interior_door','Specialty interior door assemblies'),('exterior_door','Exterior door assemblies'))
    if current:
        for role,label in groups:
            selected=[r for r in rows if r['role']==role]
            if not selected:continue
            if role=='window' and any(r.get('window_component_count') is None for r in selected):
                unknowns.append('Individual window quantity is withheld because component counts are unconfirmed.')
                continue
            count=sum(r['window_component_count'] for r in selected) if role=='window' else len(selected)
            pages=sorted({r['page'] for r in selected})
            quantities.append({'item':'Draft reference: '+label,'qty':count,'unit':'EA',
                'source':'Selected plan, page(s) '+', '.join(map(str,pages)),
                'confidence':'needs_confirmation','opening_ids':[r['opening_id'] for r in selected],
                'measurement_version':schedule['measurement_version'],'certified':False,'purchase_quantity':None})
    else:
        unknowns.append('Window and door counts are withheld because opening source reviews are missing or stale.')
    unknowns.extend(['Opening references cover only located, source-reviewed tags; untagged or undetected openings remain unverified.',
        'Nominal dimensions and drawn panels do not establish manufacturer rough openings, purchased slabs or complete product assemblies.',
        'Window and door materials, glazing, handing, hardware, installation inclusions and current prices require confirmation.'])
    source={'plan_sha256':schedule['plan_sha256'],'measurement_version':schedule['measurement_version'],
        'review_sha256':schedule['review_sha256'],'details':details,
        'missing_labels':schedule['stale_or_missing_label_ids'],'unresolved_ids':schedule['unresolved_opening_ids']}
    return {'source_sha256':hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'source_enumeration_current':current,'details':details,'quantities':quantities,'unknowns':unknowns,
        'open_passage_count':sum(d['role']=='open_passage' for d in details) if current else None,
        'coverage_certified':False,'purchase_released':False}
