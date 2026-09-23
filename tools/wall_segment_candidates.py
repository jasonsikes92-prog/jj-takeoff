"""Extract editable filled wall-strip candidates without assigning structural scope."""
import hashlib
import json
import math

METHOD = 'native_filled_wall_rectangles_v1'


def rectangle_bounds(drawing):
    """Require the actual four rectangle edges, not just a path's bounding box."""
    items = drawing['items']
    if len(items) == 1 and items[0][0] == 're':
        return list(items[0][1])
    if len(items) != 4 or any(item[0] != 'l' for item in items):
        return None
    point = lambda p: (round(p.x, 4), round(p.y, 4))
    x0, y0, x1, y1 = drawing['rect']
    corners = [(round(x0,4),round(y0,4)), (round(x1,4),round(y0,4)),
               (round(x1,4),round(y1,4)), (round(x0,4),round(y1,4))]
    expected = {frozenset((corners[i], corners[(i+1)%4])) for i in range(4)}
    actual = {frozenset((point(item[1]), point(item[2]))) for item in items}
    return [x0,y0,x1,y1] if len(expected) == 4 and actual == expected else None


def candidates(page, points_per_foot):
    if isinstance(points_per_foot, bool) or not math.isfinite(points_per_foot) or points_per_foot <= 0:
        raise ValueError('Positive finite calibrated scale required')
    found = {}
    for index, drawing in enumerate(page.get_drawings()):
        fill = drawing.get('fill')
        if fill is None or min(fill) >= .99 or drawing.get('fill_opacity', 1) <= 0:
            continue
        bounds = rectangle_bounds(drawing)
        if bounds is None:
            continue
        x0,y0,x1,y1 = bounds
        width,height = x1-x0,y1-y0
        thickness = min(width,height)/points_per_foot*12
        # Search envelope only; this does not specify a wall's actual stud size.
        if not 2.5 <= thickness <= 6.0:
            continue
        key = json.dumps([page.number+1, [round(v,6) for v in bounds]])
        if key in found:
            found[key]['source_cad_paths'].append(index)
            continue
        square = max(width,height)/min(width,height) < 1.25
        orientation = 'unresolved_short_piece' if square else 'horizontal' if width>height else 'vertical'
        if square:
            points = [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        elif width>height:
            points = [[x0,(y0+y1)/2],[x1,(y0+y1)/2]]
        else:
            points = [[(x0+x1)/2,y0],[(x0+x1)/2,y1]]
        found[key] = {
            'id':'wall-candidate-'+hashlib.sha256(key.encode()).hexdigest()[:16],
            'label':f'Wall {"short piece" if square else "segment"} candidate {len(found)+1}',
            'page':page.number+1, 'kind':'area' if square else 'length', 'points':points,
            'points_per_foot':points_per_foot, 'width_pt':page.rect.width,'height_pt':page.rect.height,
            'color':'#b45309' if square else '#0e7490', 'dependent_rows':[],
            'source_method':METHOD, 'source_cad_paths':[index], 'source_bounds_pt':bounds,
            'source_fill_rgb':list(fill), 'drawn_thickness_inches':thickness,
            'orientation':orientation, 'certified':False,
            'scope_status':'Unreviewed native wall-strip candidate; classify wall, jamb, column or other object before using it',
        }
    measurements = list(found.values())
    return {'method':METHOD, 'measurements':measurements,
        'length_candidates':sum(m['kind']=='length' for m in measurements),
        'short_piece_candidates':sum(m['kind']=='area' for m in measurements),
        'search_thickness_inches':[2.5,6.0], 'coverage_certified':False,
        'limitations':[
            'Only filled axis-aligned rectangles within the stated thickness envelope are detected; curved, diagonal, outlined and compound walls can be missed.',
            'A rectangle is not proof of wall meaning. Review source objects, redlines, wall height, openings, shared corners and duplicate/overlapping segments.',
            'Short square pieces retain their outline; no horizontal or vertical run direction is invented.',
            'Visible pieces exclude opening gaps. They are not complete wall runs, room boundaries or a stud/plate order. No lengths are summed or priced.']}
