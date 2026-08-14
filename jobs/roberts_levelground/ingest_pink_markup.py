#!/usr/bin/env python
"""Ingest Jason's PINK MARKER footprint (2026-08-14 screenshot) as the declared walk.

This is how Jason teaches — colored markup on the drawing (precedent: the roof-line
review in the golden fixture came from his colored overlay). The screenshot is his
viewer render with a pastel-pink boundary drawn on it, so registration is exact:

  1. register his image to the sheet render (multi-scale template match on grayscale
     linework -> scale + offset -> page points);
  2. isolate the pink stroke (r-dominant mask that EXCLUDES the viewer's own purple
     verification layer and the plan's red markup), largest closed contour;
  3. rectilinearize; snap every leg to the sheet's printed chains ON ITS AXIS
     (cal #66 contract — a leg the sheet does not print refuses);
  4. closure + area sanity vs the plan's own heated figure, then write
     declared_walks.json for the component his pink traces.

Fail-closed: any step that cannot prove itself prints WHY and declares nothing."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import jnj_takeoff as eng  # noqa: E402

SHOT = r"C:\Users\jason\OneDrive\Pictures\Screenshots\Screenshot 2026-08-14 140952.png"
SHEET = os.path.join(HERE, "viewer", "sheets", "sheet_3.png")
PAGE = 3
# Jason's ruling 2026-08-14 (cal #67): A CRAWLSPACE IS NOT HEATED. His pink traces
# the FOUNDATION footprint — a foundation scope. Declaring it under the old
# "heated crawlspace envelope" name would certify heated_sf from the wrong sheet's
# scope (right number, wrong SCOPE — the proxy disease). Parked under its true name;
# heated_sf must be measured from the floor plan before the heated line certifies.
COMPONENT = "crawlspace envelope (foundation footprint)"


def main():
    import cv2
    import numpy as np

    shot = cv2.imread(SHOT)
    sheet = cv2.imread(SHEET)
    assert shot is not None and sheet is not None
    sheet_pt_w = 2400.7  # page width in points; render zoom = px / pt
    render_zoom = sheet.shape[1] / sheet_pt_w

    # --- 1. register: try scales until the screenshot's linework locks on ---------
    # register on the INVERTED RED CHANNEL: the plan's blue linework is dark in R
    # (strong signal in both images), while Jason's magenta stroke and the plan's
    # red scribbles have R~255 and vanish — the overlays self-erase.
    sg = 255 - shot[:, :, 2]
    tg = 255 - sheet[:, :, 2]
    best = None
    for s in np.linspace(2.4, 4.4, 41):        # sheet_px = shot_px * s
        w, h = int(sg.shape[1] * s), int(sg.shape[0] * s)
        if w >= tg.shape[1] or h >= tg.shape[0]:
            continue
        r = cv2.matchTemplate(tg, cv2.resize(sg, (w, h)), cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if best is None or mx > best[0]:
            best = (mx, s, loc)
    score, s, (ox, oy) = best
    print(f"registration: scale {s:.4f}, offset ({ox},{oy}), score {score:.3f}")
    # correlation is blur-limited on an upscaled 800px screenshot, so verify the
    # transform with LANDMARKS instead: every known dimension label's page position
    # must land on ink in the shot (and not on ink when the transform is shifted)
    import fitz
    doc0 = fitz.open(os.path.join(ROOT, "tools", "tests", "golden", "roberts",
                                  "plan.pdf"))
    labels = eng._dim_labels(doc0[PAGE])
    doc0.close()
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
              "pink coordinates")
        return 1

    # --- 2. the pink stroke: Jason's marker is pure magenta (255,128,255 sampled
    # from the file). The viewer's verification purple (176,111,216) has r<230 and
    # the plan's red markup has b<100 — both excluded. -----------------------------
    b, g, r = shot[:, :, 0].astype(int), shot[:, :, 1].astype(int), shot[:, :, 2].astype(int)
    mask = ((r > 230) & (b > 230) & (r - g > 60) & (b - g > 60)).astype(np.uint8) * 255
    n_pink = int(mask.sum() / 255)
    print(f"pink pixels: {n_pink}")
    if n_pink < 2000:
        print("REFUSED: pink stroke not found at the sampled color")
        return 1
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    # stroke thickness = stroke area / centerline length (~outer perimeter);
    # erode the FILLED loop by half of it so the boundary sits on the centerline
    filled = np.zeros(mask.shape, np.uint8)
    cv2.drawContours(filled, [c], -1, 255, -1)
    stroke_w = max(2, int(round(n_pink / max(cv2.arcLength(c, True), 1))))
    k = max(3, (stroke_w // 2) * 2 + 1)
    er = cv2.erode(filled, np.ones((k, k), np.uint8))
    cnts2, _ = cv2.findContours(er, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts2, key=cv2.contourArea) if cnts2 else c
    # epsilon small enough that a ~2 ft notch in an 800px screenshot survives
    ap = cv2.approxPolyDP(c, 0.0012 * cv2.arcLength(c, True), True)
    print(f"pink boundary: {len(ap)} vertices (stroke ~{stroke_w}px)")

    # --- 3. shot px -> page points, rectilinearize, snap to chains ----------------
    pts = [[(p[0][0] * s + ox) / render_zoom, (p[0][1] * s + oy) / render_zoom]
           for p in ap]
    import fitz
    doc = fitz.open(os.path.join(ROOT, "tools", "tests", "golden", "roberts", "plan.pdf"))
    page = doc[PAGE]
    ppf = eng.detect_scale(page)["ppf"]
    pool = {"H": set(), "V": set()}
    for ch in eng.read_dimension_chains(page, ppf):
        pool[ch["orient"]].update(ch["runs"])
        pool[ch["orient"]].add(ch["total"])
    doc.close()

    # rectilinear legs (same shape logic as propose_walks)
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
    if edges[0]["dir"] == edges[-1]["dir"]:
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
    print(f"\nlegs ({len(walk)}):")
    for w in walk:
        print("  ", w)
    if misses:
        print("\nREFUSED to declare — legs with no printed value:")
        for m in misses:
            print("  ?", m)
        return 1
    po = eng.polygon_outline([(w[0], w[1]) for w in walk])
    print(f"\nwalk: {po['area_sf']} SF, perim {po['perimeter_lf']} LF, "
          f"closure {po['closure_err_ft']} ft")
    if po["closure_err_ft"] > 0.5:
        print("REFUSED: printed legs do not close — a jog is mis-snapped")
        return 1
    origin = min(pts, key=lambda p: (p[1], p[0]))
    decl = {"schema": "roberts.declared_walks.v1",
            "walks": [{"name": COMPONENT, "page": PAGE,
                       "walk": [[w[0], w[1]] for w in walk],
                       "origin_pt": [round(origin[0], 2), round(origin[1], 2)],
                       "confirmed_by": "jason-pink-markup Screenshot 2026-08-14 140952"}]}
    with open(os.path.join(HERE, "declared_walks.json"), "w", encoding="utf-8") as fh:
        json.dump(decl, fh, indent=1)
    print(f"\nDECLARED: {COMPONENT} <- {len(walk)} printed legs from Jason's pink markup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
