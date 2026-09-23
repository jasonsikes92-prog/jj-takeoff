"""Recalculate roof coverage from current edits and explicit component mapping."""
import hashlib
import json
from pathlib import Path
from roof_partition_review import audit_faces
from roof_coverage_review import read_review
from measurement_store import MeasurementStore,encode
from measurement_quantities import geometry_digest


def audit_state(state,config,coverage=None):
    if state['plan_sha256']!=config['plan_sha256']:raise ValueError('Roof mapping belongs to another drawing')
    ids=config['measurement_ids']
    if len(set(ids))!=len(ids) or any(i not in state['measurements'] for i in ids):
        raise ValueError('Roof mapping contains repeated or missing measurements')
    measurements=[state['measurements'][i] for i in ids]
    if coverage is not None and (coverage['plan_sha256']!=state['plan_sha256'] or
            any(m['page']!=coverage['page'] for m in measurements)):
        raise ValueError('Roof outline has a different drawing or page')
    return {'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
        'measurements_sha256':hashlib.sha256(encode([geometry_digest(m) for m in measurements]).encode()).hexdigest(),
        'coverage_review_sha256':coverage['review_sha256'] if coverage is not None else None,
        **({'unresolved_source_outlines':config['unresolved_source_outlines']} if 'unresolved_source_outlines' in config else {}),
        **audit_faces(measurements,coverage['points'] if coverage is not None else None,config['cutout_terms'])}


def from_folder(folder):
    folder=Path(folder);path=folder/'roof_partition_inputs.json'
    if not path.exists():return {'status':'not_configured','coverage':None,'certified':False,'order_released':False}
    raw=path.read_bytes();config=json.loads(raw)
    store=MeasurementStore(folder);state=store.read()
    page=state['measurements'][config['measurement_ids'][0]]['page']
    coverage=read_review(folder,state['plan_sha256'],page)
    if (coverage['review_sha256'] if coverage is not None else None)!=config['coverage_review_sha256']:
        raise ValueError('Roof outline review changed; rebuild the coverage mapping')
    result=audit_state(state,config,coverage)
    if path.read_bytes()!=raw:raise ValueError('Roof mapping changed during calculation')
    store.check_source()
    return result
