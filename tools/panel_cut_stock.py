"""Conservative rectangular-blank reuse; not an optimal nesting or installation check."""
import math


def allocate(rectangles, width, height, kerf, allow_rotation=False):
    """Use one unit consistently. Irregular parts must supply enclosing rectangles."""
    def number(v, zero=False):
        return type(v) in (int, float) and math.isfinite(v) and (v >= 0 if zero else v > 0)
    if not number(width) or not number(height) or not number(kerf, True):
        raise ValueError('Stock dimensions and kerf must be finite and valid')
    ids = [r['id'] for r in rectangles]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError('Cut identities must be unique nonempty strings')
    if any(not number(r['width']) or not number(r['height']) for r in rectangles):
        raise ValueError('Cut dimensions must be finite and positive')
    sheets = []; placements = []
    for part in sorted(rectangles, key=lambda r: (-r['width']*r['height'], r['id'])):
        orientations = [(part['width'], part['height'], False)]
        if allow_rotation:orientations.append((part['height'], part['width'], True))
        orientations = [v for v in orientations if v[0] <= width+1e-8 and v[1] <= height+1e-8]
        if not orientations:raise ValueError('Cut does not fit stock: '+part['id'])
        choices = []
        for si, spaces in enumerate(sheets):
            for fi, (x, y, w, h) in enumerate(spaces):
                for pw, ph, rotated in orientations:
                    if pw <= w+1e-8 and ph <= h+1e-8:
                        choices.append((w*h-pw*ph, si, fi, pw, ph, rotated))
        if not choices:
            sheets.append([(0, 0, width, height)])
            choices = [(width*height-pw*ph, len(sheets)-1, 0, pw, ph, rot)
                       for pw, ph, rot in orientations]
        _, si, fi, pw, ph, rotated = min(choices)
        x, y, w, h = sheets[si].pop(fi)
        # Separate right and upper remnants: they never overlap each other.
        if w-pw-kerf > 1e-8:sheets[si].append((x+pw+kerf, y, w-pw-kerf, ph))
        if h-ph-kerf > 1e-8:sheets[si].append((x, y+ph+kerf, w, h-ph-kerf))
        placements.append({'id': part['id'], 'sheet': si+1, 'rotated': rotated,
                           'bounds': [x, y, x+pw, y+ph]})
    return {'sheet_count': len(sheets), 'placements': placements,
            'stock_width': width, 'stock_height': height, 'kerf': kerf,
            'optimal': False, 'installation_verified': False}
