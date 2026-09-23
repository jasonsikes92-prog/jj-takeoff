"""Bind header cutting calculations to current opening and pocket-detail measurements."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from opening_header_review import from_folder as opening_headers
from header_cut_scope import calculate, estimate_replacements


def from_folder(folder):
    folder=Path(folder).resolve();config_path=folder/'header_cut_review.json'
    config_raw=config_path.read_bytes();config=json.loads(config_raw);checked=[];loaded={}
    keys=['study','baseline','headers']+(['estimating_replacements'] if 'estimating_replacements' in config else [])
    for key in keys:
        reference=config[key];path=(folder/reference['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Header cut evidence must stay inside its job')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=reference['sha256']:
            raise ValueError('Header cut evidence changed: '+key)
        loaded[key]=json.loads(raw);checked.append((path,raw))
    for reference in loaded.get('estimating_replacements',{}).get('sources',[]):
        path=(folder/reference['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Replacement header evidence must stay inside its job')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=reference['sha256']:
            raise ValueError('Replacement header source changed')
        checked.append((path,raw))
    mapping_path=folder/'opening_header_review.json';mapping_raw=mapping_path.read_bytes()
    if hashlib.sha256(mapping_raw).hexdigest()!=config['opening_mapping_sha256']:
        raise ValueError('Header opening mapping changed; review the cutting reference')
    store=MeasurementStore(folder);state=store.read();current=opening_headers(folder,state)
    if current['evidence_sha256']!=loaded['baseline']['evidence_sha256']:
        raise ValueError('Header source evidence differs from the cutting reference')
    result=calculate(loaded['headers']['headers'],loaded['study'],loaded['baseline'],current)
    if 'estimating_replacements' in loaded:
        result=estimate_replacements(result,loaded['study'],current,loaded['estimating_replacements']['records'])
    if loaded['headers']['sha256']!=state['plan_sha256']:
        raise ValueError('Header cut inventory belongs to another drawing')
    if store.read()['version']!=state['version']:
        raise ValueError('Opening measurements changed during header cutting calculation; retry')
    for linked in current.get('linked_measurement_versions',[]):
        if MeasurementStore(linked['job']).read()['version']!=linked['version']:
            raise ValueError('Pocket measurements changed during header cutting calculation; retry')
    if (config_path.read_bytes()!=config_raw or mapping_path.read_bytes()!=mapping_raw
            or any(path.read_bytes()!=raw for path,raw in checked)):
        raise ValueError('Header cutting references changed during calculation')
    return {**result,'opening_geometry_sha256':current['opening_geometry_sha256'],
        'linked_measurement_versions':current.get('linked_measurement_versions',[]),
        'evidence_sha256':{key:config[key]['sha256'] for key in loaded},
        'mapping_sha256':hashlib.sha256(config_raw).hexdigest()}
