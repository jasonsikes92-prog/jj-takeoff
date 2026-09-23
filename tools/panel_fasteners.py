"""Draft perimeter and field fastener locations, in the geometry's units."""
import math
from shapely.geometry import Point


def positions(polygon, spacing, inset):
    if (not polygon.is_valid or polygon.geom_type != 'Polygon' or polygon.area <= 0
            or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in (spacing, inset))):
        raise ValueError('Valid polygon, spacing and edge inset required')
    inner = polygon.buffer(-inset, join_style='mitre').simplify(1e-9, preserve_topology=True)
    if inner.is_empty or inner.geom_type != 'Polygon':
        return {'points': [], 'count': None, 'needs_review': ['Cut cannot retain one connected fastener field at the selected inset.']}
    points = {}; reviews = []
    def add(x, y, role):
        key = (round(x, 8), round(y, 8))
        points.setdefault(key, {'x': x, 'y': y, 'role': role})
    for ring in [inner.exterior, *inner.interiors]:
        coords = list(ring.coords)
        for a, b in zip(coords, coords[1:]):
            n = max(1, math.ceil(math.dist(a, b)/spacing))
            for i in range(n):
                add(a[0]+(b[0]-a[0])*i/n, a[1]+(b[1]-a[1])*i/n, 'perimeter')
    x0, y0, x1, y1 = inner.bounds
    nx = max(1, math.ceil((x1-x0)/spacing)); ny = max(1, math.ceil((y1-y0)/spacing))
    for ix in range(1, nx):
        for iy in range(1, ny):
            x = x0+(x1-x0)*ix/nx; y = y0+(y1-y0)*iy/ny
            if inner.contains(Point(x, y)):add(x, y, 'field')
    for item in points.values():
        p = Point(item['x'], item['y'])
        assert polygon.covers(p) and polygon.boundary.distance(p) >= inset-1e-7
        item['edge_distance'] = polygon.boundary.distance(p)
    if polygon.interiors or len(polygon.exterior.coords) > 5:
        reviews.append('Irregular cut: review field coverage and corner fastener placement.')
    return {'points': list(points.values()), 'count': len(points), 'needs_review': reviews}
