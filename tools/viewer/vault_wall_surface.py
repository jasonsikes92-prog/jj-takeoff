"""Measure upper wall surfaces beneath an explicitly sourced symmetric vault.

The polygon is the horizontal room boundary. This calculates geometry above
equal-height low sides, not drywall applicability or the walls below that datum.
"""
import math

from measurement_store import calculate


def vault_upper_wall_area(boundary, transverse_direction, pitch_rise, pitch_run, pitch_source):
    if boundary['kind'] != 'area':
        raise ValueError('Vault wall calculation requires a closed room boundary')
    calculate(boundary)  # Apply the editor's geometry and scale validation.
    if (not isinstance(transverse_direction, (list, tuple)) or len(transverse_direction) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in transverse_direction)):
        raise ValueError('Identify the plan direction across the vault')
    magnitude = math.hypot(*transverse_direction)
    if magnitude == 0:
        raise ValueError('Vault transverse direction cannot be zero')
    if (any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (pitch_rise, pitch_run))
            or not isinstance(pitch_source, str) or not pitch_source.strip()):
        raise ValueError('Vault needs a positive pitch and source')
    direction = [v / magnitude for v in transverse_direction]
    points, scale = boundary['points'], boundary['points_per_foot']
    origin = points[0]
    positions = [math.fsum((p[i] - origin[i]) * direction[i] for i in (0, 1)) / scale for p in points]
    low, high = min(positions), max(positions)
    span = high - low
    if span <= 0:
        raise ValueError('Vault has no transverse span')
    ridge = (low + high) / 2
    slope = pitch_rise / pitch_run
    height = lambda position: max(0.0, min(position - low, high - position) * slope)
    edges = []
    for index, start in enumerate(points):
        end_index = (index + 1) % len(points)
        end = points[end_index]
        a, b = positions[index], positions[end_index]
        length = math.dist(start, end) / scale
        cuts = [0.0, 1.0]
        if min(a, b) < ridge < max(a, b):
            cuts.insert(1, (ridge - a) / (b - a))
        # Split where the sloping height changes direction. Averaging only the
        # endpoints would give zero area for a full gable running across the ridge.
        area = math.fsum(length * (v - u) * (height(a + (b-a)*u) + height(a + (b-a)*v)) / 2
                         for u, v in zip(cuts, cuts[1:]))
        edges.append({'edge_index':index, 'start_pt':list(start), 'end_pt':list(end),
            'length_lf':length, 'start_height_above_low_side_ft':height(a),
            'end_height_above_low_side_ft':height(b), 'upper_wall_sf':area})
    return {'transverse_span_ft':span, 'rise_above_low_sides_ft':span * slope / 2,
        'transverse_direction':direction, 'pitch_rise':pitch_rise, 'pitch_run':pitch_run,
        'pitch_source':pitch_source, 'edges':edges,
        'gross_upper_wall_sf':math.fsum(e['upper_wall_sf'] for e in edges),
        'finish_scope_confirmed':False, 'low_side_height_ft':None,
        'purchase_quantity':None, 'estimate_released':False}
