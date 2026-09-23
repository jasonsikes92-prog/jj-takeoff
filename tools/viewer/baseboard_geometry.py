"""Measure wall-face base runs; cabinet fronts and door returns are separate scopes."""
import math
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from measurement_store import calculate


def baseboard_runs(state, room_ids, passages, finish_inches, obstruction_state, obstruction_ids):
    if state['plan_sha256'] != obstruction_state['plan_sha256']:
        raise ValueError('Baseboard sources must use the same plan')
    if (not room_ids or len(set(room_ids)) != len(room_ids)
            or len(set(obstruction_ids)) != len(obstruction_ids)
            or type(finish_inches) not in (int, float)
            or not math.isfinite(finish_inches) or not 0 < finish_inches < 6):
        raise ValueError('Baseboard needs unique rooms/footprints and a positive finish thickness')
    first = state['measurements'][room_ids[0]]
    scale, page = first['points_per_foot'], first['page']

    def shape(source, identity, kind):
        measurement = source['measurements'][identity]
        if (measurement['kind'] != kind or measurement['page'] != page
                or measurement.get('surface_factor', 1) != 1
                or not math.isclose(measurement['points_per_foot'], scale, rel_tol=1e-12)):
            raise ValueError('Baseboard sources require one calibrated flat sheet')
        calculate(measurement)
        return Polygon(measurement['points']) if kind == 'area' else LineString(measurement['points'])

    rooms = {identity: shape(state, identity, 'area') for identity in room_ids}
    if not math.isclose(unary_union(list(rooms.values())).area,
                        math.fsum(p.area for p in rooms.values()), abs_tol=1e-7):
        raise ValueError('Baseboard room contours overlap')
    footprints = {identity: shape(obstruction_state, identity, 'area') for identity in obstruction_ids}
    footprint_union = unary_union(list(footprints.values()))
    gaps = {identity: [] for identity in room_ids}
    seen = set()
    for passage in passages:
        identity = passage['measurement_id']
        if identity in seen:
            raise ValueError('Baseboard door identities must be unique')
        seen.add(identity)
        line = shape(state, identity, 'length')
        sides = passage['sides']
        if (len(line.coords) != 2 or len(sides) != 2
                or sorted(s['side'] for s in sides) != [-1, 1]
                or sides[0]['room_id'] == sides[1]['room_id']
                or any(s['room_id'] is not None and s['room_id'] not in rooms for s in sides)):
            raise ValueError('Baseboard doors need two distinct adjacent room sides')
        (x0, y0), (x1, y1) = line.coords
        vertical = math.isclose(x0, x1, abs_tol=1e-7)
        horizontal = math.isclose(y0, y1, abs_tol=1e-7)
        if vertical == horizontal:
            raise ValueError('Baseboard door gaps must be horizontal or vertical')
        a, b = sorted([y0, y1] if vertical else [x0, x1])
        center = x0 if vertical else y0
        for side in sides:
            if side['room_id'] is None:
                continue
            low, high = sorted([center, center + side['side'] * scale * .5])
            mask = box(low, a, high, b) if vertical else box(a, low, b, high)
            room = rooms[side['room_id']]
            if mask.intersection(room).area <= 1e-8:
                raise ValueError('Baseboard door no longer meets its assigned room')
            gaps[side['room_id']].append((identity, mask))

    result = []
    for identity, raw in rooms.items():
        finished = raw.buffer(-finish_inches / 12 * scale, join_style='mitre')
        if finished.geom_type != 'Polygon' or finished.interiors or finished.area <= 0:
            raise ValueError('Baseboard finish face must remain one simple room')
        wall = finished.boundary
        gap_union = unary_union([mask for _, mask in gaps[identity]])
        after_doors = wall.difference(gap_union)
        retained = after_doors.difference(footprint_union)
        pieces = [retained] if retained.geom_type == 'LineString' else list(retained.geoms)
        segments = [{'points': [list(p) for p in piece.coords], 'length_lf': piece.length / scale}
                    for piece in pieces if piece.geom_type == 'LineString' and piece.length > 1e-8]
        row = {'room_id': identity, 'framing_perimeter_lf': raw.length / scale,
               'finish_perimeter_lf': wall.length / scale,
               'door_gap_lf': (wall.length - after_doors.length) / scale,
               'fixed_footprint_lf': (after_doors.length - retained.length) / scale,
               'remaining_wall_run_lf': retained.length / scale, 'segments': segments,
               'door_ids': [key for key, _ in gaps[identity]],
               'footprint_contacts': [{'id': key, 'length_lf': after_doors.intersection(value).length / scale}
                                      for key, value in footprints.items()
                                      if after_doors.intersection(value).length > 1e-8]}
        if not math.isclose(sum(p['length_lf'] for p in segments), row['remaining_wall_run_lf'], abs_tol=1e-7):
            raise ValueError('Baseboard segments do not reconcile')
        result.append(row)
    return {'rooms': result, 'remaining_wall_run_lf': math.fsum(r['remaining_wall_run_lf'] for r in result),
            'room_measurement_version': state['version'], 'obstruction_measurement_version': obstruction_state['version'],
            'finish_thickness_inches': finish_inches, 'overlapping_deductions_counted_once': True,
            'final_installed_quantity': None, 'purchase_quantity': None,
            'remaining': ['Casing widths and returns beyond the drawn door gaps',
                          'Unmapped fixed cabinetry, wet finishes and fireplace finish transitions',
                          'Garage trim scope', 'Stock lengths, cuts, joints and waste']}
