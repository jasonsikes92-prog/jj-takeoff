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
DEFAULT_PAGE = {"heated envelope (floor plan)": 4}


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
    return s, ox, oy, render_zoom


def doc_page_width(page):
    import fitz
    doc = fitz.open(PLAN)
    w = doc[page].rect.width
    doc.close()
    return w


def magenta_contours(shot, want, np, cv2):
    """Largest `want` closed magenta loops, eroded to their stroke centerline.
    Jason's marker is pure magenta (255,128,255 sampled; Paint default 255,0,255).
    The viewer's verification purple (176,111,216) has r<230 and the plan's red
    markup has b<100 — both excluded by the mask."""
    b, g, r = (shot[:, :, 0].astype(int), shot[:, :, 1].astype(int),
               shot[:, :, 2].astype(int))
    mask = ((r > 230) & (b > 230) & (r - g > 60) & (b - g > 60)).astype(np.uint8) * 255
    n_pink = int(mask.sum() / 255)
    print(f"magenta pixels: {n_pink}")
    if n_pink < 2000:
        print("REFUSED: magenta stroke not found at the sampled color")
        return []
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:want]
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


def contour_to_walk(ap, transform, page, pool, ppf):
    """Contour px -> page points -> rectilinear legs snapped to printed chains."""
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
    axis = {"R": "H", "L": "H", "U": "V", "D": "V"}
    walk, misses = [], []
    for e in edges:
        cand = pool[axis[e["dir"]]]
        best_v = min(cand, key=lambda v: abs(v - e["len"])) if cand else None
        if best_v is None or abs(best_v - e["len"]) > 1.2:
            misses.append(f"{e['dir']} ~{e['len']:.1f} ft at "
                          f"({e['at'][0]:.0f},{e['at'][1]:.0f}) nearest printed {best_v}")
            walk.append([round(e["len"], 2), e["dir"], "UNPRINTED"])
        else:
            walk.append([best_v, e["dir"]])
    origin = min(pts, key=lambda p: (p[1], p[0]))
    return walk, misses, origin


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

    transform = register(shot, sheet, page, np, cv2)
    if transform is None:
        return 1

    import fitz
    doc = fitz.open(PLAN)
    ppf = eng.detect_scale(doc[page])["ppf"]
    pool = {"H": set(), "V": set()}
    for ch in eng.read_dimension_chains(doc[page], ppf):
        pool[ch["orient"]].update(ch["runs"])
        pool[ch["orient"]].add(ch["total"])
    doc.close()

    loops = magenta_contours(shot, len(components), np, cv2)
    if len(loops) < len(components):
        print(f"REFUSED: {len(components)} component(s) requested but only "
              f"{len(loops)} magenta loop(s) found")
        return 1

    declared, failures = [], []
    for component, ap_loop in zip(components, loops):
        print(f"\n-- {component} --")
        walk, misses, origin = contour_to_walk(ap_loop, transform, page, pool, ppf)
        for w in walk:
            print("  ", w)
        if misses:
            failures.append(component)
            print("REFUSED to declare — legs with no printed value:")
            for m in misses:
                print("  ?", m)
            continue
        po = eng.polygon_outline([(w[0], w[1]) for w in walk])
        print(f"walk: {po['area_sf']} SF, perim {po['perimeter_lf']} LF, "
              f"closure {po['closure_err_ft']} ft")
        if po["closure_err_ft"] > 0.5:
            failures.append(component)
            print("REFUSED: printed legs do not close — a jog is mis-snapped")
            continue
        # area-order mapping is only trusted when the walk is in the same ballpark
        # as the component's own pixel trace — a garage loop declared as the porch
        # would sail through chains and closure, so this is the gate that catches it.
        if len(components) > 1:
            ref = traced_primary_sf(component)
            if ref and abs(po["area_sf"] - ref) / ref > 0.25:
                failures.append(component)
                print(f"REFUSED: walk {po['area_sf']:.0f} SF is {abs(po['area_sf']-ref)/ref:.0%} "
                      f"from {component}'s traced {ref:.0f} SF — loop/component "
                      f"mapping is not trustworthy")
                continue
        declared.append({"name": component, "page": page,
                         "walk": [[w[0], w[1]] for w in walk],
                         "origin_pt": [round(origin[0], 2), round(origin[1], 2)],
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
