"""Recalculate upper-door stock while retaining the reviewed height bounds."""
import hashlib
import json
from pathlib import Path
from above_opening_stock import calculate
from measurement_store import MeasurementStore
from wall_field_stud_review import from_folder as field_layout
from opening_header_review import from_folder as header_review


def from_folder(folder):
    folder = Path(folder).resolve()
    path = folder/'above_door_stock_review.json'
    raw = path.read_bytes()
    config = json.loads(raw)
    checked = {path: raw}
    def load(ref):
        source = (folder/ref['path']).resolve()
        if not source.is_relative_to(folder):
            raise ValueError('Upper-door evidence must stay inside its job')
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref['sha256']:
            raise ValueError('Upper-door source changed: '+ref['path'])
        checked[source] = data
        return json.loads(data)
    basis = load(config['basis'])
    heights = load(config['heights'])
    selection = load(config['selection'])
    inventory = load(config['headers'])
    load(config['field_mapping'])
    load(config['header_mapping'])
    store = MeasurementStore(folder)
    state = store.read()
    field = field_layout(folder)
    review = header_review(folder, state)
    if any(p != state['plan_sha256'] for p in [config['plan_sha256'], basis['plan_sha256'],
            heights['plan_sha256'], selection['plan_sha256'], inventory['sha256'], field['plan_sha256']]):
        raise ValueError('Upper-door sources belong to different drawings')
    scenario, = [s for s in heights['scenarios'] if s['id'] == selection['selected_scenario']]
    if selection.get('source_kind') != 'owner_confirmation' or scenario['wall_height_inches'] != selection['wall_height_inches']:
        raise ValueError('Upper-door wall height requires its matching owner selection')
    stock, = [s for s in heights['stocks'] if s['sku'] == basis['stock_sku']]
    headers = {h['id']: h for h in inventory['headers']}
    openings = {o['opening_id']: o for o in review['openings']}
    pending, inputs = [], []
    for source in basis['openings']:
        identity = source['id']
        measurement = state['measurements'][identity]
        opening = openings[identity]
        if (measurement['label'] != source['label'] or measurement['page'] != basis['page']
                or measurement['points_per_foot'] != field['points_per_foot']
                or measurement['kind'] != 'length' or opening['header_id'] != source['header_id']):
            raise ValueError('Upper-door label, sheet, scale or header mapping needs review: '+identity)
        runs = {z['run'] for z in field['zones'] if z['assembly'] == identity}
        if len(runs) != 1 or not next(iter(runs)).startswith('IR'):
            pending.append({'id': identity, 'reason': 'Interior door needs one reviewed wall run'})
            continue
        run = next(iter(runs))
        if heights['run_height_offsets_inches'][run] != 0:
            raise ValueError('Upper-door height bound needs a revised floor datum: '+identity)
        if opening['status'] != 'end_support_length_unverified':
            pending.append({'id': identity, 'reason': 'Header no longer covers the opening with positive end allowance'})
            continue
        header = headers[source['header_id']]
        inputs.append({'id': identity, 'points': measurement['points'],
            'minimum_head_inches': source['minimum_head_inches'],
            'header_depth_inches': basis['header_depths_inches'][header['material_label']],
            'wall_top_inches': scenario['wall_height_inches']})
    result = calculate(field, inputs, stock, basis['top_plates_inches'])
    result['pending'].extend(pending)
    result.update(plan_sha256=state['plan_sha256'], measurement_version=state['version'],
        source_version=field['source_versions']['interior'], source_versions=field['source_versions'],
        mapping_sha256=hashlib.sha256(raw).hexdigest(), geometry_sha256=field['geometry_sha256'],
        source_hashes={str(p.relative_to(folder)):hashlib.sha256(data).hexdigest() for p,data in checked.items()},
        status='partial_scope_with_pending_members' if result['pending'] else 'documented_estimating_allowance',
        basis=basis['basis'], remaining=basis['remaining'], dimension_source=basis['dimension_source'],
        structural_adequacy_verified=False, purchase_quantity=None)
    if store.read() != state or field_layout(folder) != field or any(p.read_bytes() != data for p,data in checked.items()):
        raise ValueError('Upper-door sources changed during calculation; retry')
    return result
