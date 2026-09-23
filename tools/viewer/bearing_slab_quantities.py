"""Pool a wall-supported slab order and optionally extend its labor allowance."""
import copy
import hashlib
import json
import math

from measurement_store import MeasurementStore, encode
from measurement_quantities import geometry_digest
from slab_geometry import (area, horizontal_band_area, offset_edges, rebar_grid,
                           roll_layout, material_coverage_cells)
from slab_materials import material_allowances, whole_units, gravel_truckloads
from slab_review import validate_polygon


def pack_cuts(groups, stock_length):
    """Preserve every required cut and assign it to feasible whole stock units."""
    if not math.isfinite(stock_length) or stock_length <= 0:
        raise ValueError('Positive stock length required')
    cuts = []
    for scope, lengths in groups.items():
        for index, length in enumerate(lengths):
            if not math.isfinite(length) or length <= 0 or length > stock_length:
                raise ValueError('Cut must fit the selected stock length')
            cuts.append({'scope': scope, 'piece': index + 1, 'length_ft': length})
    stocks = []
    for cut in sorted(cuts, key=lambda c: -c['length_ft']):
        stock = next((s for s in stocks if s['remaining_ft'] + 1e-9 >= cut['length_ft']), None)
        if stock is None:
            stock = {'id': len(stocks) + 1, 'remaining_ft': stock_length, 'cuts': []}
            stocks.append(stock)
        stock['cuts'].append(cut)
        stock['remaining_ft'] -= cut['length_ft']
    return {'stock_count': len(stocks), 'stocks': stocks, 'stock_length_ft': stock_length,
            'cut_length_ft': sum(c['length_ft'] for c in cuts),
            'basis': 'Descending-length feasible cut schedule; no width-offcut reuse or end splices for rolls; not guaranteed minimum.'}


def calculate_bearing_slab(points, garage, bearing_inches, thickness_inches):
    """Plain bearing slab only; no copied garage haunch, footer or pump charges."""
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
           for v in (bearing_inches, thickness_inches)):
        raise ValueError('Bearing and thickness must be positive')
    profile = copy.deepcopy(garage['profile'])
    specs = profile['material_specs']
    # Validate before offsetting so crossed or folded edits cannot produce a cost.
    low = [min(p[k] for p in points) for k in (0, 1)]
    span = [max(p[k] for p in points) - low[k] for k in (0, 1)]
    validate_polygon([[p[k] - low[k] for k in (0, 1)] for p in points], span[0]+1, span[1]+1)
    offset_edges(points, [0] * len(points))
    substrate = offset_edges(points, [-bearing_inches/12] * len(points))
    for old_a, old_b, a, b in zip(points, points[1:]+points[:1], substrate, substrate[1:]+substrate[:1]):
        if sum((old_b[k]-old_a[k])*(b[k]-a[k]) for k in (0, 1)) <= 0:
            raise ValueError('Bearing consumes a slab jog; review its physical boundary')
    validate_polygon([[p[k]-low[k] for k in (0, 1)] for p in substrate], span[0]+1, span[1]+1)
    slab_sf = area(points)
    if not math.isclose(slab_sf, horizontal_band_area(points), abs_tol=1e-7):
        raise ValueError('Independent slab area check failed')
    profile['edge_roles'] = ['bearing'] * len(points)
    profile['slab_inches'] = thickness_inches
    specs['bearing_overlap_inches'] = bearing_inches
    specs.pop('footer_rebar_runs', None)
    profile['support_rules'].pop('footer', None)
    flat = material_coverage_cells(points, profile['edge_roles'], bearing_inches, 0)
    if not math.isclose(flat['net_sf'], area(substrate), abs_tol=1e-7):
        raise ValueError('Independent substrate coverage check failed')
    net_cy = slab_sf * thickness_inches / 12 / 27
    concrete = {'net_cy': net_cy, 'with_waste_cy': net_cy * (1+profile['waste_percent']/100)}
    rolls = {}
    for name, polygon, product, lap in [
        ('plastic', substrate, specs['vapor_product'], specs['vapor_lap_inches']),
        ('mesh', points, specs['mesh_product'], specs['mesh_lap_inches'])]:
        rolls[name] = roll_layout(polygon, product['width_ft'], product['length_ft'], lap)
    grid = rebar_grid(points, specs['rebar_grid_spacing_inches'], specs['rebar_grid_setback_inches'],
                      specs['rebar_grid_lap_inches'], specs['rebar_stock_length_ft'], balance_far_edge=True)
    gravel_cy = flat['net_sf'] * specs['gravel_depth_inches'] / 12 / 27
    porch = {'slab_sf': slab_sf, 'substrate_sf': flat['net_sf'], 'concrete': concrete,
             'substrate_coverage': {'flat': flat, 'gravel_in_place_cy': gravel_cy},
             'roll_layouts': rolls, 'rebar_grid': grid, 'thickened_edge_lf': 0}
    porch['purchase_materials'], porch['chair_allowances'] = material_allowances(points, profile, porch)
    old = garage['outputs']
    pooled = {'concrete_cy': whole_units(old['concrete']['with_waste_cy'] + concrete['with_waste_cy']),
              'concrete_with_waste_cy': old['concrete']['with_waste_cy'] + concrete['with_waste_cy']}
    pooled['gravel'] = gravel_truckloads(old['substrate_coverage']['gravel_in_place_cy']+gravel_cy,
                                        profile['gravel_delivery'])
    pooled['rolls'] = {}
    for name in ('plastic', 'mesh'):
        prior, added = old['roll_layouts'][name], rolls[name]
        if any(prior[k] != added[k] for k in ('roll_width_ft', 'roll_length_ft', 'lap_inches')):
            raise ValueError('Only matching roll products and laps can share stock')
        pooled['rolls'][name] = pack_cuts({
            'garage': [s['cut_length_ft'] for s in prior['strips']],
            'porch': [s['cut_length_ft'] for s in added['strips']]}, added['roll_length_ft'])
    pooled['grid'] = pack_cuts({name: [cut for segment in layout['segments'] for cut in segment['cuts_ft']]
                               for name, layout in [('garage', old['rebar_grid']), ('porch', grid)]},
                              specs['rebar_stock_length_ft'])
    pooled['chairs'] = {}
    for name in ('mesh', 'grid'):
        prior, added = old['chair_allowances'][name], porch['chair_allowances'][name]
        if prior['model'] != added['model'] or prior['pack_size'] != added['pack_size']:
            raise ValueError('Chair products must match before pooling')
        if added['special_height_count']:
            raise ValueError('Bearing slab needs an unresolved edge-chair layout')
        count = prior['standard_height_count'] + added['standard_height_count']
        pooled['chairs'][name] = {'count': count, 'packs': whole_units(count, prior['pack_size']),
                                  'pack_size': prior['pack_size'], 'model': prior['model']}
    return {'porch': porch, 'pooled': pooled, 'certified': False,
            'remaining': ['Additional bearing cap course and shared-wall ownership remain to calculate.',
                          'Porch broom-finish labor, steps, joints and exterior concrete specification remain separate.',
                          'Reinforcement placement, material delivery availability and quarry density require review.']}


def import_bearing_slab(draft, config, folder):
    """Replace shared purchase quantities, while retaining source garage budgets."""
    result = copy.deepcopy(draft)
    source = (folder/config['file']).resolve()
    if not source.is_relative_to(folder.resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != config['sha256']:
        raise ValueError('Bearing slab specification changed')
    spec = json.loads(source.read_bytes())
    if spec['plan_sha256'] != draft['plan_sha256']:
        raise ValueError('Bearing slab belongs to another plan')
    path = (folder/spec['job']).resolve()
    linked = next((r for r in draft.get('linked_quantity_reviews', []) if r['job'] == str(path)), None)
    if not linked:
        raise ValueError('Bearing slab needs its approved linked measurement review')
    rows = {r['row_id']: r for r in result['rows']+result.get('additional_cost_rows', [])}
    targets = spec['targets']
    labor_id = spec.get('labor_row_id')
    affected = list(targets.values()) + ([labor_id] if labor_id else [])
    if len(set(affected)) != len(affected):
        raise ValueError('Duplicate shared slab purchase owner')
    if any(identity not in rows for identity in affected):
        # Existing saved-trade protection withholds all garage extras after a geometry edit.
        if result.get('saved_trade_review_required'):
            return result
        raise ValueError('Missing shared slab purchase row')
    for identity in affected:
        row = rows[identity]
        if not row.get('saved_trade_budget') or row.get('line_cost') is not None or row.get('covered_by_package'):
            raise ValueError('Shared slab target is not an unpriced saved slab purchase')
    if labor_id:
        labor = rows[labor_id]
        if (labor.get('cost_type') not in ('LABOR', 'SUBCONTRACTOR') or labor.get('unit') not in ('ft2', 'sq ft', 'SF')
                or type(labor.get('draft_quantity')) not in (int, float)
                or not math.isfinite(labor['draft_quantity']) or labor['draft_quantity'] <= 0
                or spec.get('labor_rate_basis') != 'saved_garage_rate_extended_as_porch_allowance'):
            raise ValueError('Porch labor requires an explicit rate-extension allowance and measured garage SF')
        garage_labor_sf = labor['draft_quantity']
    snapshot = draft.get('slab_snapshot')
    if not snapshot:
        return result
    garage = json.loads((folder/spec['garage_snapshot']).read_bytes())
    if hashlib.sha256((folder/spec['garage_snapshot']).read_bytes()).hexdigest() != snapshot['sha256']:
        raise ValueError('Garage snapshot changed during pooling')
    state = MeasurementStore(path).read()
    current_geometry = hashlib.sha256(encode({k:geometry_digest(m) for k,m in state['measurements'].items()}).encode()).hexdigest()
    if state['version'] != linked['measurement_version'] or current_geometry != linked['geometry_sha256']:
        raise ValueError('Bearing slab changed during calculation; refresh the review')
    measurement = state['measurements'][spec['measurement_id']]
    record = {'kind': 'pooled_bearing_slab', 'linked_review': linked,
              'geometry_sha256': geometry_digest(measurement), 'source_sha256': config['sha256'],
              'source': str(source), 'certified': False}
    try:
        points = [[v/measurement['points_per_foot'] for v in p] for p in measurement['points']]
        quantities = calculate_bearing_slab(points, garage['construction'], spec['bearing_inches'], spec['thickness_inches'])
    except ValueError as error:
        for identity in affected:
            rows[identity]['draft_quantity'] = None
        result['bearing_slab_review'] = {'status': 'quantity_withheld', 'reason': str(error), **record}
        result.setdefault('pending_quantities', []).append({'id': 'bearing-slab-purchases',
            'label': 'Shared garage and porch purchases need a valid porch boundary',
            'remaining': [str(error)], 'template_rows': [rows[i].get('excel_row', i) for i in affected]})
        return result
    pool = quantities['pooled']
    values = {'concrete': pool['concrete_cy'], 'gravel': pool['gravel']['truckloads'],
              'plastic': pool['rolls']['plastic']['stock_count'], 'mesh': pool['rolls']['mesh']['stock_count'],
              'grid': pool['grid']['stock_count'], 'mesh_chairs': pool['chairs']['mesh']['packs'],
              'grid_chairs': pool['chairs']['grid']['packs']}
    if set(targets) != set(values):
        raise ValueError('Incomplete shared material ownership mapping')
    for name, identity in targets.items():
        row = rows[identity]
        row['draft_quantity'] = values[name]
        row.setdefault('quantity_sources', []).append({**record, 'material': name,
            'quantity': values[name], 'basis': 'Garage and porch combined before rounding; see bearing_slab_review cut schedules.'})
        row['certified'] = False
    if labor_id:
        porch_labor_sf = quantities['porch']['slab_sf']
        labor['draft_quantity'] = garage_labor_sf + porch_labor_sf
        labor.setdefault('quantity_sources', []).append({**record, 'kind': 'porch_labor_allowance',
            'quantity': porch_labor_sf, 'unit': 'SF',
            'basis': 'Add measured porch SF to garage labor once, with no material waste or purchase rounding. The saved garage labor rate is extended as an estimating allowance; a porch-specific quote is unverified.'})
        labor['certified'] = False
        quantities['labor_allowance'] = {'row_id': labor_id, 'garage_sf': garage_labor_sf,
            'porch_sf': porch_labor_sf, 'combined_sf': labor['draft_quantity'],
            'porch_rate_owner_confirmed': False, 'porch_quote_verified': False,
            'basis': spec['labor_rate_basis']}
        quantities['remaining'][1] = ('Porch finishing labor uses the saved garage rate as an estimating allowance; '
            'the porch-specific quote, joints and exterior concrete specification remain unverified. '
            'Steps are owned by their separate scope.')
    result['bearing_slab_review'] = {**quantities, **record, 'status': 'estimating_quantities',
                                    'source_garage_budget_preserved': True}
    result.update(whole_house_total=None, estimate_released=False)
    return result
