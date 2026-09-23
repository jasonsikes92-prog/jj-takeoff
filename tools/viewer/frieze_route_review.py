"""Recompute explicit frieze scenarios from the registered editable cladding job."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from elevation_trim_routes import calculate


def from_folder(folder):
    folder=Path(folder).resolve();config_path=folder/'frieze_route_review.json'
    raw=config_path.read_bytes();config=json.loads(raw);checked=[(config_path,raw)]
    links_path=folder/'linked_quantity_reviews.json';links_raw=links_path.read_bytes()
    checked.append((links_path,links_raw))
    links=[r for r in json.loads(links_raw) if r['job']==config['source_job']]
    if len(links)!=1:raise ValueError('Frieze source must be registered exactly once')
    job=(folder/config['source_job']).resolve()
    if not job.is_relative_to(folder.parent) or job==folder:raise ValueError('Frieze source must be a neighboring job')
    for name,key in [('measurements.json','config_sha256'),('quantity_rules.json','rules_sha256')]:
        path=job/name;data=path.read_bytes();checked.append((path,data))
        if hashlib.sha256(data).hexdigest()!=links[0][key]:raise ValueError('Frieze source configuration changed')
    path=(folder/config['mapping']['path']).resolve()
    if not path.is_relative_to(folder):raise ValueError('Frieze mapping must stay inside its job')
    data=path.read_bytes();checked.append((path,data))
    if hashlib.sha256(data).hexdigest()!=config['mapping']['sha256']:raise ValueError('Frieze mapping changed')
    basis=json.loads(data);store=MeasurementStore(job);state=store.read()
    own=MeasurementStore(folder).read()
    if basis['plan_sha256']!=state['plan_sha256'] or own['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Frieze sources belong to different drawings')
    ids={e['measurement_id'] for group in basis['routes'].values() for e in group}
    measurements={i:state['measurements'][i] for i in ids}
    result=calculate(measurements,basis['routes'])
    if store.read()['version']!=state['version']:raise ValueError('Frieze source changed during calculation; retry')
    if any(p.read_bytes()!=b for p,b in checked):raise ValueError('Frieze references changed during calculation; retry')
    result.update(plan_sha256=state['plan_sha256'],source_version=state['version'],
        source_job=str(job),mapping_sha256=hashlib.sha256(raw).hexdigest(),
        source_geometry_sha256={i:geometry_digest(m) for i,m in measurements.items()},
        interpretation='Unselected scope scenarios; gable-base and porch interface decisions remain open')
    return result
