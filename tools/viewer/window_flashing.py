"""Whole-roll flashing allowances from assembled openings and explicit cut rules."""
import copy
import hashlib
import json
import math
from pathlib import Path
from linear_stock import pack_cuts


def flashing_takeoff(assemblies, rule):
    fields = ('roll_length_ft', 'tape_width_in', 'sill_upturn_in',
              'jamb_extension_in', 'head_extension_in', 'corner_piece_in')
    if any(type(rule.get(k)) not in (int, float) or not math.isfinite(rule[k])
           or rule[k] <= 0 for k in fields):
        raise ValueError('Flashing needs positive finite product and cut dimensions')
    if rule['head_extension_in'] < rule['tape_width_in']:
        raise ValueError('Head strip must cover the side-strip width')
    cuts = []; seen = set(); perimeter = 0
    for opening in assemblies:
        identity = opening['opening_id']; count = opening['assembly_quantity']
        width = opening.get('rough_opening_width_in')
        height = opening.get('rough_opening_height_in')
        if not identity or identity in seen or type(count) is not int or count <= 0:
            raise ValueError('Unique openings and positive whole assembly counts required')
        seen.add(identity)
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
               for v in (width, height)):
            raise ValueError('Flashing needs positive finite opening dimensions')
        perimeter += 2 * (width + height) / 12 * count
        for instance in range(1, count + 1):
            for name, length in (
                ('sill', width + 2 * rule['sill_upturn_in']),
                ('left', height + 2 * rule['jamb_extension_in']),
                ('right', height + 2 * rule['jamb_extension_in']),
                ('head', width + 2 * rule['head_extension_in']),
                ('corner-left', rule['corner_piece_in']),
                ('corner-right', rule['corner_piece_in'])):
                cuts.append({'run_id': f'{identity}-{instance}-{name}',
                             'piece': 1, 'length_ft': length / 12})
    if not cuts:
        raise ValueError('Flashing needs at least one opening')
    packing = pack_cuts(cuts, rule['roll_length_ft'])
    return {'rough_opening_perimeter_ft': perimeter, 'cuts': cuts,
            'cut_length_ft': math.fsum(c['length_ft'] for c in cuts),
            'packing': packing, 'quantity': packing['quantity']}


def apply_window_flashing(draft, source_file, saved, mapping):
    """Called after the bridge has checked the window specification and membership."""
    root = Path(source_file).parent.resolve()

    def checked(item):
        path = (root / item['file']).resolve()
        if (not path.is_relative_to(root) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']):
            raise ValueError('Window flashing evidence missing, changed or outside job')
        return path

    basis_file = checked(mapping)
    basis = json.loads(basis_file.read_bytes())
    if (basis.get('plan_sha256') != draft['plan_sha256']
            or basis.get('status') != 'estimating_allowance'
            or not basis.get('basis') or not basis.get('assumptions')
            or not basis.get('remaining') or not basis.get('documents')):
        raise ValueError('Flashing allowance needs a matching plan and explicit limitations')
    for document in basis['documents']:
        checked(document)
    targets = [r for r in draft['rows'] if r['row_id'] == mapping['row_id']]
    if len(targets) != 1:
        raise ValueError('Flashing target must be unique')
    row = targets[0]
    if (row['unit'] != 'roll' or row['cost_type'] != 'MATERIAL'
            or row.get('draft_quantity') is not None or row.get('line_cost') is not None
            or row.get('quantity_sources') or row.get('assembly_inputs')
            or row.get('covered_by_package') or row.get('cost_owner_row_id')
            or row.get('completion_status', '').startswith('not_applicable')):
        raise ValueError('Flashing target is incompatible or already assigned')
    takeoff = flashing_takeoff(saved['material_schedule']['assemblies'], basis['cut_rule'])
    row['draft_quantity'] = takeoff['quantity']
    row.setdefault('quantity_sources', []).append({
        'kind': 'window_flashing_estimating_allowance', 'quantity': takeoff['quantity'],
        'unit': 'roll', 'basis': basis['basis'], 'assumptions': basis['assumptions'],
        'remaining': basis['remaining'], 'product': basis['product'],
        'cut_rule': copy.deepcopy(basis['cut_rule']), **takeoff,
        'source': {'file': str(basis_file), 'sha256': mapping['sha256'],
                   'schedule_file': str(source_file),
                   'schedule_sha256': hashlib.sha256(Path(source_file).read_bytes()).hexdigest(),
                   'documents': copy.deepcopy(basis['documents'])},
        'certified': False, 'order_released': False})
    row['certified'] = False
    return draft
