"""Recalculate plate cuts from source-bound interior runs and exterior outlines."""
import hashlib
import json
import math
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from plate_layout import stock_study


def bottom_floor_groups(runs, wall_points, floor, width_inches, wood_group, pending_group):
    """Classify full-width plate footprints; any overhang stays unresolved."""
    from shapely.geometry import LineString, Polygon
    if (floor.get('kind')!='area' or type(width_inches) not in (int,float)
            or not math.isfinite(width_inches) or width_inches<=0
            or any(not isinstance(g,str) or not g.strip() for g in (wood_group,pending_group))
            or wood_group==pending_group or set(wall_points)!={r['id'] for r in runs}):
        raise ValueError('Bottom-plate review requires a floor, positive width and distinct material groups for all runs')
    scale=floor['points_per_foot']
    if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:
        raise ValueError('Positive floor scale required')
    polygon=Polygon(floor['points'])
    if not polygon.is_valid or polygon.is_empty or not math.isfinite(polygon.area) or polygon.area<=0:
        raise ValueError('Valid floor polygon required')
    groups={};details=[]
    for run in runs:
        points=wall_points[run['id']]
        if len(points)!=2 or any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Finite straight plate footprints required')
        line=LineString(points)
        if not math.isclose(line.length/scale*12,run['length_inches'],rel_tol=0,abs_tol=1e-6):
            raise ValueError('Plate footprint and measured run length differ')
        footprint=line.buffer(width_inches/24*scale,cap_style=2)
        outside=footprint.difference(polygon).area/scale**2*144
        # Only numerical area noise is ignored, never a construction tolerance.
        covered=outside<=1e-7
        group=wood_group if covered else pending_group;groups[run['id']]=group
        details.append({'run_id':run['id'],'length_inches':run['length_inches'],
            'outside_floor_area_sq_in':outside,'material_group':group,
            'status':'wood_floor_allowance_candidate' if covered else 'support_or_treatment_unresolved'})
    return groups,{'floor_measurement_id':floor['id'],'plate_width_inches':width_inches,'runs':details,
        'wood_floor_run_count':sum(d['status']=='wood_floor_allowance_candidate' for d in details),
        'pending_run_count':sum(d['status']=='support_or_treatment_unresolved' for d in details),
        'wood_floor_run_lf':math.fsum(d['length_inches'] for d in details if d['status']=='wood_floor_allowance_candidate')/12,
        'basis':'Full plate-width footprint must lie inside the reviewed wood-floor boundary. All mixed/outside runs retain unresolved material; no partial untreated allocation or assumed concrete treatment.',
        'quantity_certified_for_order':False,'code_approval':False}


def outline_runs(measurement, original, identities, source):
    """Keep reviewed edge identities when an orthogonal centerline is edited."""
    points = measurement['points']; baseline = original['points']
    if (measurement['kind'] != 'area' or len(points) != len(baseline)
            or len(points) != len(identities) or len(set(identities)) != len(identities)):
        raise ValueError('Exterior wall topology changed; review the edge mapping')
    runs = []
    for i, identity in enumerate(identities):
        a, b = points[i], points[(i+1) % len(points)]
        old_a, old_b = baseline[i], baseline[(i+1) % len(points)]
        dx, dy = b[0]-a[0], b[1]-a[1]
        old_dx, old_dy = old_b[0]-old_a[0], old_b[1]-old_a[1]
        horizontal = abs(old_dy) < 1e-6 and abs(old_dx) > 1e-6
        vertical = abs(old_dx) < 1e-6 and abs(old_dy) > 1e-6
        if not ((horizontal and abs(dy) < 1e-6 and dx*old_dx > 0)
                or (vertical and abs(dx) < 1e-6 and dy*old_dy > 0)):
            raise ValueError('Exterior wall direction changed; review the edge mapping')
        runs.append({'id':identity, 'length_inches':math.dist(a,b) / measurement['points_per_foot'] * 12,
                     'source_kind':'editable_exterior_centerline', 'source':source + '#' + identity})
    return runs


def from_folder(folder):
    folder = Path(folder).resolve()
    config_path = folder / 'plate_stock_review.json'
    config_raw = config_path.read_bytes(); config = json.loads(config_raw)
    links_path = folder / 'linked_quantity_reviews.json'
    links_raw = links_path.read_bytes()
    matches = [r for r in json.loads(links_raw) if r['job'] == config['source_job']]
    if len(matches) != 1:
        raise ValueError('Plate source job must be registered exactly once')
    job = (folder / config['source_job']).resolve()
    if not job.is_relative_to(folder.parent) or job == folder:
        raise ValueError('Plate source must be a registered neighboring job')
    checked = []
    for name, key in [('measurements.json', 'config_sha256'), ('quantity_rules.json', 'rules_sha256')]:
        path = job / name; raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != matches[0][key]:
            raise ValueError('Plate source configuration changed')
        checked.append((path, raw))
    ref = config['evidence']; evidence_path = (folder / ref['source_file']).resolve()
    if not evidence_path.is_relative_to(folder) or not evidence_path.is_file():
        raise ValueError('Plate evidence must be inside the review folder')
    evidence_raw = evidence_path.read_bytes()
    if hashlib.sha256(evidence_raw).hexdigest() != ref['source_sha256']:
        raise ValueError('Plate run evidence changed')
    evidence = json.loads(evidence_raw)
    store = MeasurementStore(job); state = store.read()
    own = json.loads((folder / 'measurements.json').read_bytes())
    if state['plan_sha256'] != own['plan_sha256'] or evidence['plan_sha256'] != state['plan_sha256']:
        raise ValueError('Plate sources must refer to the same plan')
    rule_ids = matches[0].get('quantity_rule_ids', [])
    rules = json.loads((job / 'quantity_rules.json').read_bytes())
    rule = [r for r in rules['rules'] if r['id'] == config['quantity_rule_id']]
    live_ids = evidence['editable_run_ids']
    if (config['quantity_rule_id'] not in rule_ids or len(rule) != 1
            or len(set(live_ids)) != len(live_ids)
            or set(rule[0]['measurement_ids']) != set(live_ids)):
        raise ValueError('Plate runs must match the registered wall quantity rule')
    runs = []; digests = {}; wall_points={}
    for identity in live_ids:
        m = state['measurements'][identity]
        if m['kind'] != 'length' or m['page'] != evidence['sheet'] or len(m['points']) != 2:
            raise ValueError('Plate source must be a straight wall run on the reviewed sheet')
        runs.append({'id':identity, 'length_inches':m['result']['quantity'] * 12,
                     'source_kind':'editable_measurement', 'source':config['source_job'] + '#' + identity})
        digests[identity] = geometry_digest(m)
        wall_points[identity]=m['points']
    exterior = config.get('exterior_source')
    exterior_store = None; exterior_state = None
    if exterior is not None:
        exterior_job = (folder / exterior['job']).resolve()
        if not exterior_job.is_relative_to(folder.parent) or exterior_job in (folder, job):
            raise ValueError('Exterior plate source must be a distinct neighboring job')
        path = exterior_job / 'measurements.json'; raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != exterior['config_sha256']:
            raise ValueError('Exterior plate configuration changed')
        checked.append((path, raw))
        exterior_store = MeasurementStore(exterior_job); exterior_state = exterior_store.read()
        if exterior_state['plan_sha256'] != state['plan_sha256']:
            raise ValueError('Exterior plate source must refer to the same plan')
        identity = exterior['measurement_id']
        measurement = exterior_state['measurements'][identity]
        if measurement['page'] != evidence['sheet']:
            raise ValueError('Exterior plate source must use the reviewed sheet')
        original = next(m for m in json.loads(raw)['measurements'] if m['id'] == identity)
        edge_ids = [r['id'] for r in evidence['exterior_runs']]
        runs += outline_runs(measurement, original, edge_ids, exterior['job'] + '#' + identity)
        digests[identity] = geometry_digest(measurement)
        wall_points.update({key:[measurement['points'][i],measurement['points'][(i+1)%len(edge_ids)]] for i,key in enumerate(edge_ids)})
    else:
        runs += [{**r, 'source_kind':'saved_exterior_reference'} for r in evidence['exterior_runs']]
    zone=evidence.get('bottom_wood_floor');groups=None;support=None
    if zone is not None:
        if exterior is None:raise ValueError('Bottom-floor assignments require current exterior geometry')
        floor=state['measurements'][zone['measurement_id']]
        if (floor['page']!=evidence['sheet'] or floor['points_per_foot']!=state['measurements'][live_ids[0]]['points_per_foot']
                or measurement['points_per_foot']!=floor['points_per_foot']
                or not zone.get('basis') or zone['material_group']==evidence['material_groups']['top']):
            raise ValueError('Bottom-floor source must match the plate sheet, scale and explicit material basis')
        groups,support=bottom_floor_groups(runs,wall_points,floor,zone['plate_width_inches'],
            zone['material_group'],evidence['material_groups']['bottom'])
        support['material_basis']=zone['basis'];digests[floor['id']]=geometry_digest(floor)
    result = stock_study(runs, evidence['material_groups'], **evidence['cut_basis'],bottom_material_groups=groups)
    if support is not None:result['bottom_support_review']=support
    if store.read()['version'] != state['version']:
        raise ValueError('Wall measurements changed during plate calculation; retry')
    if exterior_store is not None and exterior_store.read()['version'] != exterior_state['version']:
        raise ValueError('Exterior wall measurements changed during plate calculation; retry')
    if (config_path.read_bytes() != config_raw or links_path.read_bytes() != links_raw
            or evidence_path.read_bytes() != evidence_raw
            or any(p.read_bytes() != raw for p, raw in checked)):
        raise ValueError('Plate references changed during calculation')
    return {**result, 'plan_sha256':state['plan_sha256'], 'source_version':state['version'],
            'source_geometry_sha256':digests, 'editable_runs':len(live_ids),
            'saved_exterior_runs':0 if exterior else len(evidence['exterior_runs']),
            'editable_exterior_runs':len(evidence['exterior_runs']) if exterior else 0,
            'exterior_source_version':exterior_state['version'] if exterior_state else None,
            'exterior_geometry_editable':exterior is not None, 'evidence_sha256':ref['source_sha256'],
            'mapping_sha256':hashlib.sha256(config_raw).hexdigest()}
