"""Whole-stock head caps from supplier frame dimensions, with included parts credited.

This is a purchasing quantity study. Unquoted products and installation/profile
assumptions remain explicit; a cutting schedule is not a complete window price.
"""
import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from linear_stock import pack_sawn_cuts


def head_cap_takeoff(assemblies, frames, products, kerf_in):
    def indexed(items, key):
        result = {item[key]: item for item in items}
        if not result or len(result) != len(items) or any(not k for k in result):
            raise ValueError('Unique nonempty head-cap identities required')
        return result

    members = indexed(assemblies, 'opening_id')
    dimensions = indexed(frames, 'opening_id')
    stocks = indexed(products, 'part_number')
    if members.keys() != dimensions.keys():
        raise ValueError('Head-cap frames must cover every supplier opening exactly once')
    for product in products:
        length = product.get('length_in')
        if type(length) not in (int, float) or not math.isfinite(length) or length <= 0:
            raise ValueError('Positive finite head-cap stock lengths required')
    if len({p.get('profile') for p in products}) != 1 or not products[0].get('profile'):
        raise ValueError('Head-cap stocks must share one identified profile')
    pieces = []; included = []; references = []
    for identity, opening in members.items():
        frame = dimensions[identity]
        width = frame.get('frame_width_in')
        rough = opening.get('rough_opening_width_in')
        count = opening['assembly_quantity']
        if (type(count) is not int or count <= 0
                or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (width, rough))
                or width >= rough or frame.get('rough_opening_width_in') != rough
                or frame.get('supplier_line') != opening.get('supplier_line')
                or frame.get('specification_page') != opening.get('specification_page')):
            raise ValueError('Head-cap frame dimensions do not match the supplier schedule')
        credited = frame.get('included_quantity', 0)
        if type(credited) is not int or not 0 <= credited <= count:
            raise ValueError('Included cap quantity cannot exceed assembly quantity')
        if credited:
            part = stocks.get(frame.get('included_part_number'))
            if part is None or part['length_in'] < width or not frame.get('inclusion_reference'):
                raise ValueError('Included cap requires an identified fitting part and source reference')
            included.append({'opening_id': identity, 'quantity': credited,
                             'part_number': part['part_number'], 'reference': frame['inclusion_reference']})
        fitting = [p for p in products if p['length_in'] >= width]
        if not fitting:
            raise ValueError('No continuous head-cap stock fits opening ' + identity)
        stock = min(fitting, key=lambda p: (p['length_in'], p['part_number']))
        references.append({'opening_id': identity, 'frame_width_in': width,
                           'assembly_quantity': count, 'included_quantity': credited,
                           'new_cut_quantity': count - credited})
        for n in range(count - credited):
            pieces.append({'id': f'{identity}-{n+1}', 'opening_id': identity,
                           'sku': stock['part_number'], 'stock_length_ft': stock['length_in']/12,
                           'cut_inches': width})
    boards = pack_sawn_cuts(pieces, kerf_in)
    counts = Counter(b['sku'] for b in boards)
    return {'status': 'conditional_estimating_quantity', 'openings': references,
            'included_caps': included, 'cuts': pieces, 'stocks': boards,
            'purchases': [{'part_number': p['part_number'], 'length_in': p['length_in'],
                           'quantity': counts[p['part_number']], 'unit': 'each', 'unit_price': None}
                          for p in products],
            'head_locations': sum(a['assembly_quantity'] for a in assemblies),
            'new_head_locations': len(pieces),
            'net_new_length_in': math.fsum(p['cut_inches'] for p in pieces),
            'purchased_length_in': math.fsum(b['length_ft']*12 for b in boards),
            'kerf_in': kerf_in, 'complete_cost': None, 'optimality_proven': False,
            'order_released': False, 'installation_approved': False}


def apply_window_head_caps(draft, source_file, saved, mapping):
    root = Path(source_file).parent.resolve()
    observed = {}

    def checked(ref):
        path = (root / ref['file']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Head-cap source is missing or outside the job')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('Head-cap source changed')
        observed[path] = raw
        return path, raw

    path, raw = checked(mapping)
    basis = json.loads(raw)
    if (basis.get('plan_sha256') != draft['plan_sha256']
            or basis.get('status') != 'estimating_allowance'
            or not basis.get('assumptions') or not basis.get('remaining')):
        raise ValueError('Head caps require a matching plan and explicit allowance limits')
    schedule = saved['material_schedule']
    if basis.get('specification_sha256') != schedule['specification_sha256']:
        raise ValueError('Head-cap specification does not match the window schedule')
    if not basis.get('documents'):
        raise ValueError('Head caps require source documents')
    for document in basis['documents']:
        checked(document)
    if not any(d['sha256'] == schedule['specification_sha256'] for d in basis['documents']):
        raise ValueError('Head caps require the original supplier specification')
    result = head_cap_takeoff(schedule['assemblies'], basis['frames'], basis['products'], basis['kerf_in'])
    result.update(assumptions=copy.deepcopy(basis['assumptions']), remaining=copy.deepcopy(basis['remaining']),
                  source={'file': str(path), 'sha256': mapping['sha256'],
                          'specification_sha256': schedule['specification_sha256'],
                          'documents': copy.deepcopy(basis['documents'])})
    if any(p.read_bytes() != original for p, original in observed.items()):
        raise ValueError('Head-cap source changed during calculation')
    if 'window_head_cap_review' in draft:
        raise ValueError('Duplicate window head-cap scope')
    draft['window_head_cap_review'] = result

