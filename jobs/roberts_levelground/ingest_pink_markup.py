#!/usr/bin/env python
"""Ingest Jason's MAGENTA MARKER boundaries as declared walks (any component).

This is how Jason teaches — colored markup on the drawing (precedent: the roof-line
review in the golden fixture came from his colored overlay; cal #67 recorded the
crawlspace footprint arriving the same way). Two input shapes are accepted:

  - a SCREENSHOT of the viewer (any resolution): registered to the sheet render by
    multi-scale template match, then landmark-verified;
  - a DIRECT DRAW on a full-res copy of the sheet render (the staged
    Desktop/ROBERTS-MARKUP canvases): registration is the identity, still
    landmark-verified — cropping or resaving at another size is caught, not trusted.

Pipeline per magenta loop:
  1. register image -> page points (inverted RED channel: the plan's blue linework
     is dark in R and matches; magenta/red overlays have R~255 and self-erase);
  2. isolate magenta strokes, one closed contour per component, erode to centerline;
  3. rectilinearize; snap every leg to the sheet's printed chains ON ITS AXIS
     (cal #66 contract — a leg the sheet does not print refuses);
  4. closure gate (<= 0.5 ft), then MERGE into declared_walks.json under the
     component's name. Existing walks for other components are preserved.

Multiple components on one canvas (e.g. garage + porch on the foundation sheet) are
mapped to contours BY AREA ORDER, then each mapping is sanity-checked against the
component's traced primary (+/-25%) so a swapped assignment can never declare.
Fail-closed: any step that cannot prove itself prints WHY and declares nothing —
per component, so one bad loop does not block a good one.

Usage:
  python ingest_pink_markup.py                       # legacy: the 140952 crawlspace shot
  python ingest_pink_markup.py IMG --component "garage slab" --component "front porch slab"
  python ingest_pink_markup.py IMG --component "heated envelope (floor plan)" --page 4
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import jnj_takeoff as eng  # noqa: E402

PLAN = os.path.join(ROOT, "tools", "tests", "golden", "roberts", "plan.pdf")
LEGACY_SHOT = (r"C:\Users\jason\OneDrive\Pictures\Screenshots"
               r"\Screenshot 2026-08-14 140952.png")
# cal #67: a crawlspace is NOT heated — the foundation footprint declares under its
# true name. The heated walk is a FLOOR-PLAN component (default --page 4).
LEGACY_COMPONENT = "crawlspace envelope (foundation footprint)"
DEFAULT_PAGE = {"heated envelope (floor plan)": 4,
                "rear deck (floor plan)": 4}


def register(shot, sheet, page, np, cv2):
    """Image px -> sheet-render px transform (scale s, offset ox,oy), landmark-proven."""
    sg = 255 - shot[:, :, 2]
    tg = 255 - sheet[:, :, 2]
    if shot.shape[:2] == sheet.shape[:2]:
        s, ox, oy = 1.0, 0, 0
        print("registration: identity (direct draw on the sheet render)")
    else:
        # The shot may be a tight CROP of the sheet (the 140952 screenshot is
        # 800x716 covering part of a 4802-wide render) or a full screen with
        # chrome, so the scale window is bounded by geometry, not guessed: the
        # resized shot must FIT inside the sheet (upper bound = min axis ratio)
        # and must cover a meaningful fraction of it (lower bound = 0.4x that).
        fit = min(tg.shape[1] / sg.shape[1], tg.shape[0] / sg.shape[0])
        best = None
        for s in np.linspace(0.4 * fit, fit, 61):
            w, h = int(sg.shape[1] * s), int(sg.shape[0] * s)
            if w > tg.shape[1] or h > tg.shape[0]:
                continue
            r = cv2.matchTemplate(tg, cv2.resize(sg, (w, h)), cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(r)
            if best is None or mx > best[0]:
                best = (mx, s, loc)
        if best is None:
            print("REFUSED: no scale in the geometric window lets the image fit "
                  "the sheet render — wrong sheet, or the image is not a view of it")
            return None
        score, s, (ox, oy) = best
        print(f"registration: scale {s:.4f}, offset ({ox},{oy}), score {score:.3f}")
    # correlation alone is blur-limited, so verify the transform with LANDMARKS:
    # known dimension-label positions must land on ink, and a shifted control must not.
    import fitz
    doc = fitz.open(PLAN)
    labels = eng._dim_labels(doc[page])
    doc.close()
    render_zoom = sheet.shape[1] / doc_page_width(page)
    ink = (255 - shot[:, :, 2]) > 55

    def hit_rate(dx, dy):
        hits = tries = 0
        for _v, cx, cy, _o, _t in labels:
            px = (cx * render_zoom - (ox + dx)) / s
            py = (cy * render_zoom - (oy + dy)) / s
            x0, x1 = int(px) - 4, int(px) + 5
            y0, y1 = int(py) - 4, int(py) + 5
            if 0 <= y0 and y1 < ink.shape[0] and 0 <= x0 and x1 < ink.shape[1]:
                tries += 1
                if ink[y0:y1, x0:x1].any():
                    hits += 1
        return hits / max(tries, 1), tries

    rate, n = hit_rate(0, 0)
    ctrl = max(hit_rate(60, 60)[0], hit_rate(-60, 60)[0])
    print(f"landmark check: {rate:.0%} of {n} dimension labels on ink "
          f"(shifted control {ctrl:.0%})")
    if rate < 0.7 or rate < ctrl + 0.15:
        print("REFUSED: transform fails the landmark check — cannot trust the "
              "magenta coordinates")
        return None
    # cal #69: this proof travels WITH the declared walk — the engine refuses a
    # markup-raster measurement whose registration cannot show its landmark oracle.
    stats = {"scale": round(s, 4), "offset": [int(ox), int(oy)],
             "landmark_rate": round(rate, 3), "landmark_n": n,
             "landmark_control": round(ctrl, 3)}
    return (s, ox, oy, render_zoom), stats


def doc_page_width(page):
    import fitz
    doc = fitz.open(PLAN)
    w = doc[page].rect.width
    doc.close()
    return w


def magenta_contours(shot, want, np, cv2, color="magenta"):
    """Largest `want` closed marker loops, eroded to their stroke centerline.
    Jason's magenta is pure (255,128,255 sampled; Paint default 255,0,255); his
    green (porch, 8/14 foundation markup) samples ~(128,255,158) RGB. The
    viewer's verification purple (176,111,216) has r<230 and the plan's red
    markup has b<100 — excluded by the magenta mask; the plan's own BLUE
    linework and green-ish fills fail g-b>60 — excluded by the green mask."""
    b, g, r = (shot[:, :, 0].astype(int), shot[:, :, 1].astype(int),
               shot[:, :, 2].astype(int))
    if color == "green":
        # bright marker green (his 8/14 screenshots) OR Paint's palette "Green"
        # (34,177,76) — both sampled from his files, never guessed.
        mask = (((g > 200) & (g - r > 60) & (g - b > 60))
                | ((np.abs(r - 34) < 45) & (np.abs(g - 177) < 50)
                   & (np.abs(b - 76) < 50))).astype(np.uint8) * 255
    elif color == "purple":
        # Paint's palette "Purple" (163,73,164), sampled off the 8/17 foundation
        # canvas. r~b keeps the plan's blue linework (b>>r) and red scribbles
        # (r>>b) out.
        mask = ((np.abs(r - 163) < 45) & (np.abs(g - 73) < 45)
                & (np.abs(b - 164) < 45)).astype(np.uint8) * 255
    else:
        mask = ((r > 230) & (b > 230) & (r - g > 60) & (b - g > 60)).astype(np.uint8) * 255
    n_pink = int(mask.sum() / 255)
    print(f"{color} pixels: {n_pink}")
    if n_pink < 2000:
        print(f"REFUSED: {color} stroke not found at the sampled color")
        return []
    # Strokes arrive as DASHED pen fragments (8/17 floor-plan magenta: 214 pieces
    # of ~170 px) and with corner gaps, so bridging must run BEFORE any size
    # filtering — a blob floor ahead of the close executes every dash. Abandoned
    # dead-end strokes and flecks need no pre-filter: a filament welded onto the
    # loop dies in the fill+erode centerline step (proven on the 8/17 purple
    # color-switch spur), and off-loop flecks lose the top-`want` selection.
    # 61 px ~ 3.7 ft at this render scale — gap territory only, and the
    # chain/closure gates downstream refuse anything a bridge invented.
    # Single-loop canvases may escalate further than multi-loop ones: a 101 px
    # bridge (~6 ft) on a two-loop canvas could weld separate components.
    kernels = (9, 31, 61, 81, 101) if want == 1 else (9, 31, 61)
    welded = False
    for k in kernels:
        closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                  np.ones((k, k), np.uint8))
        cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:want]
        band = closed.sum() / 255
        # a closed loop's contour area dwarfs its own stroke-band pixel count;
        # an unclosed C-shape's does not. Demand it before accepting this kernel.
        if len(cnts) >= want and all(cv2.contourArea(c) > 1.5 * band / want
                                     for c in cnts[:want]):
            if k > 9:
                print(f"stroke gaps bridged with a {k}px close")
            welded = True
            break
    if not welded:
        # Falling through with the last kernel's fragments once extracted an
        # 11x12 ft dash-cluster as "the heated envelope" and its legs happened
        # to snap printed — never proceed on an unwelded stroke.
        print(f"REFUSED: {color} stroke never welds into {want} closed loop(s) "
              f"(largest contour {int(cv2.contourArea(cnts[0])) if cnts else 0}px² "
              f"vs stroke band {int(band)}px) — gaps exceed "
              f"{kernels[-1]}px; draw with a continuous stroke")
        return []
    mask = closed
    out = []
    for c in cnts:
        if cv2.contourArea(c) < 1500:
            continue
        filled = np.zeros(mask.shape, np.uint8)
        cv2.drawContours(filled, [c], -1, 255, -1)
        loop_pink = int((mask & filled).sum() / 255)
        stroke_w = max(2, int(round(loop_pink / max(cv2.arcLength(c, True), 1))))
        k = max(3, (stroke_w // 2) * 2 + 1)
        er = cv2.erode(filled, np.ones((k, k), np.uint8))
        cnts2, _ = cv2.findContours(er, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c2 = max(cnts2, key=cv2.contourArea) if cnts2 else c
        ap = cv2.approxPolyDP(c2, 0.0012 * cv2.arcLength(c2, True), True)
        print(f"magenta boundary: {len(ap)} vertices (stroke ~{stroke_w}px, "
              f"contour area {cv2.contourArea(c):.0f}px²)")
        out.append(ap)
    return out


AXIS = {"R": "H", "L": "H", "U": "V", "D": "V"}
SIGN = {"R": 1, "L": -1, "D": 1, "U": -1}
SNAP_TOL = 1.2    # traced stroke -> printed value
TRACE_TOL = 1.2   # traced stroke -> closure-derived value (cal #68 drawing agreement)
CLOSE_TOL = 0.5   # ft, the cal #66 closure gate


def _leg_val(leg):
    if leg.get("printed") is not None:
        return leg["printed"]
    if leg.get("derived") is not None:
        return leg["derived"]
    return leg["traced"]


def _axis_err(legs, ax):
    return sum(SIGN[l["dir"]] * _leg_val(l) for l in legs if AXIS[l["dir"]] == ax)


def _closure(legs):
    return (_axis_err(legs, "H") ** 2 + _axis_err(legs, "V") ** 2) ** 0.5


def _forced(legs, i):
    """What closure forces leg i to be, given every OTHER leg on its axis."""
    ax = AXIS[legs[i]["dir"]]
    others = sum(SIGN[l["dir"]] * _leg_val(l)
                 for j, l in enumerate(legs) if AXIS[l["dir"]] == ax and j != i)
    return -others * SIGN[legs[i]["dir"]]


def resolve_walk(edges, pool):
    """cal #66/#68 resolution: snap every leg to the sheet's printed chains; when a
    sheet doesn't print a leg as a single dimension, derive it from closure (cal #68
    — the value is FORCED by the other, chain-verified legs; the stroke must agree
    within TRACE_TOL; at most one per axis); when an all-printed walk cannot close,
    rescue by un-snapping exactly one leg the same closure-forced way, refusing on
    ambiguity. Returns (walk, log, refusals) — walk legs are [len, dir] or
    [len, dir, 'derived-by-closure']."""
    legs = []
    for e in edges:
        cand = pool[AXIS[e["dir"]]]
        best = min(cand, key=lambda v: abs(v - e["len"])) if cand else None
        legs.append({"traced": e["len"], "dir": e["dir"], "at": e["at"],
                     "printed": best if best is not None
                     and abs(best - e["len"]) <= SNAP_TOL else None})
    log, refusals = [], []

    # cal #68: one unprinted leg per axis is closure-derivable; two are not
    for ax in ("H", "V"):
        open_i = [i for i, l in enumerate(legs)
                  if AXIS[l["dir"]] == ax and l["printed"] is None]
        if len(open_i) > 1:
            for i in open_i:
                l = legs[i]
                refusals.append(f"{l['dir']} ~{l['traced']:.1f} ft at "
                                f"({l['at'][0]:.0f},{l['at'][1]:.0f}) unprinted, and "
                                f"axis {ax} has {len(open_i)} unprinted legs — "
                                f"closure can only force one (cal #68)")
            continue
        if len(open_i) == 1:
            i = open_i[0]
            l = legs[i]
            forced = _forced(legs, i)
            if forced <= 0:
                refusals.append(f"{l['dir']} leg at ({l['at'][0]:.0f},{l['at'][1]:.0f}): "
                                f"closure forces a NEGATIVE length — the drawing's "
                                f"direction is inconsistent with the printed legs")
                continue
            near = min(pool[ax], key=lambda v: abs(v - forced)) if pool[ax] else None
            if near is not None and abs(near - forced) <= SNAP_TOL \
                    and abs(near - l["traced"]) <= SNAP_TOL + 1.0:
                l["printed"] = near
                log.append(f"closure-assisted snap: {l['dir']} traced "
                           f"{l['traced']:.2f} -> printed {near} (forced {forced:.2f})")
            elif abs(forced - l["traced"]) <= TRACE_TOL:
                l["derived"] = round(forced, 2)
                log.append(f"cal #68 derived-by-closure: {l['dir']} traced "
                           f"{l['traced']:.2f} -> forced {forced:.2f} "
                           f"(sheet prints no single dim for this leg)")
            else:
                refusals.append(f"{l['dir']} ~{l['traced']:.1f} ft at "
                                f"({l['at'][0]:.0f},{l['at'][1]:.0f}): closure forces "
                                f"{forced:.2f} ft but the stroke disagrees by "
                                f"{abs(forced - l['traced']):.2f} ft (> {TRACE_TOL})")
    if refusals:
        return None, log, refusals

    # closure rescue: all legs printed/derived, but the walk does not close —
    # exactly one leg must be mis-snapped. Un-snap each candidate in turn and let
    # closure force it (same cal #68 math); a unique winner is taken, ambiguity
    # refuses. Axes already carrying a derived leg are exempt (one per axis).
    if _closure(legs) > CLOSE_TOL:
        derived_axes = {AXIS[l["dir"]] for l in legs if l.get("derived") is not None}
        candidates = []
        for i, l in enumerate(legs):
            ax = AXIS[l["dir"]]
            if ax in derived_axes or l["printed"] is None:
                continue
            trial = [dict(t) for t in legs]
            trial[i]["printed"] = None
            if any(t["printed"] is None and j != i for j, t in enumerate(trial)
                   if AXIS[t["dir"]] == ax):
                continue
            forced = _forced(trial, i)
            if forced <= 0:
                continue
            near = min(pool[ax], key=lambda v: abs(v - forced)) if pool[ax] else None
            if near is not None and abs(near - forced) <= 0.06 and near != l["printed"]:
                trial[i]["printed"] = near
                kind = f"re-snapped {l['dir']} {l['printed']} -> printed {near}"
            elif abs(forced - l["traced"]) <= TRACE_TOL:
                trial[i]["printed"] = None
                trial[i]["derived"] = round(forced, 2)
                kind = (f"un-snapped {l['dir']} {l['printed']} -> derived-by-closure "
                        f"{forced:.2f}")
            else:
                continue
            if _closure(trial) <= CLOSE_TOL:
                deviation = sum(abs(_leg_val(t) - t["traced"]) for t in trial)
                candidates.append((round(deviation, 3), i, trial, kind))
        candidates.sort(key=lambda c: c[0])
        if not candidates:
            return None, log, [f"printed legs do not close ({_closure(legs):.2f} ft) "
                               f"and no single-leg closure rescue resolves it"]
        if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < 0.3:
            return None, log, [
                "closure rescue is AMBIGUOUS — multiple single-leg readings close "
                "the walk: " + "; ".join(c[3] for c in candidates[:3])]
        _, i, legs, kind = candidates[0]
        log.append(f"closure rescue: {kind}")

    walk = []
    for l in legs:
        if l.get("derived") is not None:
            walk.append([l["derived"], l["dir"], "derived-by-closure"])
        else:
            walk.append([l["printed"], l["dir"]])
    return walk, log, []


def contour_to_walk(ap, transform, page, pool, ppf):
    """Contour px -> page points -> rectilinear traced legs + walk origin."""
    s, ox, oy, render_zoom = transform
    pts = [[(p[0][0] * s + ox) / render_zoom, (p[0][1] * s + oy) / render_zoom]
           for p in ap]
    edges = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = (dx * dx + dy * dy) ** 0.5 / ppf
        if L < 0.8:
            continue
        d = ("R" if dx > 0 else "L") if abs(dx) >= abs(dy) else ("D" if dy > 0 else "U")
        if edges and edges[-1]["dir"] == d:
            edges[-1]["len"] += L
        else:
            edges.append({"dir": d, "len": L, "at": (x0, y0)})
    if len(edges) > 1 and edges[0]["dir"] == edges[-1]["dir"]:
        edges[0]["len"] += edges.pop()["len"]
    origin = min(pts, key=lambda p: (p[1], p[0]))
    return edges, origin


def traced_primary_sf(component):
    """Traced primary qty from the evidence file, for the multi-loop mapping sanity
    check. None when the component has no pixel trace yet (heated, by design)."""
    path = os.path.join(HERE, "evidence", "takeoff_evidence.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        ev = json.load(fh)
    cert = ev.get("takeoff", ev).get("area_certification", {})
    for c in cert.get("components", []):
        if c.get("name") == component:
            try:
                return float(c["primary"]["qty"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=LEGACY_SHOT)
    ap.add_argument("--component", action="append",
                    help="component name(s) to declare; multiple loops on one canvas "
                         "map to components by DESCENDING AREA")
    ap.add_argument("--page", type=int, default=None,
                    help="0-based sheet index (default: 3, or the component's own)")
    ap.add_argument("--color", default="magenta",
                    choices=("magenta", "green", "purple"),
                    help="marker color to extract (Jason color-codes components)")
    args = ap.parse_args()
    components = args.component or [LEGACY_COMPONENT]
    page = args.page
    if page is None:
        pages = {DEFAULT_PAGE.get(c, 3) for c in components}
        if len(pages) > 1:
            print(f"REFUSED: components span sheets {sorted(pages)} — one sheet per run")
            return 1
        page = pages.pop()

    import cv2
    import numpy as np

    shot = cv2.imread(args.image)
    sheet_png = os.path.join(HERE, "viewer", "sheets", f"sheet_{page}.png")
    sheet = cv2.imread(sheet_png)
    if shot is None or sheet is None:
        print(f"REFUSED: cannot read {'image ' + args.image if shot is None else sheet_png}")
        return 1
    print(f"ingesting {os.path.basename(args.image)} -> sheet idx {page}, "
          f"components: {components}")

    reg = register(shot, sheet, page, np, cv2)
    if reg is None:
        return 1
    transform, reg_stats = reg
    reg_stats["image"] = os.path.basename(args.image)
    reg_stats["image_sha256"] = eng.sha256_file(args.image)

    import fitz
    doc = fitz.open(PLAN)
    ppf = eng.detect_scale(doc[page])["ppf"]
    pool = {"H": set(), "V": set()}
    for ch in eng.read_dimension_chains(doc[page], ppf):
        pool[ch["orient"]].update(ch["runs"])
        pool[ch["orient"]].add(ch["total"])
    doc.close()

    loops = magenta_contours(shot, len(components), np, cv2, color=args.color)
    if len(loops) < len(components):
        print(f"REFUSED: {len(components)} component(s) requested but only "
              f"{len(loops)} magenta loop(s) found")
        return 1

    declared, failures = [], []
    for component, ap_loop in zip(components, loops):
        print(f"\n-- {component} --")
        edges, origin = contour_to_walk(ap_loop, transform, page, pool, ppf)
        walk, log, refusals = resolve_walk(edges, pool)
        for line in log:
            print("  *", line)
        if refusals:
            failures.append(component)
            print("REFUSED to declare:")
            for m in refusals:
                print("  ?", m)
            continue
        for w in walk:
            print("  ", w)
        po = eng.polygon_outline([(w[0], w[1]) for w in walk])
        print(f"walk: {po['area_sf']} SF, perim {po['perimeter_lf']} LF, "
              f"closure {po['closure_err_ft']} ft")
        if len(walk) < 4 or po["area_sf"] < 20:
            failures.append(component)
            print(f"REFUSED: degenerate walk ({len(walk)} legs, {po['area_sf']} SF) "
                  f"— the stroke collapsed in extraction; draw the loop taller/"
                  f"cleaner or check the color")
            continue
        if po["closure_err_ft"] > 0.5:
            failures.append(component)
            print("REFUSED: printed legs do not close — a jog is mis-snapped")
            continue
        # The walk must be in the same ballpark as the component's last-known
        # primary — this catches BOTH a swapped loop/component mapping on
        # multi-loop canvases AND a wrong-region grab on re-ingest (an 11x12 ft
        # dash-cluster once extracted as "the heated envelope"; every leg
        # snapped printed and it replaced a good 2,100 SF walk). A first-ever
        # ingest has no prior and skips; a deliberate boundary redefinition
        # >25% needs the old evidence purged first, on purpose.
        ref = traced_primary_sf(component)
        if ref and abs(po["area_sf"] - ref) / ref > 0.25:
            failures.append(component)
            print(f"REFUSED: walk {po['area_sf']:.0f} SF is {abs(po['area_sf']-ref)/ref:.0%} "
                  f"from {component}'s last-known {ref:.0f} SF — wrong loop or "
                  f"wrong region; purge the old evidence first if this "
                  f"redefinition is intentional")
            continue
        declared.append({"name": component, "page": page,
                         "walk": walk,  # legs keep their cal #68 marker if present
                         "origin_pt": [round(origin[0], 2), round(origin[1], 2)],
                         # cal #69: the registered PRE-SNAP stroke polygon (page
                         # points) is the pixel-side primary; its corners are the
                         # rectilinearized edge starts, so collinear vertices from
                         # the wrap-merge are harmless to the shoelace.
                         "markup_polygon_pts": [[round(e["at"][0], 2),
                                                 round(e["at"][1], 2)]
                                                for e in edges],
                         "registration": reg_stats,
                         "confirmed_by": f"jason-pink-markup {os.path.basename(args.image)}"})

    if not declared:
        print("\nnothing declared")
        return 1

    # MERGE into declared_walks.json — never clobber other components' walks
    path = os.path.join(HERE, "declared_walks.json")
    existing = {"schema": "roberts.declared_walks.v1", "walks": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            existing = json.load(fh)
    by_name = {w["name"]: w for w in existing.get("walks", [])}
    for d in declared:
        by_name[d["name"]] = d
    existing["walks"] = list(by_name.values())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=1)
    for d in declared:
        print(f"\nDECLARED: {d['name']} <- {len(d['walk'])} printed legs "
              f"from Jason's magenta markup")
    if failures:
        print(f"\nNOT declared (fix the drawing or the chains): {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
