#!/usr/bin/env python
"""Propose printed-dims WALKS for the Roberts area components (cal #66 bootstrap).

Method — the estimator's move, automated: the pixel trace knows the SHAPE (corner
topology), the sheet's chains know the TRUE LENGTHS. So: rectilinearize each traced
polygon, snap every edge to the nearest printed chain value ON ITS AXIS, and report
per leg: traced ft, printed ft, delta, matched-or-not. A leg that snaps nowhere is a
QUESTION for Jason (teach card), never a fudge. Closure of the snapped walk is the
coherence check — if the printed values don't close, the snapping is wrong somewhere
and the walk is NOT declared.

Output: proposed_walks.json next to this script — consumed as teach cards by the
viewer and, once confirmed, as verification specs by run_prebid.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import jnj_takeoff as eng  # noqa: E402

PLAN = os.path.join(ROOT, "tools", "tests", "golden", "roberts", "plan.pdf")
SNAP_TOL_FT = 0.45   # dim-line reference vs traced wall face can differ by inches


def rectilinear_edges(points, ppf):
    """Traced polygon -> ordered rectilinear edges [(len_ft, dir, (x0,y0),(x1,y1))].
    Near-axis edges snap to their axis; short jitters (<0.6 ft) merge into the
    previous edge; a genuinely diagonal edge is kept and flagged (dir '?')."""
    edges = []
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = (dx * dx + dy * dy) ** 0.5 / ppf
        if L < 0.05:
            continue
        if abs(dx) >= 3 * abs(dy):
            d = "R" if dx > 0 else "L"
        elif abs(dy) >= 3 * abs(dx):
            d = "D" if dy > 0 else "U"
        else:
            d = "?"
        edges.append({"len_ft": L, "dir": d, "a": (x0, y0), "b": (x1, y1)})
    # merge micro-edges into their predecessor (approxPolyDP jitter)
    merged = []
    for e in edges:
        if merged and (e["len_ft"] < 0.6 or e["dir"] == merged[-1]["dir"]):
            merged[-1]["len_ft"] += e["len_ft"] if e["dir"] == merged[-1]["dir"] else 0
            merged[-1]["b"] = e["b"]
        else:
            merged.append(dict(e))
    return merged


def main():
    import fitz
    with open(os.path.join(HERE, "evidence", "takeoff_evidence.json"),
              encoding="utf-8") as fh:
        ev = json.load(fh)
    doc = fitz.open(PLAN)
    out = {"schema": "roberts.proposed_walks.v1", "components": []}
    for comp in ev["area_certification"]["components"]:
        prim = comp["primary"]
        page = doc[prim["page"]]
        ppf = prim["ppf"]
        chains = eng.read_dimension_chains(page, ppf)
        pool = {"H": set(), "V": set()}
        for c in chains:
            pool[c["orient"]].update(c["runs"])
            pool[c["orient"]].add(c["total"])
        g = prim.get("geometry")
        if not g:
            out["components"].append({"name": comp["name"], "status": "no geometry"})
            continue
        edges = rectilinear_edges(g["points"], ppf)
        axis = {"R": "H", "L": "H", "U": "V", "D": "V"}
        legs, questions = [], []
        for e in edges:
            if e["dir"] == "?":
                questions.append(f"diagonal edge ~{e['len_ft']:.1f} ft at "
                                 f"({e['a'][0]:.0f},{e['a'][1]:.0f}) — trace defect "
                                 f"or real angled wall?")
                legs.append({"traced_ft": round(e["len_ft"], 2), "dir": "?",
                             "printed_ft": None, "at": e["a"]})
                continue
            cand = pool[axis[e["dir"]]]
            best = min(cand, key=lambda v: abs(v - e["len_ft"])) if cand else None
            hit = best is not None and abs(best - e["len_ft"]) <= SNAP_TOL_FT
            legs.append({"traced_ft": round(e["len_ft"], 2), "dir": e["dir"],
                         "printed_ft": best if hit else None,
                         "delta_ft": round(best - e["len_ft"], 2) if hit else None,
                         "at": [round(v, 1) for v in e["a"]]})
            if not hit:
                questions.append(f"{e['dir']} edge traced {e['len_ft']:.2f} ft at "
                                 f"({e['a'][0]:.0f},{e['a'][1]:.0f}) matches no "
                                 f"printed dim (nearest {best})")
        walk = [[l["printed_ft"], l["dir"]] for l in legs if l["printed_ft"]]
        closure = None
        area = None
        if len(walk) == len(legs) and len(walk) >= 3:
            po = eng.polygon_outline(walk)
            closure = po["closure_err_ft"]
            area = po["area_sf"]
        origin = min(g["points"], key=lambda p: (p[1], p[0]))
        out["components"].append({
            "name": comp["name"],
            "classification": comp["classification"],
            "page": prim["page"],
            "traced_primary_sf": prim["qty"],
            "traced_verification_sf": comp["verification"]["qty"],
            "proposed_walk": walk if len(walk) == len(legs) else None,
            "walk_area_sf": area,
            "walk_closure_ft": closure,
            "origin_pt": [round(origin[0], 2), round(origin[1], 2)],
            "legs": legs,
            "questions": questions,
            # the teach UI offers these as the pick-list: every printed value the
            # sheet's own chains validate, per axis — an answer can only ever BE a
            # printed number (the fail-closed contract, now in the UI)
            "printed_pool": {k: sorted(v) for k, v in pool.items()},
        })
    doc.close()
    path = os.path.join(HERE, "proposed_walks.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    for c in out["components"]:
        print(f"\n== {c['name']}  (traced primary {c.get('traced_primary_sf')} SF)")
        if c.get("proposed_walk"):
            print(f"   walk of {len(c['proposed_walk'])} printed legs -> "
                  f"{c['walk_area_sf']} SF, closure {c['walk_closure_ft']} ft")
        else:
            print(f"   INCOMPLETE — {sum(1 for l in c.get('legs', []) if not l.get('printed_ft'))} "
                  f"of {len(c.get('legs', []))} legs unmatched")
        for q in c.get("questions", []):
            print(f"   ? {q}")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
