#!/usr/bin/env python
"""Virtual takeoff (2026-08-14): every measured line carries a stable id and, where the
tracer produced one, its polygon in PAGE POINTS — and the polygon must REPRODUCE the
number it rides with.

Why the checks look the way they do:
  - shoelace(points)/ppf^2 vs qty catches a zoom/scale slip in the pixel->page mapping;
  - vertex containment (in-page here, in-clip inside the engine) catches a TRANSLATION
    slip, which area alone cannot see — a polygon missing its clip offset has exactly
    the right SF in exactly the wrong place;
  - the main wall loop must sit inside the enclosed-region polygon's bbox — the two
    tracers measure the same foundation through different frames (clip-relative canvas
    vs clipped pixmap), so agreement here proves both mappings, not one;
  - a run WITHOUT evidence_dir must behave exactly as before (same lines, same ids —
    ids are content-derived, so this also proves they are deterministic).

Coordinate frame under test: PDF points, origin top-left, y-down, 0-based page index —
the same frame the roof-line review already persists in roberts/expected.yaml.
"""

import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402

ROBERTS = os.path.join(HERE, "golden", "roberts", "plan.pdf")
SHEETS = {"foundation": 3, "slab": 3, "slab_boundary": "solid", "roof": 6}


def line(result, trade):
    return next((ln for ln in result["lines"] if ln["trade"] == trade), None)


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    import fitz
    tmp = tempfile.mkdtemp(prefix="takeoff-evidence-")
    r = eng.run_takeoff(ROBERTS, dict(SHEETS), evidence_dir=tmp)

    # --- ids: present on every line, unique -------------------------------------------
    ids = [ln.get("id") for ln in r["lines"]]
    assert all(ids), [ln["trade"] for ln in r["lines"] if not ln.get("id")]
    assert len(set(ids)) == len(ids), "duplicate measurement ids"

    # --- geometry integrity on every line that carries one ----------------------------
    doc = fitz.open(ROBERTS)
    page_rects = [p.rect for p in doc]
    doc.close()
    with_geom = [ln for ln in r["lines"] if ln.get("geometry")]
    assert with_geom, "no measured line carried geometry"
    for ln in with_geom:
        g = ln["geometry"]
        assert g["kind"] == "polygon" and len(g["points"]) >= 3, (ln["trade"], g)
        pr = page_rects[ln["page"]]
        for x, y in g["points"]:
            assert -1 <= x <= pr.width + 1 and -1 <= y <= pr.height + 1, \
                f"{ln['trade']}: vertex ({x}, {y}) outside page {ln['page']}"
        ppf = r["pages"][ln["page"]]["ppf"]
        area_pt2, perim_pt = eng._poly_area_perim_pts(g["points"])
        if "area_sf" in g:
            err = abs(area_pt2 / ppf ** 2 - g["area_sf"])
            assert err <= max(0.5, g["area_sf"] * 0.01), \
                f"{ln['trade']}: polygon {area_pt2 / ppf ** 2:.1f} SF vs {g['area_sf']}"
        if "perim_lf" in g:
            err = abs(perim_pt / ppf - g["perim_lf"])
            assert err <= max(0.2, g["perim_lf"] * 0.01), \
                f"{ln['trade']}: polygon {perim_pt / ppf:.1f} LF vs {g['perim_lf']}"

    # --- the specific trades must reproduce the LINE qty from their own polygon --------
    fnd = line(r, "foundation_wall_lf")
    assert fnd and fnd.get("geometry"), "foundation_wall_lf has no geometry"
    ppf = r["pages"][fnd["page"]]["ppf"]
    _, perim_pt = eng._poly_area_perim_pts(fnd["geometry"]["points"])
    assert abs(perim_pt / ppf - fnd["qty"]) <= fnd["qty"] * 0.01, \
        f"foundation polygon {perim_pt / ppf:.1f} LF vs line qty {fnd['qty']}"
    slab = line(r, "slab_area_sf")
    assert slab and slab["method"] == "clean-tracer" and slab.get("geometry"), slab
    area_pt2, _ = eng._poly_area_perim_pts(slab["geometry"]["points"])
    assert abs(area_pt2 / ppf ** 2 - slab["qty"]) <= slab["qty"] * 0.01, \
        f"slab polygon {area_pt2 / ppf ** 2:.1f} SF vs line qty {slab['qty']}"

    # --- cross-frame translation proof: wall loop inside the enclosed region ----------
    loop = line(r, "foundation_main_loop_lf")
    loop_checked = False
    if loop and loop.get("geometry") and fnd.get("geometry"):
        lx0, ly0, lx1, ly1 = bbox(loop["geometry"]["points"])
        rx0, ry0, rx1, ry1 = bbox(fnd["geometry"]["points"])
        pad = 3.0 * ppf  # same growth allowance the engine's containment check uses
        assert (rx0 - pad <= lx0 and ly0 >= ry0 - pad and
                lx1 <= rx1 + pad and ly1 <= ry1 + pad), \
            f"wall loop bbox {(lx0, ly0, lx1, ly1)} escapes region bbox " \
            f"{(rx0, ry0, rx1, ry1)} — one of the two pixel frames is mismapped"
        loop_checked = True

    # --- roof_lines block: classified segments, page points, engine LF totals ---------
    rl = r.get("roof_lines")
    assert rl and rl["page"] == 6, "roof_lines block missing (roof mapped at index 6)"
    n_segs = sum(len(v) for v in rl["roles"].values())
    assert n_segs >= 20, f"only {n_segs} classified roof segments"
    pr = page_rects[6]
    for role, segs in rl["roles"].items():
        for s in segs:
            x0, y0, x1, y1 = s["seg"]
            for x, y in ((x0, y0), (x1, y1)):
                assert -1 <= x <= pr.width + 1 and -1 <= y <= pr.height + 1, \
                    f"roof {role} endpoint ({x}, {y}) outside page"
    assert rl["lf"].get("fascia_lf"), rl["lf"]

    # --- the persisted evidence file ---------------------------------------------------
    path = os.path.join(tmp, "takeoff_evidence.json")
    assert os.path.exists(path), "takeoff_evidence.json was not written"
    with open(path, encoding="utf-8") as fh:
        ev = json.load(fh)
    assert ev["schema"] == eng.TAKEOFF_EVIDENCE_SCHEMA
    assert ev["coordinate_frame"].startswith("pdf-points"), ev["coordinate_frame"]
    assert len(ev["measurements"]) == len(r["lines"])
    assert [m["id"] for m in ev["measurements"]] == ids
    h = hashlib.sha256()
    with open(ROBERTS, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    sha = h.hexdigest().upper()
    assert ev["plan_sha256"] == sha == r["plan_sha256"], "plan sha mismatch"
    ledger = {e["page"]: e for e in ev["sheet_ledger"]}
    assert 3 in ledger and ledger[3]["ppf"], ledger
    assert "foundation" in ledger[3]["roles"] and "slab" in ledger[3]["roles"]
    assert ev["roof_lines"] and ev["roof_lines"]["page"] == 6

    # --- without evidence_dir: no file, identical behavior, deterministic ids ----------
    r2 = eng.run_takeoff(ROBERTS, dict(SHEETS))
    assert "evidence_json" not in r2 and "plan_sha256" not in r2
    assert [(l["trade"], l["id"], l["qty"]) for l in r2["lines"]] == \
           [(l["trade"], l["id"], l["qty"]) for l in r["lines"]], \
        "evidence_dir changed the takeoff, or ids are not deterministic"

    print(f"PASS: {len(with_geom)}/{len(r['lines'])} lines carry page-point geometry that "
          f"reproduces its own qty; wall-loop-in-region cross-frame check "
          f"{'ran' if loop_checked else 'SKIPPED (no wall-pair loop on this sheet)'}; "
          f"{n_segs} roof segments in 5 roles; evidence JSON pinned to plan sha and "
          f"identical with/without persistence")


if __name__ == "__main__":
    main()
