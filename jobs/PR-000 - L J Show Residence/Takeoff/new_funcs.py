

# =====================================================================================
# ELEVATION-FIRST COUNTING + RECONCILIATION  (cal #55, L J Show Residence, 7/31/26)
# Built after I shipped 22 windows against Jason's 46. I HAD the right evidence -- my own
# elevation scan found 53 tagged openings -- and shipped the FLOOR-PLAN tag count anyway.
# Jason's takeoff counts openings with point markers ON THE ELEVATIONS, sheet by sheet.
# These functions make the plan-only count impossible to ship.
# =====================================================================================

_OPENING_TAG = _re.compile(r'^\(?(\d)\)?(\d{2})(\d{2})(FX|SH|PT|TR|CS|AW)?$', _re.I)


def parse_opening_tag(tag):
    """J&J opening tag -> dict. '3060SH' = 3'0" wide x 6'0" high single-hung.
    '(2)3060SH' = a mulled pair (2 lites). Returns None if it is not an opening tag.
    Door tags carry no FX/SH/PT suffix and are >= 6'8" tall -- classified 'door'."""
    s = str(tag).strip()
    m = _OPENING_TAG.match(s)
    if not m:
        return None
    mull = 2 if s.startswith('(2)') else 1
    wf, wi, hf = int(m.group(1)), int(m.group(2)), int(m.group(3))
    suffix = (m.group(4) or '').upper()
    width_ft = wf + wi / 12.0
    height_ft = float(hf)
    kind = 'window' if suffix else ('door' if height_ft >= 6.5 else 'window')
    return {'tag': s, 'width_ft': round(width_ft, 3), 'height_ft': round(height_ft, 3),
            'lites': mull, 'suffix': suffix, 'kind': kind,
            'perimeter_lf': round(2 * (width_ft + height_ft), 2)}


def elevation_opening_count(doc, elevation_pages, floor_plan_page=None, tolerance_pct=20.0):
    """COUNT OPENINGS ON THE ELEVATIONS, then reconcile against the floor plan.

    `elevation_pages` = [(page_index, 'label', fitz.Rect|None), ...] -- EVERY elevation
    sheet, not a sample. Returns windows/doors counted per elevation plus the opening
    trim LF that follows from the same count (sum of each opening's perimeter).

    ok=False when the plan and elevation counts disagree by more than tolerance_pct, or
    when no elevation page was supplied.  Never returns a plan-only count as authoritative
    -- that is the exact failure this exists to stop (cal #55: shipped 22 vs a true 46)."""
    import fitz as _fitz

    def _tags(page, clip):
        seen, out = [], []
        for w in page.get_text('words'):
            cx, cy = (w[0] + w[2]) / 2.0, (w[1] + w[3]) / 2.0
            if clip is not None and not (clip.x0 <= cx <= clip.x1 and clip.y0 <= cy <= clip.y1):
                continue
            p = parse_opening_tag(w[4])
            if not p:
                continue
            if any(abs(cx - a) < 2.0 and abs(cy - b) < 2.0 for a, b in seen):
                continue          # the sheets draw every tag twice
            seen.append((cx, cy))
            out.append(p)
        return out

    per_elev, all_open = [], []
    for spec in (elevation_pages or []):
        pi, label = spec[0], spec[1]
        clip = spec[2] if len(spec) > 2 else None
        got = _tags(doc[pi], clip)
        per_elev.append({
            'page': pi, 'label': label,
            'windows': sum(g['lites'] for g in got if g['kind'] == 'window'),
            'doors': sum(1 for g in got if g['kind'] == 'door'),
            'trim_lf': round(sum(g['perimeter_lf'] * g['lites'] for g in got if g['kind'] == 'window'), 1),
        })
        all_open.extend(got)

    elev_windows = sum(e['windows'] for e in per_elev)
    elev_doors = sum(e['doors'] for e in per_elev)
    trim_lf = round(sum(e['trim_lf'] for e in per_elev), 1)

    plan_windows = plan_doors = None
    if floor_plan_page is not None:
        pg = _tags(doc[floor_plan_page], None)
        plan_windows = sum(g['lites'] for g in pg if g['kind'] == 'window')
        plan_doors = sum(1 for g in pg if g['kind'] == 'door')

    errors = []
    if not per_elev:
        errors.append('no elevation pages supplied -- opening counts must come off the '
                      'ELEVATIONS; a floor-plan tag count is never authoritative')
    if plan_windows is not None and elev_windows:
        d = abs(elev_windows - plan_windows) / float(elev_windows) * 100.0
        if d > tolerance_pct:
            errors.append(
                'window count disagrees: elevations %d vs floor plan %d (%.0f%%). '
                'Reconcile before pricing -- the elevations show every opening, the plan '
                'tags routinely miss transoms, mulled lites and gable windows.'
                % (elev_windows, plan_windows, d))
    return {
        'ok': not errors,
        'windows': elev_windows, 'doors': elev_doors,
        'opening_trim_lf': trim_lf,
        'per_elevation': per_elev,
        'plan_check': {'windows': plan_windows, 'doors': plan_doors, 'role': 'comparison-only'},
        'errors': errors,
    }


def reconcile_roof_footprint(roof_footprint_sf, under_roof_sf, roof_perimeter_lf,
                             measured_overhang_ft, tolerance_ft=0.75):
    """Roof footprint must equal the under-roof area plus an overhang band that agrees with
    the overhang you MEASURED off the roof plan.  Solves the band as a ring so the corners
    are not double counted, then reports the implied overhang.

    Catches both directions: a footprint traced too small (my structural under-bid bias) and
    one traced too large / with overlapping plane polygons (cal #55: a takeoff implying a
    5.54 ft overhang on a house whose measured eave projection was 1.50 ft)."""
    band = float(roof_footprint_sf) - float(under_roof_sf)
    P = float(roof_perimeter_lf)
    implied = band / P if P else float('nan')
    # ring solve: band = o*P_out - 4*o^2  (rectilinear, convex corners)
    o_ring = None
    if P:
        disc = P * P - 16.0 * band
        if disc >= 0:
            o_ring = (P - _math.sqrt(disc)) / 8.0
    ok = abs(implied - float(measured_overhang_ft)) <= tolerance_ft
    return {
        'ok': ok,
        'overhang_band_sf': round(band, 1),
        'implied_overhang_ft': round(implied, 2),
        'implied_overhang_ring_ft': round(o_ring, 2) if o_ring is not None else None,
        'measured_overhang_ft': float(measured_overhang_ft),
        'delta_ft': round(implied - float(measured_overhang_ft), 2),
        'note': ('consistent' if ok else
                 'ROOF FOOTPRINT DOES NOT RECONCILE: implied overhang %.2f ft vs measured '
                 '%.2f ft. Either the footprint trace is wrong or roof-plane polygons '
                 'overlap. Do not price until this closes.'
                 % (implied, float(measured_overhang_ft))),
    }


def cladding_completeness(materials_sf, wall_band_sf, gable_sf, tolerance_pct=3.0):
    """Every SF of measured wall must land in exactly one material bucket.
    `materials_sf` = {'lap':.., 'bnb':.., 'stone':.., 'brick':..}.
    Catches the silent-drop failure where unclassified area simply vanishes from the
    estimate (cal #55: my first classifier dropped every tile that failed a texture test)."""
    total_mat = sum(float(v) for v in materials_sf.values())
    total_wall = float(wall_band_sf) + float(gable_sf)
    d = abs(total_mat - total_wall) / total_wall * 100.0 if total_wall else 999.0
    return {
        'ok': d <= tolerance_pct,
        'material_total_sf': round(total_mat, 1),
        'measured_wall_sf': round(total_wall, 1),
        'unallocated_sf': round(total_wall - total_mat, 1),
        'delta_pct': round(d, 2),
        'by_material': {k: round(float(v), 1) for k, v in materials_sf.items()},
        'note': ('all measured wall area is allocated' if d <= tolerance_pct else
                 'UNALLOCATED WALL AREA %.1f SF (%.1f%%) -- every SF must land in a '
                 'material bucket or it is silently dropped from the bid'
                 % (total_wall - total_mat, d)),
    }


def beam_wrap_lf(horizontal_beam_lf, post_count, post_height_ft, bracket_count=0):
    """Exterior beam-wrap LF is NOT just the horizontal run.  Jason's takeoff draws a
    vertical line down every porch POST and bills it in the same LF line
    (cal #55: I measured 121 LF of open porch edge against his 291 LF and ran -58%).
    Posts and brackets still price EACH for the column-wrap / bracket lines -- this
    function is only for the sub's linear beam-wrap quantity."""
    posts_lf = float(post_count) * float(post_height_ft)
    return {
        'horizontal_lf': round(float(horizontal_beam_lf), 1),
        'post_lf': round(posts_lf, 1),
        'total_beam_wrap_lf': round(float(horizontal_beam_lf) + posts_lf, 1),
        'post_count': int(post_count), 'bracket_count': int(bracket_count),
        'note': 'verticals included -- horizontal-only is the documented -58% miss',
    }
