"""Reserve stock for upper-opening field studs using explicit height bounds."""
import math
from linear_stock import pack_sawn_cuts


def calculate(field, openings, stock, top_plates_inches=3):
    scale = field['points_per_foot']
    dimensions = [scale, top_plates_inches, stock['length_inches']]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in dimensions):
        raise ValueError('Positive finite scale, plates and stock dimensions required')
    stations = field['field_studs'] + field['reserved_stations']
    if len({s['id'] for s in stations}) != len(stations):
        raise ValueError('Duplicate field station')
    pieces, pending, reviewed, seen, used = [], [], [], set(), set()
    for opening in openings:
        identity = opening['id']
        if identity in seen:
            raise ValueError('Opening counted twice')
        seen.add(identity)
        dimensions = [opening[k] for k in ('wall_top_inches', 'minimum_head_inches', 'header_depth_inches')]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in dimensions):
            raise ValueError('Positive finite wall, head and header dimensions required')
        points = opening['points']
        if len(points) != 2 or any(len(p) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in p) for p in points):
            raise ValueError('Finite straight opening span required')
        a, b = points
        axis = 0 if abs(a[1] - b[1]) < 1e-6 else 1
        if abs(a[1-axis] - b[1-axis]) >= 1e-6 or a == b:
            raise ValueError('Orthogonal nonzero opening required')
        runs = {z['run'] for z in field['zones'] if z['assembly'] == identity}
        if len(runs) != 1:
            pending.append({'id': identity, 'reason': 'Opening needs one reviewed wall run'})
            continue
        run = next(iter(runs))
        maximum = opening['wall_top_inches'] - top_plates_inches - opening['minimum_head_inches'] - opening['header_depth_inches']
        if maximum <= 0:
            pending.append({'id': identity, 'reason': 'No positive upper-member height; resolve header arrangement'})
            continue
        low, high = sorted(p[axis] for p in points)
        selected = []
        for station in stations:
            if station['run'] != run or not low + scale/16 <= station['along_pt'] <= high - scale/16:
                continue
            if abs(station['point_pt'][1-axis] - a[1-axis]) > 1e-6:
                raise ValueError('Opening and field station are not on the same wall')
            if station['assembly_owners'] != [identity]:
                pending.append({'id': identity + ':' + station['id'], 'reason': 'Overlapping assembly ownership needs review'})
                continue
            if station['id'] in used:
                raise ValueError('Upper station counted twice')
            used.add(station['id'])
            selected.append(station['id'])
            pieces.append({'id': 'above:' + identity + ':' + station['id'], 'opening_id': identity,
                'station_id': station['id'], 'run': run, 'point_pt': station['point_pt'],
                'maximum_cut_inches': maximum, 'cut_inches': math.ceil(maximum*8-1e-8)/8,
                'sku': stock['sku'], 'stock_length_ft': stock['length_inches']/12})
        reviewed.append({'opening_id': identity, 'run': run, 'station_ids': selected,
            'member_count': len(selected), 'maximum_cut_inches': maximum,
            'minimum_head_inches': opening['minimum_head_inches'], 'header_depth_inches': opening['header_depth_inches'],
            'wall_top_inches': opening['wall_top_inches']})
    boards = pack_sawn_cuts(pieces, .125)
    return {'openings': reviewed, 'pieces': pieces, 'boards': boards, 'pending': pending,
        'member_count': len(pieces), 'candidate_whole_sticks': len(boards),
        'kerf_inches': .125, 'cut_rounding_inches': .125, 'installed_cut_lengths_verified': False,
        'cross_scope_offcut_credit': False, 'optimality_proven': False, 'order_released': False}
