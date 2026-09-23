"""Bind source-dimensioned subfloor cutting to the current saved floor boundary."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from subfloor_panel_layout import calculate
from subfloor_joints import from_layout


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'subfloor_panel_review.json';raw=path.read_bytes();config=json.loads(raw)
    links_path=folder/'linked_quantity_reviews.json';links_raw=links_path.read_bytes()
    links=[r for r in json.loads(links_raw) if r['job']==config['source_job']]
    if len(links)!=1:raise ValueError('Subfloor source must be registered exactly once')
    job=(folder/config['source_job']).resolve()
    if not job.is_relative_to(folder.parent) or job==folder:
        raise ValueError('Subfloor source must be a neighboring job')
    source=job/'measurements.json';source_raw=source.read_bytes()
    if hashlib.sha256(source_raw).hexdigest()!=links[0]['config_sha256']:
        raise ValueError('Subfloor source configuration changed')
    ref=config['basis'];basis_path=(folder/ref['path']).resolve()
    if not basis_path.is_relative_to(folder):raise ValueError('Subfloor basis must stay inside its job')
    basis_raw=basis_path.read_bytes()
    if hashlib.sha256(basis_raw).hexdigest()!=ref['sha256']:raise ValueError('Subfloor basis changed')
    basis=json.loads(basis_raw);store=MeasurementStore(job);state=store.read();own=MeasurementStore(folder).read()
    if state['plan_sha256']!=own['plan_sha256'] or basis['plan_sha256']!=own['plan_sha256']:
        raise ValueError('Subfloor sources belong to different drawings')
    measurement=state['measurements'][config['measurement_id']]
    old=next(m for m in json.loads(source_raw)['measurements'] if m['id']==config['measurement_id'])
    if (measurement['kind']!='area' or measurement['page']!=old['page']
            or measurement['points_per_foot']!=old['points_per_foot']):
        raise ValueError('Subfloor sheet, kind or scale changed')
    result=calculate(measurement['points'],measurement['points_per_foot'],**basis['cut_basis'])
    if store.read()['version']!=state['version']:
        raise ValueError('Subfloor measurements changed during calculation; retry')
    if (path.read_bytes()!=raw or links_path.read_bytes()!=links_raw
            or source.read_bytes()!=source_raw or basis_path.read_bytes()!=basis_raw):
        raise ValueError('Subfloor sources changed during calculation')
    return {**result,'plan_sha256':state['plan_sha256'],'source_version':state['version'],
        'source_geometry_sha256':geometry_digest(measurement),'source_measurement_id':measurement['id'],
        'mapping_sha256':hashlib.sha256(raw).hexdigest(),'basis_sha256':ref['sha256'],
        'basis':basis['description'],'remaining':basis['remaining'],'price_applied':False}


def joints_from_folder(folder):
    panels=from_folder(folder)
    return {**from_layout(panels),
        **{key:panels[key] for key in ['plan_sha256','source_version','source_geometry_sha256',
            'source_measurement_id','mapping_sha256','basis_sha256','basis','remaining','origin_pt']},
        'status':'Shared seams of the current candidate panel layout; not an installation or purchase specification',
        'coordinate_system':'Feet from the saved floor footprint minimum X/Y, aligned with plan axes',
        'scope_limit':'Excludes framing adhesive beads, extra panel-end beads, waste, fastening and installed-gap adjustments. Product coverage and support details remain unresolved.'}
