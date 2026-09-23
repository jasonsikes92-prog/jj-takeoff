"""Detect positive-area overlap between simple polygons in one drawing view."""


def overlaps(first, second):
    edges = lambda p: list(zip(p, p[1:] + p[:1]))
    a_edges, b_edges = edges(first), edges(second)
    levels = {p[1] for p in first + second}
    cross = lambda a, b: a[0]*b[1] - a[1]*b[0]
    for a, b in a_edges:
        r = [b[i]-a[i] for i in range(2)]
        for c, d in b_edges:
            s = [d[i]-c[i] for i in range(2)]
            denominator = cross(r, s)
            if abs(denominator) < 1e-12:
                continue
            offset = [c[i]-a[i] for i in range(2)]
            t, u = cross(offset, s)/denominator, cross(offset, r)/denominator
            if 0 < t < 1 and 0 < u < 1:
                levels.add(a[1] + t*r[1])

    def intervals(segments, y):
        xs = sorted(a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
                    for a, b in segments if min(a[1], b[1]) < y < max(a[1], b[1]))
        return list(zip(xs[::2], xs[1::2]))

    levels = sorted(levels)
    for low, high in zip(levels, levels[1:]):
        if high-low <= 1e-9:
            continue
        y = (low+high)/2
        for a, b in intervals(a_edges, y):
            for c, d in intervals(b_edges, y):
                if min(b, d)-max(a, c) > 1e-9:
                    return True
    return False


def overlapping_measurements(measurements, projected=False):
    reference = measurements[0]
    for measurement in measurements:
        if (measurement['kind'] != 'area' or (not projected and measurement.get('surface_factor', 1) != 1) or
                any(measurement[k] != reference[k] for k in ('page', 'points_per_foot', 'width_pt', 'height_pt'))):
            raise ValueError('Disjoint areas require compatible polygons in the same calibrated drawing view; sloped surfaces need projected overlap review')
    return [[a['id'], b['id']] for i, a in enumerate(measurements) for b in measurements[i+1:]
            if overlaps(a['points'], b['points'])]
