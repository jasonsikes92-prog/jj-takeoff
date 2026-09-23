"""Recalculate the combined interior/exterior field layout and reservation overlaps."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from exterior_field_stud_review import from_folder as exterior_field_studs
from company_profile import resolve as resolve_profile
from field_reservations import junction_points,resolve
from field_stud_layout import layout
from framing_assembly_interactions import find_interactions


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'interior_field_stud_review.json'
    raw=path.read_bytes();config=json.loads(raw);checked=[(path,raw)];evidence={}
    for key in ['evidence','profile']:
        ref=config[key];path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Interior field evidence must stay inside its review')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('Interior field evidence changed: '+key)
        evidence[key]=json.loads(raw);checked.append((path,raw))
    anchors=evidence['evidence'];exterior=exterior_field_studs(folder)
    path=folder/'plate_stock_review.json';raw=path.read_bytes();plate=json.loads(raw);checked.append((path,raw))
    detail_path=(folder/anchors['detail_job']).resolve()
    if not detail_path.is_relative_to(folder.parent) or detail_path==folder:
        raise ValueError('Interior detail source must be a neighboring job')
    path=detail_path/'measurements.json';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=anchors['detail_config_sha256']:
        raise ValueError('Interior detail configuration changed')
    checked.append((path,raw))
    stores={'openings':MeasurementStore(folder),'interior':MeasurementStore(folder/plate['source_job']),
        'exterior':MeasurementStore(folder/plate['exterior_source']['job']),'details':MeasurementStore(detail_path)}
    states={key:store.read() for key,store in stores.items()};scale=anchors['points_per_foot']
    if any(s['plan_sha256']!=anchors['plan_sha256'] for s in states.values()):
        raise ValueError('Wall field features must refer to the same plan')
    if any(states[key]['version']!=version for key,version in exterior['source_versions'].items()):
        raise ValueError('Field geometry changed during calculation; retry')
    digests={}
    def check(m):
        if m['page']!=anchors['sheet'] or m['points_per_foot']!=scale:
            raise ValueError('Wall field features need the reviewed sheet and scale')
        digests[m['id']]=geometry_digest(m)
    runs=[]
    for identity in anchors['run_ids']:
        m=states['interior']['measurements'][identity];check(m)
        if m['kind']!='length' or len(m['points'])!=2:raise ValueError('Interior wall needs a straight measured run')
        a,b=m['points'];horizontal=abs(a[1]-b[1])<1e-6
        if not horizontal and abs(a[0]-b[0])>=1e-6:raise ValueError('Interior wall direction needs review')
        axis=0 if horizontal else 1;start,end=sorted([a[axis],b[axis]])
        runs.append({'id':identity,'orientation':'horizontal' if horizontal else 'vertical',
            'coordinate_pt':a[1-axis],'start_pt':start,'end_pt':end,'source':plate['source_job']+'#'+identity})
    outline=states['exterior']['measurements'][plate['exterior_source']['measurement_id']];check(outline)
    if geometry_digest(outline)!=exterior['geometry_sha256']['outline']:
        raise ValueError('Exterior outline changed during calculation')
    points=outline['points'];identities=[r['run'] for r in exterior['runs']]
    if len(points)!=len(identities):raise ValueError('Exterior wall mapping changed')
    for i,identity in enumerate(identities):
        a,b=points[i],points[(i+1)%len(points)];axis=0 if abs(a[1]-b[1])<1e-6 else 1
        start,end=sorted([a[axis],b[axis]])
        runs.append({'id':identity,'orientation':'horizontal' if axis==0 else 'vertical',
            'coordinate_pt':a[1-axis],'start_pt':start,'end_pt':end,'source':plate['exterior_source']['job']+'#'+identity})
    by_id={r['id']:r for r in runs};junctions=junction_points(runs,anchors['junctions'],points_per_foot=scale)
    features={}
    for binding in anchors['bindings']:
        if binding['kind']!='opening':continue
        identity=binding['opening'];source='details' if identity in states['details']['measurements'] else 'openings'
        m=states[source]['measurements'][identity];check(m)
        if m['kind']!='length' or len(m['points'])!=2:raise ValueError('Opening/cavity needs a straight measured span')
        features[identity]=m['points']
    for link in anchors['pocket_links']:
        run=by_id[link['run']];axis=0 if run['orientation']=='horizontal' else 1
        door_end=max(p[axis] for p in features[link['opening']])
        cavity_start,cavity_end=sorted(p[axis] for p in features[link['cavity']])
        if abs(door_end-cavity_start)>1e-6 or abs(cavity_end-run['end_pt'])>1e-6:
            raise ValueError('Pocket opening, cavity and wall end need reconciliation: '+link['opening'])
    cavities={link['cavity'] for link in anchors['pocket_links']}
    opening_runs={(b['opening'],b['run']) for b in anchors['bindings']
                  if b['kind']=='opening' and b['opening'] not in cavities}
    opening_runs.update((z['assembly'],z['run']) for z in exterior['zones']
                        if z['assembly'] in exterior['geometry_sha256'])
    for identity,run_id in sorted(opening_runs):
        span=features[identity] if identity in features else states['openings']['measurements'][identity]['points']
        axis=0 if by_id[run_id]['orientation']=='horizontal' else 1
        start,end=sorted(p[axis] for p in span)
        for definition in anchors['junctions']:
            if any(a['run']==run_id for a in definition['attachments']):
                if start<junctions[definition['id']][axis]<end:
                    raise ValueError('Opening crosses a wall junction; reconcile layout: '+identity+'/'+definition['id'])
    zones=resolve(runs,anchors['bindings'],features,by_id,points_per_foot=scale,junctions=junctions)+exterior['zones']
    profile=resolve_profile(evidence['profile'],project_overrides=anchors.get('project_overrides'))
    result=layout(runs,zones,points_per_foot=scale,spacing_inches=profile['settings']['framing.stud_spacing_inches'],
                  first_center_inches=anchors['first_center_inches'])
    interactions=find_interactions(zones)
    if any(store.read()['version']!=states[key]['version'] for key,store in stores.items()):
        raise ValueError('Wall features changed during calculation; retry')
    if any(path.read_bytes()!=raw for path,raw in checked):raise ValueError('Wall field references changed during calculation')
    return {**result,'zones':zones,'junction_points':junctions,'assembly_interactions':interactions,
        'plan_sha256':anchors['plan_sha256'],'source_versions':{key:s['version'] for key,s in states.items()},
        'measurement_dependencies':[{'job':str(store.folder.resolve()),'version':states[key]['version']}
                                    for key,store in stores.items()],
        'geometry_sha256':digests,'exterior_geometry_sha256':exterior['geometry_sha256'],
        'evidence_sha256':config['evidence']['sha256'],'profile_sha256':config['profile']['sha256'],
        'exterior_evidence_sha256':exterior['evidence_sha256'],
        'scope':'Combined wall field candidates; not complete assembly quantities or a stud order',
        'estimate_quantity_applied':False,'price_applied':False,'order_released':False}
