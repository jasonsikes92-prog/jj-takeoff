"""
J&J Takeoff Engine — foundation for measuring ANY plan (vector or scanned), at ANY scale.

Design principle (Jason's rule): MEASURE & COUNT every item. No universal formulas, no
shortcuts. Code measures precisely; the model's vision identifies WHAT/WHERE.

This module is built and graded incrementally, trade by trade, against real actuals.
Brick 1 (here): robust feet-inch-fraction dimension parsing + scale calibration from a
KNOWN dimension on the sheet (works regardless of stated scale or PDF rescaling).

REGRESSION SUITE (run after ANY edit here):
    python tools/tests/run_golden.py          # grade every wired golden house
    python tools/tests/run_golden.py --list   # list fixtures + which need plan files
Exit code is non-zero on any FAIL, so an edit that improves one trade but breaks a
graded house is caught immediately. Ground truth traces to reference/calibration.md.
Module self-test (parser/framing/gable) still runs via:  python tools/jnj_takeoff.py
"""
import re
import math

# ---------------------------------------------------------------------------
# Brick 1a — robust dimension parser.  Handles:  59'-6 1/2"   61'-4"   9'   24'-0"
#   3'-4 3/4"   16'-9"   2'-1"   12"   6 1/2"   and rejects junk (inches>=12, etc.)
# Returns feet as float, or None if the token isn't a real dimension.
# ---------------------------------------------------------------------------
_DIM_RE = re.compile(
    r"""^\s*
    (?:(?P<ft>\d+)\s*'\s*)?            # feet + apostrophe (optional)
    [-\s]*                              # separator
    (?:(?P<in>\d+)\s*)?                 # whole inches (optional)
    (?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?  # fraction of an inch (optional)
    \s*\"?\s*$                          # optional inch mark
    """,
    re.VERBOSE,
)

def parse_dim(text, max_ft=None):
    """Parse an architectural dimension string -> feet (float). None if not a dimension.
    max_ft: optional plausibility cap (e.g. 250 for a residence) to drop concatenation junk."""
    if text is None:
        return None
    t = text.strip().replace("''", '"').replace("’", "'").replace("”", '"')
    if "'" not in t and '"' not in t and "/" not in t:
        return None  # bare number with no unit mark — not a trusted dimension
    m = _DIM_RE.match(t)
    if not m:
        return None
    ft = int(m.group("ft")) if m.group("ft") else 0
    inch = int(m.group("in")) if m.group("in") else 0
    if m.group("num"):
        inch += int(m.group("num")) / int(m.group("den"))
    # sanity: a real dimension never has >=12 whole inches written out
    if inch >= 12 and m.group("ft"):
        return None
    val = ft + inch / 12.0
    if val <= 0:
        return None
    if max_ft is not None and val > max_ft:
        return None
    return val


# ---------------------------------------------------------------------------
# Brick 1b — scale calibration from a KNOWN dimension (vector sheets).
# Strategy: a dimension string sits between two witness/extension lines whose drawn
# span (in PDF points) equals value_ft * pt_per_ft.  Find dim texts, find the
# horizontal line whose length best matches near each dim, solve pt_per_ft, and take
# the consensus (median) so one bad match can't throw the scale.
# ---------------------------------------------------------------------------
def _lines(page):
    segs = []
    for o in page.get_drawings():
        for it in o["items"]:
            if it[0] == "l":
                a, b = it[1], it[2]
                segs.append((a.x, a.y, b.x, b.y))
            elif it[0] == "re":
                r = it[1]
                segs += [(r.x0, r.y0, r.x1, r.y0), (r.x0, r.y1, r.x1, r.y1),
                         (r.x0, r.y0, r.x0, r.y1), (r.x1, r.y0, r.x1, r.y1)]
    return segs

def _cluster_mode(ratios, half=0.02, refine=2):
    """Densest cluster among candidate ratios. The TRUE scale is reinforced by many
    independent dimensions landing on the same pt/ft; junk matches scatter and never
    pile up. Returns (center, members). `half` = half-width of the cluster as a
    fraction of value (0.02 => +/-2%)."""
    rs = sorted(r for r in ratios if r > 0.5)  # drop degenerate/zero spans
    if not rs:
        return None, []
    n = len(rs)
    # slide a multiplicative window; pick the window holding the most points
    best = (0, None)
    j = 0
    for i in range(n):
        lo = rs[i]
        hi = lo * (1 + 2 * half)
        k = i
        while k < n and rs[k] <= hi:
            k += 1
        if k - i > best[0]:
            best = (k - i, (i, k))
    if best[1] is None:
        return None, []
    i, k = best[1]
    members = rs[i:k]
    center = sum(members) / len(members)
    # refine: re-center the window on the running mean a couple times
    for _ in range(refine):
        members = [r for r in rs if abs(r - center) / center <= half]
        if not members:
            break
        center = sum(members) / len(members)
    return center, members


def calibrate_scale(page, band=35.0, half=0.02, min_ft=2.0, near_k=4, segs=None):
    """Auto-detect pt_per_ft on a vector sheet, robust to busy floor plans.

    For every dimension TEXT we emit *all* plausible (drawn_span / value) ratios from
    two independent geometric signals, then take the densest cluster (the mode):
      (1) the dimension LINE  — a parallel segment the text is centered on; and
      (2) the WITNESS-LINE PAIR — the perpendicular extension ticks straddling the text.
    Redundant, independent votes => the real scale wins; mismatches scatter.

    Returns (pt_per_ft, n_votes_in_cluster, n_candidates, members)."""
    words = page.get_text("words")  # x0,y0,x1,y1,text,...
    dims = []
    for w in words:
        v = parse_dim(w[4])
        if v and v >= min_ft:
            cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
            dims.append((v, cx, cy))
    if segs is None:                                    # vector default; raster passes pixel-detected segs
        segs = _lines(page)
    H = [(min(s[0], s[2]), max(s[0], s[2]), s[1]) for s in segs if abs(s[3] - s[1]) < 1.0]
    V = [(min(s[1], s[3]), max(s[1], s[3]), s[0]) for s in segs if abs(s[2] - s[0]) < 1.0]
    ratios = []
    for v, cx, cy in dims:
        # --- horizontal dimension ---
        # (1) dim line: horizontal seg spanning cx, within vertical band of the text
        for lo, hi, y in H:
            if lo - 4 <= cx <= hi + 4 and abs(y - cy) <= band:
                ratios.append((hi - lo) / v)
        # (2) witness pair: nearest vertical ticks left & right that cross the text's y
        left = sorted((cx - x, x) for lo, hi, x in V if lo - 4 <= cy <= hi + 4 and x < cx)
        right = sorted((x - cx, x) for lo, hi, x in V if lo - 4 <= cy <= hi + 4 and x > cx)
        for _, xl in left[:near_k]:
            for _, xr in right[:near_k]:
                ratios.append((xr - xl) / v)
        # --- vertical dimension ---
        for lo, hi, x in V:
            if lo - 4 <= cy <= hi + 4 and abs(x - cx) <= band:
                ratios.append((hi - lo) / v)
        up = sorted((cy - y, y) for lo, hi, y in H if lo - 4 <= cx <= hi + 4 and y < cy)
        dn = sorted((y - cy, y) for lo, hi, y in H if lo - 4 <= cx <= hi + 4 and y > cy)
        for _, yu in up[:near_k]:
            for _, yd in dn[:near_k]:
                ratios.append((yd - yu) / v)
    center, members = _cluster_mode(ratios, half=half)
    return center, len(members), len(ratios), members


# Standard architectural scales as a sanity cross-check (pt per ft at 72 dpi)
STD_SCALES = {
    '1/8"=1\'': 9.0, '3/16"=1\'': 13.5, '1/4"=1\'': 18.0,
    '3/8"=1\'': 27.0, '1/2"=1\'': 36.0,
}
def nearest_std(ppf):
    if not ppf:
        return None
    return min(STD_SCALES.items(), key=lambda kv: abs(kv[1] - ppf))


def detect_scale(page):
    """Calibrate one sheet and return a clean, self-aware verdict.

    ppf       = measured pt/ft (what actually reproduces labeled dims — use THIS to
                measure, since it already absorbs any PDF rescaling).
    scale     = nearest standard scale name, for the human (None if not near one).
    confidence: high  -> measured cluster snaps to a standard scale, many votes: trust it.
                good  -> snaps to a standard, modest votes.
                review-> tight cluster but NOT a standard scale: human should glance.
                low   -> too few agreeing dims: don't measure off this sheet blind."""
    ppf, votes, cand, _ = calibrate_scale(page)
    if not ppf:
        return {"ppf": None, "scale": None, "confidence": "none",
                "votes": 0, "candidates": cand, "err_pct": None}
    std_name, std_val = nearest_std(ppf)
    err = abs(ppf - std_val) / std_val
    snapped = err <= 0.04
    if snapped and votes >= 15:
        conf = "high"
    elif snapped and votes >= 6:
        conf = "good"
    elif votes >= 8:
        conf = "review"
    else:
        conf = "low"
    return {"ppf": round(ppf, 3), "scale": std_name if snapped else None,
            "confidence": conf, "err_pct": round(err * 100, 1),
            "votes": votes, "candidates": cand}


# ---------------------------------------------------------------------------
# RASTER SCALE — recover pt/ft on a FLATTENED / image sheet (no vector layer), WITHOUT OCR.
# Key fact: "flattened" is a spectrum -- most flattened exports rasterize the LINEWORK but keep
# a TEXT LAYER, so get_text still returns the dimension numbers even with 0 vector lines. We read
# the VALUES from text and the SPANS from pixels, then reuse the vector consensus. Only a pure
# image scan with NO text needs OCR (not installed here) -> scale_from_reference() is the floor.
# ---------------------------------------------------------------------------
def _raster_segments(page, zoom=2.0, clip=None, ink_thr=190):
    """Detect straight segments from a RENDERED sheet (flattened/image plans). HoughLinesP on the
    ink mask; endpoints returned in PAGE POINTS so they feed calibrate_scale(segs=...) exactly
    like the vector _lines()."""
    import cv2, numpy as np, fitz
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, colorspace=fitz.csGRAY)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    ink = (g < ink_thr).astype(np.uint8) * 255
    lines = cv2.HoughLinesP(ink, 1, np.pi / 180, threshold=45,
                            minLineLength=int(zoom * 6), maxLineGap=int(zoom * 2))
    ox, oy = (clip.x0, clip.y0) if clip else (0.0, 0.0)
    out = []
    if lines is not None:
        for x0, y0, x1, y1 in lines[:, 0, :]:
            out.append((x0 / zoom + ox, y0 / zoom + oy, x1 / zoom + ox, y1 / zoom + oy))
    return out


def calibrate_scale_raster(page, zoom=2.0, clip=None, near_k=5, tol=0.03):
    """Recover pt/ft on a flattened/image sheet WITHOUT OCR, as long as the page keeps a TEXT
    LAYER: read dimension VALUES from get_text and measure their WITNESS-PAIR spans from Hough
    segments on the rendered pixels. ⛔ Unlike the vector calibrator, this SNAPS TO A STANDARD
    ARCHITECTURAL SCALE (a raster's noisy Hough segments will otherwise form a false free
    consensus) -- the true scale is one of 1/8..1/2"=1', so we test only those 5 and pick the
    one the dimension geometry actually supports. detect_scale-style verdict, mode='raster'.
    Pure image scan with NO text -> OCR (absent) or scale_from_reference()."""
    dims = []
    for w in page.get_text("words"):
        v = parse_dim(w[4])
        if v and v >= 3:                                 # ignore tiny/noise dims
            dims.append((v, (w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
    if not dims:
        return {"ppf": None, "scale": None, "confidence": "no-text", "votes": 0,
                "note": "no readable dimension text -- needs OCR (not installed) or scale_from_reference()"}
    segs = _raster_segments(page, zoom=zoom, clip=clip)
    H = [(min(s[0], s[2]), max(s[0], s[2]), (s[1] + s[3]) / 2) for s in segs if abs(s[3] - s[1]) < 2.5]
    V = [(min(s[1], s[3]), max(s[1], s[3]), (s[0] + s[2]) / 2) for s in segs if abs(s[2] - s[0]) < 2.5]
    ratios = []                                          # (witness-pair span) / (labeled feet)
    for v, cx, cy in dims:
        left = sorted((cx - x, x) for lo, hi, x in V if lo - 8 <= cy <= hi + 8 and x < cx)
        right = sorted((x - cx, x) for lo, hi, x in V if lo - 8 <= cy <= hi + 8 and x > cx)
        for _, xl in left[:near_k]:
            for _, xr in right[:near_k]:
                if xr - xl > 3: ratios.append((xr - xl) / v)
        up = sorted((cy - y, y) for lo, hi, y in H if lo - 8 <= cx <= hi + 8 and y < cy)
        dn = sorted((y - cy, y) for lo, hi, y in H if lo - 8 <= cx <= hi + 8 and y > cy)
        for _, yu in up[:near_k]:
            for _, yd in dn[:near_k]:
                if yd - yu > 3: ratios.append((yd - yu) / v)
    # INDEPENDENT cross-check: the largest H/V dim labels the building's overall extent, so the
    # traced heavy-outline pixel bbox / that dim gives a rough ppf that must AGREE with the votes.
    # (Rejects a witness-vote fluke like 27 when the building geometry says ~18.)
    bbox_ppf = _raster_bbox_ppf(page, zoom=zoom, clip=clip)
    ranked = sorted(((sum(1 for r in ratios if abs(r - ppf) / ppf <= tol), name, ppf)
                     for name, ppf in STD_SCALES.items()), reverse=True)
    pick = None
    for votes, name, ppf in ranked:
        if votes < 3:
            continue
        if bbox_ppf is None or 0.8 <= ppf / bbox_ppf <= 1.25:   # must be consistent with the outline
            pick = (votes, name, ppf); break
    if pick is None:
        return {"ppf": None, "scale": None, "confidence": "low", "votes": ranked[0][0] if ranked else 0,
                "candidates": len(ratios), "bbox_ppf": bbox_ppf,
                "note": "no standard scale passed the votes + outline cross-check -- supply ppf= / "
                        "scale_from_reference()"}
    votes, name, ppf = pick
    # ⛔ HONESTY CAP: raster auto-scale has been observed to lock a WRONG standard scale with
    # strong votes (Burns rendered: picked 27 vs true 18). Without OCR it is NOT trustworthy on
    # its own -> never report better than 'review', and always tell the caller to CONFIRM. The
    # reliable path is scale_from_reference() with one known dimension; full auto needs OCR.
    return {"ppf": round(ppf, 3), "scale": name, "mode": "raster", "confidence": "review",
            "votes": votes, "candidates": len(ratios),
            "bbox_ppf": round(bbox_ppf, 1) if bbox_ppf else None,
            "note": "ESTIMATE ONLY -- raster auto-scale is unverified and can lock the wrong scale. "
                    "CONFIRM with scale_from_reference(one known dim) before trusting any measurement. "
                    "Full auto-scale needs OCR (not installed)."}


def _raster_bbox_ppf(page, zoom=2.0, clip=None, ink_thr=190):
    """Rough pt/ft from the heavy-outline pixel bbox vs the largest labeled H/V dimension --
    an independent cross-check for calibrate_scale_raster (overhang biases it a few % high, so
    it's used to REJECT wrong scales, not as the final value)."""
    import cv2, numpy as np, fitz
    Hd = [parse_dim(w[4]) for w in page.get_text("words")
          if parse_dim(w[4]) and (w[2] - w[0]) >= (w[3] - w[1])]
    Vd = [parse_dim(w[4]) for w in page.get_text("words")
          if parse_dim(w[4]) and (w[3] - w[1]) > (w[2] - w[0])]
    Hd = [v for v in Hd if v and v >= 8]; Vd = [v for v in Vd if v and v >= 8]
    if not (Hd or Vd):
        return None
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, colorspace=fitz.csGRAY)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    ink = (g < ink_thr).astype(np.uint8) * 255
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    r = max(2, int(round(0.6 * float(np.percentile(dt[ink > 0], 95)))))
    heavy = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    cnts, _ = cv2.findContours(heavy, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    x, y, wpx, hpx = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    est = []
    if Hd: est.append((wpx / zoom) / max(Hd))
    if Vd: est.append((hpx / zoom) / max(Vd))
    est.sort()
    return est[len(est) // 2] if est else None


def scale_from_reference(px_len, feet, zoom=1.0):
    """Floor case (pure image scan: no text, no OCR): human gives ONE known dimension's drawn
    length in pixels (at render `zoom`) and its real feet -> pt/ft. e.g. a wall labeled 33'-2"
    spanning 598 px at zoom=1 -> scale_from_reference(598, 33.17). Always works."""
    if feet <= 0 or px_len <= 0:
        return None
    return round(px_len / zoom / feet, 3)


# ---------------------------------------------------------------------------
# Brick 1c — dimension-chain reader (vector sheets).  Pull every dimension label
# with position + writing direction, group collinear ones into chains by SPACING
# CONSISTENCY (adjacent centers must be (v_i+v_j)/2 * ppf apart), and cross-check
# each chain's run-sum against its drawn span.  Junk annotations ("16" notes etc.)
# don't fit the geometry and drop out.  This reads exact labeled lengths the way
# Jason reads a plan — complements the pixel trace (Brick 2) by snapping it to truth.
# ---------------------------------------------------------------------------
def _dim_labels(page, min_ft=0.4):
    """[(value, cx, cy, orient 'H'/'V', text)] from line-level text (merges fractions)."""
    out = []
    for blk in page.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            txt = "".join(sp["text"] for sp in ln["spans"]).strip()
            v = parse_dim(txt)
            if not v or v < min_ft:
                continue
            x0, y0, x1, y1 = ln["bbox"]
            dx, dy = ln["dir"]
            out.append((v, (x0 + x1) / 2, (y0 + y1) / 2,
                        "H" if abs(dx) >= abs(dy) else "V", txt))
    return out


def read_dimension_chains(page, ppf=None, line_tol=10, gap_tol_ft=0.75, min_single=6):
    """Return chains of collinear dimension labels. Each: {orient, line, runs, total, span_ck}.
    A chain is a maximal run of dims whose center spacing matches (v_i+v_j)/2*ppf; the
    span cross-check (span_ck ~= total) confirms it's real, not coincidental alignment."""
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    dims = _dim_labels(page)
    res = []
    for orient, ci, si in (("H", 2, 1), ("V", 1, 2)):
        ds = sorted((d for d in dims if d[3] == orient), key=lambda e: e[ci])
        if not ds:
            continue
        # cluster onto common dimension lines (shared cy for H / cx for V)
        groups, cur = [], [ds[0]]
        for d in ds[1:]:
            if d[ci] - cur[-1][ci] <= line_tol:
                cur.append(d)
            else:
                groups.append(cur); cur = [d]
        groups.append(cur)
        for g in groups:
            g = sorted(g, key=lambda e: e[si])
            run = [g[0]]; outruns = []
            for a, b in zip(g, g[1:]):
                exp = (a[0] + b[0]) / 2 * ppf
                if abs((b[si] - a[si]) - exp) <= gap_tol_ft * ppf:
                    run.append(b)
                else:
                    outruns.append(run); run = [b]
            outruns.append(run)
            for r in outruns:
                vals = [x[0] for x in r]
                if not (len(r) >= 2 or vals[0] >= min_single):
                    continue
                span = (r[-1][si] - r[0][si]) + (r[0][0] + r[-1][0]) / 2 * ppf
                tot = sum(vals)
                if len(r) >= 2 and abs(span / ppf - tot) / tot > 0.04:
                    continue  # span cross-check failed -> not a real chain (stray label snuck in)
                res.append({"orient": orient, "line": round(sum(x[ci] for x in r) / len(r)),
                            "runs": [round(v, 2) for v in vals],
                            "total": round(tot, 2), "span_ck": round(span / ppf, 2)})
    return res


def overall_dims(page, ppf=None):
    """Distinct overall building dimensions per axis (largest validated chain totals)."""
    cs = read_dimension_chains(page, ppf)
    H = sorted({c["total"] for c in cs if c["orient"] == "H"}, reverse=True)
    V = sorted({c["total"] for c in cs if c["orient"] == "V"}, reverse=True)
    return {"width_ft": H[:4], "depth_ft": V[:4]}


# ---------------------------------------------------------------------------
# Brick 2 — measure an enclosed region (perimeter + area) off a rendered sheet.
# Works on vector OR raster: render -> isolate axis-aligned walls -> flood the
# interior -> close partition notches -> trace the outline at the verified scale.
# Proven on Wilson p4: basement poured-wall perimeter = 155.9 LF vs 156 actual.
# ---------------------------------------------------------------------------
def trace_enclosed_region(page, clip, zoom=4.0, ppf=None, prefer="left",
                          min_sf=20, notch_ft=1.6, overlay_path=None):
    """Measure the largest enclosed (interior) region inside `clip`.

    clip: fitz.Rect around the drawing of interest (exclude title block/notes/dim lines).
    prefer: 'left'|'right'|'largest' — which interior region to take when several exist
            (e.g. 'left' picks the basement when a garage sits to the right).
    Returns dict: perimeter_lf (inside-face), area_sf, corners, ppx. Centerline run is
    ~3-4 ft longer per closed loop — report perimeter as a small range, not a point."""
    import cv2, numpy as np, fitz
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    ppx = ppf * zoom
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = img[:, :, :3].copy()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape
    _, bw = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY_INV)
    # keep only long axis-aligned runs (= walls); drops diagonals, text, dim ticks
    Lr = max(5, int(round(ppx * 0.8)))
    walls = (cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (Lr, 1)))
             | cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, Lr))))
    s = max(2, int(round(ppx * 0.5)))
    sealed = cv2.morphologyEx(walls, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (s, s)))
    free = cv2.bitwise_not(sealed)
    cv2.floodFill(free, np.zeros((H + 2, W + 2), np.uint8), (0, 0), 0)  # kill exterior
    n, lab, stats, cent = cv2.connectedComponentsWithStats(free, 8)
    pick = None
    for i in range(1, n):
        a = stats[i, cv2.CC_STAT_AREA]
        if a < ppx * ppx * min_sf:
            continue
        cx = cent[i][0]
        ok = (prefer == "largest" or (prefer == "left" and cx < 0.6 * W)
              or (prefer == "right" and cx > 0.4 * W))
        if ok and (pick is None or a > pick[1]):
            pick = (i, a)
    if pick is None:
        return None
    region = np.uint8(lab == pick[0]) * 255
    kc = int(round(ppx * notch_ft))
    closed = cv2.morphologyEx(region, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kc, kc)))
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, 0.004 * cv2.arcLength(c, True), True)
    res = {"perimeter_lf": cv2.arcLength(ap, True) / ppx,
           "area_sf": cv2.contourArea(ap) / ppx ** 2,
           "corners": len(ap), "ppx": ppx}
    if overlay_path:
        cv2.drawContours(rgb, [ap], -1, (255, 0, 0), 4)
        cv2.imwrite(overlay_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return res


def trace_footprint(page, clip, zoom=4.0, ppf=None, close_ft=1.0, overlay_path=None):
    """WHOLE building/slab footprint (outer boundary) — use for a subdivided slab where
    `trace_enclosed_region` would only return the largest room.  Seals dashed slab edges +
    door gaps, floods the exterior, takes the complement.  Validated Holbrook p5: 2,954 sf
    vs GEO's 3,122 (~5%, inside-face).  Returns area_sf, perim_lf, corners."""
    import cv2, numpy as np, fitz
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    ppx = ppf * zoom
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = img[:, :, :3].copy()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY_INV)
    k = max(3, int(round(ppx * close_ft)))
    ker = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    closed = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, ker)
    closed = cv2.copyMakeBorder(closed, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=0)
    ff = closed.copy(); h, w = ff.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    solid = cv2.erode(closed | cv2.bitwise_not(ff), ker)[5:-5, 5:-5]
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, 0.003 * cv2.arcLength(c, True), True)
    if overlay_path:
        cv2.drawContours(rgb, [ap], -1, (255, 0, 0), 4)
        cv2.imwrite(overlay_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return {"area_sf": cv2.contourArea(ap) / ppx**2, "perim_lf": cv2.arcLength(ap, True) / ppx,
            "corners": len(ap)}


def ocr_words(page, zoom=2.5, psm=11, clip=None, min_conf=40):
    """OCR fallback (Phase 2) for sheets with NO text layer (curve/outlined fonts — the
    Peterson set: 11 vector sheets, 0 extractable words) and for scanned/photographed
    uploads (Level Ground). Returns [(x0,y0,x1,y1,word)] in PDF points — same shape as
    page.get_text('words')[:5] — so schedule/dimension readers can consume OCR output as a
    drop-in. Engine: tesseract v5.5 via pytesseract (confirmed installed 7/5/26).
    VALIDATED on Peterson p2: full-page pass at zoom 2 located the SQUARE FOOTAGE schedule
    + row labels (FIRST FLOOR HEATED / TWO CAR GARAGE / ... conf 90-96 on labels).
    RULES: (1) call only when get_text('words') is empty/sparse — OCR never silently
    replaces vector text; (2) any NUMBER that will become a Quantity must be re-verified
    with ocr_numeric_cell() — numeric glyphs read far weaker than labels (1969 read at
    conf 50 while its label read at 95); (3) tag downstream Quantity notes with 'OCR'."""
    import fitz, numpy as np, pytesseract
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, clip=clip)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    d = pytesseract.image_to_data(g, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    ox, oy = (clip.x0, clip.y0) if clip else (0, 0)
    out = []
    for i in range(len(d["text"])):
        t = d["text"][i].strip()
        if not t or int(d["conf"][i]) < min_conf:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        out.append((x / zoom + ox, y / zoom + oy, (x + w) / zoom + ox, (y + h) / zoom + oy, t))
    return out


def vote_numeric(page, bbox, pad=3.0):
    """AUTHORITATIVE table-cell / dimension number read: digits-only tesseract in psm-8
    (single word) + psm-13 (raw line), across 2 zooms x {raw, otsu}, MAJORITY VOTE. psm-8 is
    the key: stylized plan fonts mis-read under psm-7 (Peterson 1969 -> 1269) but resolve
    18/18 under psm-8/13. `bbox` MUST be the value token's own bounding box from the
    full-page ocr pass — never hand-typed (a loose clip catches the neighbor: a hand box
    read OUTDOOR 258 as 7528). Returns (value:int|None, n_agree). VALIDATED Peterson p2
    integrated run: HEATED 1969 / GARAGE 559 / OUTDOOR 258 / EXPANSION 406 all correct."""
    import fitz, numpy as np, cv2, pytesseract
    from collections import Counter
    x0, y0, x1, y1 = bbox
    clip = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    votes = Counter()
    for zoom in (8, 12):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, clip=clip)
        g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
        for img in (g, cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
            for psm in (8, 13):
                t = pytesseract.image_to_string(
                    img, config=f'--psm {psm} -c tessedit_char_whitelist="0123456789"').strip()
                if t.isdigit():
                    votes[int(t)] += 1
    if not votes:
        return None, 0
    return votes.most_common(1)[0]


def ocr_numeric_cell(page, clip, zoom=8.0, psm=8):
    """Single digits-only read of ONE cell (whitelist '0123456789,'). psm=8 (single word) —
    the reliable mode for a plan-font number. For a VALUE that becomes a Quantity prefer
    vote_numeric() (multi-config majority vote). Returns raw string ('' if none)."""
    import fitz, numpy as np, pytesseract
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, clip=clip)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    cfg = f'--psm {psm} -c tessedit_char_whitelist="0123456789,"'
    return pytesseract.image_to_string(g, config=cfg).strip()


def _ocr_words_conf(page, zoom=2.5, psm=11, clip=None, min_conf=25):
    """ocr_words + per-word confidence -> (x0,y0,x1,y1,text,conf). Internal helper for
    read_sqft_schedule_ocr (confidence picks the heal suspect)."""
    import fitz, numpy as np, pytesseract
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, clip=clip)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    d = pytesseract.image_to_data(g, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    ox, oy = (clip.x0, clip.y0) if clip else (0, 0)
    out = []
    for i in range(len(d["text"])):
        t = d["text"][i].strip()
        c = int(d["conf"][i])
        if not t or c < min_conf:
            continue
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        out.append((x / zoom + ox, y / zoom + oy, (x + w) / zoom + ox, (y + h) / zoom + oy, t, c))
    return out


def read_sqft_schedule_ocr(page, zoom=2.5):
    """read_sqft_schedule for NO-TEXT-LAYER sheets (curve/outlined fonts — the Peterson set;
    scanned Level Ground uploads). Locate the SQUARE FOOTAGE header -> constrain to its X band
    (rejects digit tokens elsewhere on the sheet that poison the value column) -> group rows by
    y-gap -> read each value with vote_numeric() on its token bbox -> ENFORCE the printed TOTAL
    as the enumeration gate: an unreadable/disagreeing cell is SOLVED from the total and the
    result is flagged 'review' (the GATE, self-healing; surface uncertainty, never hide it).
    VALIDATED Peterson p2 INTEGRATED (7/5/26): heated 1969 (voted) / garage 559 / outdoor 258 /
    expansion 406 / ENTRY healed to 6 from TOTAL 3198; heated basis 1969+406 = 2375 = Jason's.
    Returns {rows:[{label,sqft,agree,klass,healed}], total, confidence, note} or None."""
    import re
    words = _ocr_words_conf(page, zoom=zoom)
    hdr = [w for w in words if "SQUARE" in w[4].upper()]
    if not hdr:
        return None
    DIGIT = re.compile(r"^[\d,]+$")
    hy0, hy1 = hdr[0][1], hdr[0][3]
    hwords = [w for w in words if w[4].upper() in ("SQUARE", "FOOTAGE") and abs(w[1] - hy0) <= 14]
    hx_lo, hx_hi = min(w[0] for w in hwords) - 30, max(w[2] for w in hwords) + 60
    body = [w for w in words if w[1] > hy1 + 2 and hx_lo <= w[0] <= hx_hi]
    digit_x = [w[0] for w in body if DIGIT.match(w[4])]
    if not digit_x:
        return None
    val_x0 = min(digit_x) - 12
    body.sort(key=lambda w: w[1])
    rows, cur, last_y = [], [], None
    for w in body:
        if last_y is None or w[1] - last_y <= 12:
            cur.append(w)
        else:
            rows.append(cur); cur = [w]
        last_y = w[1]
    if cur:
        rows.append(cur)
    parsed, total = [], None
    for row in rows:
        labs = [w[4] for w in sorted(row, key=lambda w: w[0])
                if w[0] < val_x0 and re.search("[A-Za-z]", w[4])]
        label = " ".join(labs).strip()
        vtok = [w for w in row if w[0] >= val_x0 and DIGIT.match(w[4])]
        if not label or not vtok:
            continue
        v, agree = vote_numeric(page, vtok[0][:4])
        if re.search(r"TOTAL|UNDER ROOF", label.upper()):
            total = v
        else:
            parsed.append({"label": label, "sqft": v, "agree": agree,
                           "klass": classify_area_row(label), "healed": False})
    have = [r for r in parsed if r["sqft"] is not None]
    parts_sum = sum(r["sqft"] for r in have)
    if total is None:
        return {"rows": parsed, "total": None, "confidence": "review",
                "note": "no TOTAL row -> cannot enumeration-check"}
    if abs(parts_sum - total) <= max(2, 0.004 * total) and len(have) == len(parsed):
        return {"rows": parsed, "total": total, "confidence": "high",
                "note": f"parts {parts_sum} reconcile to printed total {total}"}
    suspect = min(parsed, key=lambda r: (r["sqft"] is not None, r["agree"]))
    others = sum(r["sqft"] for r in parsed if r is not suspect and r["sqft"] is not None)
    suspect["sqft"], suspect["healed"] = total - others, True
    return {"rows": parsed, "total": total, "confidence": "review",
            "note": f"parts != total -> healed '{suspect['label']}' (agree {suspect['agree']}) "
                    f"to {suspect['sqft']} from TOTAL {total}"}


def detect_scale_ocr(page, zoom=2.5, min_pairs=3, row_tol=6.0):
    """OCR FALLBACK for detect_scale on ZERO-TEXT sheets (Phase 2; landed 7/5/26).
    Reads dimension tokens with tesseract (psm 11), groups them into horizontal chain
    rows, and solves ppf from ADJACENT-token spacing: for neighboring chain values v1,v2
    the tick-to-tick layout puts their centers ~(v1+v2)/2 * ppf apart. Median-filtered
    over all pairs so one misread can't set the scale.
    HONESTY GATE (validated): needs >=min_pairs agreeing pairs within 8% of the median or
    returns None -- on thin-CAD-font sheets tesseract yields almost no parseable dims
    (Wilson p4: 3 junk tokens -> None; Peterson p2: 5 scattered -> None) and this must
    NEVER ship a confidently-wrong scale (the banked tesseract-on-dims rejection stands;
    this only fires when a sheet's dim font is big/clean enough to vote, e.g. Lankford p5
    Rentfrow font: 3 pairs, 0.8% spread -> ppf 12.474 on a printed 3/16\" rescale).
    Returns {ppf, n_pairs, n_raw, spread_pct, confidence} or None."""
    ws = ocr_words(page, zoom=zoom, psm=11, min_conf=40)
    toks = []
    for w in ws:
        t = w[4].replace("O", "0").replace("o", "0")
        v = parse_dim(t, max_ft=200)
        if v and v >= 2.0:
            toks.append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2, v))
    rows = {}
    for x, y, v in sorted(toks, key=lambda t: t[1]):
        hit = None
        for ry in rows:
            if abs(ry - y) <= row_tol:
                hit = ry
                break
        if hit is None:
            rows[y] = [(x, v)]
        else:
            rows[hit].append((x, v))
    ests = []
    for items in rows.values():
        if len(items) < 2:
            continue
        items.sort()
        for (x1, v1), (x2, v2) in zip(items, items[1:]):
            est = (x2 - x1) / ((v1 + v2) / 2)
            if 2.0 <= est <= 60.0:
                ests.append(est)
    if len(ests) < min_pairs:
        return None
    ests.sort()
    med = ests[len(ests) // 2]
    good = [e for e in ests if abs(e / med - 1) <= 0.08]
    if len(good) < min_pairs:
        return None
    ppf = sum(good) / len(good)
    spread = (max(good) - min(good)) / ppf
    return {"ppf": round(ppf, 3), "n_pairs": len(good), "n_raw": len(ests),
            "spread_pct": round(spread * 100, 1),
            "confidence": "high" if len(good) >= 5 and spread <= 0.05 else "review"}


def foundation_wall_loops(page, ppf, clip=None, zoom=3.0, thick_ft=(0.40, 1.00),
                          close_ft=2.0, min_sf=40):
    """Enclosed POURED-WALL loops from PAIRED-PARALLEL stroke geometry (Phase 2/3 signal:
    a wall is two solid near-axis strokes ~wall-thickness apart; hairline dimension /
    extension / dashed beam lines have no such partner and never enter the mask).
    Validated Lankford p5 (zero-text, 3/16\" print-rescale, ppf via detect_scale_ocr):
    main basement loop 259.1 LF inside-face / 2,479 SF, STABLE across close_ft 1-4.
    KNOWN HAZARDS: (1) double-line NOTE-BOX borders pair like walls (a 401 SF text box
    showed up as a loop) -- take loops by size/position, don't sum blindly; (2) the loop
    is GEOMETRY, not SCOPE: which walls a vendor pours (10' basement vs stem vs framed
    walkout) needs wall-height cross-referencing or Jason's green trace -- GV billed 198
    LF on Lankford vs the full 259 LF loop.
    Returns list of {area_sf, perim_lf, corners, bbox_ft, centroid_ft}, largest first."""
    import cv2
    import numpy as np
    if clip is None:
        r = find_drawing_region(page, ppf=ppf)
        clip = r["clip"] if r else page.rect
    solid = []
    for s in extract_styled_segments(page, ppf=ppf):
        if s["dashed"]:
            continue
        x0, y0, x1, y1 = s["seg"]
        if not (clip.x0 <= (x0 + x1) / 2 <= clip.x1 and clip.y0 <= (y0 + y1) / 2 <= clip.y1):
            continue
        if s["len_ft"] < 1.0:
            continue
        if abs(x1 - x0) >= abs(y1 - y0):
            if abs(y1 - y0) > 2:
                continue
            solid.append(("h", min(x0, x1), max(x0, x1), (y0 + y1) / 2, s))
        else:
            if abs(x1 - x0) > 2:
                continue
            solid.append(("v", min(y0, y1), max(y0, y1), (x0 + x1) / 2, s))
    lo, hi = thick_ft[0] * ppf, thick_ft[1] * ppf
    walls = {}
    for i, (o1, a1, b1, c1, s1) in enumerate(solid):
        for o2, a2, b2, c2, s2 in solid[i + 1:]:
            if o1 != o2:
                continue
            d = abs(c1 - c2)
            if not (lo <= d <= hi):
                continue
            ov = min(b1, b2) - max(a1, a2)
            if ov < 0.5 * min(b1 - a1, b2 - a2) or ov < 1.0 * ppf:
                continue
            walls[id(s1)] = s1
            walls[id(s2)] = s2
            break
    if not walls:
        return []
    ppx = ppf * zoom
    W = int((clip.x1 - clip.x0) * zoom)
    H = int((clip.y1 - clip.y0) * zoom)
    base = np.zeros((H, W), np.uint8)
    for s in walls.values():
        x0, y0, x1, y1 = s["seg"]
        cv2.line(base, (int((x0 - clip.x0) * zoom), int((y0 - clip.y0) * zoom)),
                 (int((x1 - clip.x0) * zoom), int((y1 - clip.y0) * zoom)), 255, 3)
    k = max(3, int(round(ppx * close_ft)))
    sealed = cv2.morphologyEx(base, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    pad = cv2.copyMakeBorder(sealed, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=0)
    ff = pad.copy()
    cv2.floodFill(ff, np.zeros((pad.shape[0] + 2, pad.shape[1] + 2), np.uint8), (0, 0), 255)
    interior = (ff[5:-5, 5:-5] != 255) & (sealed == 0)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(interior.astype(np.uint8), 8)
    out = []
    for i in range(1, n):
        a_sf = stats[i, cv2.CC_STAT_AREA] / ppx / ppx
        if a_sf < min_sf:
            continue
        cnts, _ = cv2.findContours((lab == i).astype(np.uint8),
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cnts, key=cv2.contourArea)
        ap = cv2.approxPolyDP(c, 0.004 * cv2.arcLength(c, True), True)
        _, _, bbox_w, bbox_h = cv2.boundingRect(ap)
        out.append({"area_sf": round(cv2.contourArea(ap) / ppx / ppx, 1),
                    "perim_lf": round(cv2.arcLength(ap, True) / ppx, 1),
                    "corners": len(ap),
                    "bbox_ft": (round(bbox_w / ppx, 1), round(bbox_h / ppx, 1)),
                    "centroid_ft": (round(cent[i][0] / ppx, 1), round(cent[i][1] / ppx, 1))})
    out.sort(key=lambda d: -d["area_sf"])
    return out


def find_drawing_region(page, ppf=None, pad_ft=2.0):
    """AUTONOMY (Phase 1): auto-locate the MAIN drawing on a sheet so measurement calls stop
    needing hand-fed clips. Signal: a house's walls form ONE physically connected network
    (every interior wall touches the exterior shell), while title blocks / notes columns /
    side details are separate islands. Method: keep wall-length SOLID non-blue segments,
    drop page-border spans, rasterize sample points to a 2-ft grid, take the largest
    8-connected component by linework length (2-ft cells bridge door openings ~4 ft but
    leave detail drawings, separated by >2 in of paper, disconnected), return padded bbox.
    VALIDATED: Wilson p4 foundation + Holbrook p5 slab — with this clip + detect_scale,
    trace_enclosed_region reproduced Wilson's GV invoice EXACTLY (155.9 vs 156 LF, 1,372 vs
    1,372 SF) with prefer='largest' (no side hint). Returns {clip, ppf, n_segs, linework_ft}
    or None (<20 usable segments -> raster/flattened sheet, use the raster path)."""
    import math as _m
    from collections import defaultdict, deque
    import fitz as _fitz
    if ppf is None:
        ppf = detect_scale(page)["ppf"] or 18.0
    W, H = page.rect.width, page.rect.height
    def _is_blue(c): return c is not None and c[2] - max(c[0], c[1]) > 0.12
    keep = []
    for s in extract_styled_segments(page, ppf=ppf):
        if s["dashed"] or _is_blue(s["color"]):
            continue
        x0, y0, x1, y1 = s["seg"]
        L = _m.hypot(x1 - x0, y1 - y0)
        if not (1.2 * ppf <= L <= 80 * ppf):
            continue
        if L > 0.8 * min(W, H) and (abs(y0 - y1) < 2 or abs(x0 - x1) < 2):
            continue                                   # page border / title-block frame
        keep.append((x0, y0, x1, y1, L))
    if len(keep) < 20:
        return None
    G = 2.0 * ppf
    cells = defaultdict(float)
    for x0, y0, x1, y1, L in keep:
        n = max(2, int(L // (G / 2)))
        for i in range(n + 1):
            t = i / n
            cells[(int((x0 + (x1 - x0) * t) // G), int((y0 + (y1 - y0) * t) // G))] += L / (n + 1)
    seen, best = set(), None
    for c in cells:
        if c in seen:
            continue
        comp, q, tot = [], deque([c]), 0.0
        seen.add(c)
        while q:
            cur = q.popleft()
            comp.append(cur); tot += cells[cur]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (cur[0] + dx, cur[1] + dy)
                    if nb in cells and nb not in seen:
                        seen.add(nb); q.append(nb)
        if best is None or tot > best[1]:
            best = (comp, tot)
    xs = [c[0] for c in best[0]]; ys = [c[1] for c in best[0]]
    pad = pad_ft * ppf
    clip = _fitz.Rect(max(0, min(xs) * G - pad), max(0, min(ys) * G - pad),
                      min(W, (max(xs) + 1) * G + pad), min(H, (max(ys) + 1) * G + pad))
    return {"clip": clip, "ppf": ppf, "n_segs": len(keep), "linework_ft": round(best[1] / ppf, 0)}


def trace_footprint_clean(page, clip=None, ppf=None, zoom=3.0, close_ft=1.5,
                          axis_only=True, include_dashed=False, overlay_path=None):
    """CLUTTER-ROBUST footprint trace (Phase 3): rasterize ONLY the classified wall-like
    vector segments (solid, non-blue/dimension, wall-length, near-axis) onto a blank canvas,
    then seal + flood + outer contour. Furniture, hatching, text, and dimension strings never
    enter the mask -- unlike trace_footprint, which thresholds ALL ink (that gave a jumbled
    1,688 SF one-room trace on Holbrook's subdivided slab; this gives a stable, clean
    building outline: 2,294 SF at ANY close_ft 1.5-4.0, clutter-immune).
    KNOWN LIMIT (do not silently trust on cut-up slabs): boundary pockets drawn in neither
    the solid nor dashed wall layer are excluded -- Holbrook's bottom-center strip leaves it
    ~22% under the 2,954 inside-face proof. On subdivided/cut-up slabs the PRIMARY footprint
    method is the sheet's own dimension chains (polygon_outline / read_dimension_chains);
    use this trace as the independent cross-check, and reconcile().
    clip=None -> find_drawing_region(); ppf=None -> detect_scale()."""
    import cv2, numpy as np, fitz, math as _m
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    if clip is None:
        r = find_drawing_region(page, ppf=ppf)
        if r is None:
            return None
        clip = r["clip"]
    def _is_blue(c): return c is not None and c[2] - max(c[0], c[1]) > 0.12
    keep = []
    for s in extract_styled_segments(page, ppf=ppf):
        if (s["dashed"] and not include_dashed) or _is_blue(s["color"]):
            continue
        x0, y0, x1, y1 = s["seg"]
        if not (clip.x0 <= (x0 + x1) / 2 <= clip.x1 and clip.y0 <= (y0 + y1) / 2 <= clip.y1):
            continue
        if not (1.2 <= s["len_ft"] <= 80):
            continue
        if axis_only and abs(x1 - x0) > 2 and abs(y1 - y0) > 2:
            ang = abs(_m.degrees(_m.atan2(y1 - y0, x1 - x0))) % 90
            if 8 < ang < 82:
                continue                               # stoop/leader diagonals
        keep.append(s)
    ppx = ppf * zoom
    W = int(page.rect.width * zoom); H = int(page.rect.height * zoom)
    canvas = np.zeros((H, W), np.uint8)
    for s in keep:
        x0, y0, x1, y1 = s["seg"]
        th = max(2, int(round((s["width"] or 1.0) * zoom * 0.6)))
        cv2.line(canvas, (int(x0 * zoom), int(y0 * zoom)), (int(x1 * zoom), int(y1 * zoom)), 255, th)
    k = max(3, int(round(ppx * close_ft)))
    ker = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    closed = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, ker)
    closed = cv2.copyMakeBorder(closed, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=0)
    ff = closed.copy(); h, w = ff.shape
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    solid = (closed | cv2.bitwise_not(ff))[5:-5, 5:-5]
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, 0.003 * cv2.arcLength(c, True), True)
    if overlay_path:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.drawContours(bgr, [ap], -1, (0, 0, 255), 6)
        cv2.imwrite(overlay_path, bgr)
    return {"area_sf": cv2.contourArea(ap) / ppx ** 2, "perim_lf": cv2.arcLength(ap, True) / ppx,
            "corners": len(ap), "n_segs": len(keep)}


def measure_colored_path(image_path, ppf, color="green", overlay_path=None):
    """Measure the length of a hand-traced colored path (Jason marks the poured wall in
    green on the plan). Isolates the color, skeletonizes the stroke to its centerline, and
    sums length at the given scale -> LF. Solves scans/clutter: I follow HIS clean line, not
    the faint drawing, and only what he traces counts (scope handled by the marking)."""
    import cv2, numpy as np
    from skimage.morphology import skeletonize
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)
    b, g, r = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    if color == "green":
        mask = (g > 90) & (g - r > 35) & (g - b > 35)
    elif color == "blue":
        mask = (b > 90) & (b - r > 35) & (b - g > 35)
    elif color == "red":
        mask = (r > 110) & (r - g > 45) & (r - b > 45)
    elif color in ("orange", "magenta"):
        mask = (r > 120) & (r - b > 40) & (abs(r - g) < 80) if color == "orange" else \
               (r > 110) & (b > 110) & (r - g > 40) & (b - g > 40)
    else:
        raise ValueError(color)
    m = (mask.astype(np.uint8)) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))  # bridge stroke gaps
    skel = skeletonize(m > 0)
    ys, xs = np.where(skel)
    pts = set(zip(ys.tolist(), xs.tolist()))
    L = 0.0
    for (y, x) in pts:
        for dy, dx, w in [(0, 1, 1), (1, 0, 1), (1, 1, 1.4142), (1, -1, 1.4142)]:
            if (y + dy, x + dx) in pts:
                L += w
    if overlay_path:
        ov = img.copy(); ov[skel] = (0, 0, 255)
        cv2.imwrite(overlay_path, ov)
    cl = L / ppf
    return {"centerline_lf": round(cl, 1), "wall_lf": round(cl / 0.90, 1), "color_px": int(mask.sum())}


def polygon_outline(segments):
    """Assemble a rectilinear outline from VISION-READ labeled dimensions and return its
    perimeter + area. Works on ANY plan (vector or scan) because it uses the plan's own
    labeled numbers, not pixels — the universal fallback when the pixel bricks can't isolate
    the wall amid clutter. `segments` = [(length_ft, 'R'|'L'|'U'|'D'), ...] walked around the
    loop. `closure_err` should be ~0 for a correctly-read closed loop (built-in self-check)."""
    x = y = 0.0
    pts = [(0.0, 0.0)]
    for length, d in segments:
        dx, dy = {"R": (1, 0), "L": (-1, 0), "U": (0, -1), "D": (0, 1)}[d.upper()]
        x += dx * length; y += dy * length
        pts.append((x, y))
    perim = sum(l for l, _ in segments)
    area = abs(sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
                   for i in range(len(pts) - 1))) / 2.0
    return {"perimeter_lf": round(perim, 1), "area_sf": round(area, 1),
            "closure_err_ft": round((x ** 2 + y ** 2) ** 0.5, 2), "corners": len(segments)}


# ---------------------------------------------------------------------------
# classify_lines -- THE RELIABILITY FRONT-END.  "Be reliable on the lines" (Jason).
# The failure mode was rasterizing the plan to a picture and letting pixel CV GUESS which
# marks are roof vs wall vs dimension -- blind by construction. But a plan ENCODES the line
# meaning, and enough of that survives to separate them WITHOUT tracing pixels:
#   COLOR  -- vector plans draw roof/dims/walls in different colors (Burns roof = olive-green,
#             the thickest stroke; dims = blue). Strongest signal; vector-only.
#   WEIGHT -- roof/primary lines are drawn HEAVY, dims THIN. SURVIVES FLATTENING to one color
#             (proven on Burns: recovered the roof by thickness alone from a mono raster).
#   DASH   -- walls-below on a roof plan are DASHED; the roof edge is solid. SURVIVES flattening.
#   NUMBER -- a thin line centered on a dimension NUMBER (+ ticks) is a dimension line -> strip it.
# Degradation ladder: vector (color+weight+dash) -> flattened raster (weight+dash+number) ->
# read/OCR the labeled DIMENSIONS as a color-independent cross-check -> human green-trace floor.
# Always cross-check the traced result against the plan's own dims and FLAG low confidence
# (trust-green / review-yellow) rather than shipping a blind number.
# ---------------------------------------------------------------------------
def extract_styled_segments(page, ppf=None):
    """Every drawn line segment WITH its vector style -- the raw material for classify_lines.
    Returns [{seg:(x0,y0,x1,y1), color:(r,g,b)|None, width, dashed, len_ft}]; rectangles are
    exploded into 4 edges. Style is what lets us tell roof from wall from dimension without
    tracing pixels. (Vector sheets only; a flattened raster has no styles -> classify_lines
    reports mode='raster' and you separate by weight/dash on the rendered image instead.)"""
    if ppf is None:
        ppf = detect_scale(page)["ppf"] or 18.0
    out = []
    for o in page.get_drawings():
        col = o.get("color")
        col = tuple(round(c, 2) for c in col) if col else None
        w = round(o.get("width") or 0.0, 2)
        dsh = o.get("dashes")
        dashed = bool(dsh) and str(dsh).strip() not in ("[] 0", "[] 0.0", "[] 0.00", "")
        def add(x0, y0, x1, y1):
            out.append({"seg": (x0, y0, x1, y1), "color": col, "width": w,
                        "dashed": dashed, "len_ft": math.hypot(x0 - x1, y0 - y1) / ppf})
        for it in o["items"]:
            if it[0] == "l":
                add(it[1].x, it[1].y, it[2].x, it[2].y)
            elif it[0] == "re":
                r = it[1]
                add(r.x0, r.y0, r.x1, r.y0); add(r.x1, r.y0, r.x1, r.y1)
                add(r.x1, r.y1, r.x0, r.y1); add(r.x0, r.y1, r.x0, r.y0)
    return out


def _roof_from_raster(page, ppf, zoom=3.0, clip=None, ink_thr=190, overlay_path=None):
    """RASTER fallback for a FLATTENED / image-only sheet (no vector layer): recover the roof
    outline by stroke WEIGHT, the signal that survives flattening to one color. Steps: render
    gray -> ink mask -> distance transform gives each stroke's half-width -> morphological OPEN
    with a disk sized BETWEEN the thin mode and the heavy tail keeps only heavy lines -> flood
    the exterior -> largest enclosed contour = footprint. `weight_sep` = heavy/thin width ratio;
    if it's ~<2 the lines are uniform weight and this can't separate them -> read the labeled
    dimensions or green-trace. Returns footprint_sf, perim_lf, roof_polygon (PDF pts), conf."""
    import cv2, numpy as np, fitz
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip, colorspace=fitz.csGRAY)
    g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    ppx = ppf * zoom
    ink = (g < ink_thr).astype(np.uint8) * 255
    if int((ink > 0).sum()) < 500:
        return {"confidence": "low", "footprint_sf": None, "roof_polygon": [],
                "note": "raster: too little ink to measure"}
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    vals = dt[ink > 0]
    p50, p95 = float(np.percentile(vals, 50)), float(np.percentile(vals, 95))
    weight_sep = round(p95 / max(p50, 1e-6), 2)
    r = max(2, int(round(0.6 * p95 + 0.4 * p50)))          # disk fits heavy strokes, not thin
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    thick = cv2.morphologyEx(ink, cv2.MORPH_OPEN, disk)
    if int((thick > 0).sum()) < 300:
        return {"confidence": "low", "footprint_sf": None, "roof_polygon": [], "weight_sep": weight_sep,
                "note": "raster: no separable heavy-line tier -- read labeled DIMENSIONS or green-trace"}
    kk = cv2.getStructuringElement(cv2.MORPH_RECT, (int(ppx * 1.2), int(ppx * 1.2)))
    closed = cv2.morphologyEx(thick, cv2.MORPH_CLOSE, kk)
    ff = closed.copy(); hh, ww = ff.shape
    cv2.floodFill(ff, np.zeros((hh + 2, ww + 2), np.uint8), (0, 0), 255)
    solid = closed | cv2.bitwise_not(ff)
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return {"confidence": "low", "footprint_sf": None, "roof_polygon": [], "weight_sep": weight_sep,
                "note": "raster: could not close an outline -- green-trace"}
    c = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, 0.004 * cv2.arcLength(c, True), True)
    ox, oy = (clip.x0, clip.y0) if clip else (0, 0)
    poly = [(round(px / zoom + ox, 1), round(py / zoom + oy, 1)) for pt in ap for (px, py) in [pt[0]]]
    area = cv2.contourArea(ap) / ppx ** 2
    perim = cv2.arcLength(ap, True) / ppx
    if overlay_path:
        ov = cv2.cvtColor(ink, cv2.COLOR_GRAY2BGR); ov[thick > 0] = (0, 180, 0)
        cv2.drawContours(ov, [ap], -1, (0, 0, 255), 3); cv2.imwrite(overlay_path, ov)
    conf = "review" if weight_sep >= 2.0 else "low"
    return {"confidence": conf, "footprint_sf": round(area, 0), "perim_lf": round(perim, 0),
            "roof_polygon": poly, "corners": len(ap), "weight_sep": weight_sep,
            "note": "raster: roof recovered by stroke WEIGHT (no vector layer). NOTE scale must be "
                    "supplied/OCR'd (not auto-detectable without vector dims). Cross-check vs "
                    "labeled dims; if weight_sep<~2 lines are uniform -> green-trace."}


def classify_lines(page, ppf=None):
    """Split a sheet's linework into roof / dimension / reference / other so the measurement
    functions get a CLEAN segment set instead of guessing on a flattened picture.
      roof      = the sheet's PRIMARY heavy outline (on a ROOF sheet = the roof; on a floor
                  plan = the walls -- the CALLER knows the sheet type). Prefers a distinct
                  non-gray COLOR cluster; falls back to the heaviest SOLID strokes when there
                  is no color (flattened plan).
      dimension = blue/thin lines and any thin line centered on a dimension NUMBER.
      reference = DASHED lines (walls-below on a roof plan, hidden lines).
      other     = the medium solid linework (typically the walls on a roof sheet).
    Returns the four segment lists + per-class counts/lengths + which SIGNAL was used +
    CONFIDENCE. mode='raster' with a note when the sheet has no usable vector layer."""
    segs = extract_styled_segments(page, ppf)            # ppf None -> extract defaults internally
    if len(segs) < 30:                                   # no vector layer -> flattened / image sheet
        recovered = None
        if ppf is None:                                  # recover scale from text layer + pixels (no OCR)
            recovered = calibrate_scale_raster(page); ppf = recovered.get("ppf")
        if not ppf:
            why = recovered.get("note", "supply ppf= or use scale_from_reference()") if recovered else ""
            return {"mode": "raster", "confidence": "low", "roof": [], "dimension": [],
                    "reference": [], "other": [], "footprint_sf": None,
                    "note": "raster + scale unknown: " + why}
        r = _roof_from_raster(page, ppf)
        out = {"mode": "raster", "signal": "weight-on-pixels (no vector layer)",
               "confidence": r.get("confidence", "low"), "scale_ppf": round(ppf, 3),
               "roof": r.get("roof_polygon", []),        # a closed POLYGON of PDF points (not styled segs)
               "footprint_sf": r.get("footprint_sf"), "perim_lf": r.get("perim_lf"),
               "weight_sep": r.get("weight_sep"),
               "dimension": [], "reference": [], "other": [], "note": r.get("note")}
        if recovered:
            out["scale_recovered"] = f"{recovered.get('confidence')} ({recovered.get('votes', '?')} votes)"
        return out
    if ppf is None:
        ppf = detect_scale(page)["ppf"] or 18.0
    widths = sorted(s["width"] for s in segs)
    wmed = widths[len(widths) // 2]
    def is_gray(c): return c is None or (max(c) - min(c) < 0.12)
    def blueish(c): return c is not None and c[2] - max(c[0], c[1]) > 0.12
    lab_pts = [(cx, cy) for _, cx, cy, _, _ in _dim_labels(page)]
    def near_label(seg, r=42):
        mx, my = (seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2
        return any(abs(mx - lx) < r and abs(my - ly) < r for lx, ly in lab_pts)
    # ROOF COLOR = the most-drawn NON-GRAY color among heavier-than-median solid strokes
    heavy_thresh = max(1.4 * wmed, wmed + 0.3)
    colorlen = {}
    for s in segs:
        if s["width"] >= heavy_thresh and not s["dashed"] and not is_gray(s["color"]):
            colorlen[s["color"]] = colorlen.get(s["color"], 0.0) + s["len_ft"]
    roof_color = max(colorlen, key=colorlen.get) if colorlen else None
    solid_heavy = max(1.6 * wmed, wmed + 0.4)
    cls = {"roof": [], "dimension": [], "reference": [], "other": []}
    for s in segs:
        if s["dashed"]:
            cls["reference"].append(s)
        elif blueish(s["color"]) or (s["width"] <= wmed * 1.3 and near_label(s["seg"])):
            cls["dimension"].append(s)
        elif roof_color is not None and s["color"] == roof_color:
            cls["roof"].append(s)                       # distinct heavy color = the sheet's outline
        elif roof_color is None and s["width"] >= solid_heavy:
            cls["roof"].append(s)                       # no color (flattened) -> heaviest solid
        else:
            cls["other"].append(s)
    roof_ft = sum(s["len_ft"] for s in cls["roof"])
    signal = "color+weight" if roof_color is not None else "weight-only (no color -- flattened?)"
    conf = "high" if (roof_color is not None and roof_ft > 50) else \
           ("review" if roof_ft > 30 else "low")
    return {"mode": "vector", "signal": signal, "roof_color": roof_color, "confidence": conf,
            "counts": {k: len(v) for k, v in cls.items()},
            "lengths_ft": {k: round(sum(s["len_ft"] for s in v), 0) for k, v in cls.items()},
            **cls}


def _pitch_calls(page):
    """Every roof pitch RISE read off the sheet's "8 : 12" callouts."""
    words = page.get_text("words")
    rises = []
    for i, w in enumerate(words):
        if w[4] == ":" and 0 < i < len(words) - 1:
            a, b = words[i - 1][4], words[i + 1][4]
            if a.isdigit() and b.isdigit() and 0 < int(a) <= 24 and int(b) == 12:
                rises.append(int(a))
    return rises


def slope_arrows(page, shaft_min=20.0, shaft_max=150.0, barb_min=4.0, barb_max=16.0,
                 join_tol=3.0):
    """Every roof SLOPE ARROW on the sheet as (x, y, heading_degrees).

    Jason reads a roof plan by the arrows, so the engine should too. An arrow is drawn the
    same way on every set because it has to be legible: one shaft (about 33pt) plus two short
    barbs (about 7.7pt) meeting at ONE end of the shaft. The end the barbs converge on is the
    HEAD, and the head points DOWNSLOPE -- the direction the roof falls.

    That single fact separates the cases nothing else could:
      ridge      -- arrows on both sides point AWAY from the line
      valley     -- arrows on both sides point INTO the line
      shed/step  -- arrows on both sides point the SAME way; the roof keeps falling
      eave       -- roof on one side, arrow pointing at the line
      rake       -- roof on one side, arrow running ALONGSIDE the line
    heading is in PDF space: 0 = +x (east), 90 = +y (south).
    """
    segs = [x for x in extract_styled_segments(page) if not x["dashed"]]
    def length(sg):
        x1, y1, x2, y2 = sg["seg"]
        return math.hypot(x2 - x1, y2 - y1)
    shafts = [sg for sg in segs if shaft_min <= length(sg) <= shaft_max]
    barbs = [sg for sg in segs if barb_min <= length(sg) <= barb_max]
    field = _pitch_field(page)
    arrows = []
    for sh in shafts:
        x1, y1, x2, y2 = sh["seg"]
        ends = ((x1, y1), (x2, y2))
        heads = []
        for k, end in enumerate(ends):
            touching = 0
            for b in barbs:
                bx1, by1, bx2, by2 = b["seg"]
                if (math.hypot(bx1 - end[0], by1 - end[1]) <= join_tol
                        or math.hypot(bx2 - end[0], by2 - end[1]) <= join_tol):
                    touching += 1
            if touching >= 2:
                heads.append(k)
        # A DIMENSION line carries an arrowhead at BOTH ends. A slope arrow has exactly one,
        # because it means "the roof falls this way". Two heads is a dimension -- drop it.
        if len(heads) != 1:
            continue
        end, other = ends[heads[0]], ends[1 - heads[0]]
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        # A slope arrow belongs to a pitch callout; anything far from one is a leader.
        if field and not any(math.hypot(px - mx, py - my) <= 70.0 for px, py, _ in field):
            continue
        heading = math.degrees(math.atan2(end[1] - other[1], end[0] - other[0])) % 360.0
        arrows.append((mx, my, heading))
    # One arrow per location; a shaft occasionally resolves twice on redrawn linework.
    unique = []
    for ax, ay, ah in arrows:
        if not any(math.hypot(ax - bx, ay - by) < 6.0 and abs(ah - bh) < 5.0
                   for bx, by, bh in unique):
            unique.append((ax, ay, ah))
    return unique


def _pitch_field(page):
    """Every pitch callout as (x, y, rise) so a line can be asked what slopes each side."""
    words = page.get_text("words")
    out = []
    for i, w in enumerate(words):
        if w[4] == ":" and 0 < i < len(words) - 1:
            a, b = words[i - 1][4], words[i + 1][4]
            if a.isdigit() and b.isdigit() and 0 < int(a) <= 24 and int(b) == 12:
                out.append(((words[i - 1][0] + words[i + 1][2]) / 2.0,
                            (w[1] + w[3]) / 2.0, int(a)))
    return out


def _arrow_in_plane(px, py, plane, arrows, mask):
    """Nearest arrow that actually sits in the given roof plane.

    Nearest-on-the-sheet is not good enough: on roberts a bottom EAVE picked up a small
    feature's east-west arrow, read it as parallel, and classified as rake -- 29 LF of gutter
    run lost. An edge must consult the arrow for the plane it bounds.
    """
    best, bestd = None, None
    for ax, ay, ah in arrows:
        if _cell_label(ax, ay, mask) != plane:
            continue
        d = math.hypot(ax - px, ay - py)
        if bestd is None or d < bestd:
            bestd, best = d, ah
    return best


def _arrow_each_side(seg, nx, ny, arrows, reach=340.0):
    """Nearest slope arrow heading on each perpendicular side of a segment."""
    x1, y1, x2, y2 = seg
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    best = [None, None]
    bestd = [reach, reach]
    for ax, ay, ah in arrows:
        dx, dy = ax - mx, ay - my
        side = 0 if (dx * nx + dy * ny) >= 0 else 1
        d = math.hypot(dx, dy)
        if d < bestd[side]:
            bestd[side] = d
            best[side] = ah
    return best


def _pitch_each_side(seg, nx, ny, field, reach=260.0):
    """Nearest pitch callout on each perpendicular side of a segment."""
    x1, y1, x2, y2 = seg
    mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    best = [None, None]
    bestd = [reach, reach]
    for px, py, rise in field:
        dx, dy = px - mx, py - my
        side = 0 if (dx * nx + dy * ny) >= 0 else 1
        d = math.hypot(dx, dy)
        if d < bestd[side]:
            bestd[side] = d
            best[side] = rise
    return best


def _pitch_callout_points(page):
    """Centres of every roof PITCH callout ("8 : 12") on the sheet."""
    words = page.get_text("words")
    pts = []
    for i, w in enumerate(words):
        if w[4] == ":" and 0 < i < len(words) - 1:
            a, b = words[i - 1][4], words[i + 1][4]
            if a.isdigit() and b.isdigit() and 0 < int(a) <= 24 and 0 < int(b) <= 24:
                pts.append(((words[i - 1][0] + words[i + 1][2]) / 2.0, (w[1] + w[3]) / 2.0))
    return pts


def roof_outline_segments(page, ppf=None, join_tol=3.0, min_ft=1.0):
    """Isolate a roof plan's roof linework WITHOUT relying on colour.

    classify_lines picks the most-drawn heavy non-grey COLOUR as the roof. That works on a
    plan whose roof is drawn in its own colour (burns olive-green) and fails on one where it
    is not -- on roberts it locks onto the RED REDLINE layer and returns 242 LF of roof while
    17,706 LF falls into "other". Colour is a drafter's choice and does not generalise.

    TOPOLOGY does. A roof is one CONNECTED figure spanning the sheet's drawing area;
    annotations, redlines, leaders and callouts are small disconnected fragments. So: take
    every solid segment, join them where endpoints meet, and keep the largest connected
    component by total length. No colour, no stroke weight, no per-plan tuning.

    Returns {segments, total_lf, components, bbox, confidence}.
    """
    segs = [x for x in extract_styled_segments(page, ppf)
            if not x["dashed"] and x["len_ft"] >= min_ft]
    if len(segs) < 8:
        return {"segments": [], "total_lf": 0.0, "components": 0, "confidence": "low",
                "note": "too few solid segments to form an outline"}
    parent = list(range(len(segs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    # Bucket endpoints on a grid so joining is near-linear instead of O(n^2).
    cell = max(join_tol, 1.0)
    grid = {}
    for idx, sgm in enumerate(segs):
        x1, y1, x2, y2 = sgm["seg"]
        for (px, py) in ((x1, y1), (x2, y2)):
            gx, gy = int(px // cell), int(py // cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for other, ox, oy in grid.get((gx + dx, gy + dy), ()):
                        if abs(ox - px) <= join_tol and abs(oy - py) <= join_tol:
                            union(idx, other)
            grid.setdefault((gx, gy), []).append((idx, px, py))

    comps = {}
    for idx in range(len(segs)):
        comps.setdefault(find(idx), []).append(segs[idx])
    # SELECT the roof by PITCH CALLOUTS, not by size. Every roof plan labels its pitches
    # ("8 : 12") because the framer needs them -- that is a construction requirement, not a
    # drafter's style choice, so it survives across plan sets where colour and stroke weight
    # do not. The roof is the component whose extent encloses those callouts. Falls back to
    # the largest component only when a sheet carries no pitch callout at all.
    pitches = _pitch_callout_points(page)
    def _encloses(c):
        if not pitches:
            return 0
        xs = [v for x in c for v in (x["seg"][0], x["seg"][2])]
        ys = [v for x in c for v in (x["seg"][1], x["seg"][3])]
        x0, y0, x1b, y1b = min(xs), min(ys), max(xs), max(ys)
        return sum(1 for px, py in pitches if x0 <= px <= x1b and y0 <= py <= y1b)
    ranked = sorted(comps.values(),
                    key=lambda c: (_encloses(c), sum(x["len_ft"] for x in c)), reverse=True)
    best = ranked[0]
    total = sum(x["len_ft"] for x in best)
    runner = sum(x["len_ft"] for x in ranked[1]) if len(ranked) > 1 else 0.0
    xs = [v for x in best for v in (x["seg"][0], x["seg"][2])]
    ys = [v for x in best for v in (x["seg"][1], x["seg"][3])]
    # A real roof outline dominates the sheet; a near-tie means we may have grabbed a table
    # or a title block instead, so say so rather than shipping a confident wrong number.
    enclosed = _encloses(best)
    conf = "high" if (enclosed >= 2 or total > max(40.0, 2.5 * runner)) else "review"
    return {"segments": best, "total_lf": round(total, 1), "components": len(ranked),
            "runner_up_lf": round(runner, 1), "confidence": conf,
            "pitch_callouts": len(pitches), "pitch_callouts_enclosed": enclosed,
            "bbox": (min(xs), min(ys), max(xs), max(ys))}


def _dedupe_segments(segs, tol=4.0):
    """Plans draw the same roof line more than once (Burns: 40 strokes for 33 real lines).
    Collapse segments whose endpoints coincide within `tol` PDF points."""
    kept = []
    for s in segs:
        x1, y1, x2, y2 = s["seg"]
        a, b = (x1, y1), (x2, y2)
        if a > b:
            a, b = b, a
        dup = False
        for k in kept:
            kx1, ky1, kx2, ky2 = k["seg"]
            c, e = (kx1, ky1), (kx2, ky2)
            if c > e:
                c, e = e, c
            if (abs(a[0] - c[0]) <= tol and abs(a[1] - c[1]) <= tol
                    and abs(b[0] - e[0]) <= tol and abs(b[1] - e[1]) <= tol):
                dup = True
                break
        if not dup:
            kept.append(s)
    return kept


def _seg_angle(s):
    x1, y1, x2, y2 = s["seg"]
    return math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0


def _exterior_mask(segs, cell=2.0, pad=8):
    """Label every grid cell by which ROOF PLANE it belongs to (0 = outside the roof).

    Ray-cast parity cannot answer "is this point inside the roof": parity is only defined
    against a CLOSED polygon, and roof linework is a graph full of interior ridges, hips and
    valleys. Painting the segments onto a grid and flooding gives the right answer, and
    flooding EVERY region rather than just the outside also tells us which plane a point is
    in -- which is what lets an edge consult the arrow for its OWN plane instead of whatever
    arrow happens to be nearest on the sheet.
    """
    xs = [v for s in segs for v in (s["seg"][0], s["seg"][2])]
    ys = [v for s in segs for v in (s["seg"][1], s["seg"][3])]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    w = int((x1 - x0) / cell) + 2 * pad + 2
    h = int((y1 - y0) / cell) + 2 * pad + 2

    def to_cell(px, py):
        return int((px - x0) / cell) + pad, int((py - y0) / cell) + pad

    blocked = [[False] * w for _ in range(h)]

    def mark(cx, cy):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                gx, gy = cx + dx, cy + dy
                if 0 <= gx < w and 0 <= gy < h:
                    blocked[gy][gx] = True

    for sg in segs:
        ax, ay, bx, by = sg["seg"]
        cax, cay = to_cell(ax, ay)
        cbx, cby = to_cell(bx, by)
        steps = max(abs(cbx - cax), abs(cby - cay), 1)
        for i in range(steps + 1):
            mark(cax + (cbx - cax) * i // steps, cay + (cby - cay) * i // steps)

    label = [[-1] * w for _ in range(h)]

    def flood(sx, sy, lab):
        stack = [(sx, sy)]
        label[sy][sx] = lab
        n = 0
        while stack:
            cx, cy = stack.pop()
            n += 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                gx, gy = cx + dx, cy + dy
                if (0 <= gx < w and 0 <= gy < h and label[gy][gx] == -1
                        and not blocked[gy][gx]):
                    label[gy][gx] = lab
                    stack.append((gx, gy))
        return n

    flood(0, 0, 0)                       # 0 is always the exterior
    nxt = 1
    for cy in range(h):
        for cx in range(w):
            if label[cy][cx] == -1 and not blocked[cy][cx]:
                if flood(cx, cy, nxt) >= 12:   # ignore slivers between doubled strokes
                    nxt += 1
                else:
                    flood(cx, cy, 0)
    return label, to_cell, w, h


def _cell_label(px, py, mask):
    """Which roof plane a point falls in. 0 = outside, -1 = on a line."""
    label, to_cell, w, h = mask
    cx, cy = to_cell(px, py)
    if not (0 <= cx < w and 0 <= cy < h):
        return 0
    return label[cy][cx]


def _plane_arrows(arrows, mask):
    """Group arrow headings by the roof plane each arrow sits in."""
    out = {}
    for ax, ay, ah in arrows:
        out.setdefault(_cell_label(ax, ay, mask), []).append(ah)
    return out


def _is_exterior(px, py, mask):
    return _cell_label(px, py, mask) == 0


def _refine_roof_line_topology(page, groups, segs, mask, arrows, ppf=None, probe=8.0,
                               touch=8.0):
    """Resolve ambiguous roof strokes from plane-bound arrows and graph topology.

    This pass deliberately ignores stroke color. It removes annotation strokes that entered
    the connected roof graph, rejects unsupported interior underlay chains, corrects boundary
    and step edges with the arrow from their own roof plane, and closes short topology gaps.
    """
    roles = ("eave", "rake", "ridge", "hip_valley", "transition")
    groups = {role: list(groups[role]) for role in roles}
    refinements = []
    arrow_planes = [(x, y, heading, _cell_label(x, y, mask))
                    for x, y, heading in arrows]

    def length_pts(item):
        x1, y1, x2, y2 = item["seg"]
        return math.hypot(x2 - x1, y2 - y1)

    def midpoint(item):
        x1, y1, x2, y2 = item["seg"]
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def angle_delta(a, b):
        return abs((a - b + 90.0) % 180.0 - 90.0)

    def locate(item):
        for role in roles:
            if item in groups[role]:
                return role
        return None

    def drop(item, reason):
        old_role = locate(item)
        if old_role is None:
            return None
        groups[old_role].remove(item)
        refinements.append({"action": "remove", "old_role": old_role,
                            "segment": item["seg"], "reason": reason})
        return old_role

    def move(item, new_role, reason):
        old_role = locate(item)
        if old_role is None or old_role == new_role:
            return
        groups[old_role].remove(item)
        groups[new_role].append(item)
        refinements.append({"action": "reclassify", "old_role": old_role,
                            "new_role": new_role, "segment": item["seg"], "reason": reason})

    def side_labels(item):
        x1, y1, x2, y2 = item["seg"]
        length = length_pts(item) or 1.0
        nx, ny = -(y2 - y1) / length, (x2 - x1) / length
        mx, my = midpoint(item)
        return (_cell_label(mx + nx * probe, my + ny * probe, mask),
                _cell_label(mx - nx * probe, my - ny * probe, mask),
                nx, ny)

    def plane_arrow(plane, item):
        if plane <= 0:
            return None
        mx, my = midpoint(item)
        candidates = [(math.hypot(x - mx, y - my), heading)
                      for x, y, heading, arrow_plane in arrow_planes
                      if arrow_plane == plane]
        return min(candidates)[1] if candidates else None

    def evidence(item):
        side0, side1, nx, ny = side_labels(item)
        head0, head1 = plane_arrow(side0, item), plane_arrow(side1, item)
        dot0 = None if head0 is None else (
            math.cos(math.radians(head0)) * nx + math.sin(math.radians(head0)) * ny)
        dot1 = None if head1 is None else (
            math.cos(math.radians(head1)) * -nx + math.sin(math.radians(head1)) * -ny)
        return (side0, side1), (head0, head1), (dot0, dot1)

    # Invisible paths and slope-arrow geometry can share endpoints with the roof graph. An
    # arrow shaft is removed only when its head stroke is also in the graph; this avoids
    # deleting a legitimate hip that happens to carry a coincident slope arrow.
    for item in [item for role in roles for item in groups[role]]:
        if float(item.get("width") or 0.0) <= 0.0:
            drop(item, "zero-width non-roof path")
    for ax, ay, heading in arrows:
        live = [item for role in roles for item in groups[role]]
        shafts = []
        for item in live:
            mx, my = midpoint(item)
            if (math.hypot(mx - ax, my - ay) <= 3.0
                    and 20.0 <= length_pts(item) <= 150.0
                    and angle_delta(_seg_angle(item), heading) <= 5.0):
                shafts.append(item)
        for shaft in shafts:
            x1, y1, x2, y2 = shaft["seg"]
            vx, vy = math.cos(math.radians(heading)), math.sin(math.radians(heading))
            head = max(((x1, y1), (x2, y2)),
                       key=lambda point: (point[0] - ax) * vx + (point[1] - ay) * vy)
            head_parts = []
            for item in live:
                if item is shaft or length_pts(item) > 22.0:
                    continue
                sx1, sy1, sx2, sy2 = item["seg"]
                if min(math.hypot(sx1 - head[0], sy1 - head[1]),
                       math.hypot(sx2 - head[0], sy2 - head[1])) <= 12.0:
                    head_parts.append(item)
            if head_parts:
                drop(shaft, "slope-arrow shaft")
                for item in head_parts:
                    drop(item, "slope-arrow head")

    # A long interior axis whose adjacent arrows do not describe a ridge, valley, or step is
    # underlay/annotation, not a roof line. Remove its connected unsupported interior chain.
    excluded_long = []
    excluded_chain = []
    for item in list(groups["transition"]):
        (side0, side1), _heads, dots = evidence(item)
        if (item["len_ft"] >= 20.0 and side0 > 0 and side1 > 0
                and None not in dots and min(abs(dots[0]), abs(dots[1])) < 0.25):
            drop(item, "unsupported long interior line")
            excluded_long.append(item)
    frontier = [point for item in excluded_long
                for point in ((item["seg"][0], item["seg"][1]),
                              (item["seg"][2], item["seg"][3]))]
    while frontier:
        point = frontier.pop()
        for item in [item for role in ("ridge", "rake", "transition")
                     for item in groups[role]]:
            ends = ((item["seg"][0], item["seg"][1]),
                    (item["seg"][2], item["seg"][3]))
            distances = [math.hypot(end[0] - point[0], end[1] - point[1]) for end in ends]
            if min(distances) > 4.0:
                continue
            (side0, side1), _heads, dots = evidence(item)
            if (side0 <= 0 or side1 <= 0 or None in dots
                    or min(abs(dots[0]), abs(dots[1])) >= 0.25):
                continue
            old_role = drop(item, "unsupported connected interior line")
            excluded_chain.append((item, old_role))
            frontier.append(ends[1 - distances.index(min(distances))])
            break

    # Plane-bound arrow evidence supersedes nearest-on-sheet guesses only in the ambiguous
    # classes. This keeps already-verified hips and exterior gables stable.
    for item in list(groups["transition"]):
        (side0, side1), heads, dots = evidence(item)
        x1, y1, x2, y2 = item["seg"]
        length = length_pts(item) or 1.0
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        if (side0 > 0 and side1 > 0 and side0 != side1 and None not in dots
                and dots[0] > 0.70 and dots[1] > 0.70):
            move(item, "ridge", "two roof planes fall away from line")
        elif (side0 > 0 and side1 > 0 and side0 != side1
              and ((heads[0] is None) ^ (heads[1] is None))):
            head = heads[0] if heads[0] is not None else heads[1]
            along = abs(math.cos(math.radians(head)) * ux
                        + math.sin(math.radians(head)) * uy)
            if along > 0.70:
                move(item, "rake", "single roof-plane arrow runs along step edge")

    for item in list(groups["hip_valley"]):
        (side0, side1), _heads, dots = evidence(item)
        if (item["len_ft"] <= 1.25 and side0 > 0 and side1 > 0 and side0 != side1
                and None not in dots and dots[0] > 0.50 and dots[1] > 0.50):
            move(item, "ridge", "short two-plane ridge connector")

    ridge_ends = [point for item in groups["ridge"]
                  for point in ((item["seg"][0], item["seg"][1]),
                                (item["seg"][2], item["seg"][3]))]
    for item in list(groups["rake"]):
        side0, side1, _nx, _ny = side_labels(item)
        roof_plane = side0 if side0 > 0 and side1 == 0 else (
            side1 if side1 > 0 and side0 == 0 else None)
        head = plane_arrow(roof_plane, item) if roof_plane is not None else None
        if head is None:
            continue
        x1, y1, x2, y2 = item["seg"]
        length = length_pts(item) or 1.0
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        along = abs(math.cos(math.radians(head)) * ux
                    + math.sin(math.radians(head)) * uy)
        touches_ridge = any(
            min(math.hypot(ex - x1, ey - y1), math.hypot(ex - x2, ey - y2)) <= touch
            for ex, ey in ridge_ends)
        if along < 0.30 and not touches_ridge:
            move(item, "eave", "own-plane arrow falls across boundary")

    # Thin open ridge continuations may not divide the flood mask, but their junction with a
    # verified ridge still identifies them topologically.
    for item in list(groups["rake"]):
        side0, side1, _nx, _ny = side_labels(item)
        if float(item.get("width") or 0.0) > 0.30 or side0 <= 0 or side0 != side1:
            continue
        x1, y1, x2, y2 = item["seg"]
        if any(min(math.hypot(ex - x1, ey - y1), math.hypot(ex - x2, ey - y2)) <= touch
               for ex, ey in ridge_ends):
            move(item, "ridge", "thin continuation touches verified ridge")

    # Close only short, axis-aligned gaps from a rejected interior chain to an exterior edge.
    # The inherited ridge branch is construction topology; no plan identity or coordinates
    # participate in this inference.
    scale_candidates = sorted(length_pts(item) / item["len_ft"]
                              for item in segs if item.get("len_ft", 0) > 0)
    scale_ppf = float(ppf or scale_candidates[len(scale_candidates) // 2])
    boundaries = [item for role in ("eave", "rake") for item in groups[role]]

    def nearest_point(item, point):
        x1, y1, x2, y2 = item["seg"]
        dx, dy = x2 - x1, y2 - y1
        denominator = dx * dx + dy * dy
        t = 0.0 if denominator == 0 else max(
            0.0, min(1.0, ((point[0] - x1) * dx + (point[1] - y1) * dy) / denominator))
        nearest = x1 + t * dx, y1 + t * dy
        return math.hypot(nearest[0] - point[0], nearest[1] - point[1]), nearest

    for item in excluded_long:
        for point in ((item["seg"][0], item["seg"][1]),
                      (item["seg"][2], item["seg"][3])):
            candidates = sorted(
                ((*nearest_point(edge, point), edge) for edge in boundaries),
                key=lambda candidate: (candidate[0], candidate[1][0], candidate[1][1]),
            )
            if not candidates:
                continue
            distance, nearest, _edge = candidates[0]
            if not (1.0 < distance <= scale_ppf * 1.25
                    and (abs(nearest[0] - point[0]) <= 1.0
                         or abs(nearest[1] - point[1]) <= 1.0)):
                continue
            connected_roles = [
                role for chain_item, role in excluded_chain
                if min(math.hypot(chain_item["seg"][0] - point[0],
                                  chain_item["seg"][1] - point[1]),
                       math.hypot(chain_item["seg"][2] - point[0],
                                  chain_item["seg"][3] - point[1])) <= 4.0
            ]
            if "ridge" not in connected_roles:
                continue
            inferred = {"seg": (point[0], point[1], nearest[0], nearest[1]),
                        "len_ft": distance / scale_ppf,
                        "inferred_by": "short topology closure"}
            groups["ridge"].append(inferred)
            refinements.append({"action": "add", "new_role": "ridge",
                                "segment": inferred["seg"],
                                "reason": inferred["inferred_by"]})
    return groups, refinements


def classify_roof_lines(page, ppf=None, tol=4.0, axis_tol=10.0, probe=8.0, touch=8.0):
    """Split a ROOF PLAN's linework into EAVE / RAKE / RIDGE / HIP_VALLEY.

    Gutters run on EAVES. Fascia runs on EAVE + RAKE. Drip edge follows eave + rake.
    Hip-and-ridge cap follows RIDGE + HIP. Splitting the roof line by type is what makes
    those four trades measurable instead of one undifferentiated perimeter number.

    Geometry rules, in order:
      1. Duplicate strokes are collapsed first -- a raw length is roughly double.
      2. BOUNDARY vs INTERIOR: step perpendicular from the segment midpoint; a segment with
         solid roof on one side only is on the boundary.
      3. INTERIOR: axis-aligned -> RIDGE; diagonal -> HIP_VALLEY.
      4. BOUNDARY parallel to the nearest ridge -> EAVE.
         BOUNDARY perpendicular to it -> RAKE, but only where a ridge END actually touches
         the segment (a true gable). If hips meet it instead, the roof turns down and it is
         still an EAVE -- that is what separates a hip roof from a gable.
      5. No ridge found at all -> every boundary run is an EAVE.

    Returns {eave_lf, rake_lf, ridge_lf, hip_valley_lf, fascia_lf, gutter_lf, segments...}.
    """
    iso = roof_outline_segments(page, ppf)
    raw = iso.get("segments") or []
    if not raw:
        return {"confidence": "low", "note": iso.get("note", "no roof segments isolated"),
                "eave_lf": None}
    base = {"mode": "vector", "confidence": iso.get("confidence")}
    segs = _dedupe_segments(raw, tol)
    mask = _exterior_mask(segs)
    boundary, interior = [], []
    for s in segs:
        x1, y1, x2, y2 = s["seg"]
        L = math.hypot(x2 - x1, y2 - y1) or 1.0
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        # Sample along the run, not just the midpoint: on a long eave broken by a wing the
        # midpoint alone can sit against interior linework and mis-call the whole segment.
        votes_b = 0
        for f in (0.25, 0.5, 0.75):
            sx, sy = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
            a = _is_exterior(sx + nx * probe, sy + ny * probe, mask)
            b = _is_exterior(sx - nx * probe, sy - ny * probe, mask)
            if a != b:
                votes_b += 1
        (boundary if votes_b >= 2 else interior).append(s)

    # A RIDGE has the SAME roof sloping away on both sides. A line where a shallow shed roof
    # runs into a steeper roof is NOT a ridge -- Jason, marking up the roberts overlay: "that
    # is a shed roof that comes in to the steeper roof and will just be regular shingles."
    # It takes no ridge cap, so counting it inflates the cap order. Different pitch callouts
    # either side is the tell, and pitch callouts are on every roof plan.
    # SLOPE ARROWS decide this, because that is what Jason reads. The head points downslope.
    arrows = slope_arrows(page)
    field = _pitch_field(page)
    ridge, hipval, transition, step_rakes = [], [], [], []
    for s in interior:
        a = _seg_angle(s)
        axis = a < axis_tol or a > 180 - axis_tol or abs(a - 90) < axis_tol
        if not axis:
            hipval.append(s)
            continue
        x1, y1, x2, y2 = s["seg"]
        L = math.hypot(x2 - x1, y2 - y1) or 1.0
        nx, ny = -(y2 - y1) / L, (x2 - x1) / L
        # A confirmed pitch CHANGE across the line is decisive and was verified by Jason on
        # roberts, so it is tested before the arrows and cannot be overridden by them.
        lo, hi = _pitch_each_side(s["seg"], nx, ny, field)
        if lo is not None and hi is not None and lo != hi:
            transition.append(s)
            continue
        left, right = _arrow_each_side(s["seg"], nx, ny, arrows)
        if left is not None and right is not None:
            # Positive dot = that side's roof falls AWAY from the line.
            dl = math.cos(math.radians(left)) * nx + math.sin(math.radians(left)) * ny
            dr = math.cos(math.radians(right)) * -nx + math.sin(math.radians(right)) * -ny
            if dl > 0 and dr > 0:
                ridge.append(s)          # roof falls away both sides -> true ridge, takes cap
            elif dl < 0 and dr < 0:
                hipval.append(s)         # roof falls into the line from both sides -> valley
            else:
                transition.append(s)     # both sides fall the SAME way -> shed/step, no cap
        elif left is not None or right is not None:
            # Roof on ONE side only. The flood fill called this interior because a lower roof
            # abuts it -- a step-down -- so it never saw exterior on either side. The arrow
            # settles it: running ALONGSIDE the line means the roof falls past it and stops,
            # which is a RAKE, not a ridge. Jason marked exactly this run on roberts.
            # Requiring the arrow to be parallel is what keeps genuine ridges out: on a ridge
            # the arrows sit on both sides, so this branch is never reached for one.
            head = left if left is not None else right
            ux, uy = (x2 - x1) / L, (y2 - y1) / L
            along = abs(math.cos(math.radians(head)) * ux + math.sin(math.radians(head)) * uy)
            if along > 0.70:
                boundary.append(s)
                step_rakes.append(s)
            else:
                ridge.append(s)
        else:
            lo, hi = _pitch_each_side(s["seg"], nx, ny, field)
            (transition if (lo is not None and hi is not None and lo != hi)
             else ridge).append(s)

    # A boundary run with roof on one side only: the arrow tells eave from rake. An arrow
    # pointing ACROSS the line means the roof falls to it -- an eave, where the gutter goes.
    # An arrow running ALONGSIDE it means the roof falls past it -- a rake.
    reclassified_rakes = []
    for s in list(boundary):
        x1, y1, x2, y2 = s["seg"]
        L = math.hypot(x2 - x1, y2 - y1) or 1.0
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = -uy, ux
        # Use the arrow on the side the ROOF is on. Plane-bound lookup was tried here and
        # REGRESSED the suite (roberts fascia -2.6% -> -6.5%, and the step vertical fell out
        # of rake), so nearest-on-the-roof-side stands until something demonstrably beats it.
        la, ra = _arrow_each_side(s["seg"], nx, ny, arrows)
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        side0_out = _is_exterior(mx + nx * probe, my + ny * probe, mask)
        side1_out = _is_exterior(mx - nx * probe, my - ny * probe, mask)
        if side0_out and not side1_out:
            head = ra
        elif side1_out and not side0_out:
            head = la
        else:
            head = la if la is not None else ra
        if head is None:
            continue
        along = abs(math.cos(math.radians(head)) * ux + math.sin(math.radians(head)) * uy)
        if along > 0.70:
            reclassified_rakes.append(s)

    arrow_rakes = {id(x) for x in reclassified_rakes} | {id(x) for x in step_rakes}
    ridge_dirs = [_seg_angle(s) for s in ridge]
    ridge_ends = [pt for s in ridge for pt in ((s["seg"][0], s["seg"][1]), (s["seg"][2], s["seg"][3]))]
    eave, rake = [], []
    for s in boundary:
        if id(s) in arrow_rakes:
            rake.append(s)
            continue
        if not ridge_dirs:
            eave.append(s)
            continue
        a = _seg_angle(s)
        perp = min(abs((a - rd) % 180 - 90) for rd in ridge_dirs) < axis_tol
        x1, y1, x2, y2 = s["seg"]
        gable = any(min(math.hypot(ex - x1, ey - y1), math.hypot(ex - x2, ey - y2)) <= touch
                    for ex, ey in ridge_ends)
        (rake if (perp and gable) else eave).append(s)

    groups, refinements = _refine_roof_line_topology(
        page,
        {"eave": eave, "rake": rake, "ridge": ridge, "hip_valley": hipval,
         "transition": transition},
        segs, mask, arrows, ppf=ppf, probe=probe, touch=touch,
    )
    eave, rake, ridge = groups["eave"], groups["rake"], groups["ridge"]
    hipval, transition = groups["hip_valley"], groups["transition"]

    # A roof PLAN is a top-down projection. An eave and a ridge are level, so their drawn
    # length is their true length. A RAKE and a HIP/VALLEY run UP the slope, so the drawn
    # length is only the horizontal leg -- true length is that times the pitch factor. Both
    # houses read ~18-19% short against the sub's quote before this correction, which is
    # exactly the shortfall the projection produces.
    pf = 1.0
    calls = _pitch_calls(page)
    if calls:
        pf = sum(pitch_factor(r) for r in calls) / len(calls)
    ft = lambda v: round(sum(x["len_ft"] for x in v), 1)
    slope_ft = lambda v: round(sum(x["len_ft"] for x in v) * pf, 1)
    out = {"mode": base.get("mode"), "confidence": base.get("confidence"),
           "pitch_factor": round(pf, 4), "pitch_calls": calls,
           "raw_segments": len(raw), "unique_segments": len(segs),
           "raw_lf": round(sum(x["len_ft"] for x in raw), 1),
           "topology_refinements": refinements,
           "eave_lf": ft(eave), "rake_lf": slope_ft(rake), "ridge_lf": ft(ridge),
           "hip_valley_lf": slope_ft(hipval),
           "rake_plan_lf": ft(rake), "hip_valley_plan_lf": ft(hipval),
           "transition_lf": ft(transition),
           "eave": eave, "rake": rake, "ridge": ridge, "hip_valley": hipval,
           "transition": transition}
    out["fascia_lf"] = round(out["eave_lf"] + out["rake_lf"], 1)
    out["gutter_lf"] = out["eave_lf"]
    return out


def apply_roof_line_review(classified, corrections, ppf=None, match_tol=1.0):
    """Apply an audited colored-overlay review to a roof-line classification.

    The base classifier stays plan-agnostic. Human review is a separate, fail-closed layer:
    white-marked segments are removed, colored segments are reclassified, and missed short
    connectors can be added. Corrections identify geometry in PDF points, so rendering zoom
    and screenshot size cannot change what was approved.
    """
    roles = ("eave", "rake", "ridge", "hip_valley", "transition")
    groups = {role: [dict(segment) for segment in classified.get(role, []) or []]
              for role in roles}
    applied = []

    def endpoint_error(left, right):
        a1, a2 = left[:2], left[2:]
        b1, b2 = right[:2], right[2:]
        direct = max(math.hypot(a1[0] - b1[0], a1[1] - b1[1]),
                     math.hypot(a2[0] - b2[0], a2[1] - b2[1]))
        reverse = max(math.hypot(a1[0] - b2[0], a1[1] - b2[1]),
                      math.hypot(a2[0] - b1[0], a2[1] - b1[1]))
        return min(direct, reverse)

    def find_segment(target):
        matches = []
        for role in roles:
            for index, segment in enumerate(groups[role]):
                error = endpoint_error(tuple(target), tuple(segment["seg"]))
                if error <= match_tol:
                    matches.append((error, role, index, segment))
        if not matches:
            raise ValueError(f"review segment not found within {match_tol} PDF points: {target}")
        matches.sort(key=lambda item: item[0])
        if len(matches) > 1 and abs(matches[0][0] - matches[1][0]) < 1e-6:
            raise ValueError(f"review segment is ambiguous: {target}")
        return matches[0]

    for correction in corrections:
        action = correction.get("action")
        target = correction.get("segment")
        if not isinstance(target, list) or len(target) != 4:
            raise ValueError(f"review correction requires four PDF coordinates: {correction}")
        if action in ("remove", "reclassify"):
            _error, old_role, index, segment = find_segment(target)
            groups[old_role].pop(index)
            new_role = correction.get("role") if action == "reclassify" else None
            if new_role is not None:
                if new_role not in roles:
                    raise ValueError(f"unknown reviewed roof-line role: {new_role}")
                segment["review_scope"] = correction.get("scope", "main")
                segment["review_source"] = correction.get("source", "human colored overlay")
                groups[new_role].append(segment)
            applied.append({"action": action, "old_role": old_role, "new_role": new_role,
                            "segment": target})
        elif action == "add":
            role = correction.get("role")
            if role not in roles:
                raise ValueError(f"unknown reviewed roof-line role: {role}")
            if ppf is None or ppf <= 0:
                raise ValueError("ppf is required to add a reviewed roof-line segment")
            try:
                find_segment(target)
            except ValueError as exc:
                if "not found" not in str(exc):
                    raise
            else:
                raise ValueError(f"reviewed add duplicates an existing segment: {target}")
            x1, y1, x2, y2 = (float(value) for value in target)
            groups[role].append({
                "seg": (x1, y1, x2, y2),
                "len_ft": math.hypot(x2 - x1, y2 - y1) / ppf,
                "review_scope": correction.get("scope", "main"),
                "review_source": correction.get("source", "human colored overlay"),
            })
            applied.append({"action": action, "old_role": None, "new_role": role,
                            "segment": target})
        else:
            raise ValueError(f"unknown roof-line review action: {action}")

    pf = float(classified.get("pitch_factor") or 1.0)
    flat_ft = lambda segments: round(sum(item["len_ft"] for item in segments), 1)
    slope_ft = lambda segments: round(sum(item["len_ft"] for item in segments) * pf, 1)
    out = dict(classified)
    out.update(groups)
    out.update({
        "eave_lf": flat_ft(groups["eave"]),
        "rake_lf": slope_ft(groups["rake"]),
        "ridge_lf": flat_ft(groups["ridge"]),
        "hip_valley_lf": slope_ft(groups["hip_valley"]),
        "rake_plan_lf": flat_ft(groups["rake"]),
        "hip_valley_plan_lf": flat_ft(groups["hip_valley"]),
        "transition_lf": flat_ft(groups["transition"]),
        "review_status": "human-reviewed",
        "review_corrections": list(corrections),
        "reviewed_corrections": applied,
    })
    out["eave_main_lf"] = flat_ft(
        [item for item in groups["eave"] if item.get("review_scope", "main") != "porch"])
    out["eave_porch_lf"] = flat_ft(
        [item for item in groups["eave"] if item.get("review_scope") == "porch"])
    out["fascia_lf"] = round(out["eave_lf"] + out["rake_lf"], 1)
    out["gutter_lf"] = out["eave_lf"]
    return out


ROOF_LINE_COLORS = {"eave": (0.0, 0.65, 0.0), "rake": (0.0, 0.35, 1.0),
                    "ridge": (0.9, 0.0, 0.0), "hip_valley": (1.0, 0.55, 0.0),
                    "transition": (0.55, 0.0, 0.75)}


def render_roof_line_overlay(page, out_path, classified=None, zoom=2.2, width=5.0):
    """Draw the EAVE / RAKE / RIDGE / HIP-VALLEY split back onto the sheet as a PNG.

    A measurement nobody can see is a measurement nobody can check. Jason has to be able to
    point at a line and say "that is not an eave" -- this is the only honest way to close the
    gap between what the engine thinks it measured and what is really on the plan.
    """
    import fitz
    r = classified or classify_roof_lines(page)
    doc = fitz.open()
    src = page.parent
    new_page = doc.new_page(width=page.rect.width, height=page.rect.height)
    new_page.show_pdf_page(page.rect, src, page.number)
    for kind, color in ROOF_LINE_COLORS.items():
        for sg in r.get(kind, []) or []:
            x1, y1, x2, y2 = sg["seg"]
            new_page.draw_line(fitz.Point(x1, y1), fitz.Point(x2, y2),
                               color=color, width=width)
    legend = [("EAVE  (gutter runs here)", "eave", r.get("eave_lf")),
              ("RAKE  (slope-corrected)", "rake", r.get("rake_lf")),
              ("RIDGE  (takes cap)", "ridge", r.get("ridge_lf")),
              ("HIP / VALLEY", "hip_valley", r.get("hip_valley_lf")),
              ("SHED TRANSITION  (no cap)", "transition", r.get("transition_lf"))]
    x0, y0 = 24, 24
    new_page.draw_rect(fitz.Rect(x0 - 8, y0 - 8, x0 + 380, y0 + 26 * len(legend) + 34),
                       color=(0, 0, 0), fill=(1, 1, 1), width=1.2)
    for i, (label, kind, lf) in enumerate(legend):
        yy = y0 + 18 + i * 26
        new_page.draw_line(fitz.Point(x0, yy - 4), fitz.Point(x0 + 34, yy - 4),
                           color=ROOF_LINE_COLORS[kind], width=6)
        new_page.insert_text(fitz.Point(x0 + 44, yy), f"{label}: {lf} LF",
                             fontsize=13, color=(0, 0, 0))
    yy = y0 + 18 + len(legend) * 26
    new_page.insert_text(fitz.Point(x0, yy), f"FASCIA = eave + rake = {r.get('fascia_lf')} LF",
                         fontsize=13, color=(0, 0, 0))
    new_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(out_path)
    doc.close()
    return {"path": out_path, "eave_lf": r.get("eave_lf"), "rake_lf": r.get("rake_lf"),
            "ridge_lf": r.get("ridge_lf"), "hip_valley_lf": r.get("hip_valley_lf"),
            "fascia_lf": r.get("fascia_lf")}


def roof_segments(page, ppf=None):
    """Convenience: the (x0,y0,x1,y1) roof-line segments from classify_lines -- ready to render
    clean or feed a footprint measurement. VECTOR mode returns the styled roof lines (outline +
    ridge/valley, walls & dims stripped); RASTER mode returns the recovered footprint polygon's
    edges (a closed outline, no interior ridge/valley)."""
    c = classify_lines(page, ppf)
    if c["mode"] == "vector":
        return [s["seg"] for s in c["roof"]]
    poly = c.get("roof") or []                            # raster: closed polygon of points -> edges
    return [(poly[i][0], poly[i][1], poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1])
            for i in range(len(poly))]


def roof_footprint(page, ppf=None, zoom=3.0, overlay_path=None):
    """VISION-GUIDED roof FOOTPRINT -- the reliable replacement for a blind trace_footprint on a
    cluttered roof plan. classify_lines isolates the roof lines, then we flood the area they
    enclose (Burns: 2,678 SF clean vs 1,915 SF blind). Returns area_sf, perim_lf, corners, mode,
    scale_ppf. ⛔ This is the PLAN-VIEW footprint incl. overhang -- multiply by pitch factor(s)
    PER ZONE for true surface, and measure porch roofs separately."""
    import cv2, numpy as np, fitz
    c = classify_lines(page, ppf)
    if c["mode"] == "raster":                             # raster path already computed the footprint
        return {"area_sf": c.get("footprint_sf"), "perim_lf": c.get("perim_lf"),
                "corners": len(c.get("roof", [])), "mode": "raster", "scale_ppf": c.get("scale_ppf"),
                "confidence": c.get("confidence", "review"), "flags": [c.get("note")] if c.get("note") else []}
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    segs = [s["seg"] for s in c["roof"]]
    if not segs or not ppf:
        return {"area_sf": None, "perim_lf": None, "corners": 0, "mode": c["mode"],
                "note": "no roof lines isolated or no scale"}
    ppx = ppf * zoom
    W, H = int(page.rect.width * zoom), int(page.rect.height * zoom)
    mask = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in segs:
        cv2.line(mask, (int(x0 * zoom), int(y0 * zoom)), (int(x1 * zoom), int(y1 * zoom)), 255, 3)
    k = int(ppx * 1.2); ker = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ker)
    ff = closed.copy(); hh, ww = ff.shape
    cv2.floodFill(ff, np.zeros((hh + 2, ww + 2), np.uint8), (0, 0), 255)
    solid = closed | cv2.bitwise_not(ff)
    cnts, _ = cv2.findContours(solid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return {"area_sf": None, "perim_lf": None, "corners": 0, "mode": c["mode"],
                "note": "roof lines did not enclose a region"}
    cc = max(cnts, key=cv2.contourArea)
    ap = cv2.approxPolyDP(cc, 0.004 * cv2.arcLength(cc, True), True)
    corners = len(ap)
    if overlay_path:
        ov = np.full((H, W, 3), 255, np.uint8)
        for x0, y0, x1, y1 in segs:
            cv2.line(ov, (int(x0 * zoom), int(y0 * zoom)), (int(x1 * zoom), int(y1 * zoom)), (0, 150, 0), 2)
        cv2.drawContours(ov, [ap], -1, (0, 0, 255), 3); cv2.imwrite(overlay_path, ov)
    # ⛔ RELIABILITY VERDICT -- do not silently ship a bad trace (Peterson: no color + 69 corners).
    flags = []
    if c.get("roof_color") is None:
        flags.append("no roof COLOR signal -- isolated by weight only")
    if detect_scale(page)["ppf"] is None:
        flags.append("no vector dimension text -- scale not verified (assumed); confirm w/ a known dim")
    if corners > 24:
        flags.append(f"{corners} corners -- outline likely CORRUPTED (cut-up roof and/or detail "
                     f"vignettes on the sheet). CLIP to the roof, or GREEN-TRACE it, or use Jason's takeoff.")
    conf = "high" if (not flags and c.get("confidence") == "high") else ("low" if corners > 24 else "review")
    return {"area_sf": round(cv2.contourArea(ap) / ppx ** 2, 0),
            "perim_lf": round(cv2.arcLength(ap, True) / ppx, 0),
            "corners": corners, "mode": c["mode"], "scale_ppf": round(ppf, 3),
            "confidence": conf, "flags": flags}


def render_no_redline(page, out_path, zoom=2.2):
    """Render a sheet with red redline markups removed (set to white) to declutter scans
    before reading the underlying drawing/dimensions."""
    import cv2, numpy as np, fitz
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
    r, g, b = img[:, :, 0].astype(int), img[:, :, 1].astype(int), img[:, :, 2].astype(int)
    red = (r > 110) & (r - g > 45) & (r - b > 45)
    img[red] = (255, 255, 255)
    cv2.imwrite(out_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return out_path


def render_with_grid(page, out_path, step=200, zoom=1.3):
    """Render a sheet with a labeled pt-coordinate grid for VISION-GUIDED region selection.
    The model views this, reads the main drawing's bbox in page points (excluding title
    block / section details / 3D views), and passes that as the `clip` to the measurement
    bricks. Pure-geometry region detection is unreliable here (section details, borders,
    and dim lines mimic the building), so vision picks the region; code measures it. The
    measurement bricks are built to be invariant to imprecise bounds."""
    import cv2, numpy as np, fitz
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].copy()
    W, H = page.rect.width, page.rect.height
    for x in range(0, int(W) + 1, step):
        X = int(x * zoom); cv2.line(img, (X, 0), (X, img.shape[0]), (0, 150, 255), 1)
        cv2.putText(img, str(x), (X + 2, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 90, 200), 1)
    for y in range(0, int(H) + 1, step):
        Y = int(y * zoom); cv2.line(img, (0, Y), (img.shape[1], Y), (0, 150, 255), 1)
        cv2.putText(img, str(y), (2, Y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 90, 200), 1)
    cv2.imwrite(out_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return out_path


def measure_wall_lf(page, clip, zoom=4.0, ppf=None, band_ft=1.1, overlay_path=None):
    """Centerline LENGTH of a poured-wall outline (footer/wall LF) on a foundation sheet.
    Isolates the wall as the largest connected linework (drops section detail / notes / 3D),
    closes the double-line faces into one band, skeletonizes, and sums the centerline.
    Holbrook p3: 162 LF vs 178 actual (~9% low; from a 774 failure with naive summing).
    NOTE: pass a `clip` that excludes the wall-section detail + title block; remaining gap is
    judgment on angled returns vs a separately-billed retaining wall."""
    import cv2, numpy as np, fitz
    from skimage.morphology import skeletonize
    if ppf is None:
        d = detect_scale(page); ppf = d["ppf"] or 18.0
    ppx = ppf * zoom
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = img[:, :, :3].copy()
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, bw = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY_INV)
    # drop small components (notes/text) so they can't beat the wall when banded -> makes
    # the result invariant to the exact clip (region only needs to exclude title block +
    # section detail; text inside the clip is harmless).
    nc, lc, sc, _ = cv2.connectedComponentsWithStats(bw, 8)
    mf = 2.5 * ppx
    keep = np.zeros_like(bw)
    for i in range(1, nc):
        if max(sc[i, cv2.CC_STAT_WIDTH], sc[i, cv2.CC_STAT_HEIGHT]) >= mf:
            keep[lc == i] = 255
    k = max(3, int(round(ppx * band_ft)))
    band = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(band, 8)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    skel = skeletonize(lab == big)
    ys, xs = np.where(skel)
    pts = set(zip(ys.tolist(), xs.tolist()))
    L = 0.0
    for (y, x) in pts:
        for dy, dx, w in [(0, 1, 1), (1, 0, 1), (1, 1, 1.4142), (1, -1, 1.4142)]:
            if (y + dy, x + dx) in pts:
                L += w
    if overlay_path:
        ov = rgb.copy(); ov[skel] = (255, 0, 0)
        cv2.imwrite(overlay_path, cv2.cvtColor(ov, cv2.COLOR_RGB2BGR))
    cl = L / ppx
    # billed/takeoff wall LF = centerline / 0.90 (skeleton cuts corners ~10% on jogged
    # basement walls; 0.90 calibrated on 3 houses: Holbrook/Lankford/Pace, all within ~1%).
    return {"centerline_lf": round(cl, 1), "wall_lf": round(cl / 0.90, 1)}


# cabinet CODE grammar — the plan LABELS every casework box with its nominal width.
# Width = the first 2 digits AFTER the letter prefix (e.g. B36 = 36"w base; SB50 = 50"
# sink base; DCB36R = 36" diagonal-corner base; U242496 = 24" full-height utility tower;
# OTC33.. = 33" oven tall cabinet; W3624 = 36" upper). This is GIVEN DATA (Guardrail #1:
# a printed number beats a pixel trace) — Jason's own takeoff method (calibration #34/#39).
_CAB_UPPER = re.compile(r"^(?:DCW|WB|W)(\d{2})")           # wall/upper cabinet
_CAB_TALL = re.compile(r"^(?:U\d|OTC(\d{2})|FHB?(\d{2})|T(\d{2})|PC(\d{2}))")  # full-height
_CAB_LOWER = re.compile(r"^(?:DCB|SB|DB|VB|BC|BD|PB|B)(\d{2})")  # base / lower


def _classify_cab(tag):
    """(klass, width_in) for a cabinet code, or None if not a cabinet tag.
    Order matters: uppers (W) and tall (U/OTC/FH/T/PC) are tested before bare 'B' base."""
    m = _CAB_UPPER.match(tag)
    if m:
        return ("upper", int(m.group(1)))
    m = _CAB_TALL.match(tag)
    if m:
        w = next((int(g) for g in m.groups() if g), 24)  # U-towers default 24" wide
        return ("tall", w)
    m = _CAB_LOWER.match(tag)
    if m:
        return ("lower", int(m.group(1)))
    return None


def _island_faces_lf(page, tags_bbox, ppf):
    """Island run LF = the two long parallel cabinet FACES (a plan island is a closed box
    with interior on BOTH long sides, so LF counts both faces). Given the island tags'
    bbox, find the two longest near-parallel horizontal (or vertical) segments that span
    the box and sum their lengths. Returns (island_lf, n_faces)."""
    bx0, by0, bx1, by1 = tags_bbox
    pad = 1.6 * ppf   # island faces sit ~1-2 ft outside the tag band (tags are centered
                      # in each 24"-deep row; the outer slab faces are beyond them)
    H, V = [], []
    for path in page.get_drawings():
        for it in path["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
            if not (bx0 - pad <= mx <= bx1 + pad and by0 - pad <= my <= by1 + pad):
                continue
            if abs(a.y - b.y) < 1.0:
                H.append((abs(a.x - b.x) / ppf, (a.y + b.y) / 2))
            elif abs(a.x - b.x) < 1.0:
                V.append((abs(a.y - b.y) / ppf, (a.x + b.x) / 2))
    # island long axis = whichever direction has the longest spanning faces
    box_w, box_h = (bx1 - bx0) / ppf, (by1 - by0) / ppf
    faces = H if box_w >= box_h else V
    faces = [f for f in faces if f[0] >= 0.7 * max(box_w, box_h)]  # spanning faces only
    faces.sort(key=lambda f: -f[0])
    # take the two extreme parallel faces (top+bottom, or left+right)
    if len(faces) < 2:
        return (round(faces[0][0], 2) if faces else 0.0, len(faces))
    top = max(faces, key=lambda f: f[1])
    bot = min(faces, key=lambda f: f[1])
    return (round(top[0] + bot[0], 2), 2)


def _cluster_cabs(cabs, link_ft, ppf):
    """Single-linkage spatial clustering of cabinet tags: two tags join a cluster if their
    centers are within link_ft. Returns list of clusters (each a list of cab dicts). Used to
    AUTO-ISOLATE the kitchen casework cluster so the caller need not hand-tune a tight clip
    ('works every time' = no bespoke clip per plan). The kitchen is the cluster with the most
    total cabinet width (it has the most casework)."""
    link = link_ft * ppf
    unassigned = list(cabs)
    clusters = []
    while unassigned:
        seed = unassigned.pop()
        cur = [seed]
        changed = True
        while changed:
            changed = False
            for c in list(unassigned):
                ccx, ccy = (c["x0"] + c["x1"]) / 2, (c["y0"] + c["y1"]) / 2
                for m in cur:
                    mcx, mcy = (m["x0"] + m["x1"]) / 2, (m["y0"] + m["y1"]) / 2
                    if abs(ccx - mcx) <= link and abs(ccy - mcy) <= link:
                        cur.append(c)
                        unassigned.remove(c)
                        changed = True
                        break
        clusters.append(cur)
    return clusters


def cabinet_run_lf(page, clip, ppf=None, room=None, auto_cluster=True, link_ft=7.0):
    """Base-cabinet RUN LENGTH (LF) off the FLOOR PLAN, TAG-ANCHORED (rebuild per DEV_SPEC B).

    METHOD (why this replaced the bare-offset-line scaffold): the flattened redline PDF puts
    cabinet faces in the SAME vector layer as the floor-tile hatch + dim lines, so a "segment
    offset ~24" from a wall" filter cannot separate casework (it returned ~19 LF tight / ~900
    LF loose on the Pack kitchen). But the plan LABELS every box with its nominal width
    (B36 = 36", SB50 = 50", DCB36R = 36" corner, U242496 = 24" tower...). Cabinet
    width tags are direct item dimensions, not an area schedule. So we:
      1. read every cabinet CODE in `clip`, dedupe double-draws, classify lower/upper/tall;
      2. detect the ISLAND (a lower-cabinet cluster with a long closed box, interior on both
         long faces) and measure its run as the TWO parallel faces x length (a plan island's
         LF counts both faces) — geometry, because tag widths under-count an island;
      3. base run = perimeter lowers (tag widths) + island (face geometry) + tall (tag widths).
         Uppers are reported separately (not part of the BASE run).

    CLIP-ROBUST (auto_cluster=True, default): the kitchen casework cluster is AUTO-ISOLATED
    (densest single-linkage cluster of base tags by total width), so you can pass a GENEROUS
    or even WHOLE-PAGE clip and still land the same answer — no hand-tuned clip per plan.
    Pack: clips from (1140,400,1420,600) up to the whole page (0,0,2592,1728) ALL return
    base_run_lf 48.7 LF, island 24.0 captured.

    VALIDATED — 1 kitchen only: PACK kitchen (ppf 13.593) base_run_lf = 48.7 LF vs Jason's
    hand takeoff 49.5 (-1.6%, within +/-10%) WITH the island captured (24.0 LF vs his 24.41,
    -1.7%). = lower 12.0 + island 24.0 + tall 12.75; matches calibration #34.

    ⚠️ STATUS: calibrated=False — and it STAYS False (DEV_SPEC B3 needs >=3 real kitchens).
    HONEST FINDING (data point #44): the tag-anchored method requires the plan to LABEL each
    base box with a width code IN PLAN VIEW ON THE FLOOR PLAN. That holds for Pack, but:
      - WILSON tags cabinets only on a separate cabinet-DETAIL sheet (p15) that mixes plan
        callouts with multiple elevation views — the same box appears twice (double-count),
        and the island is an elevation, not a closed plan box, so face-geometry can't read it.
      - BURNS tags NO width codes on the floor plan at all (only room labels + ELEVATION
        bubbles E5/E6/E7).
    So the method does NOT generalize to Wilson/Burns as-is; the 3-kitchen bar is unmet with
    the tag method. Kitchen GROUND TRUTH was found for all three (Jason's own files) and is
    recorded in calibration #44 (Pack base 49.5, Wilson 36, Burns 35.39) for whoever wires
    the next method. Until 3 kitchens pass, this function MUST NOT auto-ship a cabinet number
    (same discipline as the roofing placeholder) — estimate falls back to a hand-traced LF.

    Returns: {base_run_lf, lower_lf, island_lf, tall_lf, upper_lf, island_captured,
              n_cabinets, auto_bbox, calibrated, note}."""
    if ppf is None:
        ppf = detect_scale(page)["ppf"] or 13.5
    x0, y0, x1, y1 = clip
    seen, cabs = set(), []
    for w in page.get_text("words"):
        c = _classify_cab(w[4])
        if not c:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if not (x0 <= cx <= x1 and y0 <= cy <= y1):
            continue
        key = (round(w[0]), round(w[1]), w[4])
        if key in seen:               # exact double-draw at same spot -> one cabinet
            continue
        seen.add(key)
        cabs.append({"x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3],
                     "klass": c[0], "w_in": c[1], "tag": w[4]})

    # --- AUTO-ISOLATE the kitchen casework cluster (no hand-tuned clip needed).
    # Cluster the BASE (lower+tall) tags by proximity; the kitchen = the cluster with the
    # most total cabinet width. Then keep only cabs whose center falls in that cluster's
    # padded bbox (this also grabs the uppers sitting over that run). A generous / rough
    # clip now resolves to the same answer as a tight one.
    auto_bbox = None
    if auto_cluster:
        base_tags = [c for c in cabs if c["klass"] in ("lower", "tall")]
        clusters = _cluster_cabs(base_tags, link_ft, ppf)
        if clusters:
            kit = max(clusters, key=lambda cl: sum(c["w_in"] for c in cl))
            pad = 1.5 * ppf
            bx0 = min(c["x0"] for c in kit) - pad
            by0 = min(c["y0"] for c in kit) - pad
            bx1 = max(c["x1"] for c in kit) + pad
            by1 = max(c["y1"] for c in kit) + pad
            auto_bbox = (bx0, by0, bx1, by1)
            cabs = [c for c in cabs
                    if bx0 <= (c["x0"] + c["x1"]) / 2 <= bx1
                    and by0 <= (c["y0"] + c["y1"]) / 2 <= by1]

    lowers = [c for c in cabs if c["klass"] == "lower"]
    talls = [c for c in cabs if c["klass"] == "tall"]
    uppers = [c for c in cabs if c["klass"] == "upper"]

    # --- island detection: a tight cluster of >=3 lowers with an enclosing long box.
    # cluster lowers by proximity; the cluster whose bbox has a long side AND is not
    # against the clip edge (interior on both long faces) is the island.
    island_lf, island_captured, island_ids = 0.0, False, set()
    if len(lowers) >= 3:
        # simple grid cluster on the lowers
        pts = sorted(lowers, key=lambda c: (round(c["y0"] / (2 * ppf)), c["x0"]))
        # group by y-band ~ within 4 ft, then look for a 2-row (back-to-back) cluster
        rows = {}
        for c in lowers:
            rows.setdefault(round(c["y0"] / (2.2 * ppf)), []).append(c)
        # island = two adjacent y-rows of lowers spanning the same x-range (back-to-back)
        rk = sorted(rows)
        for i in range(len(rk) - 1):
            a, b = rows[rk[i]], rows[rk[i + 1]]
            if len(a) < 2 or len(b) < 1:
                continue
            ax = (min(c["x0"] for c in a), max(c["x1"] for c in a))
            bx = (min(c["x0"] for c in b), max(c["x1"] for c in b))
            overlap = min(ax[1], bx[1]) - max(ax[0], bx[0])
            if overlap > 4 * ppf:      # two rows sharing a >4ft x-span = an island
                grp = a + b
                bbox = (min(c["x0"] for c in grp), min(c["y0"] for c in grp),
                        max(c["x1"] for c in grp), max(c["y1"] for c in grp))
                lf, nf = _island_faces_lf(page, bbox, ppf)
                if lf > 0:
                    island_lf, island_captured = lf, nf >= 2
                    island_ids = {id(c) for c in grp}
                break

    perim_lowers = [c for c in lowers if id(c) not in island_ids]
    lower_lf = round(sum(c["w_in"] for c in perim_lowers) / 12.0, 2)
    tall_lf = round(sum(c["w_in"] for c in talls) / 12.0, 2)
    upper_lf = round(sum(c["w_in"] for c in uppers) / 12.0, 2)
    base_run_lf = round(lower_lf + island_lf + tall_lf, 2)

    return {"base_run_lf": base_run_lf, "lower_lf": lower_lf,
            "island_lf": island_lf, "tall_lf": tall_lf, "upper_lf": upper_lf,
            "island_captured": island_captured, "n_cabinets": len(cabs),
            "auto_bbox": tuple(round(v, 1) for v in auto_bbox) if auto_bbox else None,
            "calibrated": False,
            "note": ("TAG-ANCHORED base run; island via parallel faces; kitchen cluster "
                     "auto-isolated (clip-robust). Validated on Pack kitchen only (-1.6%); "
                     "calibrated stays False until >=3 kitchens pass (DEV_SPEC B3). Wilson "
                     "tags its cabinets on a separate elevation-detail sheet (not the floor "
                     "plan) and Burns tags no width codes at all — the tag-anchored method "
                     "does NOT apply to those plans, so the 3-kitchen bar is unmet. Do NOT "
                     "auto-ship; hand-trace fallback until then.")}


# ---------------------------------------------------------------------------
# Brick 3 — slab concrete volume (Jason's flatwork model).
#   4" slab everywhere, EXCEPT: 16"x18" thickened edge around the ENTIRE perimeter
#   of each slab, and 8"x8" grade beams under interior walls.  Concrete + pump trucks
#   are builder-bought (FFCI ~$180/yd); flatwork sub provides all other material+labor.
# ---------------------------------------------------------------------------
def plumbing_estimate(whole, half, base=8000, whole_rate=450, half_rate=400):
    """Plumbing SUB cost (rough + trim), margin-protected. Count fixtures off the plan:
    WHOLE (drain + supply) = toilet, sink, tub, shower, water heater, washer box, sump.
    HALF (supply OR drain only) = dishwasher, fridge/icemaker line, hose bib, floor drain.
    Model = fixed base (service/mobilization/DWV mains) + per-fixture. Calibrated to plumber
    David Holman across 3 houses: base $8,000 + $450/whole + $400/half sits ~3-6% ABOVE his
    actual quotes (Sailview/Holbrook/Wilson) — never under-bids, even small houses where flat
    per-fixture fails. JJCH furnishes fixtures separately; this is labor+rough only."""
    return {"sub_cost": base + whole * whole_rate + half * half_rate,
            "whole": whole, "half": half, "base": base}


def slab_concrete(area_sf, perim_edge_lf, grade_beam_lf=0.0,
                  slab_in=4, edge_w_in=16, edge_d_in=18, gb_in=8,
                  price_per_yd=180.0, over_order=0.0):
    """Cubic yards (and $) of slab concrete. area_sf = total flat slab footprint;
    perim_edge_lf = total thickened-edge run; grade_beam_lf = interior grade beams.
    over_order = fraction added for waste/over-order (concrete is ordered a bit heavy)."""
    # Jason's convention: slab over the full footprint at 4", PLUS the full
    # thickened-edge / grade-beam beam sections (the small slab/beam overlap is left
    # in as conservatism).  Thickened edge runs only where the slab edge is NOT on a
    # foundation-wall footing.  over_order = waste/over-order fraction.
    f = lambda i: i / 12.0
    flat = area_sf * f(slab_in)
    edge = perim_edge_lf * f(edge_w_in) * f(edge_d_in)            # full 16x18 beam
    gb = grade_beam_lf * f(gb_in) * f(gb_in)                       # full 8x8 beam
    cf = (flat + edge + gb) * (1 + over_order)
    yd = cf / 27.0
    return {"yd": round(yd, 1), "flat_yd": round(flat / 27, 1),
            "edge_yd": round(edge / 27, 1), "gb_yd": round(gb / 27, 1),
            "cost": round(yd * price_per_yd, 2)}


# ---------------------------------------------------------------------------
# Trade — FRAMING.  Materials and labor priced SEPARATELY.
#   Labor  = blended $/sf of area UNDER ROOF that gets FRAMED (per-level sum).
#   Material = two Builders FirstSource plug-in quotes: lumber package (incl
#   stick-framed roof) + engineered floor system. Roof is stick-framed -> in pkg.
# ---------------------------------------------------------------------------
FRAMING_LABOR_RATE = 6.00  # $/sf, blended under-roof FRAMED area. JASON LIVE 2026-08-04,
                           # supersedes the $6.50 weighted constant. Framing is NOT turnkey:
                           # material, labor and engineered floor are SEPARATE lines.
                           # The actuals span both sides of this: Wilson 38,210/5,792.59=$6.60,
                           # Watkins 28,862/4,518=$6.39, and $5.35/SF Feb-2025 (cal, conventional
                           # truss single-story). $6.00 is Jason's current blended call inside
                           # that range -- his number wins, but if a job grades over on framing
                           # labor, this constant is the first place to look.
                           # ⚠ framing QUOTES run ~25% under ACTUAL (Wilson labor quote $30,424
                           # vs actual $38,210). Bid the actual, never the quote.

# SQFT-schedule row classification (Jason's "under roof" rule):
#   FRAMED   = heated levels, garage, covered porches/decks  -> count for labor
#   FLATWORK = patios/stoops/walks (slab-on-grade)           -> excluded (paid as flatwork)
_FRAME_FLATWORK = ("patio", "stoop", "sidewalk", "side walk", "driveway", "walk", "concrete")
_FRAME_FRAMED   = ("htd", "heated", "main", "basement", "second", "upper", "third",
                   "loft", "bonus", "attic", "garage", "covered", "porch", "deck", "screen",
                   "expansion", "unfinished", "outdoor", "under roof")  # future-expansion/
                   # unfinished bonus IS framed + in TOTAL UNDER ROOF (Peterson/Fairview)

def classify_area_row(label):
    """Classify a SQFT-schedule row as 'framed' (counts for framing labor),
    'flatwork' (slab-on-grade, excluded), or 'review'.  EXCLUDE wins ties so
    'BASEMENT PATIO' -> flatwork even though it contains 'basement'."""
    L = label.lower()
    if any(k in L for k in _FRAME_FLATWORK):
        return "flatwork"
    if any(k in L for k in _FRAME_FRAMED):
        return "framed"
    return "review"

def read_sqft_schedule(page, min_sf=40, max_sf=12000):
    """Best-effort read of a J&J SQFT schedule: returns [{label, sqft, klass}].
    Area values carry decimals (2406.22); window/door callouts are clean ints
    (10080) -> prefer the last DECIMAL number on a keyword row. ALWAYS show the
    user the extracted table to confirm before trusting it."""
    import re
    rows = {}
    for x0, y0, x1, y1, w, *_ in page.get_text("words"):
        rows.setdefault(round(y0 / 6) * 6, []).append((x0, w))
    out = []
    for y in sorted(rows):
        line = " ".join(w for _, w in sorted(rows[y]))
        if classify_area_row(line) == "review":
            continue                                   # no area keyword on this row
        nums = re.findall(r"\d{2,5}\.\d{1,2}", line) or re.findall(r"\b\d{2,5}\b", line)
        if not nums:
            continue
        val = float(nums[-1])
        if not (min_sf <= val <= max_sf):
            continue
        label = line[:line.rfind(nums[-1])].strip()
        if not any(c.isalpha() for c in label):
            continue
        out.append({"label": label, "sqft": val, "klass": classify_area_row(label)})
    return out


def _is_total_row(label):
    """True if a SQFT-schedule label is a TOTAL / UNDER-ROOF SUMMARY row (not a component).
    Summing a total alongside its components is the 2x framing double-count; read_sqft_schedule_ocr
    already excludes TOTAL|UNDER ROOF -- this makes the text reader + run_takeoff consistent."""
    import re
    return bool(re.search(r"\btotal\b|under\s*roof", label, re.I))


def framed_under_roof_sf(rows):
    """Comparison-only under-roof SF from read_sqft_schedule() rows.

    This helper protects schedule reconciliation from total+component double-counting,
    but its result is never an estimate quantity. Certified component geometry is the
    sole source for run_takeoff pricing:
      + every 'framed' component row (heated levels, garage, covered porches/decks)
      + covered outdoor rows even when 'patio' mislabeled them flatwork (covered = under roof)
      - 'uncovered' slab patios -> flatwork. ⛔ 'uncovered' CONTAINS the substring 'covered', so a
        naive `"covered" in label` wrongly frames a slab patio -- guard it.
      - TOTAL / UNDER-ROOF summary rows -> NEVER summed with their components (the 2x framing
        double-count: 10,074 vs 5,037 on a Davis-sized schedule = ~$33k phantom labor at $6.50/SF).
    If a schedule lists no components, return its total for comparison only."""
    comp, total, n = 0.0, None, 0
    for r in rows:
        if _is_total_row(r["label"]):
            if r.get("sqft"):
                total = r["sqft"]
            continue
        lab = r["label"].lower()
        if "uncovered" in lab:                       # slab-on-grade patio -> flatwork (excluded)
            continue
        if r["klass"] == "framed" or "covered" in lab:
            comp += r["sqft"]; n += 1
    return total if (n == 0 and total is not None) else comp


def framing_estimate(framed_sf, lumber_pkg=0.0, eng_floor=0.0, labor_rate=FRAMING_LABOR_RATE):
    """Framing trade — materials and labor SEPARATE.
      framed_sf  = total area UNDER ROOF that gets FRAMED, summed per level
                   (basement + main + any 2nd + garage + covered porches/decks).
                   Measure each floor on its OWN sheet at its OWN scale (floors
                   don't always stack). EXCLUDE slab-on-grade patios (flatwork), but
                   INCLUDE deck framing (framer frames the deck at normal $/sf; he does
                   NOT do deck flooring or railings -- those are a separate scope).
      labor_rate = blended $/sf. Default $6.50, validated on 2 ACTUALS (Wilson $6.60,
                   Watkins $6.39). NOT the quote rate -- framing quotes run ~25% light.
      lumber_pkg = BFS lumber package quote (all lumber/OSB/subfloor/nails/straps/
                   glue/anchors; STICK-FRAMED ROOF is inside this). Plug-in.
      eng_floor  = BFS engineered floor system (main deck over basement/crawl, any
                   2nd floor, + garage ceiling for the span). Plug-in; slab gets none."""
    labor = round(framed_sf * labor_rate, 2)
    return {"framed_sf": framed_sf, "labor_rate": labor_rate, "labor": labor,
            "lumber_pkg": lumber_pkg, "eng_floor": eng_floor,
            "material": lumber_pkg + eng_floor,
            "total": round(labor + lumber_pkg + eng_floor, 2)}


# ---------------------------------------------------------------------------
# GABLE AREA off an ELEVATION (material-agnostic) -- a HELPER inside the ONE
# exterior-CLADDING takeoff (the siding method), NOT a separate masonry tool.
# Gables are cladding like any wall; a stone gable is measured like a shake/lap
# gable -- only the material+rate switches. Use as part of measuring every wall
# (L*H) + gable (triangle) BY MATERIAL off the elevations.
#   A gable shows two roof RAKES meeting at an apex; each rake is a right
#   triangle (1/2*run*rise), so summing
# 1/2*run*rise over every (deduped) rake = the total gable area, with NO assumed
# height.  Returns a per-gable breakdown (apex x/y, base, rise) so you tag EACH
# gable's material from the elevation's material map -- gables are NOT all one
# material (Pack: garage gable=brick, others=stone). Run on every elevation sheet
# (front/rear/sides) and sum.  Validated Pack 8:12: f/r 610 + sides 855 = 1,465 sf;
# rake slopes read the true pitch and rises self-check vs the story-pole ridges.
# ---------------------------------------------------------------------------
def gable_area(page=None, ppf=None, segments=None, clip=None,
               slope_lo=0.30, slope_hi=1.60, min_run_ft=2.0, min_rise_ft=1.5,
               dedupe_ft=0.8, apex_tol_ft=2.5):
    """Total gable area + per-gable breakdown off an elevation. MATERIAL-AGNOSTIC:
    measures the triangles; you assign stone/brick/shake/siding per gable from the
    elevation. slope band admits roof pitches (~3.6:12 to ~19:12); dedupe drops the
    double-drawn roof-edge+fascia; apex-pairing rejects stray diagonals (a real gable
    pairs L+R rakes). Pass `segments` (list of (x0,y0,x1,y1)) for testing, else a page."""
    import math
    if segments is None:
        if ppf is None:
            ppf = detect_scale(page)["ppf"]
        segments = _lines(page)
    if clip is not None:
        segments = [s for s in segments
                    if clip.x0 <= (s[0]+s[2])/2 <= clip.x1 and clip.y0 <= (s[1]+s[3])/2 <= clip.y1]
    rk = []                                   # each: [tx,ty,bx,by,run,rise,dir] in feet
    for x0, y0, x1, y1 in segments:
        run = abs(x1 - x0) / ppf; rise = abs(y1 - y0) / ppf
        if run < 1e-6:
            continue
        if not (slope_lo <= rise / run <= slope_hi):
            continue
        if run < min_run_ft or rise < min_rise_ft:
            continue
        (tx, ty), (bx, by) = ((x0, y0), (x1, y1)) if y0 < y1 else ((x1, y1), (x0, y0))
        rk.append([tx/ppf, ty/ppf, bx/ppf, by/ppf, run, rise, 1 if bx < tx else -1])
    def _dup(d, r):                           # a double-drawn edge (roof line + fascia) is the
        if r[6] != d[6] or abs(r[4]-d[4]) > max(2.0, 0.25*d[4]):   # SAME rake: same dir, similar
            return False                       # run, OVERLAPPING in x, small PERP offset.
        amin, amax = min(d[0], d[2]), max(d[0], d[2])  # separate gables fail the x-overlap test
        bmin, bmax = min(r[0], r[2]), max(r[0], r[2])
        if min(amax, bmax) - max(amin, bmin) < 0.5 * min(d[4], r[4]):
            return False
        dx, dy = d[2]-d[0], d[3]-d[1]; L = math.hypot(dx, dy) or 1e-9
        mx, my = (r[0]+r[2])/2, (r[1]+r[3])/2
        return abs((mx-d[0])*dy - (my-d[1])*dx)/L < dedupe_ft
    ded = []                                  # (separate gable rakes are many ft apart perp)
    for r in rk:
        if any(_dup(d, r) for d in ded):
            continue
        ded.append(r)
    used = [False]*len(ded); gables = []
    for i, a in enumerate(ded):               # pair a left rake (+1) with its right rake (-1)
        if used[i] or a[6] != 1:
            continue
        best, bestd = None, apex_tol_ft
        for j, b in enumerate(ded):
            if used[j] or b[6] != -1:
                continue
            d = math.hypot(a[0]-b[0], a[1]-b[1])
            if d < bestd:
                bestd, best = d, j
        if best is None:
            continue
        b = ded[best]; used[i] = used[best] = True
        gables.append({"apex_x": round((a[0]+b[0])/2, 1), "apex_y": round((a[1]+b[1])/2, 1),
                       "base_ft": round(abs(a[2]-b[2]), 1), "rise_ft": round(max(a[5], b[5]), 1),
                       "area_sf": round(0.5*abs(a[2]-b[2])*max(a[5], b[5]), 1),
                       "material": None})     # <- caller tags from the elevation map
    unpaired = round(sum(0.5*r[4]*r[5] for k, r in enumerate(ded) if not used[k]), 1)
    total = round(sum(g["area_sf"] for g in gables) + unpaired, 1)
    return {"total_sf": total, "n_gables": len(gables), "unpaired_sf": unpaired,
            "gables": sorted(gables, key=lambda g: -g["area_sf"])}


# ---------------------------------------------------------------------------
# COUNTERTOPS -- measured by SQUARE FOOT, ROOM BY ROOM.  Rates: Level 3
# granite/quartz $55/SF (kitchen), Level 1/remnant $35/SF (every other room).
#
# ⛔⛔⛔ THE STEADFAST RULE -- MEASURE THE TRUE SLAB POLYGON.  NEVER price tops as
# base-cabinet-LF x nominal depth.  That shortcut ran us -8% on Pack's kitchen
# (95.3 vs Jason's 103.70 SF) because it drops THREE things:
#   1. the OVERHANG  -- the slab runs to ~27" deep (24" cabinet + ~3" overhang to
#      the wall), NOT 25.5".  Measure overhang-edge -> wall, not the cabinet face.
#   2. the CORNER    -- an L-counter's slab carries through the (often 45 deg) corner;
#      the base-LF count omits it.
#   3. the APPLIANCE -- the slab front edge runs CONTINUOUS across a slide-in/drop-in
#      range/cooktop (you don't lay counter ON the appliance, but the slab doesn't stop).
# RECIPE (what actually worked on Pack, repeatable): verify per-page scale; then per
# slab pull the OUTERMOST counter front-edge line(s) and the WALL FACE from
# get_drawings() and compute  (front-edge RUN) x (front-overhang -> wall DEPTH).
# Cross-check a measured island's bounding box against the cabinet LF (Pack island
# 24.1 vs Jason 24.41 = 1%) to prove the geometry read.  Do it per slab; no shortcut.
#
# KITCHEN (L3): keep the SINK in, take the STOVE out, MEASURE the stove opening (custom
#   = not always 30").  INCLUDE the island seating overhang.  Backsplash is TILE (a
#   SEPARATE line, not stone) = wall-touching counter LF x height mult: x2 normal,
#   x4 at stove, x6 where NO uppers.
# OTHER ROOMS (L1, Jason's actual splash method -- validated on Pack):
#   keep sinks in.  ⛔ NO separate 4" splash LINE.  Instead OVER-MEASURE the top polygon
#   by 4-6" (use ~5"=0.417 ft) into EVERY wall it touches -- back edge AND each end that
#   abuts a wall.  This folds the splash INTO the slab SF.  An alcove vanity touches 3
#   walls (back + 2 ends) so it catches the over-measure on three edges -- that is most
#   of what makes vanities bigger than a plain top.  (On Pack this over-measure was the
#   last ~3-4% overall; my plain tops were -3.3% vs Jason until I applied it.)
# ⛔⛔ MEASURE EACH TOP'S FULL EXTENT -- CROP WIDE.  My worst vanity miss was cropping
#   tight and dropping a 3-ft cabinet section off Lynn's vanity (9.5 -> 15.4 SF).  Render
#   the WHOLE room, capture every base cabinet in the run, then measure the polygon.
# ⛔ The cabinet file is NOT the enumeration -- find EVERY top on the floor plan
#   (laundry + BOTH garages get tops; 90"-tall garage storage towers get NO top).
#   Waste: tops ~1.24%, kitchen tile splash 10%.
# ---------------------------------------------------------------------------
COUNTERTOP_L3_RATE = 55.0   # $/SF installed, Level 3 granite/quartz (kitchen, mid-grade)
COUNTERTOP_L1_RATE = 35.0   # $/SF installed, Level 1 / remnant (all other rooms)

def l1_top_sf(run_ft, depth_ft, wall_ends=0, over_in=5.0):
    """L1 top polygon SF with Jason's wall over-measure folded in (NO separate splash).
       run_ft, depth_ft = the MEASURED top polygon (front overhang -> wall, full extent).
       wall_ends = number of run-ends that abut a wall (alcove vanity = 2; open run = 0-1).
       The back edge always abuts the wall, so depth gets the over-measure; each wall_end
       extends the run.  over_in = 4-6\" (default 5\")."""
    om = over_in/12.0
    return round((run_ft + wall_ends*om) * (depth_ft + om), 2)

WINDOW_TAG = re.compile(r"^(\d{4})(SH|DH|FX|MU|CA|SL|AW|PW|TR|OC)$", re.I)
DOOR_TAG = re.compile(r"^(\d{2})(\d{2})$")
MULL_LABELS = {"DOUBLE": 2, "TRIPLE": 3, "QUAD": 4}


def _tag_words(page):
    """(text, cx, cy) for every word on the page."""
    return [(w[4], (w[0] + w[2]) / 2.0, (w[1] + w[3]) / 2.0) for w in page.get_text("words")]


def window_count(page, label_radius=200.0, default_mull=2):
    """COUNT windows off a FLOOR-PLAN page from manufacturer size tags.

    Jason's rule (2026-07-27): a mulled unit is separate windows -- a double mull is 2
    windows, a triple is 3. Multiplicity comes from a DOUBLE/TRIPLE/QUAD label near the
    tag when the plan states one; an unlabelled *MU* tag falls back to `default_mull`
    because a mull is at least two units by definition.

    NEVER run this on an elevation sheet. Elevations draw the same opening on more than
    one view and double-count -- measured 26 tags for 13 real windows on burns.
    Returns (count, detail_rows).
    """
    words = _tag_words(page)
    labels = [(t.upper(), x, y) for t, x, y in words if t.upper() in MULL_LABELS]
    rows, total = [], 0
    for text, x, y in words:
        m = WINDOW_TAG.match(text)
        if not m:
            continue
        mult, basis = 1, "single"
        near = sorted(((lt, ((x - lx) ** 2 + (y - ly) ** 2) ** 0.5) for lt, lx, ly in labels),
                      key=lambda n: n[1])
        if near and near[0][1] <= label_radius:
            mult, basis = MULL_LABELS[near[0][0]], "labelled_" + near[0][0].lower()
        elif m.group(2).upper() == "MU":
            mult, basis = default_mull, "unlabelled_mull_default"
        total += mult
        rows.append({"tag": text, "multiplier": mult, "basis": basis})
    return total, rows


def window_trim_lf(page, label_radius=200.0):
    """1x4 window trim LF: the perimeter of each window OPENING on the floor plan.

    Jason's rule (2026-07-27): **trim runs around the whole assembly, and the mullion strip is
    built into the window** -- so a double-mulled unit gets ONE perimeter, not two. **Doors do
    not get trim**, which is why this reads window tags only (a size tag with a type suffix
    like SH/DH/FX/MU); bare four-digit door tags are ignored.

    A tag is WWHH in feet-inches: 3050 is 3'-0" wide x 5'-0" high, so 16 LF of trim.

    ⚠ The manual takeoffs measure this PER SASH and therefore run over -- burns 214.79 vs 206.67
    here, roberts 439.75 vs 283.33. Jason ruled the assembly method correct on both.
    ⚠ Waste is a separate column on the takeoff (10% on this line). This returns RAW LF.
    Returns (total_lf, detail_rows).
    """
    rows, total = [], 0.0
    for text, _x, _y in _tag_words(page):
        m = WINDOW_TAG.match(text)
        if not m:
            continue
        size = m.group(1)
        width = int(size[0]) + int(size[1]) / 12.0
        height = int(size[2]) + int(size[3]) / 12.0
        perim = 2.0 * (width + height)
        total += perim
        rows.append({"tag": text, "width_ft": round(width, 3),
                     "height_ft": round(height, 3), "perimeter_lf": round(perim, 2)})
    return round(total, 2), rows


RECESSED_TAG = re.compile(r"^R\d*$", re.I)


def recessed_can_count(page, tags=None):
    """COUNT recessed can lights off an ELECTRICAL sheet by their fixture tag.

    Jason's rule (2026-07-27): a can light is a RECESSED CAN and nothing else. Vanity
    lights and single room/ceiling fixtures are separate lines and must never be folded
    into this count -- doing so prices the wrong fixture at the wrong rate on both lines.
    Burns reads 37 `R4` tags and 37 is the correct answer; the manual takeoff's 32 rolled
    other fixture types in and was wrong.

    `tags` restricts which tags count (default: any R-prefixed tag such as R4 or R6).
    Returns (count, detail_rows).
    """
    allowed = {t.upper() for t in tags} if tags else None
    rows, total = [], 0
    for text, x, y in _tag_words(page):
        t = text.strip().upper()
        if not RECESSED_TAG.match(t):
            continue
        if allowed is not None and t not in allowed:
            continue
        total += 1
        rows.append({"tag": t, "x": round(x, 1), "y": round(y, 1)})
    return total, rows


def interior_door_count(page, heights=("68",), min_width_in=24, max_width_in=60):
    """COUNT interior doors off a FLOOR-PLAN page from WWHH size tags.

    A tag is WWHH in feet-inches: 2868 is 2'-8" x 6'-8". Exterior and garage openings are
    excluded by width -- 6068 and 8068 are patio and garage units, not interior doors.
    Returns (count, detail_rows).
    """
    rows, total = [], 0
    for text, _x, _y in _tag_words(page):
        m = DOOR_TAG.match(text)
        if not m or m.group(2) not in heights:
            continue
        feet, inches = int(m.group(1)[0]), int(m.group(1)[1])
        width_in = feet * 12 + inches
        if not (min_width_in <= width_in <= max_width_in):
            continue
        total += 1
        rows.append({"tag": text, "width_in": width_in})
    return total, rows


def kitchen_tile_backsplash_sf(lf_standard=0.0, lf_at_stove=0.0, lf_no_uppers=0.0):
    """Kitchen TILE backsplash SF (separate tile line) -- wall-touching counter LF x
    height multiplier: x2 standard (under uppers), x4 at the stove, x6 where no uppers."""
    return round(lf_standard*2 + lf_at_stove*4 + lf_no_uppers*6, 2)

def countertop_estimate(slabs, waste=0.0124):
    """Price measured countertop slabs.  slabs = list of dicts, each:
         {"room": str, "sf": <MEASURED polygon SF>, "level": 1 or 3}
       sf MUST be a measured slab polygon, FULL extent, with the L1 4-6\" wall
       over-measure already folded in (use l1_top_sf) -- NOT base-LF x nominal depth,
       and NOT a separate splash line.  Returns per-room + totals with waste applied."""
    rate = {1: COUNTERTOP_L1_RATE, 3: COUNTERTOP_L3_RATE}
    rows, total_sf, total_cost = [], 0.0, 0.0
    for s in slabs:
        sf = float(s["sf"])
        sf_w = round(sf * (1 + waste), 2)
        cost = round(sf_w * rate[s["level"]], 2)
        rows.append({"room": s["room"], "level": s["level"],
                     "sf": round(sf, 2), "sf_waste": sf_w, "cost": cost})
        total_sf += sf_w; total_cost += cost
    return {"rows": rows, "total_sf": round(total_sf, 2), "total": round(total_cost, 2)}


# ---------------------------------------------------------------------------
# ROOFING (data point #13 -- Southern Expert Roofing actuals, Burns + Peterson).
# ⛔ Priced by the SQUARE (100 SF) of true roof SURFACE -- NEVER $/SF of footprint.
#   surface = Σ(footprint_zone × pitch_factor);  pitch_factor = √(rise²+144)/12.
#   READ every plane's pitch off the roof plan -- NEVER eyeball it (a raster guess of
#   Peterson's 16:12 came in 17% low; the 16:12 alone was 54% of the area).
# FIELD shingle rate is FLAT vs pitch: $174/sq (Burns, CT Landmark) .. $175/sq
#   (Peterson, GAF Timberline HDZ). Underlayment / 18" ice&water valley / ridge vent are
#   BUNDLED in the field rate ($0 separate). Field shingle ≈ 85-90% of the roof total.
# ⛔⛔ THE #1 ROOFING LEAK: the 15% waste gets DROPPED at the takeoff→estimate handoff.
#   Peterson's estimate priced the RAW 4,897 SF ($9,707) instead of the waste-loaded
#   5,631 SF ($11,162 ≈ actual $11,204, 0.4%). The rate was CORRECT; the miss was the
#   dropped waste. ALWAYS price the WASTE-LOADED surface. J&J's flat 15% is right (~4%
#   conservative): Southern bills only ~10-11% over true surface on BOTH a simple AND a
#   steep/cut-up roof -- waste does NOT escalate with complexity (a cut-up roof costs
#   more purely through more SURFACE, same rate, same waste).
# ACCESSORIES are SEPARATE lines: Hip&Ridge cap $4.25/LF · Drip edge $1.85/LF (full roof
#   edge; rakes are the SLOPED true length) · Pipe boots $50 ea.
# METAL: Jason does NOT use Southern for metal (too expensive) -- any metal-roof area is a
#   SEPARATE vendor line; measure it OUT of the shingle scope (flagged here, not priced).
# ---------------------------------------------------------------------------
ROOF_FIELD_RATE_PER_SQ = 175.0   # $/square (100 SF) field shingle, FLAT vs pitch (Burns 174 / Peterson 175)
ROOF_WASTE = 0.15                # applied to the SURFACE and ALWAYS priced (the #1 leak)
ROOF_HIP_RIDGE_RATE = 4.25       # $/LF hip & ridge cap
ROOF_DRIP_EDGE_RATE = 1.85       # $/LF drip edge (full roof edge; rakes = sloped length)
ROOF_PIPE_BOOT_RATE = 50.0       # $ each pipe boot

def pitch_factor(rise, run=12):
    """Roof-surface multiplier for a pitch = √(rise²+run²)/run. `rise` per `run` (default
    12) so pitch_factor(8) = 8:12. COMPUTED (not a lookup) so ANY pitch works, and it
    reproduces J&J's table exactly: 5:12=1.083, 6:12=1.118, 8:12=1.202, 10:12=1.302,
    12:12=1.414, 16:12=1.667."""
    return round(math.hypot(rise, run) / run, 4)

def roof_surface(zones):
    """True roof SURFACE from footprint zones. zones = [{'footprint_sf': x, 'pitch': rise}],
    pitch = rise in :12 (8 == 8:12). Returns per-zone surface + raw total.
    ⛔ `footprint_sf` = the PLAN-VIEW area under each roof plane WITH the overhang included
    (measure the overhang off the eave/cornice SECTION -- a 1-ft vs 2-ft overhang miss ran
    my Burns surface a uniform -12.4%). surface = footprint × pitch_factor."""
    rows, total = [], 0.0
    for z in zones:
        fp = float(z["footprint_sf"]); pf = pitch_factor(z["pitch"])
        s = fp * pf
        rows.append({"pitch": f"{z['pitch']}:12", "footprint_sf": round(fp, 1),
                     "factor": pf, "surface_sf": round(s, 1)})
        total += s
    return {"zones": rows, "raw_surface_sf": round(total, 1)}

def roofing_estimate(zones, hip_ridge_lf=0.0, drip_edge_lf=0.0, n_pipe_boots=0,
                     metal_sf=0.0, field_rate=ROOF_FIELD_RATE_PER_SQ, waste=ROOF_WASTE):
    """Shingle roofing SUB cost -- priced by the SQUARE of WASTE-LOADED true surface +
    itemized accessories (data point #13; reproduced Southern's Peterson actual to 0.4% and
    Burns to ~1% at their measured surfaces).
      zones        = footprint-by-pitch list (see roof_surface); the model MEASURES these.
      hip_ridge_lf = total hip + ridge length (off the roof plan).
      drip_edge_lf = total roof-edge length = eaves (horizontal) + rakes (SLOPED true
                     length); same LF as fascia (data #16c roof-plan cross-reference).
      n_pipe_boots = count of plumbing-vent penetrations.
      metal_sf     = any metal-roof plan area -- EXCLUDED here (separate vendor), returned as
                     a flag so it is never silently rolled into the shingle scope.
    Returns the surface build-up, waste-loaded ORDER qty (what gets priced), field +
    accessory costs, total, field %, and an all-in $/SF cross-check (validated band
    ~$1.9-2.0/SF of order surface on Burns $1.92 and Peterson $1.98)."""
    surf = roof_surface(zones)
    raw = surf["raw_surface_sf"]
    order_sf = round(raw * (1 + waste), 1)               # WASTE-LOADED surface -- ALWAYS priced
    order_sq = round(order_sf / 100.0, 2)
    field = round(order_sq * field_rate, 2)
    hip_ridge = round(hip_ridge_lf * ROOF_HIP_RIDGE_RATE, 2)
    drip = round(drip_edge_lf * ROOF_DRIP_EDGE_RATE, 2)
    boots = round(n_pipe_boots * ROOF_PIPE_BOOT_RATE, 2)
    accessories = round(hip_ridge + drip + boots, 2)
    total = round(field + accessories, 2)
    out = {"zones": surf["zones"], "raw_surface_sf": raw,
           "waste_pct": round(waste * 100, 1), "order_surface_sf": order_sf,
           "order_squares": order_sq, "field_rate_per_sq": field_rate, "field_cost": field,
           "hip_ridge_cost": hip_ridge, "drip_edge_cost": drip, "pipe_boot_cost": boots,
           "accessories_total": accessories, "total": total,
           "field_pct": round(field / total * 100, 1) if total else 0.0,
           "all_in_per_sf": round(total / order_sf, 3) if order_sf else 0.0}
    if metal_sf:
        out["metal_sf_EXCLUDED"] = round(float(metal_sf), 1)
        out["flags"] = [f"{round(metal_sf, 1)} SF metal roof EXCLUDED -- price via a separate "
                        f"vendor (Jason does not use Southern for metal)"]
    return out


# ---------------------------------------------------------------------------
# SIDING / EXTERIOR CLADDING (data points #12, #12c, #16, #16c -- Southern Siding &
# Gutters actuals: Burns/Peterson/Wilson/McPherson/Leone/Jeffries).
# ⛔⛔ J&J's #1 BUDGET LEAK. A siding contract is ~1/3-2/5 FIELD + ~3/5-2/3 TRIM/DETAILS
#   (Burns/Peterson 35% field, Wilson 40%) -- pricing the field $/SF and lumping the rest is
#   exactly why it blows. PRICE IT AS THE SUB DOES: FIELD by the SQUARE (100 SF), every detail
#   by LF or EACH, every line MEASURED/COUNTED off the elevations. NO blended $/SF, ever.
# ⛔ MEASURE EVERY PIECE, NO FORMULAS (Jason): walls L×H by material (GROSS, openings left in),
#   gables as separate triangles, fascia/soffit off the ROOF EDGE (eaves off roof plan + rakes
#   off elevations), hidden walls off the floor plan. Perimeter×avg-height ran Leone +30%.
# ⚠️ RATES CREPT UP Mar->May->Jun 2026 -- DATE-STAMP + re-confirm. Notably lap Smooth may have
#   jumped $250 -> $330/sq late June 2026 (pass rate= to override; CONFIRM which is live).
# WASTE: +10% on AREA (field/shake/porch-ceiling) converts RAW->quoted (Leone raw 43 sq × 1.10
#   = 47.3 ≈ Southern 47.7, 1%). LF/EACH are counted to match the sub's line -> no waste.
#   ⛔ Grade like-to-like: my measure is RAW; Southern's quote is waste-loaded (the "I'm light"
#   trap was a raw-vs-loaded comparison error, not a measurement error).
# ⛔ THREE-WAY WOOD-WRAP SPLIT -- never lump into one "beam wrap LF": horizontal beam = LF,
#   column/post = EACH (by size), gable bracket/truss = EACH (by type). ⛔ SCOPES I MISS:
#   exterior CROWN, band board, shake/B&B gable accents, water-table flashing, porch
#   beams/ceilings. EXCLUDE masonry (brick/stone = mason scope, not siding).
# RATE_BOOK below is the SINGLE source of truth for siding rates in code; a line may pass an
# explicit rate= to override (a range item, or a re-confirmed rate). Unknown item -> ValueError.
# ---------------------------------------------------------------------------
# item -> (rate, unit, category).  unit: 'sq' = $/100 SF (+waste on area); 'lf'; 'each'.
SIDING_RATE_BOOK = {
    # FIELD (by the square) -- confirm B&B vs lap per house; lap rate depends on EXPOSURE
    "lap_smooth_7":     (250.0, "sq", "field"),  # Hardie Smooth 8.25"/7" exp
    # ⚠ OPEN 2026-08-04: Jason gave ONE flat rate for "horizontal lap Hardi" -- $3.30/SF
    # = $330/sq -- with no exposure qualifier. That confirms the old "maybe $330" flag but
    # does NOT say which exposure it maps to; this book splits lap by exposure because a
    # narrower reveal means more boards. rate_book.json's "Siding (Fiber Cement, Horizontal)"
    # already carries 3.30 and is what price_lines() uses, so estimates are correct today.
    # Ask Jason whether $3.30 is flat regardless of exposure before touching these entries.
    "lap_cedarmill_5":  (350.0, "sq", "field"),  # Hardie Cedarmill 6.25"/5" exp (narrower = more boards)
    "lap_7":            (250.0, "sq", "field"),  # generic 7" exposure ($240-250)
    "lap_5":            (350.0, "sq", "field"),  # generic 5" exposure
    "bnb":              (440.0, "sq", "field"),  # board & batten panel. Jason live 2026-08-04:
                                                 # $4.40/SF of wall = $440/sq (was $430).
    "shake":            (820.0, "sq", "field"),  # Hardie shake accent (gables) -- often missed
    # PORCH CEILING (by the square) -- read which
    "porch_tg_wood":    (540.0, "sq", "porch_ceiling"),  # 1x6 wood T&G (~$5.40/SF)
    "porch_hardie":     (430.0, "sq", "porch_ceiling"),  # Hardie panel porch ceiling
    # SOFFIT & FASCIA (by LF) -- scales with soffit WIDTH + vented/solid; measure off ROOF EDGE
    "sf_narrow":        (11.00, "lf", "soffit_fascia"),  # 12" soffit + 8" fascia
    "sf_12_solid":      (13.50, "lf", "soffit_fascia"),
    "sf_16_solid":      (14.25, "lf", "soffit_fascia"),
    "sf_24_vented":     (16.50, "lf", "soffit_fascia"),
    "sf_30_vented":     (18.50, "lf", "soffit_fascia"),
    "sf_cantilever_16": ( 9.00, "lf", "soffit_fascia"),
    # PORCH BEAM (by LF) -- horizontal beams ONLY (posts/brackets are EACH); MATERIAL-dependent
    "beam_hardie":      (11.00, "lf", "porch_beam"),
    "beam_cedar":       (23.00, "lf", "porch_beam"),
    # TRIM / BOARDS (by LF)
    "frieze":           ( 4.50, "lf", "trim"),   # Hardie 4/4x6"
    "frieze_brick":     ( 5.50, "lf", "trim"),   # at brick transition ("brick box")
    "corner":           ( 4.25, "lf", "trim"),   # 5/4x4 double outside corner ($4.00-4.25) × stacked height
    "trim_5_4x6":       ( 4.50, "lf", "trim"),
    "trim_5_4x8":       ( 5.00, "lf", "trim"),
    "trim_5_4x10":      ( 6.00, "lf", "trim"),
    "band_board":       ( 7.50, "lf", "trim"),   # 5/4x12 between-floor band
    "crown_ext":        ( 6.50, "lf", "trim"),   # exterior crown / cornice (missed on Leone = 11% of job)
    "water_table":      ( 3.50, "lf", "trim"),   # flashing/water table brick|stone-to-siding (I've omitted this)
    # TRIMMED OPENINGS (EACH) -- classify by header; mulled units count as # of lites
    "opening_std":      (72.50, "each", "opening"),   # standard 2x10 cedar header ($65-80)
    "opening_brick":    (145.0, "each", "opening"),   # 4x10 header on brick
    "opening_garage":   (195.0, "each", "opening"),   # 8x7 wrapped garage (header+surround)
    # COLUMNS (EACH, cedar wrap) -- by size
    "col_cedar_6x6":    (270.0, "each", "column"),
    "col_cedar_12x12":  (480.0, "each", "column"),
    # BRACKETS / PUNCH (EACH) -- by type (range ~9x; identify the ACTUAL member)
    "bracket_corbel_6x6":  (105.0, "each", "bracket"),
    "bracket_corbel_10x6": (135.0, "each", "bracket"),
    "bracket_gable":       (535.0, "each", "bracket"),  # 2x6->4x8 finish, pitch-spec
    "bracket_truss_wrap":  (810.0, "each", "bracket"),  # decorative gable-truss wrap ($695-925)
    "porch_vert_trim":     (385.0, "each", "bracket"),  # vertical front-porch trim (2x6->4x8 finish)
}
SIDING_UNIT_KEY = {"sq": "sf", "lf": "lf", "each": "count"}

def roof_zone_surface(page, clip, pitch_calls, underroof_sf, overhang_in=(12.0, 17.0),
                      zoom=3.0, close_px=45, min_face_pt2=400, len_ft=(1.0, 130.0),
                      nominal_ppf=18.0):
    """Sloped roof surface from FACE DECOMPOSITION of the roof plan, scale SOLVED from the
    sheet's own printed data (Phase 2/3; validated Peterson cal #44: 46.5 sq mid vs
    Southern's reconciled 48.97 = -5.1%, inside +/-8%, ZERO hand-fed scale on a set with
    no text layer and per-page print rescaling).
    METHOD
      1. Rasterize solid + DASHED vector segments in `clip` (dashed pitch-change lines are
         REAL plane boundaries) -> morphological close (close_px) -> flood exterior ->
         connected components = roof planes.
      2. Each plane takes the pitch of the callout(s) landing inside it (short radial
         search); majority vote on conflict (a stray arrow whose tail crosses a ridge).
      3. Scale: filled outline area A (pt^2) and eave perimeter P (pt) satisfy
             A/ppf^2 = underroof_sf + (P/ppf)*OH + 4*OH^2      (quadratic in 1/ppf)
         where underroof_sf comes only from the certified measured component roll-up
         (never a schedule or caller-supplied total) and OH is the PRINTED
         overhang range (cornice details) -- evaluated at lo/mid/hi OH for honest bounds.
      4. Surface = sum(face_area * pitch_factor) scaled by A/sum(assigned faces), which
         distributes boundary ink + unassigned slivers at the average pitch factor.
    pitch_calls: [(x_pt, y_pt, rise_over_12), ...] in ABS PDF points. Callouts MUST be
    eye/VLM-verified, never raw OCR -- tesseract reads "16/12 P." as "12/12" (cal #43).
    Returns dict (n_faces, assigned, conflicts, outline/faces pt^2, ppf + surface bounds
    per OH, mid squares) or None if decomposition fails."""
    import cv2
    import numpy as np
    import math as _m
    segs = extract_styled_segments(page, ppf=nominal_ppf)
    keep = [s for s in segs
            if clip.x0 <= (s["seg"][0] + s["seg"][2]) / 2 <= clip.x1
            and clip.y0 <= (s["seg"][1] + s["seg"][3]) / 2 <= clip.y1
            and len_ft[0] <= s["len_ft"] <= len_ft[1]]
    if not keep:
        return None
    W = int((clip.x1 - clip.x0) * zoom)
    H = int((clip.y1 - clip.y0) * zoom)
    base = np.zeros((H, W), np.uint8)
    for s in keep:
        x0, y0, x1, y1 = s["seg"]
        cv2.line(base, (int((x0 - clip.x0) * zoom), int((y0 - clip.y0) * zoom)),
                 (int((x1 - clip.x0) * zoom), int((y1 - clip.y0) * zoom)), 255, 3)
    closed = cv2.morphologyEx(base, cv2.MORPH_CLOSE,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (close_px, close_px)))
    pad = cv2.copyMakeBorder(closed, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=0)
    ff = pad.copy()
    cv2.floodFill(ff, np.zeros((pad.shape[0] + 2, pad.shape[1] + 2), np.uint8), (0, 0), 255)
    interior = (ff[5:-5, 5:-5] != 255)
    inside = interior & (closed == 0)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(inside.astype(np.uint8), 8)
    # filled outline (largest component of interior|ink) -> true roof envelope
    solid = (interior | (closed == 255)).astype(np.uint8)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(solid, 8)
    if n2 < 2:
        return None
    big = max(range(1, n2), key=lambda i: st2[i, cv2.CC_STAT_AREA])
    cnts, _ = cv2.findContours((lab2 == big).astype(np.uint8),
                               cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    apx = cv2.approxPolyDP(c, 2.5, True)
    A = cv2.contourArea(apx) / zoom / zoom
    P = cv2.arcLength(apx, True) / zoom
    order = sorted([i for i in range(1, n)
                    if stats[i, cv2.CC_STAT_AREA] / zoom / zoom >= min_face_pt2],
                   key=lambda i: -stats[i, cv2.CC_STAT_AREA])
    idx_of = {i: k for k, i in enumerate(order)}
    assign = {}
    for x_pt, y_pt, rise in pitch_calls:
        px, py = int((x_pt - clip.x0) * zoom), int((y_pt - clip.y0) * zoom)
        fc = None
        for rad in range(0, 40, 4):
            hit = False
            for ang in range(0, 360, 45):
                yy = int(py + rad * _m.sin(_m.radians(ang)))
                xx = int(px + rad * _m.cos(_m.radians(ang)))
                if 0 <= yy < H and 0 <= xx < W and lab[yy, xx] in idx_of:
                    fc = idx_of[lab[yy, xx]]
                    hit = True
                    break
            if hit:
                break
        if fc is not None:
            assign.setdefault(fc, []).append(rise)
    conflicts = sum(1 for v in assign.values() if len(set(v)) > 1)
    pitch_of = {f: max(set(v), key=v.count) for f, v in assign.items()}
    foot = sum(stats[order[f], cv2.CC_STAT_AREA] / zoom / zoom for f in pitch_of)
    if foot <= 0:
        return None
    surf = sum(stats[order[f], cv2.CC_STAT_AREA] / zoom / zoom * pitch_factor(pitch_of[f])
               for f in pitch_of)
    una = sum(stats[order[k], cv2.CC_STAT_AREA] / zoom / zoom
              for k in range(len(order)) if k not in pitch_of)
    out = {"n_faces": len(order), "assigned": len(pitch_of), "conflicts": conflicts,
           "outline_pt2": round(A), "eave_perim_pt": round(P), "faces_pt2": round(foot),
           "unassigned_pt2": round(una), "scaleup": round(A / foot, 4),
           "avg_pitch_factor": round(surf / foot, 3), "bounds": {}}
    lo, hi = min(overhang_in), max(overhang_in)
    for oh_in in (lo, (lo + hi) / 2, hi):
        oh = oh_in / 12.0
        c1 = -P * oh
        c0 = -(underroof_sf + 4 * oh * oh)
        u = (-c1 + _m.sqrt(c1 * c1 - 4 * A * c0)) / (2 * A)
        ppf = 1 / u
        s_sf = surf * (A / foot) / ppf ** 2
        out["bounds"][oh_in] = {"ppf": round(ppf, 3), "surface_sf": round(s_sf, 1),
                                "squares": round(s_sf / 100, 2)}
    mid = out["bounds"][(lo + hi) / 2]
    out["ppf"] = mid["ppf"]
    out["surface_sf"] = mid["surface_sf"]
    out["squares"] = mid["squares"]
    return out


def siding_estimate(lines, field_waste=0.10):
    """Exterior CLADDING sub cost, priced the way Southern bills -- FIELD by the square + every
    detail by LF/EACH, each line MEASURED/COUNTED (data #12/#12c/#16). NO blended $/SF.
      lines = list of measured line items, each:
        {'item': <SIDING_RATE_BOOK key>, 'sf'|'lf'|'count': <measured qty>,
         'rate': <optional override>, 'label': <optional note>}
      The unit comes from the rate book ('sq'->give sf, 'lf'->give lf, 'each'->give count).
      field_waste (default 10%) applies to AREA ('sq') lines ONLY -- it converts RAW measured
      area to Southern's waste-loaded quoted area (Leone 43 sq × 1.10 = 47.3 ≈ 47.7). LF/EACH
      are counted to match the sub's line -> no waste.
    Returns per-line cost, per-category subtotals, total, and field_pct (SANITY: FIELD should
    be only ~35-40% of a real siding job -- if it's much higher you've UNDER-measured the
    trim/details, which is J&J's chronic leak). Pass rate= on a line to override a range item
    or a re-confirmed rate (e.g. lap jumped to $330/sq)."""
    rows, cats, total = [], {}, 0.0
    for ln in lines:
        item = ln["item"]
        if item not in SIDING_RATE_BOOK:
            raise ValueError(f"unknown siding item {item!r}; valid: {sorted(SIDING_RATE_BOOK)}")
        base_rate, unit, cat = SIDING_RATE_BOOK[item]
        rate = float(ln.get("rate", base_rate))
        qkey = SIDING_UNIT_KEY[unit]
        if qkey not in ln:
            raise ValueError(f"siding item {item!r} needs '{qkey}=' (unit {unit})")
        qty = float(ln[qkey])
        if unit == "sq":
            order = qty * (1 + field_waste)               # RAW area -> waste-loaded quoted area
            cost = round(order / 100.0 * rate, 2)
            q_out = {"raw_sf": round(qty, 1), "order_sf": round(order, 1),
                     "squares": round(order / 100.0, 2)}
        else:
            cost = round(qty * rate, 2)
            q_out = {qkey: round(qty, 2)}
        rows.append({"item": item, "label": ln.get("label", ""), "cat": cat,
                     "rate": rate, "unit": unit, **q_out, "cost": cost})
        cats[cat] = round(cats.get(cat, 0.0) + cost, 2)
        total += cost
    total = round(total, 2)
    field_pct = round(cats.get("field", 0.0) / total * 100, 1) if total else 0.0
    flags = []
    if total and field_pct > 45:
        flags.append(f"field is {field_pct}% of the job (>45%) -- likely UNDER-measured the "
                     f"TRIM/DETAILS (J&J's chronic leak). Re-check soffit/fascia LF, corners, "
                     f"openings, crown, band board, water-table flashing, porch beams/ceilings.")
    return {"rows": rows, "by_category": cats, "total": total, "field_pct": field_pct,
            "field_waste_pct": round(field_waste * 100, 1), "flags": flags}


# ---------------------------------------------------------------------------
# ROOM PERIMETERS off the floor-plan GEOMETRY (raster) -- the FOUNDATION that
# feeds BASE molding, CROWN, and DRYWALL (all run on the same room perimeters).
# ⛔ Built because relying on printed room dimensions FAILS (not every plan has
# them; half of Pack's rooms had no dim label).  MEASURE the geometry instead.
#
# Pipeline (validated on Pack p6: total perim 1,384 LF vs drywall-derived ~1,333
# = +4%, and total area 4,265 SF vs heated 4,326 = -1.4% -- two independent checks):
#   1. render the heated footprint; wall mask = dark ink OR pink (offset walls).
#   2. drop small components (text); CLOSE small gaps (interior doors).
#   3. heavy-CLOSE -> solid blob -> largest contour = building footprint; draw it
#      thick to SEAL big exterior openings (patio doors) so open rooms don't leak.
#   4. rooms = enclosed free space inside the footprint.
#   5. ⭐ per room: MORPH_CLOSE ~1.5 ft to FILL cabinet/fixture notches (else the
#      contour wraps every cabinet and inflates perimeter ~2x), then arcLength.
# Returns total_perim_lf, total_area_sf, and per-room (sf, perim, centroid) so you
# can match rooms to the crown list by position.  Validate every house against the
# drywall actual (perim x blended height + ceilings ~= drywall SF).
# ---------------------------------------------------------------------------
def room_perimeters(page, ppf=None, clip=None, zoom=2.5,
                    min_sf=10, max_sf=4000, door_close_ft=1.6,
                    notch_close_ft=1.5, seal_ft=6.0):
    import cv2, numpy as np, fitz
    if ppf is None:
        ppf = detect_scale(page)["ppf"]
    pxft = ppf * zoom
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    img = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    R, G, B = (img[:, :, i].astype(int) for i in range(3))
    pink = (R > 170) & (R - G > 50) & (R - B > 20)
    wall = ((gray < 160) | pink).astype(np.uint8) * 255
    n, lab, st, _ = cv2.connectedComponentsWithStats(wall, 8)
    walls = np.zeros_like(wall)
    for i in range(1, n):
        if st[i, 4] > 800:
            walls[lab == i] = 255

    def kk(ft):
        s = max(3, int(round(ft * pxft)))
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (s, s))
    interior = cv2.morphologyEx(walls, cv2.MORPH_CLOSE, kk(door_close_ft))
    blob = cv2.morphologyEx(walls, cv2.MORPH_CLOSE, kk(seal_ft))
    cnts, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bldg = max(cnts, key=cv2.contourArea)
    foot = np.zeros_like(wall)
    cv2.drawContours(foot, [bldg], -1, 255, -1)
    seal = interior.copy()
    cv2.drawContours(seal, [bldg], -1, 255, max(3, int(0.8 * pxft)))
    free = cv2.bitwise_and(255 - seal, foot)
    n2, lab2, st2, cent = cv2.connectedComponentsWithStats(free, 4)
    rooms = []
    for i in range(1, n2):
        sf0 = st2[i, 4] / pxft ** 2
        if sf0 < min_sf or sf0 > max_sf:
            continue
        m = (lab2 == i).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kk(notch_close_ft))
        c, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(c, key=cv2.contourArea)
        ap = cv2.approxPolyDP(c, 0.5 * pxft, True)
        per = cv2.arcLength(ap, True) / pxft
        sf = cv2.contourArea(ap) / pxft ** 2
        # map centroid back to PDF coords (undo the 40px border + zoom + clip origin)
        cx = (cent[i][0] - 40) / zoom + (clip.x0 if clip else 0)
        cy = (cent[i][1] - 40) / zoom + (clip.y0 if clip else 0)
        rooms.append({"sf": round(sf, 1), "perim": round(per, 1),
                      "cx": round(cx), "cy": round(cy)})
    rooms.sort(key=lambda r: -r["sf"])
    foot_sf = round(cv2.countNonZero(foot) / pxft ** 2, 0)
    return {"total_perim_lf": round(sum(r["perim"] for r in rooms), 1),
            "total_area_sf": round(sum(r["sf"] for r in rooms), 0),
            "footprint_sf": foot_sf, "n_rooms": len(rooms), "rooms": rooms}


# ---------------------------------------------------------------------------
# VERIFICATION FORCING FUNCTION -- a number CANNOT exist without its proof.
# Built because banked RULES don't fire in the moment (I kept writing the GATE
# then breaking it). This makes the SOURCE + VIEW + RECONCILIATION a MANDATORY
# artifact of CONSTRUCTING a quantity, so an unverified/assumed/given-not-measured
# number can't be silently shipped as if it were measured.
#   MEASURED -> requires sheet + a rendered VIEW FILE THAT EXISTS (proof I looked)
#   GIVEN    -> requires given_by (legit, but flagged "not independently measured")
#   ASSUMED  -> requires a note; certify() refuses to pass while any exist
# Use: build every estimate quantity as a Quantity; certify() before you trust a total.
# ---------------------------------------------------------------------------
import os as _os
class Quantity:
    SOURCES = ("MEASURED", "GIVEN", "ASSUMED")
    def __init__(self, name, value, unit, source,
                 sheet=None, view=None, given_by=None, note=None):
        if source not in self.SOURCES:
            raise ValueError(f"{name}: source must be one of {self.SOURCES}, got {source!r}")
        self.name, self.value, self.unit, self.source = name, value, unit, source
        self.sheet, self.view, self.given_by, self.note = sheet, view, given_by, note
        self.recon = None
        if source == "MEASURED":
            if not sheet or not view:
                raise ValueError(f"{name}: MEASURED requires sheet= AND view= (the rendered proof)")
            if not _os.path.exists(view):
                raise ValueError(f"{name}: MEASURED view '{view}' does not exist -- render AND look before claiming MEASURED")
        elif source == "GIVEN" and not given_by:
            raise ValueError(f"{name}: GIVEN requires given_by= (whose number is this)")
        elif source == "ASSUMED" and not note:
            raise ValueError(f"{name}: ASSUMED requires note= (why + what to verify)")
    def reconcile(self, check_value, tol_pct, against=""):
        err = abs(self.value - check_value) / check_value * 100 if check_value else 999
        self.recon = (check_value, tol_pct, err <= tol_pct, round(err, 1), against)
        return self
    def tag(self):
        if self.source == "MEASURED":
            t = f"MEASURED off {self.sheet} [{_os.path.basename(self.view)}]"
        elif self.source == "GIVEN":
            t = f"GIVEN by {self.given_by} -- NOT independently measured"
        else:
            t = f"ASSUMED -- {self.note}"
        if self.recon:
            cv, tol, ok, err, ag = self.recon
            t += f" | reconcile {self.value} vs {cv}{(' '+ag) if ag else ''} = {err}% {'OK' if ok else 'FAIL'}"
        return t

def certify(quantities):
    """Return (ok, report). ok=False if ANY quantity is ASSUMED or has a FAILED
    reconciliation -- those cannot be shipped as verified. GIVEN passes but is flagged."""
    lines, ok = [], True
    for q in quantities:
        flag = ""
        if q.source == "ASSUMED":
            ok = False; flag = "   <== UNVERIFIED (assumed)"
        elif q.recon and not q.recon[2]:
            ok = False; flag = "   <== RECONCILE FAILED"
        elif q.source == "GIVEN":
            flag = "   <== given, not independently measured"
        lines.append(f"  {q.name:<22} {q.value:>8} {q.unit:<3} [{q.tag()}]{flag}")
    return ok, "\n".join(lines)


# ---------------------------------------------------------------------------
# CORE AREA CERTIFICATION -- schedules are CHECKS, never estimate quantities.
#
# Dugger exposed the exact failure this gate prevents: a printed 5,164-SF total
# was labeled "heated," then garage and porch components were added to it again.
# A core area can now reach pricing only as a roll-up of individually measured
# components.  Every component requires a second independent geometry measure
# and two real overlay files.  A schedule may be recorded below as a comparison,
# but it can never contribute a square foot to heated_sf or framing_sf.
# ---------------------------------------------------------------------------
CORE_AREA_TRADES = ("heated_sf", "framing_sf")
AREA_COMPONENT_CLASSES = (
    "heated",
    "garage",
    "covered",
    "workshop",
    "conditioned_accessory",
    "uncovered",
)
UNDER_ROOF_AREA_CLASSES = {
    "heated", "garage", "covered", "workshop", "conditioned_accessory"
}
HEATED_AREA_CLASSES = {"heated", "conditioned_accessory"}
_AREA_FORBIDDEN_METHOD_TOKENS = ("schedule", "given", "hardcod", "allowance")
_AREA_ENGINE_ORIGIN = "jnj_takeoff.plan-pixel-geometry.v1"
_AREA_ENGINE_METHODS = {
    "trace-footprint-clean",
    "trace-footprint-all-ink",
    "trace-enclosed-region",
}
_AREA_SCALE_METHODS = {
    "text-dims",
    "ocr-chains",
    "two-printed-dimension-checks",
}


def _area_evidence_errors(component_name, evidence, label):
    """Validate one geometry proof without trusting its claimed label."""
    errors = []
    prefix = f"{component_name} {label}"
    if not isinstance(evidence, dict):
        return [f"{prefix}: missing geometry evidence"]
    if evidence.get("source") != "MEASURED":
        errors.append(f"{prefix}: source must be MEASURED")
    try:
        qty = float(evidence.get("qty"))
        if qty <= 0:
            errors.append(f"{prefix}: quantity must be positive")
    except (TypeError, ValueError):
        errors.append(f"{prefix}: quantity must be numeric")
    if str(evidence.get("unit", "")).upper() != "SF":
        errors.append(f"{prefix}: unit must be SF")
    if evidence.get("sheet") in (None, ""):
        errors.append(f"{prefix}: sheet is required")
    method = str(evidence.get("method", "")).strip()
    if not method:
        errors.append(f"{prefix}: geometry method is required")
    elif any(token in method.lower() for token in _AREA_FORBIDDEN_METHOD_TOKENS):
        errors.append(f"{prefix}: {method!r} is not a geometry measurement method")
    view = evidence.get("view")
    if not view:
        errors.append(f"{prefix}: overlay view is required")
    elif not _os.path.isfile(view):
        errors.append(f"{prefix}: overlay view does not exist: {view}")
    confidence = str(evidence.get("confidence", "")).lower()
    if confidence not in ("high", "good"):
        errors.append(f"{prefix}: scale/trace confidence must be high or good")
    return errors


def _schedule_area_checks(rows, measured):
    """Return comparison-only schedule values.  Never feeds a priced quantity."""
    checks = []
    if not rows:
        return checks
    heated = sum(
        float(r.get("sqft") or 0)
        for r in rows
        if not _is_total_row(str(r.get("label", "")))
        and ("heated" in str(r.get("label", "")).lower()
             or "htd" in str(r.get("label", "")).lower())
    )
    framed = framed_under_roof_sf(rows)
    for trade, schedule_qty in (("heated_sf", heated), ("framing_sf", framed)):
        if not schedule_qty:
            continue
        measured_qty = measured.get(trade)
        delta_pct = (abs(measured_qty - schedule_qty) / schedule_qty * 100
                     if measured_qty is not None and schedule_qty else None)
        checks.append({
            "trade": trade,
            "schedule_qty": round(schedule_qty, 1),
            "measured_qty": round(measured_qty, 1) if measured_qty is not None else None,
            "delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
            "role": "comparison-only",
        })
    return checks


def certify_area_measurements(components, schedule_rows=None, tolerance_pct=2.0):
    """Certify heated and under-roof SF from measured component geometry.

    `components` is a list of:
      {name, classification, primary:{qty,unit,source,sheet,view,method,confidence},
       verification:{same fields}}

    The primary and verification must be independent (different method, sheet,
    or overlay), reconcile within tolerance, and both carry real overlay files.
    Aggregate labels such as TOTAL/UNDER ROOF are prohibited as components; the
    totals are derived here exactly once.  Schedule rows are recorded only as
    comparisons and never influence the certified quantities.
    """
    errors, normalized, seen = [], [], set()
    for raw in components or []:
        if not isinstance(raw, dict):
            errors.append("area component must be a mapping")
            continue
        name = str(raw.get("name", "")).strip()
        classification = str(raw.get("classification", "")).strip().lower()
        if not name:
            errors.append("area component name is required")
            continue
        key = name.lower()
        if key in seen:
            errors.append(f"{name}: duplicate area component")
        seen.add(key)
        if _is_total_row(name):
            errors.append(
                f"{name}: TOTAL/UNDER ROOF rows cannot be components; derive the total once"
            )
        if classification not in AREA_COMPONENT_CLASSES:
            errors.append(
                f"{name}: classification must be one of {AREA_COMPONENT_CLASSES}"
            )
        primary = raw.get("primary")
        verification = raw.get("verification")
        errors.extend(_area_evidence_errors(name, primary, "primary"))
        errors.extend(_area_evidence_errors(name, verification, "verification"))
        if not isinstance(primary, dict) or not isinstance(verification, dict):
            continue
        independent = (
            primary.get("method") != verification.get("method")
            or primary.get("sheet") != verification.get("sheet")
            or _os.path.abspath(str(primary.get("view", "")))
               != _os.path.abspath(str(verification.get("view", "")))
        )
        if not independent:
            errors.append(f"{name}: verification is not independent of the primary measure")
        try:
            primary_qty = float(primary.get("qty"))
            verification_qty = float(verification.get("qty"))
            delta_pct = (abs(primary_qty - verification_qty) / verification_qty * 100
                         if verification_qty else 999.0)
            if delta_pct > tolerance_pct:
                errors.append(
                    f"{name}: geometry measures differ by {delta_pct:.1f}% "
                    f"(limit {tolerance_pct:.1f}%)"
                )
        except (TypeError, ValueError):
            continue
        normalized.append({
            "name": name,
            "classification": classification,
            "qty": round(primary_qty, 2),
            "verification_qty": round(verification_qty, 2),
            "delta_pct": round(delta_pct, 2),
            "primary": dict(primary),
            "verification": dict(verification),
        })

    if not normalized:
        errors.append("no measured area components were supplied")
    heated_sf = sum(c["qty"] for c in normalized
                    if c["classification"] in HEATED_AREA_CLASSES)
    framing_sf = sum(c["qty"] for c in normalized
                     if c["classification"] in UNDER_ROOF_AREA_CLASSES)
    if heated_sf <= 0:
        errors.append("no heated component was measured")
    if framing_sf < heated_sf:
        errors.append("framing SF cannot be less than heated SF")

    measured = {"heated_sf": heated_sf, "framing_sf": framing_sf}
    schedule_checks = _schedule_area_checks(schedule_rows or [], measured)
    ok = not errors
    lines = []
    if ok:
        component_names = [c["name"] for c in normalized]
        sheets = sorted({str(e["sheet"]) for c in normalized
                         for e in (c["primary"], c["verification"])})
        proof = [{
            "component": c["name"],
            "classification": c["classification"],
            "primary_view": c["primary"]["view"],
            "verification_view": c["verification"]["view"],
            "delta_pct": c["delta_pct"],
        } for c in normalized]
        for trade, qty in measured.items():
            lines.append({
                "trade": trade,
                "qty": round(qty, 1),
                "unit": "SF",
                "source": "MEASURED",
                "method": "certified-component-rollup",
                "confidence": "high",
                "page": sheets,
                "note": f"derived once from: {', '.join(component_names)}",
                "certified": True,
                "proof": proof,
            })
    return {
        "ok": ok,
        "status": "certified" if ok else "more_information_required",
        "tolerance_pct": float(tolerance_pct),
        "components": normalized,
        "lines": lines,
        "schedule_checks": schedule_checks,
        "errors": errors,
    }


def certify_explicit_scale(ppf, checks, tolerance_pct=2.0):
    """Validate a raster-sheet scale against at least two printed dimensions.

    Each check is {printed_ft, measured_points, label?}.  PDF points are measured at
    matrix 1.0.  This is the fail-closed fallback for image-only sheets where vector
    scale detection cannot run.
    """
    errors, solved = [], []
    try:
        ppf = float(ppf)
        if ppf <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"ok": False, "errors": ["explicit ppf must be positive"]}
    if len(checks or []) < 2:
        return {"ok": False, "errors": ["explicit scale requires two printed-dimension checks"]}
    for index, check in enumerate(checks):
        try:
            printed_ft = float(check.get("printed_ft"))
            measured_points = float(check.get("measured_points"))
            if printed_ft <= 0 or measured_points <= 0:
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            errors.append(f"scale check {index + 1}: printed_ft and measured_points must be positive")
            continue
        check_ppf = measured_points / printed_ft
        delta_pct = abs(check_ppf - ppf) / ppf * 100
        solved.append({
            "label": check.get("label", f"check {index + 1}"),
            "printed_ft": printed_ft,
            "measured_points": measured_points,
            "ppf": round(check_ppf, 4),
            "delta_pct": round(delta_pct, 2),
        })
        if delta_pct > tolerance_pct:
            errors.append(
                f"scale check {index + 1}: {check_ppf:.3f} ppf differs from "
                f"{ppf:.3f} by {delta_pct:.1f}% (limit {tolerance_pct:.1f}%)"
            )
    return {
        "ok": not errors,
        "ppf": ppf,
        "confidence": "high" if not errors else "review",
        "method": "two-printed-dimension-checks",
        "checks": solved,
        "errors": errors,
    }


def _measure_area_evidence(doc, spec, evidence_dir, label):
    """Measure one area from plan pixels; the caller supplies WHERE, never the SF."""
    import fitz as _fitz
    page_i = int(spec["page"])
    page = doc[page_i]
    scale = _page_scale(page)
    if scale is None or scale.get("confidence") not in ("high", "good"):
        explicit = certify_explicit_scale(
            spec.get("ppf"), spec.get("scale_checks"),
            tolerance_pct=spec.get("scale_tolerance_pct", 2.0),
        )
        if not explicit["ok"]:
            raise ValueError(
                f"{label}: no verified scale on page {page_i + 1}: "
                + "; ".join(explicit["errors"])
            )
        scale = explicit
    clip = spec.get("clip")
    if clip is None:
        region = find_drawing_region(page, ppf=scale["ppf"])
        if region is None:
            raise ValueError(f"{label}: no drawing region found on page {page_i + 1}")
        clip = region["clip"]
    else:
        clip = _fitz.Rect(clip)
    method = str(spec.get("method", "clean-tracer")).lower()
    safe = _re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    view = _os.path.join(evidence_dir, f"{safe}.png")
    if method in ("clean", "clean-tracer", "trace_footprint_clean"):
        result = trace_footprint_clean(
            page, clip=clip, ppf=scale["ppf"], overlay_path=view
        )
        method_name = "trace-footprint-clean"
    elif method in ("all-ink", "ink", "trace_footprint"):
        result = trace_footprint(
            page, clip=clip, ppf=scale["ppf"], overlay_path=view
        )
        method_name = "trace-footprint-all-ink"
    elif method in ("enclosed", "enclosed-region", "trace_enclosed_region"):
        result = trace_enclosed_region(
            page, clip=clip, ppf=scale["ppf"], prefer=spec.get("prefer", "largest"),
            overlay_path=view,
        )
        method_name = "trace-enclosed-region"
    else:
        raise ValueError(f"{label}: unsupported geometry method {method!r}")
    if not result or not result.get("area_sf"):
        raise ValueError(f"{label}: geometry tracer returned no area")
    return {
        "qty": round(float(result["area_sf"]), 2),
        "unit": "SF",
        "source": "MEASURED",
        "sheet": spec.get("sheet", f"page {page_i + 1}"),
        "page": page_i,
        "view": view,
        "method": method_name,
        "confidence": scale["confidence"],
        "ppf": scale["ppf"],
        "origin": _AREA_ENGINE_ORIGIN,
        "scale_method": scale["method"],
        "scale_checks": scale.get("checks", []),
    }


def measure_and_certify_area_components(plan_pdf, component_specs, evidence_dir,
                                        schedule_rows=None, tolerance_pct=2.0):
    """Measure primary + verification geometry for every area component, then certify."""
    import fitz as _fitz
    if not evidence_dir:
        return {
            "ok": False, "status": "more_information_required", "lines": [],
            "components": [], "schedule_checks": [],
            "errors": ["evidence_dir is required for measured area overlays"],
        }
    _os.makedirs(evidence_dir, exist_ok=True)
    doc = _fitz.open(plan_pdf)
    measured, measurement_errors = [], []
    try:
        for raw in component_specs or []:
            name = str(raw.get("name", "area component")).strip()
            try:
                primary = _measure_area_evidence(
                    doc, raw["primary"], evidence_dir, f"{name}-primary"
                )
                verification = _measure_area_evidence(
                    doc, raw["verification"], evidence_dir, f"{name}-verification"
                )
                measured.append({
                    "name": name,
                    "classification": raw.get("classification"),
                    "primary": primary,
                    "verification": verification,
                })
            except (KeyError, TypeError, ValueError) as exc:
                measurement_errors.append(f"{name}: {exc}")
    finally:
        doc.close()
    result = certify_area_measurements(
        measured, schedule_rows=schedule_rows, tolerance_pct=tolerance_pct
    )
    if measurement_errors:
        result["errors"] = measurement_errors + result["errors"]
        result["ok"] = False
        result["status"] = "more_information_required"
        result["lines"] = []
    return result


def certify_takeoff_for_pricing(takeoff, required_area_trades=CORE_AREA_TRADES):
    """Fail closed unless core pricing areas came through the measured-area gate."""
    errors = []
    area_cert = takeoff.get("area_certification") or {}
    if not area_cert.get("ok") or area_cert.get("status") != "certified":
        errors.append("core area certification is missing or failed")
    rechecked = certify_area_measurements(
        area_cert.get("components", []),
        tolerance_pct=area_cert.get("tolerance_pct", 2.0),
    )
    if not rechecked.get("ok"):
        errors.append(
            "stored area proof does not re-certify: "
            + "; ".join(rechecked.get("errors", []))
        )
    for component in area_cert.get("components", []):
        component_name = component.get("name", "area component")
        for label in ("primary", "verification"):
            evidence = component.get(label) or {}
            prefix = f"{component_name} {label}"
            if evidence.get("origin") != _AREA_ENGINE_ORIGIN:
                errors.append(
                    f"{prefix}: evidence was not produced by the plan-pixel measurement engine"
                )
            if evidence.get("method") not in _AREA_ENGINE_METHODS:
                errors.append(f"{prefix}: unsupported engine geometry method")
            if evidence.get("scale_method") not in _AREA_SCALE_METHODS:
                errors.append(f"{prefix}: verified scale method is missing")
            try:
                if int(evidence.get("page")) < 0 or float(evidence.get("ppf")) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{prefix}: page and positive pixels-per-foot are required")
            if evidence.get("scale_method") == "two-printed-dimension-checks" \
                    and len(evidence.get("scale_checks") or []) < 2:
                errors.append(f"{prefix}: two printed-dimension scale checks are required")
    rechecked_qty = {line["trade"]: line["qty"]
                     for line in rechecked.get("lines", [])}
    by_trade = {}
    for line in takeoff.get("lines", []):
        by_trade.setdefault(line.get("trade"), []).append(line)
    for trade in required_area_trades:
        matches = by_trade.get(trade, [])
        if len(matches) != 1:
            errors.append(f"{trade}: expected one certified line, found {len(matches)}")
            continue
        line = matches[0]
        if line.get("source") != "MEASURED":
            errors.append(f"{trade}: source must be MEASURED, got {line.get('source')!r}")
        if line.get("method") != "certified-component-rollup" or not line.get("certified"):
            errors.append(f"{trade}: did not come from certified component geometry")
        if "schedule" in str(line.get("source", "")).lower() \
                or "schedule" in str(line.get("method", "")).lower():
            errors.append(f"{trade}: schedules are comparison-only and cannot be priced")
        if not line.get("proof"):
            errors.append(f"{trade}: measurement proof is missing")
        if trade in rechecked_qty and float(line.get("qty", -1)) != rechecked_qty[trade]:
            errors.append(
                f"{trade}: priced quantity {line.get('qty')} does not match re-certified "
                f"geometry {rechecked_qty[trade]}"
            )
    return not errors, errors

# ---------------------------------------------------------------------------
# DESCRIPTION LINT (Zegarra 7/8/26 forcing function) — the Buildern Import
# "Description" column is READ BY THE CLIENT for scope clarification. It must be
# plain-English scope, NEVER takeoff math/derivation, internal SRC/CONFIRM/FLAG
# tags, or a bare quantity echo (the qty already has its own Quantity + Unit
# columns). This reproduces the EXACT Zegarra leak that shipped -- descriptions
# like "3261 SF x4\" = 44.30 CY", "base 8000 + 23x450 + 6x400 = 20750", "1 ea",
# and "[CONFIRM: garage foam?]" -- and blocks it before delivery. A scope line
# that ENDS with a qty clarifier ("... slab -- 3,261 SF (incl. waste)") passes;
# only a BARE echo with no scope fails. Run on the finished import; ship at 0.
# ---------------------------------------------------------------------------
import re as _re

_DESC_BARE_QTY = _re.compile(
    r"^\s*[\d,]+(?:\.\d+)?\s*"
    r"(sf|lf|sy|cy|cf|ea|each|pair|roll|load|month|mo|ls|sq|gal|hr|day|ton|"
    r"unit|bag|bdl|sheet|yd|board|stick)\b\s*$", _re.I)
# internal-only tags (uppercase, as they appear in the SRC/FLAG trail)
_DESC_FLAG_TOKENS = ("CONFIRM", "FLAG:", "SRC:", "SRC ", "UNLOCKED", "MEASURED",
                     "ASSUMED", "COUNTED", "CALC", "TODO", "XXX")
# arithmetic / derivation signatures that never belong in client-facing text
_DESC_MATH = _re.compile(
    r"(=|->|→|≈|\[|\]|x\d*\.\d|x\d+\"|\bSF\s*x|\d[\d,\.]*\s*\+\s*\d)", _re.I)


def lint_buildern_descriptions(rows):
    """Forcing function for the CLIENT-FACING Description column. Returns a list
    of violations; a clean import returns []. `rows` may be:
      - a path to the Buildern Import *.xlsx (auto-detects Name/Description cols), or
      - an iterable of (name, description) pairs or dicts with those keys.
    Delivery REQUIRES zero findings. Each violation is
    {name, description, reason}."""
    pairs = []
    if isinstance(rows, str):
        import openpyxl
        wb = openpyxl.load_workbook(rows, data_only=True)
        ws = wb.active
        hdr = [str(c.value or "").strip().lower() for c in ws[1]]
        ni = hdr.index("name") if "name" in hdr else None
        if "description" not in hdr:
            raise ValueError("no 'Description' column in " + rows)
        di = hdr.index("description")
        for r in ws.iter_rows(min_row=2, values_only=True):
            nm = r[ni] if ni is not None else ""
            if ni is not None and (nm is None or str(nm).strip() == ""):
                continue  # skip blank/spacer rows
            pairs.append((nm, r[di]))
    else:
        for row in rows:
            if isinstance(row, dict):
                pairs.append((row.get("name") or row.get("Name") or "",
                              row.get("description", row.get("Description"))))
            else:
                pairs.append((row[0], row[1]))

    violations = []
    for nm, d in pairs:
        s = "" if d is None else str(d).strip()
        if s == "":
            why = "blank description"
        elif any(t in s for t in _DESC_FLAG_TOKENS):
            why = "internal source/CONFIRM/FLAG tag leaked to the client"
        elif _DESC_MATH.search(s):
            why = "takeoff math/derivation in a client-facing description"
        elif _DESC_BARE_QTY.match(s):
            why = "bare quantity echo, no scope (qty is already its own column)"
        else:
            continue
        violations.append({"name": nm, "description": s, "reason": why})
    return violations

# ---------------------------------------------------------------------------
# SELF-LEARNING (Phase 4b) — split by SAFETY, not lumped together:
#   IDENTIFICATION (what a symbol/term/room IS) -> auto-banks with a source trail.
#     Low-stakes + self-correcting (next plan's legend or a reconcile catches an error),
#     and every entry is cited, so it's auditable. Research once, reuse forever.
#   VALUATION (what a thing COSTS) -> NEVER auto-learned. A bad rate compounds silently
#     across every future bid (the estimator's cardinal sin). Rates are proposed as
#     CANDIDATES with evidence and only enter the LOCKED RATE_BOOK by human confirmation
#     against actuals -- the calibration discipline, formalized as a queue.
# ---------------------------------------------------------------------------
def _reference_dir():
    import os
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "reference")


def _cache_path():
    import os
    return os.path.join(_reference_dir(), "research_cache.json")


def _load_cache(path=None):
    import json
    import os
    path = path or _cache_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"symbols": {}, "terms": {}, "room_types": {}}


def bank_knowledge(term, answer, source, kind="terms", path=None):
    """SELF-LEARN one identification fact (symbol / term / room_type). Writes it to the
    persistent research cache so it's researched ONCE then reused (keeps the cheap/local
    runtime fast, makes the engine smarter each job). REFUSES to bank an empty answer or
    a sourceless fact (no fact without a source -- the mandate). Re-banking updates +
    keeps a small history. Returns the stored record."""
    import json
    import datetime
    if not answer or not str(answer).strip():
        raise ValueError("refuse to bank an empty answer")
    if not source or not str(source).strip():
        raise ValueError("refuse to bank a sourceless fact")
    if kind not in ("symbols", "terms", "room_types"):
        raise ValueError(f"unknown kind {kind!r}")
    path = path or _cache_path()
    cache = _load_cache(path)
    key = term.strip().lower()
    prev = cache[kind].get(key)
    rec = {"term": term.strip(), "answer": str(answer).strip(), "source": str(source),
           "learned": datetime.date.today().isoformat(),
           "seen": (prev["seen"] + 1 if prev else 1)}
    cache[kind][key] = rec
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False, sort_keys=True)
    return rec


def recall_knowledge(term, kind=None, path=None):
    """Look up a banked identification fact (any kind if kind=None). Returns the record
    or None. This is the 'reuse' half of the self-learning loop."""
    cache = _load_cache(path)
    key = term.strip().lower()
    kinds = (kind,) if kind else ("symbols", "terms", "room_types")
    for k in kinds:
        if key in cache.get(k, {}):
            return dict(cache[k][key], kind=k)
    return None


DRYWALL_WASTE = 0.10
DRYWALL_RATE_PER_SF = 1.44


def drywall_turnkey(net_surface_sf, waste=DRYWALL_WASTE, rate=DRYWALL_RATE_PER_SF):
    """Price Level 4 drywall from the measured NET room-by-room surface.

    V3 forcing function: applies Jason's approved 10% waste exactly once, then
    prices the waste-adjusted order quantity at $1.44/SF.
    """
    net_sf = float(net_surface_sf)
    if net_sf < 0:
        raise ValueError("net drywall surface cannot be negative")
    if waste < 0 or rate < 0:
        raise ValueError("drywall waste and rate cannot be negative")
    order_sf = round(net_sf * (1 + waste), 1)
    direct_cost = round(order_sf * rate, 2)
    return {"net_surface_sf": round(net_sf, 1),
            "waste_pct": round(waste * 100, 1),
            "order_surface_sf": order_sf,
            "rate_per_order_sf": round(rate, 4),
            "direct_cost": direct_cost}


def load_rate_book(path=None):
    """The FULL machine-readable rate book: every line of the active estimate
    template (603 lines / 504 priced), extracted 7/6/26 and VERIFIED current against all
    calibration-locked rates (punch $1.75, shiplap $5.50, encapsulation $3, mudroom
    $300/LF, garage wrap $200, foam 1.35/1.00 -- cal #53).

    JASON LIVE RATES 2026-08-04 (supersede the extracted template values; each carries an
    entry in book["overrides"] with its evidence): framing lumber $10/SF under-roof,
    framing labor $6.00/SF under-roof, electrical $6.00/SF of HEATED + GARAGE with PORCHES
    EXCLUDED even when under roof, siding vertical B&B $4.40/SF wall. CONFIRMED unchanged:
    horizontal lap Hardi $3.30/SF wall, drywall $1.44/SF.

    ⚠ price_lines() reads book["lines"], NOT book["overrides"] -- an override is the audit
    trail, so a new rate must be written into BOTH or it will not price.
    Rates change ONLY via rate_candidates.json + Jason's confirmation, then re-extract."""
    import json
    import os
    p = path or os.path.join(_reference_dir(), "rate_book.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def find_rate(query, book=None):
    """Search the full rate book by name/group/description substring (case-insensitive).
    Returns matching lines, best (shortest-name) first -- use to locate the template
    line for a scope item instead of hand-reading the xlsx."""
    book = book or load_rate_book()
    q = query.lower()
    hits = [l for l in book["lines"]
            if q in l["name"].lower() or q in l["group"].lower()
            or q in l["description"].lower()]
    return sorted(hits, key=lambda l: (q not in l["name"].lower(), len(l["name"])))


def price_lines(quantities, book=None):
    """Price ANY set of template lines in code: quantities = {exact line name: qty}
    (name collisions across groups -> qualify as 'Group/Name'). Uses each line's own
    unit_cost + markup_pct from the rate book -> assemble_estimate. This is the FULL
    template wired into the coded pricing path: measured or hand-taken-off quantities
    in, priced estimate out. Unknown names raise (never silently dropped)."""
    book = book or load_rate_book()
    by_name, by_qual = {}, {}
    for l in book["lines"]:
        by_name.setdefault(l["name"], []).append(l)
        by_qual.setdefault(l["group"] + "/" + l["name"], []).append(l)   # LIST, not last-wins

    def _resolve(name):
        cands = by_qual.get(name) or by_name.get(name)
        if not cands:
            raise KeyError(f"no template line named {name!r} -- use find_rate() to locate it")
        if len(cands) == 1:
            return cands[0]
        # a real Buildern group holds an ASSEMBLY container ($0) + priced leaves under the SAME
        # name -> price the LEAF, never the $0 container (the old last-wins could silently pick
        # the container -> a $0 line). Collapse exact-duplicate leaves; raise on genuine conflict.
        leaves = [c for c in cands if str(c.get("cost_type", "")).upper() != "ASSEMBLY"]
        uniq = {(c["cost_type"], c["unit_cost"], c["unit"]) for c in leaves}
        if len(uniq) == 1 and leaves:
            return leaves[0]
        if "/" not in name:
            raise KeyError(f"{name!r} is ambiguous across groups "
                           f"{[c['group'] for c in cands]} -- qualify as 'Group/Name'")
        raise KeyError(f"{name!r} maps to {len(cands)} template lines with differing rates "
                       f"{sorted(uniq)} -- rate book has a true duplicate; resolve it (never priced silently)")

    est_lines = []
    for name, qty in quantities.items():
        l = _resolve(name)
        est_lines.append({"name": l["name"], "cost_type": l["cost_type"], "qty": qty,
                          "unit_cost": l["unit_cost"], "unit": l["unit"],
                          "group": l["group"], "markup_pct": l["markup_pct"]})
    return assemble_estimate(est_lines)


def propose_rate(trade, unit_cost, unit, evidence, path=None):
    """VALUATION candidate -- the HUMAN-GATED half. Files a proposed rate WITH its evidence
    to rate_candidates.json. It NEVER touches RATE_BOOK: a rate is only priced once Jason
    (or I) confirm it against actuals and hand-add it to the locked book. This makes the
    calibration discipline a queue instead of prose, without ever letting the engine
    silently re-price itself. Returns the candidate record (status 'pending')."""
    import json
    import os
    import datetime
    if not evidence or not str(evidence).strip():
        raise ValueError("a rate candidate MUST carry its evidence (source actual/quote)")
    p = path or os.path.join(_reference_dir(), "rate_candidates.json")
    queue = []
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            queue = json.load(f)
    rec = {"trade": trade, "unit_cost": float(unit_cost), "unit": unit,
           "evidence": str(evidence), "proposed": datetime.date.today().isoformat(),
           "status": "pending",
           "note": "ADVISORY ONLY -- not priced until confirmed against actuals + "
                   "hand-added to RATE_BOOK (estimator mandate)"}
    queue.append(rec)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)
    return rec


def resolve_unknown(term, pdf=None, pages=None, known=None):
    """RESEARCH ROUTINE -- the moment I don't know a symbol/note/convention, resolve it
    in order instead of guessing: (1) the PLAN'S OWN legend / note schedule (plans define
    their own symbols -- always look here first), (2) banked calibration/template knowledge,
    (3) UNRESOLVED -> must WebSearch the convention or ASK Jason (never assume).
    Returns {term, answer, source, resolved}. A measurement that depends on an UNRESOLVED
    term must not proceed."""
    import re
    # 1) the plan's own note schedule / legend
    if pdf is not None:
        import fitz
        d = fitz.open(pdf)
        for i in (pages if pages is not None else range(d.page_count)):
            for ln in d[i].get_text("text").splitlines():
                s = ln.strip()
                if term.lower() in s.lower() and (("=" in s) or len(s.split()) >= 3) and len(s) < 90:
                    try:
                        bank_knowledge(term, s, f"PLAN legend/notes p{i}", kind="terms")
                    except Exception:
                        pass
                    return {"term": term, "answer": s, "source": f"PLAN legend/notes p{i}", "resolved": True}
    # 2) banked knowledge -- the SELF-LEARNED cache first, then any passed-in dict
    hit = recall_knowledge(term)
    if hit:
        return {"term": term, "answer": hit["answer"],
                "source": f"self-learned cache ({hit['source']}, seen {hit['seen']}x)",
                "resolved": True}
    if known and term.lower() in known:
        return {"term": term, "answer": known[term.lower()], "source": "banked calibration", "resolved": True}
    # 3) not known anywhere I've checked -> research or ask; DO NOT assume
    return {"term": term, "answer": None,
            "source": "UNRESOLVED -> WebSearch the convention or ASK Jason (do NOT guess)",
            "resolved": False}


# ---------------------------------------------------------------------------
# SHEET ENUMERATION FORCING FUNCTION -- "no completeness without enumeration," in CODE.
# Built because banked diligence fails in the moment: I looked at 4 of 11 Peterson sheets and
# claimed "no roof plan" -- it was sheet 4, named in the cover index I skipped. For Level Ground
# there is no human backstop, so this must be a MECHANISM, not a promise. Same shape as Quantity/
# certify: every page must be EXAMINED with a rendered VIEW FILE THAT EXISTS (proof I looked),
# each classified by role; certify() refuses to pass while ANY page is unexamined, refuses to
# honor an "X is ABSENT" claim until EVERY page is classified, and FAILS LOUD if a core sheet
# (roof plan, foundation, floor plan, elevation) isn't found -- the exact miss it prevents.
# ---------------------------------------------------------------------------
def render_all_sheets(pdf_path, out_dir, zoom=1.5):
    """Render EVERY page to out_dir/sheet_{i}.png so no sheet can be skipped for lack of a view.
    Returns [(i, path)]. Use each path as the view= proof when you examine() that page."""
    import fitz
    _os.makedirs(out_dir, exist_ok=True)
    d = fitz.open(pdf_path)
    out = []
    for i in range(d.page_count):
        p = _os.path.join(out_dir, f"sheet_{i}.png")
        d[i].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(p)
        out.append((i, p))
    return out


class SheetLedger:
    """Forcing function for FULL sheet enumeration. examine() EVERY page (role + a view file that
    exists); read the cover index with set_index() when the set has one; then certify(). It will
    not pass while any page is unexamined or a required core sheet is missing, and assert_absent()
    won't let you say a sheet type is missing until the whole set is enumerated."""
    ROLES = ("cover", "site", "foundation", "floor_plan", "roof_plan", "framing", "elevation",
             "section", "electrical", "plumbing", "mechanical", "schedule", "detail", "notes", "other")
    CORE = ("foundation", "floor_plan", "roof_plan", "elevation")   # a residential set must have these
    # major STANDALONE sheet types worth cross-checking vs the cover index. 'detail'/'notes'/
    # 'schedule' are excluded -- they're usually embedded IN another sheet (e.g. "Cross Section +
    # Foundation DETAILS"), so a substring match there is not a real missing sheet.
    INDEXED = ("site", "foundation", "floor_plan", "roof_plan", "framing", "elevation",
               "section", "electrical", "plumbing", "mechanical")

    def __init__(self, pdf_path, n_pages):
        self.pdf_path, self.n = pdf_path, n_pages
        self.pages = {i: None for i in range(n_pages)}
        self.index = None                                          # [(num_or_None, name)] from the cover

    def set_index(self, sheets):
        """Record the authoritative sheet list read off the cover index (name per row). Enables
        the cross-check: if the index names a ROOF PLAN, certify FAILS unless a page is classified
        roof_plan."""
        self.index = list(sheets)
        return self

    def examine(self, page_i, role, view, title=None, note=None):
        if role not in self.ROLES:
            raise ValueError(f"role must be one of {self.ROLES}, got {role!r}")
        if not view or not _os.path.exists(view):
            raise ValueError(f"page {page_i}: examine requires view= a rendered file that EXISTS "
                             f"(render AND look before you classify -- no skipping)")
        self.pages[page_i] = {"role": role, "view": view, "title": title, "note": note}
        return self

    def unexamined(self):
        return [i for i, v in self.pages.items() if v is None]

    def pages_with_role(self, role):
        return [i for i, v in self.pages.items() if v and v["role"] == role]

    def assert_absent(self, role):
        """True only if `role` is genuinely absent AND the whole set was enumerated first.
        Blocks the exact 'there is no roof plan' claim-from-a-partial-look that started this."""
        if self.unexamined():
            raise ValueError(f"cannot claim '{role}' is ABSENT: {len(self.unexamined())} of "
                             f"{self.n} sheets still UNEXAMINED {self.unexamined()} -- look first")
        return not self.pages_with_role(role)

    def _index_expects(self, role):
        if not self.index:
            return False
        key = {"roof_plan": "roof", "floor_plan": "floor", "foundation": "foundation",
               "elevation": "elevation", "section": "section", "electrical": "electrical",
               "site": "site"}.get(role, role)
        return any(key in str(name).lower() for _, name in self.index)

    def certify(self, require=CORE):
        """(ok, report). ok=False if any page is unexamined, a required core sheet is missing, or
        the cover index names a sheet type that no page was classified as."""
        lines, ok = [], True
        un = self.unexamined()
        if un:
            ok = False
            lines.append(f"  UNEXAMINED PAGES: {un}   <== every sheet must be examined (no skipping)")
        for i in range(self.n):
            v = self.pages[i]
            lines.append(f"  p{i:<2} {v['role'] if v else '??? UNEXAMINED':<12}"
                         f"{'  ['+_os.path.basename(v['view'])+']' if v else ''}"
                         f"{'  '+v['title'] if v and v.get('title') else ''}")
        for role in require:
            found = self.pages_with_role(role)
            if not found:
                ok = False
                lines.append(f"  MISSING CORE SHEET: '{role}' not found on any page   <== FAIL")
            else:
                lines.append(f"  core '{role}': p{found}")
        if self.index:
            for role in self.INDEXED:
                if self._index_expects(role) and not self.pages_with_role(role):
                    ok = False
                    lines.append(f"  INDEX names a '{role}' sheet but NO page classified as one   <== FAIL")
        return ok, "\n".join(lines)


DEFAULT_MARKUP_PCT = {"MATERIAL": 15.0, "LABOR": 7.0, "SUBCONTRACTOR": 7.0,
                      "EQUIPMENT": 7.0, "FEE": 15.0, "ALLOWANCE": 8.0}


def assemble_estimate(lines):
    """Buildern-convention ESTIMATE ASSEMBLY in code (Phase 5 adapter math, landed
    7/6/26): per line builder_cost = qty * unit_cost, markup = builder_cost * pct/100
    (line's own pct if given, else DEFAULT_MARKUP_PCT by cost type -- MATERIAL 15 =
    tax+markup, LABOR/SUB/EQUIP 7, FEE 15, ALLOWANCE 8 = tax; Jason's convention,
    cal #40/feedback), amount = builder_cost + markup. ASSEMBLY container rows carry 0.
    VALIDATED against Jason's Roberts reference estimate line-by-line: 589 lines,
    builder 465,252 / markup 51,337 / amount 516,589 reproduced (1 rounding exception
    in the file itself). NOTE the file's Buildern FOOTER (Total 649,312) does not equal
    its own items and cal #1's narrative sell 591,341 appears nowhere in the file --
    ground-truth discrepancy logged #49, sell-level assert parked pending Jason.
    lines: [{cost_type, qty, unit_cost, markup_pct?, group?}] ->
    {lines: [...], by_group, by_cost_type, builder_cost, markup, amount}."""
    out = {"lines": [], "by_group": {}, "by_cost_type": {},
           "builder_cost": 0.0, "markup": 0.0, "amount": 0.0}
    for ln in lines:
        ct = str(ln.get("cost_type", "")).upper()
        qty = float(ln.get("qty") or 0)
        uc = float(ln.get("unit_cost") or 0)
        bc = qty * uc
        pct = ln.get("markup_pct")
        if pct is None:
            pct = 0.0 if ct == "ASSEMBLY" else DEFAULT_MARKUP_PCT.get(ct, 7.0)
        mk = bc * float(pct) / 100.0
        amt = bc + mk
        rec = dict(ln, builder_cost=round(bc, 2), markup_pct=float(pct),
                   markup=round(mk, 2), amount=round(amt, 2))
        out["lines"].append(rec)
        g = ln.get("group") or "(ungrouped)"
        out["by_group"][g] = round(out["by_group"].get(g, 0.0) + amt, 2)
        out["by_cost_type"][ct] = round(out["by_cost_type"].get(ct, 0.0) + amt, 2)
        out["builder_cost"] += bc
        out["markup"] += mk
        out["amount"] += amt
    for k in ("builder_cost", "markup", "amount"):
        out[k] = round(out[k], 2)
    return out


def _page_scale(page):
    """Best-available scale for a page with method + confidence. Order: text-layer dim
    voting (detect_scale) -> OCR chain-token fallback (detect_scale_ocr, zero-text sheets).
    Returns {ppf, method, confidence} or None — NEVER a guessed/nominal scale."""
    try:
        sc = detect_scale(page)
        if sc and sc.get("ppf") and sc.get("confidence") in ("high", "good", "review"):
            return {"ppf": sc["ppf"], "method": "text-dims", "confidence": sc["confidence"]}
    except Exception:
        pass
    try:
        sc = detect_scale_ocr(page)
        if sc:
            return {"ppf": sc["ppf"], "method": "ocr-chains", "confidence": sc["confidence"]}
    except Exception:
        pass
    return None


def run_takeoff(plan_pdf, sheet_map, pitch_calls=None, underroof_sf=None,
                overhang_in=(12.0, 17.0), area_specs=None, evidence_dir=None,
                area_tolerance_pct=2.0):
    """Deterministic plan measurement entrypoint.

    The model identifies WHERE to measure; code calculates the quantities. Area schedules
    are extracted only into `checks`. Core heated/framing quantities are emitted only when
    `area_specs` supplies two independent geometry regions for every component and both
    measurements reconcile within `area_tolerance_pct`. Without that proof the result is
    `more_information_required`, and estimate_from_takeoff() refuses to price it.

    The legacy `underroof_sf` argument is deliberately ignored. Roof geometry uses the
    certified measured framing_sf so an external total can never bypass the area gate.
    """
    import fitz as _f
    doc = _f.open(plan_pdf)
    out = {"plan": str(plan_pdf), "pages": {}, "lines": [], "checks": [],
           "not_measured": [], "assumptions": [],
           "status": "more_information_required"}

    def add(trade, qty, unit, source, method, conf, page, note=""):
        out["lines"].append({"trade": trade, "qty": round(float(qty), 1), "unit": unit,
                             "source": source, "method": method, "confidence": conf,
                             "page": page, "note": note})

    # --- schedule: comparison only; never emits heated/framed SF ----------------------
    schedule_rows = []
    pi = sheet_map.get("sqft_schedule")
    if pi is not None:
        page = doc[pi]
        rows = None
        try:
            rows = read_sqft_schedule(page)
        except Exception:
            rows = None
        if rows:
            schedule_rows = rows
        else:
            try:
                ocr_result = read_sqft_schedule_ocr(page)
            except Exception:
                ocr_result = None
            if ocr_result and ocr_result.get("rows"):
                schedule_rows = [
                    {"label": row.get("label", ""), "sqft": row.get("sqft"),
                     "klass": classify_area_row(row.get("label", ""))}
                    for row in ocr_result["rows"] if row.get("sqft")
                ]
        out["checks"].append({
            "check": "area_schedule",
            "page": pi,
            "role": "comparison-only",
            "rows": schedule_rows,
            "note": "schedule values cannot feed estimate quantities",
        })

    if area_specs:
        area_cert = measure_and_certify_area_components(
            plan_pdf, area_specs, evidence_dir, schedule_rows=schedule_rows,
            tolerance_pct=area_tolerance_pct,
        )
    else:
        area_cert = {
            "ok": False,
            "status": "more_information_required",
            "tolerance_pct": float(area_tolerance_pct),
            "components": [],
            "lines": [],
            "schedule_checks": _schedule_area_checks(schedule_rows, {}),
            "errors": [
                "core areas were not measured: supply area_specs with primary and "
                "verification geometry for every component"
            ],
        }
    out["area_certification"] = area_cert
    out["status"] = area_cert["status"]
    if area_cert["ok"]:
        out["lines"].extend(area_cert["lines"])
    else:
        for trade in CORE_AREA_TRADES:
            out["not_measured"].append({
                "trade": trade,
                "page": sheet_map.get("floor_area", sheet_map.get("sqft_schedule")),
                "why": "; ".join(area_cert["errors"]),
            })
    if underroof_sf is not None:
        out["assumptions"].append(
            "ignored legacy underroof_sf argument; roof/framing must use certified measured geometry"
        )

    # --- foundation: enclosed region + wall loops --------------------------------------
    pi = sheet_map.get("foundation")
    if pi is not None:
        page = doc[pi]
        sc = _page_scale(page)
        out["pages"][pi] = sc
        if sc is None:
            out["not_measured"].append({"trade": "foundation_wall_lf", "page": pi,
                                        "why": "no scale solvable from sheet"})
        else:
            r = find_drawing_region(page, ppf=sc["ppf"])
            if r is not None:
                t = trace_enclosed_region(page, r["clip"], ppf=sc["ppf"],
                                          prefer="largest")
                if t:
                    add("foundation_wall_lf", t["perimeter_lf"], "LF", "MEASURED",
                        "enclosed-region", sc["confidence"], pi,
                        "inside-face; scope (poured vs framed/ledge) needs heights")
                    add("basement_area_sf", t["area_sf"], "SF", "MEASURED",
                        "enclosed-region", sc["confidence"], pi)
                loops = foundation_wall_loops(page, ppf=sc["ppf"])
                if loops:
                    add("foundation_main_loop_lf", loops[0]["perim_lf"], "LF",
                        "MEASURED", "wall-pairs", sc["confidence"], pi,
                        f"{len(loops)} enclosed loops total")

    # --- slab: BOTH tracers, reconciled (cal #46 tracer-choice rule, coded) -------------
    pi = sheet_map.get("slab")
    if pi is not None:
        page = doc[pi]
        sc = _page_scale(page)
        out["pages"][pi] = sc
        if sc is None:
            out["not_measured"].append({"trade": "slab_area_sf", "page": pi,
                                        "why": "no scale solvable from sheet"})
        else:
            a_clean = a_ink = None
            t1 = trace_footprint_clean(page, ppf=sc["ppf"])
            if t1:
                a_clean = t1["area_sf"]
            r = find_drawing_region(page, ppf=sc["ppf"], pad_ft=8.0)
            if r is not None:
                t2 = trace_footprint(page, r["clip"], ppf=sc["ppf"])
                if t2:
                    a_ink = t2["area_sf"]
            if a_clean and a_ink:
                hi, lo = max(a_clean, a_ink), min(a_clean, a_ink)
                if (hi - lo) / hi <= 0.08:
                    add("slab_area_sf", (a_clean + a_ink) / 2, "SF", "MEASURED",
                        "two-tracer-agree", "high", pi,
                        f"clean {a_clean:,.0f} / all-ink {a_ink:,.0f}")
                else:
                    # dashed-boundary sheets read LOW on the clean tracer (cal #46):
                    # report the all-ink number, keep both visible, flag review
                    add("slab_area_sf", a_ink, "SF", "MEASURED", "all-ink-tracer",
                        "review", pi,
                        f"tracers disagree: clean {a_clean:,.0f} vs all-ink "
                        f"{a_ink:,.0f} — dashed-boundary sheet suspected (cal #46)")
            elif a_ink or a_clean:
                add("slab_area_sf", a_ink or a_clean, "SF", "MEASURED",
                    "single-tracer", "review", pi, "only one tracer returned")
            else:
                out["not_measured"].append({"trade": "slab_area_sf", "page": pi,
                                            "why": "both tracers returned None"})

    # --- roof: face decomposition (needs verified pitch callouts) -----------------------
    pi = sheet_map.get("roof")
    if pi is not None:
        certified_underroof = next(
            (line["qty"] for line in area_cert.get("lines", [])
             if line.get("trade") == "framing_sf" and line.get("certified")),
            None,
        )
        if pitch_calls and certified_underroof:
            page = doc[pi]
            clip = sheet_map.get("roof_clip")
            clip = _f.Rect(clip) if clip else (find_drawing_region(page) or
                                               {"clip": page.rect})["clip"]
            rz = roof_zone_surface(page, clip, pitch_calls, certified_underroof,
                                   overhang_in=overhang_in)
            if rz:
                lo_k = min(rz["bounds"]); hi_k = max(rz["bounds"])
                add("roof_surface_sq", rz["squares"], "sq", "MEASURED",
                    "face-decomposition", "review" if rz["conflicts"] else "high", pi,
                    f"bounds {rz['bounds'][lo_k]['squares']}-"
                    f"{rz['bounds'][hi_k]['squares']} sq over overhang range; "
                    f"ppf solved {rz['ppf']}")
            else:
                out["not_measured"].append({"trade": "roof_surface_sq", "page": pi,
                                            "why": "face decomposition failed"})
        else:
            out["not_measured"].append(
                {"trade": "roof_surface_sq", "page": pi,
                 "why": "needs eye/VLM-verified pitch_calls + certified measured framing_sf "
                        "(OCR pitch trap, cal #43 — never automated away)"})
            out["assumptions"].append(
                "roof not measured: supply pitch callouts from a verified read")
    doc.close()
    return out


RATE_BOOK = {
    # LOCKED calibrated rates only (each cites its calibration data point). A trade
    # belongs here ONLY when the rate is validated on actuals and the quantity basis is
    # exactly what run_takeoff emits -- no placeholder pricing (feedback: use decoded
    # rates, never defaults).
    "framing_sf": [{"name": "Framing Labor (blended, per level under roof)",
                    "cost_type": "LABOR", "unit_cost": FRAMING_LABOR_RATE, "unit": "SF",
                    "group": "Framing", "basis": "cal #33: $6.50 locked on 3 actuals"}],
    "heated_sf": [{"name": "Punch-Out Allowance", "cost_type": "SUBCONTRACTOR",
                   "unit_cost": 1.75, "unit": "SF", "group": "Punch Out",
                   "basis": "cal #41: $1.75/heated SF from 4 closed-job actuals"}],
    "roof_surface_sq": [{"name": "Roofing (arch shingle, waste-loaded all-in)",
                         "cost_type": "SUBCONTRACTOR", "unit_cost": 227.70, "unit": "sq",
                         "group": "Roofing",
                         "basis": "cal #13: $1.98/SF all-in x 1.15 shingle waste x 100 "
                                  "SF/sq = $227.70/sq; reconciles Southern Peterson "
                                  "$11,204 to 0.5% from Jason's raw surface"}],
}


def estimate_from_takeoff(takeoff, rate_book=None):
    """THE CHAIN ADAPTER (Phase 5, 7/6/26): run_takeoff() JSON -> priced estimate via
    the LOCKED rate book -> assemble_estimate(). Plans in, priced lines out, zero hands.
    Only rates validated on actuals are applied (RATE_BOOK cites the calibration point
    per line); every measured line without a locked rate is carried in `unpriced` --
    NEVER silently priced with a placeholder. Each priced line keeps the measurement's
    source/confidence so review-yellow flows through to the estimate.
    Returns {estimate: assemble_estimate(...), unpriced: [takeoff lines], n_priced}."""
    certified, certification_errors = certify_takeoff_for_pricing(takeoff)
    if not certified:
        raise ValueError(
            "takeoff is not certified for pricing:\n - "
            + "\n - ".join(certification_errors)
        )
    rb = rate_book or RATE_BOOK
    priced, unpriced = [], []
    for ln in takeoff.get("lines", []):
        specs = rb.get(ln["trade"])
        if not specs:
            unpriced.append(ln)
            continue
        for spec in specs:
            priced.append({"name": spec["name"], "cost_type": spec["cost_type"],
                           "qty": ln["qty"], "unit_cost": spec["unit_cost"],
                           "unit": spec["unit"], "group": spec.get("group"),
                           "basis": spec.get("basis"),
                           "meas_source": ln["source"],
                           "meas_confidence": ln["confidence"]})
    est = assemble_estimate(priced)
    return {"estimate": est, "unpriced": unpriced, "n_priced": len(priced)}


# ---------------------------------------------------------------------------
# LEVEL GROUND -- Risk & Gap Report adapter (Phase 1: PRE-BID, plans only, landed 7/6/26).
# report_from_takeoff() turns a run_takeoff() result + homeowner intake into the exact JSON the
# Level Ground report HTML renders. PRE-BID needs ONLY the plans: it publishes the MEASURED
# quantities + a standard-scope CHECKLIST ("confirm your bid covers X") + the meeting questions
# + the honest unknowns. NO builder bid is ingested yet -- that is Phase 3 (report_type='bid_gap',
# which fills `findings` by comparing measured+priced scope to an ingested bid; the report HTML
# already reconciles that headline via the forcing function). Source/confidence flow through from
# the takeoff, and anything run_takeoff could NOT measure is surfaced in `unknowns`, never hidden.
# ---------------------------------------------------------------------------
# homeowner-facing label + unit for each run_takeoff trade (only these surface to the client)
_REPORT_QTY = {
    "heated_sf":          ("Heated living area", "sq ft"),
    "framing_sf":         ("Total area under roof", "sq ft"),
    "roof_surface_sq":    ("Roof area", "squares"),
    "foundation_wall_lf": ("Foundation / slab edge", "lin ft"),
    "slab_area_sf":       ("Slab footprint", "sq ft"),
    "basement_area_sf":   ("Basement footprint", "sq ft"),
}
_REPORT_QTY_ORDER = ["heated_sf", "framing_sf", "roof_surface_sq",
                     "foundation_wall_lf", "slab_area_sf", "basement_area_sf"]

# THE STANDARD-SCOPE CHECKLIST = the scopes a complete custom-home bid should address, and the
# ones J&J's own calibration flags as the chronic zero-traps / under-allowances (site+driveway+
# final grade, gutters, low-voltage, landscaping, defined allowances, insulation grade, vague
# lumps, change-order pricing). Pre-bid renders each as "confirm your bid covers this" + the
# homeowner's meeting question. This is the advocacy IP -- what builders most often leave out.
PRE_BID_SCOPE_CHECKLIST = [
    # PHASE 3 fields (ignored by pre-bid; drive the bid comparison):
    #   detect: 'dollar' = a $ finding if the bid line is ABSENT or under expected_low;
    #           'grade'  = a mispriced finding if the plan wants an upgrade the bid under-carries;
    #           'process'= a question only, never a $ finding.
    #   scope_keys: substrings to match a bid line's description.  expected: (low, high) $ band
    #   (PROVISIONAL, regional — same human-gated caveat as the $/SF bands).
    {"category": "missing_scope", "title": "Site work, driveway & final grading",
     "detail": "Grading, the driveway, and the final grade are the single most common thing a bid "
               "under-carries or buries in a vague \"site allowance.\" It lands late, and it is "
               "rarely small.", "confidence": "estimate_regional",
     "question": "What exactly does the site/allowance line cover -- clearing, driveway, and final "
                 "grade -- and what happens if it runs over?",
     "detect": "dollar", "expected": (18000, 28000),
     "scope_keys": ["site work", "sitework", "site allow", "driveway", "final grad", "grading",
                    "excavat", "dirt work"]},
    {"category": "missing_scope", "title": "Gutters & downspouts",
     "detail": "A small line that goes missing from bids more than almost any other. It never gets "
               "cheaper after the paint is on.", "confidence": "estimate_regional",
     "question": "Are gutters and downspouts in the bid, and who is carrying them?",
     "detect": "dollar", "expected": (3000, 5000), "scope_keys": ["gutter", "downspout"]},
    {"category": "missing_scope", "title": "Home technology, security & low-voltage",
     "detail": "Structured wiring, cameras, alarm, and automation are frequently left out and come "
               "back as a five-figure change order mid-build, when your leverage is gone.",
     "confidence": "estimate_regional",
     "question": "Is low-voltage / structured wiring / security in the contract as a defined line, "
                 "or is it excluded?",
     "detect": "dollar", "expected": (40000, 60000),
     "scope_keys": ["low volt", "low-volt", "structured wir", "automation", "smart home",
                    "security", "camera", "alarm", "audio", "home tech"]},
    {"category": "low_allowance", "title": "Every allowance defined in writing",
     "detail": "Countertops, flooring, plumbing fixtures, lighting, and appliances usually ride as "
               "allowances. A low or undefined allowance is a change order waiting to happen -- the "
               "overage is on you.", "confidence": "fact",
     "question": "Can you list every allowance, its dollar figure, and the exact material and "
                 "square footage it buys -- in writing?",
     "detect": "process", "expected": None, "scope_keys": []},
    {"category": "missing_scope", "title": "Landscaping, sod & irrigation",
     "detail": "Almost always excluded or zeroed. Fine if you know it going in -- a surprise if you "
               "don't.", "confidence": "estimate_regional",
     "question": "Is any landscaping, sod, or irrigation included, or is that on me?",
     "detect": "dollar", "expected": (5000, 15000),
     "scope_keys": ["landscap", "sod", "irrigation", "seeding"]},
    {"category": "mispriced", "title": "Insulation matches the plan spec",
     "detail": "If your plans call for spray foam and the bid is priced for a batt package, the real "
               "number is different. Confirm the grade the bid actually carries.",
     "confidence": "estimate_regional",
     "question": "Does the insulation line match the spec on my plans (foam vs. batt), and can I see "
                 "the quote behind it?",
     "detect": "grade", "expected": (16000, 21000),
     "scope_keys": ["insulat", "spray foam", "foam", "batt"], "upgrade_keys": ["foam"]},
    {"category": "vague_lump", "title": "No vague lump sums",
     "detail": "A one-line \"Electrical -- $35,000\" with no breakdown is where change orders breed. "
               "It isn't wrong; it's unverifiable -- and unverifiable favors the builder.",
     "confidence": "fact",
     "question": "Can the big trade lines (electrical, plumbing, HVAC) be broken into scope and "
                 "allowances so I can see what's actually included?",
     "detect": "process", "expected": None, "scope_keys": []},
    {"category": "missing_scope", "title": "Change-order pricing is in the contract",
     "detail": "How overages are priced matters as much as the bid. Cost-plus-a-fixed-markup vs. "
               "re-quoted-each-time is the difference between a fair overage and a painful one.",
     "confidence": "fact",
     "question": "How are change orders priced -- cost plus a fixed markup, or re-quoted each time "
                 "-- and is that language in the contract?",
     "detect": "process", "expected": None, "scope_keys": []},
]

STANDARD_UNKNOWNS = [
    "What's under the dirt -- rock, unsuitable soil, or drainage surprises no plan can show.",
    "Your final selections -- a $12 tile and a $40 tile read identically on a floor plan.",
    "Market swings between signing and dry-in -- lumber and labor move.",
    "Permit and utility-connection fees, which vary by county and can't be verified from plans alone.",
]


# ---------------------------------------------------------------------------
# PHASE 2 -- MARKET PRICING. Turns the measured quantities into a defensible EXPECTED BUILD-COST
# range for the homeowner. Basis = SELL $/UNDER-ROOF-SF (what a competent custom builder charges),
# by MARKET then finish level. ⛔ Calibrated for MIDDLE GEORGIA ONLY -- Jason confirmed these bands
# for HIS market (7/7/26) and does NOT have data for other US markets. So an uncalibrated market is
# FLAGGED (market_calibrated=False), never silently priced as if it were Middle GA; extend via a
# regional cost index off this base, or confirm locally (v2). Tune in ONE place.
# ---------------------------------------------------------------------------
MARKET_RATE_BOOK = {
    "_default_market": "middle_ga",
    "_basis": "SELL $/under-roof-SF from Jason's completed jobs, MIDDLE GEORGIA (Jason-confirmed 7/7/26)",
    "markets": {
        "middle_ga": {
            "_confirmed": True,     # Jason confirmed 7/7/26 for HIS market
            "state": "GA",          # calibrated match also requires the state (blocks Monroe LA, Newton MA, ...)
            "aliases": ["middle georgia", "middle ga", "macon", "monticello", "310", "jasper",
                        "monroe", "morgan", "putnam", "newton", "henry", "rockdale", "butts",
                        "jones", "lake county"],
            # finish level -> (low, high) SELL dollars per UNDER-ROOF square foot
            "build_cost_per_ur_sf": {"mid": (140, 160), "custom": (160, 200), "high": (200, 300)},
        },
    },
    # PHASE 2b: US CONSTRUCTION COST INDEX (national avg = 1.00), for markets NOT individually
    # calibrated. Researched 7/7/26 (workflow us-market-cost-index: RSMeans 2021 CCI / Gordian,
    # calcsummit, roofobservations, Mortenson; medium confidence). An indexed market's band =
    # Middle-GA band x (market_index / ga_index) -> tier 'regional_estimate' (cited research, NOT
    # Jason's actuals). ⛔ It's a CONSTRUCTION-cost basis: the anchor validation showed high-demand
    # metros (Austin/Denver/Seattle/SF) run WELL ABOVE it (land + soft costs + margin the index can't
    # see, and demand does NOT track the construction index) -> every indexed report flags "confirm
    # locally." Only Middle GA earns 'calibrated'. Extend a market to calibrated by getting local actuals.
    "index": {
        "_source": "RSMeans 2021 CCI/Gordian, calcsummit 2026, roofobservations 2026, Mortenson; national=1.00; medium confidence",
        "ga_index": 0.87,
        "demand_note": "Construction-cost basis. High-demand metros (Austin/Denver/Seattle/SF Bay) run "
                       "well ABOVE this on land + soft costs + builder margin; treat as a floor and confirm locally.",
        "state_index": {
            "AL": 0.85, "AK": 1.24, "AZ": 0.90, "AR": 0.80, "CA": 1.18, "CO": 0.96, "CT": 1.09,
            "DE": 1.04, "DC": 1.02, "FL": 0.87, "GA": 0.87, "HI": 1.32, "ID": 0.93, "IL": 1.10,
            "IN": 0.91, "IA": 0.95, "KS": 0.91, "KY": 0.87, "LA": 0.83, "ME": 0.91, "MD": 0.94,
            "MA": 1.12, "MI": 1.00, "MN": 1.06, "MS": 0.80, "MO": 0.96, "MT": 0.92, "NE": 0.90,
            "NV": 0.99, "NH": 0.95, "NJ": 1.14, "NM": 0.88, "NY": 1.17, "NC": 0.83, "ND": 0.92,
            "OH": 0.92, "OK": 0.83, "OR": 1.05, "PA": 1.00, "RI": 1.06, "SC": 0.84, "SD": 0.90,
            "TN": 0.85, "TX": 0.85, "UT": 0.92, "VT": 0.92, "VA": 0.88, "WA": 1.05, "WV": 0.94,
            "WI": 0.99, "WY": 0.90,
        },
        # major-metro overrides (city token, state, national-relative index)
        "metro_overrides": [
            {"city": "new york", "state": "NY", "index": 1.32},
            {"city": "san francisco", "state": "CA", "index": 1.30},
            {"city": "san jose", "state": "CA", "index": 1.27},
            {"city": "los angeles", "state": "CA", "index": 1.12},
            {"city": "san diego", "state": "CA", "index": 1.09},
            {"city": "sacramento", "state": "CA", "index": 1.15},
            {"city": "seattle", "state": "WA", "index": 1.07},
            {"city": "boston", "state": "MA", "index": 1.14},
            {"city": "chicago", "state": "IL", "index": 1.20},
            {"city": "philadelphia", "state": "PA", "index": 1.15},
            {"city": "washington", "state": "DC", "index": 0.99},
            {"city": "minneapolis", "state": "MN", "index": 1.07},
            {"city": "detroit", "state": "MI", "index": 0.99},
            {"city": "st. louis", "state": "MO", "index": 1.00},
            {"city": "kansas city", "state": "MO", "index": 0.96},
            {"city": "columbus", "state": "OH", "index": 0.94},
            {"city": "indianapolis", "state": "IN", "index": 0.95},
            {"city": "denver", "state": "CO", "index": 0.97},
            {"city": "portland", "state": "OR", "index": 1.03},
            {"city": "salt lake city", "state": "UT", "index": 0.92},
            {"city": "las vegas", "state": "NV", "index": 1.05},
            {"city": "phoenix", "state": "AZ", "index": 0.93},
            {"city": "atlanta", "state": "GA", "index": 0.90},
            {"city": "charlotte", "state": "NC", "index": 0.86},
            {"city": "raleigh", "state": "NC", "index": 0.85},
            {"city": "nashville", "state": "TN", "index": 0.89},
            {"city": "dallas", "state": "TX", "index": 0.87},
            {"city": "houston", "state": "TX", "index": 0.88},
            {"city": "austin", "state": "TX", "index": 0.89},
            {"city": "orlando", "state": "FL", "index": 0.90},
            {"city": "tampa", "state": "FL", "index": 0.88},
            {"city": "miami", "state": "FL", "index": 0.85},
            {"city": "birmingham", "state": "AL", "index": 0.88},
            {"city": "honolulu", "state": "HI", "index": 1.19},
            {"city": "anchorage", "state": "AK", "index": 1.16},
        ],
    },
}


def _finish_key(finish):
    f = (finish or "custom").lower()
    if any(k in f for k in ("high", "luxury", "modern", "premium")):
        return "high"
    if any(k in f for k in ("mid", "standard", "budget", "base")):
        return "mid"
    return "custom"


def _resolve_market(mb, market_name, state_code=None):
    """(market_key, market_dict, is_calibrated) for a report's market. Matches by key/alias against
    the CALIBRATED markets, requiring the STATE to match too when both are known (so 'Monroe, LA' or
    'Newton, MA' can't match a Middle-GA county alias). No match -> default, is_calibrated=False, so an
    unknown market is never silently priced as if it were Jason's Middle GA."""
    markets = mb.get("markets", {})
    name = (market_name or "").lower()
    sc = (state_code or "").upper()
    for key, m in markets.items():
        mstate = (m.get("state") or "").upper()
        if mstate and sc and mstate != sc:
            continue                                 # different state -> not this calibrated market
        if key.replace("_", " ") in name or any(a in name for a in m.get("aliases", [])):
            return key, m, True
    dk = mb.get("_default_market")
    return dk, markets.get(dk, {}), False


def _index_factor(mb, market_name, state_code):
    """Location cost factor vs the Middle-GA anchor for an UNCALIBRATED market, from the construction
    cost index: (metro override, else state index) / ga_index. A metro override also requires the
    state to match (so Portland OR != Portland ME). Returns a float, or None if the market can't be
    placed on the index at all."""
    idx = mb.get("index")
    if not idx or not idx.get("ga_index"):
        return None
    ga = idx["ga_index"]
    name = (market_name or "").lower()
    sc = (state_code or "").upper()
    if not sc:                                       # try to parse a ", XX" state out of the name
        import re as _re
        m = _re.search(r",\s*([A-Za-z]{2})\b", market_name or "")
        if m:
            sc = m.group(1).upper()
    for mo in idx.get("metro_overrides", []):
        if mo["city"] in name and (not sc or mo["state"] == sc):
            return mo["index"] / ga
    si = idx.get("state_index", {})
    if sc in si:
        return si[sc] / ga
    return None


def price_report(quantities, home, market_book=None, market=None, state=None):
    """PHASE 2/2b: a defensible EXPECTED BUILD-COST range for the measured home, in THREE tiers:
      'calibrated'        -> a market with Jason's own actuals (Middle GA). Delivered, confirmed.
      'regional_estimate' -> any other market, via the construction cost index: Middle-GA band x
                             (market_index / ga_index). CONSTRUCTION-cost basis (delivered runs higher
                             in high-demand metros -> the report flags 'confirm locally').
      'uncalibrated'      -> market can't be placed on the index at all -> Middle-GA band, flagged.
    Returns {total, per_sf, sf, sf_label, finish, market, tier, market_calibrated, market_indexed,
    index_factor, confirmed, basis} or None if no area quantity is present (never fabricates an area)."""
    mb = market_book or MARKET_RATE_BOOK
    sf = sf_label = None
    for item, lbl in (("Total area under roof", "under-roof"), ("Heated living area", "heated")):
        q = next((x for x in quantities if x["item"] == item), None)
        if q:
            sf = float(str(q["qty"]).replace(",", "")); sf_label = lbl; break
    if not sf:
        return None
    fk = _finish_key(home.get("finish_level"))
    mname = market if market is not None else home.get("market")
    mkt_key, mkt, cal = _resolve_market(mb, mname, state)
    base = mb["markets"].get(mb.get("_default_market"), {}).get("build_cost_per_ur_sf", {})
    if cal:                                          # CALIBRATED (Jason's actuals)
        band = mkt.get("build_cost_per_ur_sf", {})
        if fk not in band:
            return None
        lo_r, hi_r = band[fk]; tier = "calibrated"; fac = None
    else:
        if fk not in base:
            return None
        fac = _index_factor(mb, mname, state)
        if fac:                                      # REGIONAL ESTIMATE via the cost index
            lo_r, hi_r = round(base[fk][0] * fac), round(base[fk][1] * fac); tier = "regional_estimate"
        else:                                        # UNCALIBRATED: can't place -> GA band, flagged
            lo_r, hi_r = base[fk]; tier = "uncalibrated"
    return {"total": {"low": round(sf * lo_r, -3), "high": round(sf * hi_r, -3)},
            "per_sf": (lo_r, hi_r), "sf": sf, "sf_label": sf_label, "finish": fk,
            "market": mkt_key if cal else (mname or "unknown"), "tier": tier,
            "market_calibrated": cal, "market_indexed": tier == "regional_estimate",
            "index_factor": round(fac, 3) if fac else None,
            "confirmed": bool(mkt.get("_confirmed")) and cal, "basis": mb.get("_basis", "")}


# ---------------------------------------------------------------------------
# PHASE 3 -- BUILDER-BID INGESTION + FINDING GENERATION. The report's core promise: an INDEPENDENT
# read of the plans vs. the homeowner's builder's bid, auto-generating the findings (missing scope /
# low allowance / mispriced / vague lump) that fill the reconciled bid_gap headline. Split by
# difficulty: ANALYSIS (structured bid -> findings) is deterministic IP, built here; INGESTION
# (arbitrary PDF/photo -> structured) is the fuzzy front-end -- v1 accepts a STRUCTURED bid + a
# simple xlsx reader; PDF/photo parsing is the v2 follow-on.
# Bid contract:  {"total": <num>, "lines": [{"desc": str, "amount": num, "is_lump": bool?}]}
# ---------------------------------------------------------------------------
def ingest_bid(lines, total=None):
    """Normalize a builder's bid into the structured contract. `lines` = list of
    {desc, amount, is_lump?}. total defaults to the sum of line amounts. The fuzzy part
    (PDF/photo/xlsx -> this shape) is the replaceable front-end; the analysis runs on THIS."""
    norm = [{"desc": str(ln.get("desc", "")), "amount": float(ln.get("amount") or 0),
             "is_lump": bool(ln.get("is_lump"))} for ln in lines]
    return {"total": float(total) if total is not None else round(sum(l["amount"] for l in norm), 2),
            "lines": norm}


def ingest_bid_xlsx(path, desc_col=0, amount_col=1, header_rows=1, lump_threshold=25000):
    """Thin xlsx reader -> structured bid (a common bid format). Reads (desc, amount) columns and
    flags a line is_lump when it's a big number with a one-/two-word (trade-only) description. For
    anything messier (PDF, photo, merged cells) do the ingestion by hand/VLM into ingest_bid()."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    lines = []
    for r in ws.iter_rows(min_row=header_rows + 1, values_only=True):
        desc = r[desc_col] if desc_col < len(r) else None
        amt = r[amount_col] if amount_col < len(r) else None
        try:
            amt = float(amt)
        except (TypeError, ValueError):
            continue
        if not desc or amt <= 0:
            continue
        lines.append({"desc": str(desc), "amount": amt,
                      "is_lump": amt >= lump_threshold and len(str(desc).split()) <= 2})
    return ingest_bid(lines)


def _bid_match(bid_lines, keys):
    return [ln for ln in bid_lines if any(k in ln["desc"].lower() for k in keys)]


def _bid_finding(c, bid_amount, low, high):
    absent = bid_amount <= 0
    return {"category": c["category"], "title": c["title"],
            "detail": c["detail"] + (" It isn't in the bid at all." if absent
                                     else " The bid carries less than a realistic number for it."),
            "bid_amount": bid_amount, "realistic_low": low, "realistic_high": high,
            "confidence": c.get("confidence", "estimate_regional"),
            "basis": (("Not found in the bid; " if absent else f"Bid carries ${bid_amount:,.0f}; ")
                      + "regional range for a build like yours (provisional).")}


def findings_from_bid(bid, home, checklist=None, quantities=None):
    """PHASE 3 core: compare the plans' expected scope to the builder's bid -> report `findings[]`.
      DOLLAR items -> a finding when the bid line is ABSENT or under expected_low (missing / low).
      GRADE items  -> a mispriced finding when the plan wants an upgrade (home flag, e.g. 'foam')
                      that the bid under-carries.
      VAGUE LUMPS  -> any bid line flagged is_lump -> unverifiable, flagged (NEVER priced -> not
                      added to the exposure total).
    Bands are PROVISIONAL / regional (same human-gated caveat as the $/SF bands)."""
    cl = checklist or PRE_BID_SCOPE_CHECKLIST
    blines = bid.get("lines", [])
    insul = (home.get("insulation") or "").lower()
    findings = []
    for c in cl:
        det, keys, band = c.get("detect", "process"), (c.get("scope_keys") or []), c.get("expected")
        m = _bid_match(blines, keys) if keys else []
        amt = round(sum(ln["amount"] for ln in m), 2)
        if det == "dollar" and band:
            lo, hi = band
            if not m or amt < lo:                        # absent OR under the floor
                findings.append(_bid_finding(c, amt, lo, hi))
        elif det == "grade" and band:
            lo, hi = band
            if any(k in insul for k in c.get("upgrade_keys", [])) and m and amt < lo:
                findings.append(_bid_finding(c, amt, lo, hi))    # plan wants foam; bid under-carries
        # 'process' items never generate a $ finding -- they stay meeting questions
    for ln in blines:                                    # vague lumps: unverifiable -> flag, no price
        if ln["is_lump"]:
            findings.append({
                "category": "vague_lump",
                "title": f"\"{ln['desc']} -- ${ln['amount']:,.0f}\"",
                "detail": "A big one-line number with no breakdown -- no scope split, no allowances. "
                          "We can't call it wrong; we can tell you it's unverifiable as written, and "
                          "unverifiable favors the builder.",
                "bid_amount": ln["amount"], "realistic_low": None, "realistic_high": None,
                "confidence": "fact",
                "basis": "Flagged, not priced -- no quantities to check. Not added to the exposure total."})
    return findings


def report_from_takeoff(takeoff, home, region, prepared_for="Homeowner",
                        property_label=None, report_id=None, date=None,
                        report_type="pre_bid", is_sample=False, checklist=None,
                        market_book=None, bid=None):
    """Adapter: a run_takeoff() result + homeowner intake -> the Level Ground report JSON dict the
    report HTML consumes (json.dumps it into the <script id='report-data'> block).
    Phase 1 = PRE-BID (plans only): measured `quantities` + the standard-scope `checklist` as
    `findings` (no dollars) + `questions` + `unknowns`; bid_total/our_range stay None so the report
    hides the bid-vs-range verdict strip. Every quantity keeps the takeoff's source+confidence;
    whatever run_takeoff could NOT measure is added to `unknowns` honestly.
      takeoff : run_takeoff() output.   home: {heated_sf?, stories, foundation, garage, finish_level}.
      region  : {state, zip3, market}."""
    by_trade = {}
    for ln in takeoff.get("lines", []):
        by_trade.setdefault(ln["trade"], ln)          # first line per trade

    quantities = []
    for trade in _REPORT_QTY_ORDER:
        ln = by_trade.get(trade)
        if not ln:
            continue
        label, unit = _REPORT_QTY[trade]
        src = f"page {ln['page'] + 1}" if isinstance(ln.get("page"), int) else "your plans"
        if ln.get("method"):
            src += f" · {ln['method']}"
        quantities.append({"item": label, "qty": f"{float(ln['qty']):,.0f}", "unit": unit,
                           "source": src, "confidence": "measured"})   # off the drawings

    home = dict(home)
    if not home.get("heated_sf") and by_trade.get("heated_sf"):
        home["heated_sf"] = int(round(by_trade["heated_sf"]["qty"]))

    cl = checklist if checklist is not None else PRE_BID_SCOPE_CHECKLIST
    if bid is not None:                                # BID GAP: findings by comparison to the bid
        findings = findings_from_bid(bid, home, cl, quantities)
    else:                                              # PRE-BID: the checklist as watch-items (no $)
        findings = [{"category": c["category"], "title": c["title"], "detail": c["detail"],
                     "bid_amount": None, "realistic_low": None, "realistic_high": None,
                     "confidence": c["confidence"],
                     "basis": "Standard scope for a build like yours -- confirm your bid addresses it."}
                    for c in cl]
    questions = [c["question"] for c in cl]            # the meeting script (both modes)

    unknowns = list(STANDARD_UNKNOWNS)
    for nm in takeoff.get("not_measured", []):         # honest: what we could NOT measure
        lbl = _REPORT_QTY.get(nm.get("trade"), (str(nm.get("trade", "an item")),))[0]
        unknowns.append(f"We could not measure {lbl.lower()} from the plans provided "
                        f"({nm.get('why', 'insufficient detail')}) -- ask your builder for it.")

    priced = (price_report(quantities, home, market_book, market=region.get("market"),
                           state=region.get("state")) if market_book is not None else None)
    is_bid = bid is not None
    _tier = priced["tier"] if priced else None
    if _tier == "regional_estimate":
        mkt_caveat = (" This range is a regional estimate -- construction cost adjusted from a "
                      "Middle-Georgia base by regional cost index; land, permits, and (especially in "
                      "high-demand metros) builder margin can push delivered prices higher, so confirm "
                      "with local builders.")
    elif _tier == "uncalibrated":
        mkt_caveat = (" Note: we couldn't place your market on our cost index -- this range is a rough "
                      "proxy from Middle Georgia; confirm locally.")
    else:
        mkt_caveat = ""
    if is_bid:
        vnote = ("An independent review of your plans against your builder's bid -- what's solid, "
                 "what's thin, and what to ask before you sign. The range below is your bid corrected "
                 "for every gap we found; each dollar of it traces to a finding.")
    elif priced:
        vnote = ("This is a pre-bid review: your home measured off your drawings, an estimated "
                 "build-cost range for a build like this in your market, and the scope to make sure "
                 "any bid actually covers it. The range is regional and provisional -- a sanity check "
                 "to bring to the table, not a quote." + mkt_caveat)
    else:
        vnote = ("This is a pre-bid review: your home measured straight off your drawings, plus the "
                 "scope to make sure any bid you get actually covers. Bring it to the table before you sign.")

    meta = {
        "report_id": report_id or ("LG-BIDGAP" if is_bid else "LG-PREBID"),
        "report_type": "bid_gap" if is_bid else report_type,
        "is_sample": bool(is_sample),
        "prepared_for": prepared_for,
        "property_label": property_label or "Your Residence",
        "region": {"state": region.get("state", ""), "zip3": region.get("zip3", ""),
                   "market": region.get("market", "")},
        "date": date or "",
        "home": {"heated_sf": home.get("heated_sf", 0), "stories": home.get("stories", 1),
                 "foundation": home.get("foundation", ""), "garage": home.get("garage", ""),
                 "finish_level": home.get("finish_level", "custom")},
        "bid_total": (bid["total"] if is_bid else None),  # bid_gap sets it -> the reconciled strip
        "our_range": ({"low": priced["total"]["low"], "high": priced["total"]["high"]}
                      if priced else None),            # market range: hero (pre-bid) / cross-check (bid_gap)
        "cost_basis": (f"{priced['finish']} finish · {region.get('market') or 'regional'} · "
                       f"${priced['per_sf'][0]}-{priced['per_sf'][1]}/sf {priced['sf_label']}"
                       + {"calibrated": "", "regional_estimate": " · regional estimate",
                          "uncalibrated": " · uncalibrated"}.get(priced["tier"], "")
                       if priced else None),
        "pricing_confirmed": (priced["confirmed"] if priced else None),
        "market_calibrated": (priced["market_calibrated"] if priced else None),
        "pricing_tier": (priced["tier"] if priced else None),
        "verdict_note": vnote,
    }
    return {"meta": meta, "findings": findings, "quantities": quantities,
            "questions": questions, "unknowns": unknowns}


# ---------------------------------------------------------------------------
# DAVIS (PR-109) CALIBRATION FIXES (7/6/26) -- graded MY cold estimate vs J&J's own
# (Skip's) estimate + measurements. Four repeatable misses, encoded so they can't recur.
# NOTE: Skip's numbers are an ESTIMATE, not actuals -- these are METHOD fixes (how to measure
# / which basis), not new locked rates. Confirm rates against actuals per calibration hygiene.
# ---------------------------------------------------------------------------
def cladding_by_elevation(elevations, perimeter_lf, band_ht=3.0):
    """FORCING FUNCTION for exterior CLADDING / VENEER by material -- the fix for the Davis
    stone miss. I measured the front + 'partial sides' and got 450 SF vs a true ~600; the
    OPPOSITE trap is blindly wrapping the full perimeter -> Skip's 1,127 SF, which counted a
    REAR that has NO stone. Both come from not going face-by-face. This makes you account for
    ALL FOUR cardinal elevations explicitly, then cross-checks.

    elevations: dict that MUST contain every face -> {'front':[...], 'rear':[...], 'left':[...],
      'right':[...]}. Each list holds pieces on that face:
        {'material': 'stone'|'lap'|'bnb'|..., 'run_ft': x, 'ht_ft': y}   -- a wall/wainscot band
        {'material': ..., 'sf': z, 'feature': 'pier'|'chimney'|'gable'}  -- a tall feature
      An EMPTY list [] is a valid, explicit 'this face has none' (Davis rear stone = []). But
      OMITTING a face raises -- silently skipping a face is the miss.
    Returns per-material area + a perimeter x band_ht cross-check that FLAGS any material under
    60% (skipped a face?) or over 140% (over-wrapped?) of that bound -- prompts a re-look, both
    directions. Gross areas (openings left in); features summed separately.
    ⚠️ SCOPE: this forcing function is for a VENEER / WAINSCOT band (stone/brick) -- band_ht
    defaults to 3 ft. For a FULL-HEIGHT FIELD material (lap/B&B covering a whole wall), pass
    band_ht = the wall height (or measure it through the siding path); otherwise the >140%
    over-wrap flag fires spuriously (a full wall is legitimately >> perimeter x 3 ft)."""
    from collections import defaultdict
    import math as _m
    faces = ("front", "rear", "left", "right")
    missing = [f for f in faces if f not in elevations]
    if missing:
        raise ValueError(
            f"cladding_by_elevation: account for EVERY elevation; missing {missing}. "
            f"Measuring 'front + partial sides' is the #1 cladding under-measure "
            f"(Davis stone 450 vs ~600). Pass [] for a face that genuinely has none.")
    by_mat = defaultdict(float)
    detail = []
    for face in faces:
        for pc in elevations[face]:
            m = pc["material"]
            if "sf" in pc:
                a = float(pc["sf"]); how = f"{pc.get('feature', 'feature')} = {a:.0f} SF"
            else:
                a = float(pc["run_ft"]) * float(pc["ht_ft"]); how = f"{pc['run_ft']}x{pc['ht_ft']} ft"
            by_mat[m] += a
            detail.append({"face": face, "material": m, "sf": round(a, 1), "how": how})
    bound = perimeter_lf * band_ht
    flags = []
    for m, a in by_mat.items():
        if a < 0.60 * bound:
            flags.append(f"{m} {a:.0f} SF < 60% of perimeter-band {bound:.0f} SF -- "
                         f"did you SKIP a face? (under-measure trap: Davis stone 450 vs 600)")
        elif a > 1.40 * bound:
            flags.append(f"{m} {a:.0f} SF > 140% of perimeter-band {bound:.0f} SF -- "
                         f"OVER-wrapped? confirm each face really has it (Skip stone 1,127)")
    return {"by_material": {m: round(a, 1) for m, a in by_mat.items()},
            "detail": detail, "perimeter_band_sf": round(bound, 0), "flags": flags}


TRIM_LABOR_RATE_PER_SF = 2.0   # $/SF of (heated+garage). Davis miss: I priced trim/finish-
# carpentry LABOR by base-LF (~$2,350); J&J's basis is (heated+garage) SF x $2 = $8,898.
def trim_labor(heated_sf, garage_sf=0.0, rate=TRIM_LABOR_RATE_PER_SF):
    """Interior trim / finish-carpentry LABOR = (heated + garage) SF x rate -- NOT per LF of
    base. (Davis: base-LF x $2 = ~$2,350 was ~$6.5k light vs J&J's SF basis.)"""
    return round((heated_sf + garage_sf) * rate, 2)


CABINET_MATERIAL_RATE_PER_LF = 150.0
CABINET_INSTALL_RATE_PER_LF = 75.0


def cabinet_pricing(runs, material_rate=CABINET_MATERIAL_RATE_PER_LF,
                    install_rate=CABINET_INSTALL_RATE_PER_LF):
    """Price cabinet material and installation by LF under Jason's 2026-07-20 rule.

    `runs` contains measured LF by cabinet type. Tall-cabinet LF counts twice for both
    material and installation; every other run counts once. Hardware and vent-hood cabinet
    allowances stay outside this calculation.
    """
    measured = {}
    for kind, raw_lf in runs.items():
        lf = float(raw_lf)
        if lf < 0:
            raise ValueError(f"cabinet run {kind!r} cannot be negative")
        measured[str(kind)] = lf
    material_rate = float(material_rate)
    install_rate = float(install_rate)
    if material_rate <= 0 or install_rate <= 0:
        raise ValueError("cabinet material and install rates must be positive")
    measured_lf = sum(measured.values())
    tall_lf = measured.get("tall", 0.0)
    priced_lf = measured_lf + tall_lf
    return {
        "measured_lf": round(measured_lf, 2),
        "tall_lf": round(tall_lf, 2),
        "priced_lf": round(priced_lf, 2),
        "material_rate_per_lf": material_rate,
        "install_rate_per_lf": install_rate,
        "material_total": round(priced_lf * material_rate, 2),
        "install_total": round(priced_lf * install_rate, 2),
    }


def cabinet_boxes(runs, box_ft=None):
    """Diagnostic cabinet-box estimate for schedule reconciliation only, never pricing."""
    import math as _m
    W = {"base": 2.0, "upper": 2.0, "tall": 2.0, "island": 2.5, "vanity": 2.0, "pantry": 2.0}
    if box_ft:
        W = dict(W, **box_ft)
    return int(sum(_m.ceil(float(lf) / W.get(k, 2.0)) for k, lf in runs.items()))


ROOF_TURNKEY_PER_SF = 2.25   # J&J TEMPLATE turnkey $/SF of waste-loaded roof surface. Davis miss:
# I priced the estimate line off the decoded field+accessories ($2.07/SF); J&J's template (and
# Skip) bill the turnkey $2.25. Use roofing_turnkey() for the ESTIMATE LINE; roofing_estimate()
# stays the itemized decoded cross-check.
def roofing_turnkey(zones, waste=ROOF_WASTE, rate=ROOF_TURNKEY_PER_SF):
    """Shingle roofing at J&J's template TURNKEY rate = waste-loaded surface x $2.25/SF.
    (roofing_estimate() gives the decoded field+accessory build-up ~$2.07 as a cross-check.)"""
    surf = roof_surface(zones)
    order = round(surf["raw_surface_sf"] * (1 + waste), 1)
    return {"raw_surface_sf": surf["raw_surface_sf"], "order_surface_sf": order,
            "rate_per_sf": rate, "total": round(order * rate, 2)}


def _verify_selftest():
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False); f.write(b"x"); f.close()
    # forcing function: MEASURED can't be built without a real view file
    for bad in (lambda: Quantity("p", 1, "LF", "MEASURED", sheet="p6"),
                lambda: Quantity("p", 1, "LF", "MEASURED", sheet="p6", view="/no/such.png"),
                lambda: Quantity("b", 111, "LF", "GIVEN"),
                lambda: Quantity("h", 10, "ft", "ASSUMED")):
        try:
            bad(); raise AssertionError("forcing function failed to block an unproven number")
        except ValueError:
            pass
    # the EXACT session failures, run through the system:
    beam  = Quantity("beam", 111, "LF", "GIVEN", given_by="Jason")            # the 111 I leaned on
    perim = Quantity("room_perim", 984, "LF", "MEASURED", sheet="p6", view=f.name
                     ).reconcile(1357, 5, against="Jason base")              # my light perimeter
    okp = certify([perim])[0]
    okb = certify([beam])[0]
    assert okp is False, "should FAIL: 984 vs 1357 = 27% off"
    assert okb is True,  "GIVEN passes (flagged)"
    _os.unlink(f.name)
    return certify([beam, perim])



# =====================================================================================
# ELEVATION-FIRST COUNTING + RECONCILIATION  (cal #63, L J Show Residence, 7/31/26)
# Built after I shipped 22 windows against Jason's 46. I HAD the right evidence -- my own
# elevation scan found 53 tagged openings -- and shipped the FLOOR-PLAN tag count anyway.
# Jason's takeoff counts openings with point markers ON THE ELEVATIONS, sheet by sheet.
# These functions make the plan-only count impossible to ship.
# =====================================================================================

_OPENING_TAG = _re.compile(r'^(?:\((\d)\))?(\d{4,6})(FX|SH|PT|TR|CS|AW|DH|SL)?$', _re.I)


def _split_wh(digits):
    """J&J opening-tag digits -> (width_ft, height_ft).  Each half reads [feet][inches]
    with inches a single digit: 30=3'0", 28=2'8", 100=10'0".  4 digits split 2/2;
    5 digits try 3/2 then 2/3; 6 digits 3/3.  Both halves must be plausible openings,
    which is what rejects the bogus 1'0"-wide reading of a 10080 garage door."""
    n = len(digits)
    cands = {4: [(2, 2)], 5: [(3, 2), (2, 3)], 6: [(3, 3)]}.get(n, [])
    best = None
    for a, _b in cands:
        lw, lh = digits[:a], digits[a:]
        w = int(lw[:-1]) + int(lw[-1]) / 12.0
        h = int(lh[:-1]) + int(lh[-1]) / 12.0
        if not (1.0 <= w <= 24.0 and 1.5 <= h <= 16.0):
            continue
        best = (0, round(w, 3), round(h, 3))   # FIRST plausible split in order wins
        break
    return (best[1], best[2]) if best else (None, None)


def parse_opening_tag(tag):
    """J&J opening tag -> dict.  '3060SH' = 3'0" wide x 6'0" high single-hung.
    '(2)3060SH' is a mulled pair (2 lites).  A tag with no FX/SH/PT suffix standing
    >= 6'6" tall is a DOOR.  Returns None when the token is not an opening tag."""
    s = str(tag).strip()
    m = _OPENING_TAG.match(s)
    if not m:
        return None
    mull = int(m.group(1)) if m.group(1) else 1
    w, h = _split_wh(m.group(2))
    if w is None:
        return None
    suffix = (m.group(3) or '').upper()
    kind = 'window' if suffix else ('door' if h >= 6.5 else 'window')
    return {'tag': s, 'width_ft': w, 'height_ft': h, 'lites': mull, 'suffix': suffix,
            'kind': kind, 'perimeter_lf': round(2 * (w + h), 2)}


def elevation_opening_count(doc, elevation_pages, floor_plan_page=None, tolerance_pct=20.0):
    """COUNT OPENINGS ON THE ELEVATIONS, then reconcile against the floor plan.

    `elevation_pages` = [(page_index, 'label', fitz.Rect|None), ...] -- EVERY elevation
    sheet, not a sample. Returns windows/doors counted per elevation plus the opening
    trim LF that follows from the same count (sum of each opening's perimeter).

    ok=False when the plan and elevation counts disagree by more than tolerance_pct, or
    when no elevation page was supplied.  Never returns a plan-only count as authoritative
    -- that is the exact failure this exists to stop (cal #63: shipped 22 vs a true 46)."""
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


def footer_lf(outer_perimeter_lf, step_lf, interior_bearing_lf=0.0):
    """MONO-SLAB THICKENED-EDGE (FOOTER) LENGTH (Jason, 7/31/26).

    House, garage and porches are ONE monolithic pour -- but the garage and porch slabs
    STEP DOWN from the house floor, so every internal transition still takes a thickened
    edge.  Count each line exactly ONCE:

        footer LF = outer perimeter of the WHOLE slab (all areas unioned)
                  + every internal STEP line (house<->garage, house<->each porch)
                  + interior bearing lines

    `step_lf` = {'garage': 75.42, 'rear_porch': 100.33, 'front_porch': 25.81}.
    Recover a step that a union dissolved as (P_a + P_b - P_merged) / 2.

    Pair with the pricing rule: carry the footer MATERIAL lines (form boards, concrete,
    rebar -- they book the thickened edge's extra concrete and steel) and NO footer
    labour, which already sits inside `Labor - Monolithic slab` at $/SF.

    L J Show: outer 394.32 + garage 75.42 + rear porch 100.33 + front porch 25.81
    = 595.88 LF vs Jason's 634.79 raw (-6.1%).  ⚠ The ~39 LF residual is UNRESOLVED --
    Jason traced sheet 4 (SLAB PLAN, whose edge is dashed and not cleanly vectorisable);
    these figures come from the sheet-2 SQFT area polygons.  Candidates: interior bearing
    /step lines inside the house, or a slab outline that runs past the SQFT area boundary
    (stoops, steps, equipment pads).  ASK -- do not curve-fit.

    ⛔ HISTORY: two earlier attempts hit 635 by accident and were structurally WRONG --
    (a) a "1.64x perimeter" ratio reverse-engineered from his total; (b) envelope + FULL
    porch outlines (635.88), which double-counts each house<->porch step and omits the
    house<->garage step entirely.  Matching the number is not the same as being right."""
    steps = dict(step_lf or {})
    total = float(outer_perimeter_lf) + sum(float(v) for v in steps.values())         + float(interior_bearing_lf)
    return {
        'footer_lf': round(total, 2),
        'outer_perimeter_lf': round(float(outer_perimeter_lf), 2),
        'step_lf': {k: round(float(v), 2) for k, v in steps.items()},
        'step_total_lf': round(sum(float(v) for v in steps.values()), 2),
        'interior_bearing_lf': round(float(interior_bearing_lf), 2),
        'note': 'outer-perimeter-only would be %.1f%% light'
                % (100 * (1 - float(outer_perimeter_lf) / total)) if total else '',
    }


def reconcile_roof_footprint(roof_footprint_sf, under_roof_sf, roof_perimeter_lf,
                             measured_overhang_ft, tolerance_ft=0.75):
    """Roof footprint must equal the under-roof area plus an overhang band that agrees with
    the overhang you MEASURED off the roof plan.  Solves the band as a ring so the corners
    are not double counted, then reports the implied overhang.

    Catches both directions: a footprint traced too small (my structural under-bid bias) and
    one traced too large / with overlapping plane polygons (cal #63: a takeoff implying a
    5.54 ft overhang on a house whose measured eave projection was 1.50 ft)."""
    band = float(roof_footprint_sf) - float(under_roof_sf)
    P = float(roof_perimeter_lf)
    implied = band / P if P else float('nan')
    # ring solve: band = o*P_out - 4*o^2  (rectilinear, convex corners)
    o_ring = None
    if P:
        disc = P * P - 16.0 * band
        if disc >= 0:
            o_ring = (P - math.sqrt(disc)) / 8.0
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
    estimate (cal #63: my first classifier dropped every tile that failed a texture test)."""
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
    (cal #63: I measured 121 LF of open porch edge against his 291 LF and ran -58%).
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


if __name__ == "__main__":
    # self-test the parser on the cases that bit us
    cases = {
        "59'-6 1/2\"": 59.5417, "61'-4\"": 61.3333, "9'": 9.0, "24'-0\"": 24.0,
        "3'-4 3/4\"": 3.3958, "16'-9\"": 16.75, "2'-1\"": 2.0833, "12\"": 1.0,
        "596'-1": 596.0833,   # valid dim; absurd values are caught by max_ft + consensus, not here
        "31064": None, "1/4\"=1'": None,
    }
    ok = True
    for s, exp in cases.items():
        got = parse_dim(s)
        good = (exp is None and got is None) or (exp and got and abs(got - exp) < 0.01)
        ok = ok and good
        print(f"  {'OK ' if good else 'FAIL'} parse_dim({s!r}) = {got} (exp {exp})")
    # plausibility cap rejects the absurd value
    cap = parse_dim("596'-1", max_ft=250)
    ok = ok and cap is None
    print(f"  {'OK ' if cap is None else 'FAIL'} parse_dim('596\\'-1', max_ft=250) = {cap} (exp None)")
    # framing: $6.50 default reconciles 3 ACTUALS within ~2%; classifier handles patio trap
    acts = [(5792.59, 38210, "Wilson"), (4518.0, 28862, "Watkins"), (3198.0, 20688, "Peterson")]
    fr_ok = all(abs(framing_estimate(sf)["labor"] - act) / act < 0.025 for sf, act, _ in acts)
    ok = ok and fr_ok
    msg = ", ".join(f"{n} {framing_estimate(sf)['labor']:.0f}/{act}" for sf, act, n in acts)
    print(f"  {'OK ' if fr_ok else 'FAIL'} framing @6.50: {msg}")
    cls = [classify_area_row(s) for s in
           ("BASEMENT PATIO", "COVERED DECK", "GARAGE SQFT", "MAIN FLOOR HTD", "CONCRETE PATIO",
            "FUTURE EXPANSION", "OUTDOOR LIVING")]
    cls_ok = cls == ["flatwork", "framed", "framed", "framed", "flatwork", "framed", "framed"]
    ok = ok and cls_ok
    print(f"  {'OK ' if cls_ok else 'FAIL'} classify_area_row = {cls}")
    # gable_area: synthetic 8:12 gable (base 30, rise 10 = 150 sf) + a double-drawn edge (dedupes)
    seg = [(15, 0, 0, 10), (15, 0, 30, 10), (15.3, 0.2, 0.3, 10.2)]
    g = gable_area(segments=seg, ppf=1.0)
    g_ok = g["n_gables"] == 1 and abs(g["total_sf"] - 150.0) < 1.0
    ok = ok and g_ok
    print(f"  {'OK ' if g_ok else 'FAIL'} gable_area synthetic = {g['total_sf']} sf, {g['n_gables']} gable (exp 150, 1)")
    # roofing: pitch_factor reproduces J&J's table EXACTLY (computed, not looked up)
    pf_exp = {5: 1.083, 6: 1.118, 8: 1.202, 10: 1.302, 12: 1.414, 16: 1.667}
    pf_ok = all(abs(pitch_factor(p) - v) < 0.001 for p, v in pf_exp.items())
    ok = ok and pf_ok
    print(f"  {'OK ' if pf_ok else 'FAIL'} pitch_factor table = {[pitch_factor(p) for p in pf_exp]}")
    # Burns (#13): zone surfaces 772+2376+496 = 3644 raw -> +15% waste = 4190 order = 41.9 sq
    b_zones = [{"footprint_sf": 772 / pitch_factor(6), "pitch": 6},
               {"footprint_sf": 2376 / pitch_factor(8), "pitch": 8},
               {"footprint_sf": 496 / pitch_factor(10), "pitch": 10}]
    rb = roofing_estimate(b_zones)
    b_ok = abs(rb["raw_surface_sf"] - 3644) < 1 and abs(rb["order_surface_sf"] - 4190) < 2 \
        and abs(rb["order_squares"] - 41.9) < 0.1
    ok = ok and b_ok
    print(f"  {'OK ' if b_ok else 'FAIL'} roofing Burns: raw {rb['raw_surface_sf']} -> order "
          f"{rb['order_surface_sf']} sf ({rb['order_squares']} sq) (exp 3644 -> 4190, 41.9)")
    # Peterson (#13): raw 4897 surface -> +15% = 5631 order; all-in $1.98/sf reconciles actual $11,204
    p_zones = [{"footprint_sf": 4897 / pitch_factor(16), "pitch": 16}]
    rp = roofing_estimate(p_zones)
    recon = abs(rp["order_surface_sf"] * 1.98 - 11204) / 11204
    p_ok = abs(rp["order_surface_sf"] - 5631) < 2 and recon < 0.006
    ok = ok and p_ok
    print(f"  {'OK ' if p_ok else 'FAIL'} roofing Peterson: raw {rp['raw_surface_sf']} -> order "
          f"{rp['order_surface_sf']} sf; all-in $1.98 = ${rp['order_surface_sf']*1.98:,.0f} vs actual "
          f"$11,204 ({recon*100:.1f}%)")
    # siding: Wilson columns (#16) = 6× 6x6 + 15× 12x12 = $8,820 EXACT (sourced EACH line)
    sc = siding_estimate([{"item": "col_cedar_6x6", "count": 6},
                          {"item": "col_cedar_12x12", "count": 15}])
    sc_ok = abs(sc["total"] - 8820) < 0.01 and abs(sc["by_category"]["column"] - 8820) < 0.01
    ok = ok and sc_ok
    print(f"  {'OK ' if sc_ok else 'FAIL'} siding Wilson columns = ${sc['total']:,.0f} (exp $8,820)")
    # siding: Leone field (#16) raw 43 sq (4,300 SF) lap +10% waste = 47.3 sq ≈ Southern 47.7 (1%)
    sf = siding_estimate([{"item": "lap_7", "sf": 4300}])
    row = sf["rows"][0]
    sf_ok = abs(row["squares"] - 47.3) < 0.1 and abs(row["squares"] - 47.7) / 47.7 < 0.01 \
        and abs(row["cost"] - 47.3 * 250) < 5
    ok = ok and sf_ok
    print(f"  {'OK ' if sf_ok else 'FAIL'} siding Leone field: 4,300 SF raw -> {row['order_sf']} SF "
          f"({row['squares']} sq) ~= Southern 47.7 sq; ${row['cost']:,.0f}")
    # siding: rate override (lap jumped to $330/sq) + unknown-item guard
    ov = siding_estimate([{"item": "lap_7", "sf": 4300, "rate": 330}])["rows"][0]["cost"]
    try:
        siding_estimate([{"item": "vinyl", "sf": 100}]); guard = False
    except ValueError:
        guard = True
    g2_ok = abs(ov - 47.3 * 330) < 5 and guard
    ok = ok and g2_ok
    print(f"  {'OK ' if g2_ok else 'FAIL'} siding override(${ov:,.0f} @ $330) + unknown-item guard = {guard}")
    # SheetLedger: the EXACT "claimed no roof plan from a partial look" failure, now blocked
    import tempfile
    vf = tempfile.NamedTemporaryFile(suffix=".png", delete=False); vf.write(b"x"); vf.close()
    slok = True
    led = SheetLedger("plan.pdf", 4)
    try:                                   # examine needs a REAL view file (proof I looked)
        led.examine(0, "roof_plan", view="/no/such.png"); slok = False
    except ValueError:
        pass
    try:                                   # can't claim ABSENT while pages are unexamined
        led.assert_absent("roof_plan"); slok = False
    except ValueError:
        pass
    led.examine(0, "cover", vf.name).examine(1, "foundation", vf.name).examine(2, "floor_plan", vf.name)
    okA = led.certify()[0]                  # p3 unexamined + no roof_plan -> FAIL
    led.examine(3, "roof_plan", vf.name)
    okB = led.certify(require=("foundation", "floor_plan", "roof_plan"))[0]   # complete -> PASS
    idx = SheetLedger("p.pdf", 1).set_index([(1, "FOUNDATION PLAN"), (4, "ROOF PLAN")])
    idx.examine(0, "foundation", vf.name)
    okC = idx.certify(require=("foundation",))[0]   # index names ROOF PLAN, none classified -> FAIL
    _os.unlink(vf.name)
    slok = slok and okA is False and okB is True and okC is False
    ok = ok and slok
    print(f"  {'OK ' if slok else 'FAIL'} SheetLedger forcing function (blocks partial-look 'no roof plan')")
    # DAVIS fixes (7/6/26): cladding forcing function -- per-face accounting + cross-check
    davis = cladding_by_elevation({
        "front": [{"material": "stone", "run_ft": 65, "ht_ft": 3.5},
                  {"material": "stone", "sf": 60, "feature": "pier"}],
        "left":  [{"material": "stone", "run_ft": 30, "ht_ft": 3.5},
                  {"material": "stone", "sf": 54, "feature": "chimney"}],
        "right": [{"material": "stone", "run_ft": 40, "ht_ft": 3.5}],
        "rear":  [],                              # explicit: rear has NO stone (the whole point)
    }, perimeter_lf=379)
    cl_sum_ok = abs(davis["by_material"]["stone"] - 586.5) < 2 and any("60%" in f for f in davis["flags"])
    try:                                          # OMITTING a face must raise (the real miss)
        cladding_by_elevation({"front": [], "left": [], "right": []}, 379); face_guard = False
    except ValueError:
        face_guard = True
    over = cladding_by_elevation({"front": [{"material": "stone", "sf": 2000}],
                                  "rear": [], "left": [], "right": []}, 379)  # 2000 >> perim-band
    cl_ok = cl_sum_ok and face_guard and any("OVER" in f for f in over["flags"])
    ok = ok and cl_ok
    print(f"  {'OK ' if cl_ok else 'FAIL'} cladding_by_elevation: Davis stone {davis['by_material']['stone']:.0f} SF "
          f"(under-flag on), face-omit guard={face_guard}, over-wrap flag on")
    tl = trim_labor(3551, 898)
    tl_ok = abs(tl - 8898) < 1
    ok = ok and tl_ok
    print(f"  {'OK ' if tl_ok else 'FAIL'} trim_labor(3551,898) = ${tl:,.0f} (exp $8,898; heated+garage SF, not LF)")
    cp = cabinet_pricing({"base": 32, "upper": 25, "island": 14, "tall": 8})
    cb_ok = (cp["measured_lf"] == 79 and cp["priced_lf"] == 87
             and cp["material_total"] == 13050 and cp["install_total"] == 6525)
    ok = ok and cb_ok
    print(f"  {'OK ' if cb_ok else 'FAIL'} cabinet_pricing(kitchen) = {cp['priced_lf']:.0f} priced LF "
          f"(${cp['material_total']:,.0f} material + ${cp['install_total']:,.0f} install)")
    rt = roofing_turnkey([{"footprint_sf": 5413, "pitch": 6}, {"footprint_sf": 150, "pitch": 2}])
    rt_ok = abs(rt["rate_per_sf"] - 2.25) < 1e-6 and abs(rt["total"] - rt["order_surface_sf"] * 2.25) < 1
    ok = ok and rt_ok
    print(f"  {'OK ' if rt_ok else 'FAIL'} roofing_turnkey Davis = {rt['order_surface_sf']:.0f} SF x $2.25 = ${rt['total']:,.0f} (template line rate)")
    # AUDIT FIXES (7/6/26) — three latent holes the golden suite never exercised, now locked:
    # F1: framed SF must NOT double-count a TOTAL UNDER ROOF row nor frame an UNCOVERED patio.
    _rows = [{"label": "MAIN FLOOR HEATED", "sqft": 3551.0, "klass": classify_area_row("MAIN FLOOR HEATED")},
             {"label": "GARAGE",           "sqft": 898.0,  "klass": classify_area_row("GARAGE")},
             {"label": "COVERED PORCH",     "sqft": 166.0,  "klass": classify_area_row("COVERED PORCH")},
             {"label": "REAR PORCH",        "sqft": 422.0,  "klass": classify_area_row("REAR PORCH")},
             {"label": "UNCOVERED PATIO",   "sqft": 300.0,  "klass": classify_area_row("UNCOVERED PATIO")},
             {"label": "TOTAL UNDER ROOF",  "sqft": 5037.0, "klass": classify_area_row("TOTAL UNDER ROOF")}]
    _fr = framed_under_roof_sf(_rows)
    fr2_ok = abs(_fr - 5037.0) < 1        # 3551+898+166+422; TOTAL row + uncovered patio excluded
    ok = ok and fr2_ok
    print(f"  {'OK ' if fr2_ok else 'FAIL'} framed_under_roof_sf = {_fr:,.0f} (exp 5,037; no TOTAL-row 2x, no uncovered-patio leak)")
    # F2: _page_scale must accept a 'good' (snapped-to-standard) scale, not only high/review.
    _sav_ds, _sav_ocr = detect_scale, detect_scale_ocr
    globals()["detect_scale"] = lambda p: {"ppf": 18.0, "confidence": "good", "scale": "1/4\"=1'"}
    globals()["detect_scale_ocr"] = lambda p: None
    class _P:  # _page_scale only calls detect_scale(page)/detect_scale_ocr(page)
        rect = None
    _ps = _page_scale(_P())
    globals()["detect_scale"], globals()["detect_scale_ocr"] = _sav_ds, _sav_ocr
    ps_ok = _ps is not None and abs(_ps["ppf"] - 18.0) < 1e-9
    ok = ok and ps_ok
    print(f"  {'OK ' if ps_ok else 'FAIL'} _page_scale accepts 'good' scale -> {_ps} (was dropped to None)")
    # F5: price_lines must never silently price a dup (group,name) as the $0 ASSEMBLY container.
    try:
        pl_ok = price_lines({"Windows/Windows": 1})["builder_cost"] > 0   # picks the priced leaf
    except KeyError:
        pl_ok = True                                                       # raising loud is fine too
    ok = ok and pl_ok
    print(f"  {'OK ' if pl_ok else 'FAIL'} price_lines dup (group,name) -> priced leaf, never a silent $0 ASSEMBLY")
    # LEVEL GROUND (7/6/26): report_from_takeoff() pre-bid adapter -> valid, honest report JSON.
    import json as _json
    _tk = {"lines": [
              {"trade": "heated_sf", "qty": 3214, "unit": "SF", "source": "MEASURED",
               "method": "certified-component-rollup", "confidence": "high", "page": 1,
               "note": "synthetic certified test quantity", "certified": True,
               "proof": [{"component": "synthetic heated"}]},
              {"trade": "roof_surface_sq", "qty": 48, "unit": "sq", "source": "MEASURED",
               "method": "face-decomposition", "confidence": "high", "page": 3, "note": ""}],
           "not_measured": [{"trade": "slab_area_sf", "page": 2, "why": "both tracers returned None"}],
           "assumptions": []}
    _rep = report_from_takeoff(_tk, {"stories": 1, "foundation": "slab", "garage": "3-car"},
                               {"state": "GA", "market": "Middle Georgia"},
                               property_label="Sample Residence", report_type="pre_bid")
    _s = _json.dumps(_rep)                                            # must be JSON-serializable
    rft_ok = (_rep["meta"]["bid_total"] is None                      # pre-bid hides the verdict strip
              and _rep["meta"]["home"]["heated_sf"] == 3214          # backfilled from the takeoff
              and len(_rep["findings"]) == len(PRE_BID_SCOPE_CHECKLIST)
              and all(f["bid_amount"] is None for f in _rep["findings"])   # no dollars pre-bid
              and any(q["item"] == "Heated living area" for q in _rep["quantities"])
              and any("slab" in u.lower() for u in _rep["unknowns"]))      # not-measured surfaced
    ok = ok and rft_ok
    print(f"  {'OK ' if rft_ok else 'FAIL'} report_from_takeoff pre-bid: {len(_rep['quantities'])} qty, "
          f"{len(_rep['findings'])} checklist findings, bid hidden, not-measured surfaced (JSON {len(_s)}b)")
    # PHASE 2 (7/6/26): price_report() + report_from_takeoff(market_book=...) -> expected-cost range.
    _q = [{"item": "Total area under roof", "qty": "4,400", "unit": "sq ft"},
          {"item": "Heated living area", "qty": "3,214", "unit": "sq ft"}]
    _pr = price_report(_q, {"finish_level": "custom"}, market="Middle Georgia")          # CALIBRATED
    _prS = price_report(_q, {"finish_level": "custom"}, market="Seattle", state="WA")     # REGIONAL (metro index)
    _prU = price_report(_q, {"finish_level": "custom"}, market="Nowheresville")           # UNCALIBRATED
    _facS = round(1.07 / 0.87, 3)                                                         # Seattle / GA anchor
    _repP = report_from_takeoff(_tk, {"stories": 1, "foundation": "slab", "finish_level": "custom"},
                                {"state": "GA", "market": "Middle Georgia"},
                                report_type="pre_bid", market_book=MARKET_RATE_BOOK)
    mp_ok = (_pr["tier"] == "calibrated" and _pr["market_calibrated"] is True
             and _pr["total"]["low"] == round(4400 * 160, -3) and _pr["total"]["high"] == round(4400 * 200, -3)
             and _prS["tier"] == "regional_estimate" and _prS["market_indexed"] is True
             and _prS["index_factor"] == _facS
             and _prS["total"]["low"] == round(4400 * round(160 * _facS), -3)   # GA band x Seattle cost factor
             and _prU["tier"] == "uncalibrated" and _prU["market_calibrated"] is False
             and _repP["meta"]["pricing_confirmed"] is True and _repP["meta"]["pricing_tier"] == "calibrated")
    ok = ok and mp_ok
    print(f"  {'OK ' if mp_ok else 'FAIL'} price_report tiers: Middle-GA calibrated ${_pr['total']['low']:,.0f}-"
          f"{_pr['total']['high']:,.0f}; Seattle regional_estimate x{_facS} ${_prS['total']['low']:,.0f}-"
          f"{_prS['total']['high']:,.0f}; Nowheresville uncalibrated")
    # PHASE 3 (7/6/26): findings_from_bid() -> auto findings from a structured builder's bid.
    _bid = ingest_bid([
        {"desc": "Site work allowance", "amount": 4500},          # present but under expected -> finding
        {"desc": "Insulation (batt)", "amount": 8200},            # plan spec is foam -> mispriced
        {"desc": "Electrical", "amount": 35000, "is_lump": True}, # big undescribed -> vague lump
        {"desc": "Framing labor and materials", "amount": 120000},
        {"desc": "Roofing", "amount": 16000}], total=587400)      # gutters / home-tech / landscaping ABSENT
    _bf = findings_from_bid(_bid, {"insulation": "spray foam roofline"})
    _cats = [f["category"] for f in _bf]
    _lumps = [f for f in _bf if f["category"] == "vague_lump"]
    b3_ok = (_bid["total"] == 587400
             and any(f["title"].startswith("Gutters") for f in _bf)                 # absent -> missing
             and any(f["title"].startswith("Home techn") for f in _bf)              # absent -> missing
             and any(f["category"] == "mispriced" and "Insulation" in f["title"] for f in _bf)  # foam grade
             and any("Site work" in f["title"] for f in _bf)                        # underpriced -> finding
             and len(_lumps) == 1 and _lumps[0]["realistic_low"] is None            # lump flagged, not priced
             and all(f["realistic_low"] is not None for f in _bf if f["category"] != "vague_lump"))
    _repB = report_from_takeoff(_tk, {"finish_level": "custom", "insulation": "spray foam roofline"},
                                {"market": "Middle Georgia"}, bid=_bid, market_book=MARKET_RATE_BOOK)
    b3_ok = b3_ok and (_repB["meta"]["report_type"] == "bid_gap"
                       and _repB["meta"]["bid_total"] == 587400
                       and len(_repB["findings"]) == len(_bf))
    ok = ok and b3_ok
    print(f"  {'OK ' if b3_ok else 'FAIL'} findings_from_bid: {len(_bf)} findings "
          f"({_cats.count('missing_scope')} missing, {_cats.count('mispriced')} mispriced, "
          f"{len(_lumps)} vague-lump); report_from_takeoff(bid=) -> bid_gap $587,400")
    # ZEGARRA (7/8/26): the Buildern Import Description column is CLIENT-FACING.
    # lint_buildern_descriptions blocks the EXACT leaks that shipped -- takeoff
    # math, internal SRC/CONFIRM/FLAG tags, and bare quantity echoes -- while
    # passing real scope lines (incl. ones that carry a "(17)" count or trailing qty).
    _bad_desc = [
        ("Concrete 4\" flat slab", "3261 SF x4\" ≈ 44.30 CY"),                 # slab math
        ("Plumbing", "base 8000 + 23x450 + 6x400 = 20750; 5 WC, 10 sinks"),   # arithmetic
        ("Shingle Roof", "3159 fp x1.054 (4:12) x1.15 = 3829 SF"),            # waste/pitch mult.
        ("Spray Foam - Walls", "5,041 SF  [CONFIRM: garage foam? net-of-openings?]"),  # flag leak
        ("Drywall", "walls 11,909 + clg 4,147 + garage 1,591 ≈ 17,647 SF"),   # summation + ≈
        ("Concrete washout pit", "1 ea"),                                     # bare qty
        ("Building Permit", "4,415 SF"),                                      # bare qty
        ("Water Heaters (2)", "2.00 each"),                                   # bare qty
        ("Orphan", None),                                                     # blank
    ]
    _good_desc = [
        ("Slab", "4-inch steel-reinforced concrete slab foundation across the full home footprint."),
        ("Plumbing", "Complete plumbing rough-in and fixtures — 5 toilets, 10 sinks, 3 tubs, 2 showers, and 2 water heaters."),
        ("Spray Foam", "Allowance — open-cell spray foam insulation in all exterior walls."),
        ("Garage doors", "Allowance — two 9-ft carriage-style garage doors."),
        ("Interior doors", "8-ft solid-core single interior doors (17)."),
        ("Electrical", "Complete electrical rough-in and finish incl. 200A service — 110 recessed cans, 5 fans, 29 GFCI outlets, 7 exhaust fans."),
        ("Slab w/ qty", "4-inch reinforced concrete slab across the full footprint — 3,261 SF (incl. 10% waste)."),
    ]
    _bad_hits = lint_buildern_descriptions(_bad_desc)
    _good_hits = lint_buildern_descriptions(_good_desc)
    ld_ok = len(_bad_hits) == len(_bad_desc) and len(_good_hits) == 0
    ok = ok and ld_ok
    print(f"  {'OK ' if ld_ok else 'FAIL'} lint_buildern_descriptions: caught {len(_bad_hits)}/{len(_bad_desc)} "
          f"client-facing leaks, {len(_good_hits)} false-positive on {len(_good_desc)} good lines")
    # ---- cal #63 (L J Show): elevation-first counting + reconciliation guards
    _tags_ok = all(
        (lambda r, w, h: r and abs(r['width_ft'] - w) < .02 and abs(r['height_ft'] - h) < .02)(
            parse_opening_tag(t), w, h)
        for t, w, h in [('3060SH', 3, 6), ('2020FX', 2, 2), ('2880', 2.667, 8),
                        ('10080', 10, 8), ('80100', 8, 10), ('1260', 1.167, 6)])
    ok = ok and _tags_ok
    print(f"  {'OK ' if _tags_ok else 'FAIL'} parse_opening_tag: 10080=10x8 (not 1x8), 80100=8x10, 1260 sidelight kept")
    _rf_bad = reconcile_roof_footprint(7758, 5529.8, 402.0, 1.50)
    _rf_good = reconcile_roof_footprint(6159, 5529.8, 402.0, 1.50)
    _rf_ok = (not _rf_bad['ok']) and _rf_good['ok']
    ok = ok and _rf_ok
    print(f"  {'OK ' if _rf_ok else 'FAIL'} reconcile_roof_footprint: flags 5.54ft-implied trace, passes the 1.57ft one")
    _cc = cladding_completeness({'lap': 1658, 'bnb': 3318, 'stone': 562}, 4292.0, 1247.0)
    _cc_bad = cladding_completeness({'lap': 1658, 'bnb': 3318}, 4292.0, 1247.0)
    _cc_ok = _cc['ok'] and (not _cc_bad['ok'])
    ok = ok and _cc_ok
    print(f"  {'OK ' if _cc_ok else 'FAIL'} cladding_completeness: catches {_cc_bad['unallocated_sf']:.0f} SF silently dropped")
    _fl = footer_lf(394.32, {'garage': 75.42, 'rear_porch': 100.33, 'front_porch': 25.81})
    _fl_ok = abs(_fl['footer_lf'] - 595.88) < 0.5 and _fl['step_total_lf'] > 200
    ok = ok and _fl_ok
    print(f"  {'OK ' if _fl_ok else 'FAIL'} footer_lf: whole-slab outer + every internal step, each ONCE = {_fl['footer_lf']} LF (Jason 634.79; 39 LF residual OPEN)")
    _bw = beam_wrap_lf(121.0, 14, 12.0)
    _bw_ok = abs(_bw['total_beam_wrap_lf'] - 289.0) < 1.0
    ok = ok and _bw_ok
    print(f"  {'OK ' if _bw_ok else 'FAIL'} beam_wrap_lf: 121 LF horizontal + 14 posts = {_bw['total_beam_wrap_lf']} LF (Jason 291)")
    print("ALL PASS" if ok else "SOME FAILED")
