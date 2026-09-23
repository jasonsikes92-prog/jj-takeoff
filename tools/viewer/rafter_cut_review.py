"""Rebuild provisional rafter stock from current roof faces and bound source evidence."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from rafter_cut_layout import stations,allocate


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'rafter_cut_review.json';raw=path.read_bytes();config=json.loads(raw)
    links_path=folder/'linked_quantity_reviews.json';links_raw=links_path.read_bytes()
    links=[r for r in json.loads(links_raw) if r['job']==config['source_job']]
    if len(links)!=1:raise ValueError('Rafter source must be registered exactly once')
    job=(folder/config['source_job']).resolve()
    if not job.is_relative_to(folder.parent) or job==folder:raise ValueError('Rafter source must be a neighboring job')
    checked=[];loaded={}
    for name,key in [('measurements.json','config_sha256'),('quantity_rules.json','rules_sha256')]:
        source=job/name;data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=links[0][key]:raise ValueError('Rafter source configuration changed')
        checked.append((source,data))
    for key in ['gradients','basis']:
        ref=config[key];source=(folder/ref['path']).resolve()
        if not source.is_relative_to(folder):raise ValueError('Rafter evidence must stay inside its job')
        data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Rafter evidence changed: '+key)
        loaded[key]=json.loads(data);checked.append((source,data))
    store=MeasurementStore(job);state=store.read();own=MeasurementStore(folder).read()
    if any(x['plan_sha256']!=own['plan_sha256'] for x in [state,*loaded.values()]):
        raise ValueError('Rafter sources belong to different drawings')
    gradients=loaded['gradients'];basis=loaded['basis']
    rule=next(r for r in json.loads((job/'quantity_rules.json').read_bytes())['rules'] if r['id']==config['quantity_rule_id'])
    if set(rule['measurement_ids'])!=set(gradients['upslope_gradients']):
        raise ValueError('Rafter face set differs from the roof rule')
    segments=[];digests={};originals={m['id']:m for m in json.loads(checked[0][1])['measurements']}
    for identity,gradient in gradients['upslope_gradients'].items():
        m=state['measurements'][identity];old=originals[identity]
        if m['kind']!='area' or m['page']!=gradients['sheet'] or m['points_per_foot']!=old['points_per_foot']:
            raise ValueError('Rafter source sheet, kind or scale changed')
        segments.extend(stations(m,gradient,**basis['station_basis']));digests[identity]=geometry_digest(m)
    result=allocate(segments,basis['stock'],**basis['cut_basis'])
    if store.read()['version']!=state['version']:raise ValueError('Roof changed during rafter calculation; retry')
    if path.read_bytes()!=raw or links_path.read_bytes()!=links_raw or any(p.read_bytes()!=data for p,data in checked):
        raise ValueError('Rafter source references changed during calculation')
    return {**result,'plan_sha256':state['plan_sha256'],'source_version':state['version'],
        'source_geometry_sha256':digests,'mapping_sha256':hashlib.sha256(raw).hexdigest(),
        'evidence_sha256':{k:config[k]['sha256'] for k in loaded},
        'basis':basis['description'],'remaining':basis['remaining']}
