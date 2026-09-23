"""Recalculate a nominal panel study from a registered, editable roof job."""
import hashlib
import json
import math
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from roof_panel_layout import panel_modules,pack_blanks
from roof_junction_quantities import calculate as roof_junctions


def junction_allowance(review,plan_sha256,gradient_sha256,geometry_sha256):
    if review.get('plan_sha256')!=plan_sha256:
        raise ValueError('Roof junction approximation belongs to another drawing')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Roof junction approximation needs reviewer and basis')
    value=review.get('maximum_rise_difference_inches')
    if type(value) not in (int,float) or not math.isfinite(value) or value<.0001:
        raise ValueError('Finite positive roof junction rise allowance required')
    if (review.get('gradient_sha256')!=gradient_sha256
            or review.get('source_geometry_sha256')!=geometry_sha256):
        return None,'stale_source_review'
    return value,'current_estimating_review'


def from_folder(folder):
    folder=Path(folder).resolve()
    path=folder/'roof_panel_review.json';raw=path.read_bytes();config=json.loads(raw)
    links_path=folder/'linked_quantity_reviews.json';links_raw=links_path.read_bytes()
    matches=[link for link in json.loads(links_raw) if link['job']==config['source_job']]
    if len(matches)!=1:raise ValueError('Roof job must be registered exactly once')
    job=(folder/config['source_job']).resolve()
    if not job.is_relative_to(folder.parent) or job==folder:
        raise ValueError('Roof source must be a registered neighboring job')
    link=matches[0]
    checked=[]
    for name,key in [('measurements.json','config_sha256'),('quantity_rules.json','rules_sha256')]:
        source=job/name
        if hashlib.sha256(source.read_bytes()).hexdigest()!=link[key]:
            raise ValueError('Roof source configuration changed')
        checked.append((source,link[key]))
    ref=config['gradients'];source=(folder/ref['source_file']).resolve()
    if not source.is_relative_to(folder) or not source.is_file():
        raise ValueError('Roof gradient evidence must be inside the review folder')
    source_raw=source.read_bytes()
    if hashlib.sha256(source_raw).hexdigest()!=ref['source_sha256']:
        raise ValueError('Roof gradient evidence changed')
    evidence=json.loads(source_raw);store=MeasurementStore(job);state=store.read()
    own=json.loads((folder/'measurements.json').read_bytes())
    if state['plan_sha256']!=own['plan_sha256'] or evidence['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Roof panel sources must refer to the same plan')
    rules=json.loads((job/'quantity_rules.json').read_bytes())
    roof_rules=[r for r in rules['rules'] if r['id']==config['quantity_rule_id']]
    if len(roof_rules)!=1 or set(roof_rules[0]['measurement_ids'])!=set(evidence['upslope_gradients']):
        raise ValueError('Roof panel face set does not match the registered quantity rule')
    faces=[];digests={};source_faces=[]
    for identity,gradient in evidence['upslope_gradients'].items():
        m=state['measurements'][identity]
        if m['kind']!='area' or m['page']!=evidence['sheet']:
            raise ValueError('Roof panel source must be an area on the reviewed roof sheet')
        faces.append(panel_modules({**m,'id':identity},gradient))
        source_faces.append({**m,'id':identity})
        digests[identity]=geometry_digest(m)
    sheets=pack_blanks([p for f in faces for p in f['pieces']])
    junction_path=folder/'roof_junction_approximation_review.json'
    junction_raw=junction_path.read_bytes() if junction_path.exists() else None
    allowance=None
    if junction_raw is not None:
        junction_review=json.loads(junction_raw)
        allowance,junction_status=junction_allowance(junction_review,state['plan_sha256'],ref['source_sha256'],digests)
    junctions=roof_junctions(source_faces,evidence['upslope_gradients'],rise_allowance_inches=allowance)
    if junction_raw is not None:
        junctions['approximation_review']={**junction_review,'status':junction_status,
            'review_sha256':hashlib.sha256(junction_raw).hexdigest(),
            'owner_approved':False,'structural_approval':False}
    if store.read()['version']!=state['version']:
        raise ValueError('Roof measurements changed during panel calculation; retry')
    if path.read_bytes()!=raw or links_path.read_bytes()!=links_raw or source.read_bytes()!=source_raw:
        raise ValueError('Roof panel references changed during calculation')
    if any(hashlib.sha256(p.read_bytes()).hexdigest()!=digest for p,digest in checked):
        raise ValueError('Roof source configuration changed during calculation')
    if (junction_path.read_bytes() if junction_path.exists() else None)!=junction_raw:
        raise ValueError('Roof junction approximation changed during calculation; retry')
    return {'plan_sha256':state['plan_sha256'],'source_version':state['version'],
        'source_geometry_sha256':digests,'faces':faces,'sheets':sheets,'junctions':junctions,
        'candidate_sheets':len(sheets),'module_sections':sum(len(f['pieces']) for f in faces),
        'gross_surface_sf':sum(f['surface_sf'] for f in faces),
        'basis':'Nominal 96 x 48-inch modules with 1/8-inch saw kerf; rectangular reuse without rotating strength axis.',
        'remaining':['Confirm panel sizing/gaps, grade and span stamp.',
                     'Reconcile support datum, seams, boundary pieces, clips/blocking and ridge openings.',
                     'Review roof interfaces and remaining framing scope.'],
        'purchase_quantity':None,'complete_framing_total':None,'price_applied':False,
        'mapping_sha256':hashlib.sha256(raw).hexdigest(),'gradient_sha256':ref['source_sha256']}
