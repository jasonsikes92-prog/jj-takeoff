"""Recalculate exterior field candidates from source-bound live wall features."""
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from plate_stock_review import from_folder as plate_stock
from company_profile import resolve as resolve_profile
from field_reservations import resolve as resolve_reservations
from field_stud_layout import layout


def from_folder(folder):
    folder = Path(folder).resolve()
    config_path = folder/'exterior_field_stud_review.json'
    config_raw = config_path.read_bytes(); config = json.loads(config_raw)
    checked = [(config_path,config_raw)]; evidence = {}
    for key in ['evidence','profile']:
        ref = config[key]; path = (folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Field-stud evidence must stay inside its review')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('Field-stud evidence changed: '+key)
        evidence[key] = json.loads(raw); checked.append((path,raw))
    anchors = evidence['evidence']
    # Reuse the plate review's neighboring-job, configuration, drawing and
    # orthogonal edge-identity checks before interpreting its wall geometry.
    plates = plate_stock(folder)
    plate_path = folder/'plate_stock_review.json'; raw = plate_path.read_bytes()
    plate_config = json.loads(raw); checked.append((plate_path,raw))
    if hashlib.sha256(raw).hexdigest() != plates['mapping_sha256']:
        raise ValueError('Wall mapping changed during field calculation')
    if not plates['exterior_geometry_editable']:
        raise ValueError('Exterior field calculation needs an editable centerline')
    stores = {'openings':MeasurementStore(folder),
        'interior':MeasurementStore(folder/plate_config['source_job']),
        'exterior':MeasurementStore(folder/plate_config['exterior_source']['job'])}
    states = {key:store.read() for key,store in stores.items()}
    if any(s['plan_sha256'] != anchors['plan_sha256'] for s in states.values()):
        raise ValueError('Field features must refer to the same drawing')
    if (states['interior']['version'] != plates['source_version']
            or states['exterior']['version'] != plates['exterior_source_version']):
        raise ValueError('Wall geometry changed during field calculation; retry')
    outline = states['exterior']['measurements'][plate_config['exterior_source']['measurement_id']]
    run_ids = anchors['run_ids']; points = outline['points']
    if len(points) != len(run_ids) or len(set(run_ids)) != len(run_ids):
        raise ValueError('Exterior field run mapping changed')
    if run_ids != [r['id'] for r in plates['runs'] if r['source_kind']=='editable_exterior_centerline']:
        raise ValueError('Exterior field and plate run identities must agree')
    scale = anchors['points_per_foot']; digests = {'outline':geometry_digest(outline)}
    def check(measurement):
        if measurement['page'] != anchors['sheet'] or measurement['points_per_foot'] != scale:
            raise ValueError('Field features require the reviewed sheet and scale')
    check(outline); runs = []
    for i,identity in enumerate(run_ids):
        a,b = points[i],points[(i+1)%len(points)]
        axis = 0 if abs(a[1]-b[1])<1e-6 else 1
        start,end = sorted([a[axis],b[axis]])
        runs.append({'id':identity,'orientation':'horizontal' if axis==0 else 'vertical',
            'coordinate_pt':a[1-axis],'start_pt':start,'end_pt':end,
            'source':plate_config['exterior_source']['job']+'#'+identity})
    opening_points = {}; branches = {}
    for binding in anchors['bindings']:
        if binding['kind'] == 'opening':
            identity = binding['opening']; m = states['openings']['measurements'][identity]; check(m)
            if m['kind'] != 'length' or len(m['points']) != 2:
                raise ValueError('Opening anchor needs one straight measured span')
            opening_points[identity] = m['points']; digests[identity] = geometry_digest(m)
        elif binding['kind'] == 'intersection':
            identity = binding['branch']; m = states['interior']['measurements'][identity]; check(m)
            if m['kind'] != 'length' or len(m['points']) != 2:
                raise ValueError('Branch anchor needs one straight measured span')
            a,b = m['points']; horizontal = abs(a[1]-b[1])<1e-6
            if not horizontal and abs(a[0]-b[0])>=1e-6:
                raise ValueError('Branch direction needs review')
            axis = 0 if horizontal else 1; start,end = sorted([a[axis],b[axis]])
            branches[identity] = {'id':identity,'orientation':'horizontal' if horizontal else 'vertical',
                'coordinate_pt':a[1-axis],'start_pt':start,'end_pt':end}
            digests[identity] = geometry_digest(m)
    zones = resolve_reservations(runs,anchors['bindings'],opening_points,branches,points_per_foot=scale)
    profile = resolve_profile(evidence['profile'],project_overrides=anchors.get('project_overrides'))
    result = layout(runs,zones,points_per_foot=scale,
        spacing_inches=profile['settings']['framing.stud_spacing_inches'],
        first_center_inches=anchors['first_center_inches'])
    if any(store.read()['version'] != states[key]['version'] for key,store in stores.items()):
        raise ValueError('Wall features changed during field calculation; retry')
    if any(path.read_bytes() != raw for path,raw in checked):
        raise ValueError('Field-stud references changed during calculation')
    return {**result,'zones':zones,'plan_sha256':anchors['plan_sha256'],
        'source_versions':{key:state['version'] for key,state in states.items()},
        'geometry_sha256':digests,'evidence_sha256':config['evidence']['sha256'],
        'profile_sha256':config['profile']['sha256'],
        'spacing_provenance':profile['provenance']['framing.stud_spacing_inches'],
        'scope':'Exterior field candidates only; partial assemblies remain separately reviewed',
        'estimate_quantity_applied':False,'price_applied':False,'order_released':False}
