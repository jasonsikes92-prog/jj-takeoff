#!/usr/bin/env python
"""cal #66 (Jason's ruling 2026-08-14): the sheet's OWN printed dimension chains,
walked into a closed outline, are an admitted area-gate verification measurement.

Why this exists: the three pixel methods measure different envelopes (outside face /
all ink / inside face — FINDINGS.md root cause), so requiring two of them to agree
within 2% could never pass on a real drawing. Printed numbers vs traced pixels are
genuinely different INPUTS (text layer vs ink raster) measuring the same thing — the
comparison a human estimator actually makes, and one a 2% gate can pass.

What must hold, on the real Roberts foundation sheet (p4, 0-based index 3):
  - a walk whose every leg is printed on the sheet, and which closes, returns the
    outline's area/perimeter and a polygon ANCHORED at origin_pt in page points;
  - a walk with one fabricated leg is REFUSED (a made-up walk cannot certify);
  - a walk that does not close is REFUSED;
  - the allow-lists admit the new method/origin so certification can accept it.

The walk here is the sheet's own two overall chain totals folded into a rectangle —
a mechanism proof, deliberately NOT a claim about the heated envelope. Real component
walks are DECLARED inputs read off the sheet (the pitch_calls / slab_boundary
contract), not something this test invents.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402

ROBERTS = os.path.join(HERE, "golden", "roberts", "plan.pdf")
PAGE = 3  # foundation/slab sheet


def main():
    import fitz
    doc = fitz.open(ROBERTS)
    page = doc[PAGE]
    sc = eng.detect_scale(page)
    # Roberts is THE print-rescaled fixture: ppf lands ~7.5% off every standard scale,
    # so detect_scale honestly says "review" — but the dim-voted ppf itself is solid
    # (86 votes on this sheet). That ppf is exactly what chain matching needs.
    assert sc["ppf"] and sc["votes"] >= 25, sc
    ppf = sc["ppf"]

    # the sheet's own printed overall dimensions become the declared walk
    overall = eng.overall_dims(page, ppf)
    assert overall["width_ft"] and overall["depth_ft"], overall
    W, D = overall["width_ft"][0], overall["depth_ft"][0]
    region = eng.find_drawing_region(page, ppf=ppf)
    assert region, "no drawing region on the foundation sheet"
    origin = [region["clip"].x0 + 2 * ppf, region["clip"].y0 + 2 * ppf]

    walk = [[W, "R"], [D, "D"], [W, "L"], [D, "U"]]
    r = eng.dims_outline_evidence(page, ppf, walk, origin)
    assert abs(r["area_sf"] - W * D) <= 0.5, (r["area_sf"], W * D)
    assert abs(r["perim_lf"] - 2 * (W + D)) <= 0.2
    assert r["closure_err_ft"] == 0.0
    assert all(c["ok"] for c in r["chain_checks"]), r["chain_checks"]
    # polygon anchored at origin, in page points, closed without a duplicate vertex
    pts = r["polygon_pts"]
    assert pts[0] == [round(origin[0], 3), round(origin[1], 3)]
    assert len(pts) == 4, f"rectangle should keep 4 vertices, got {len(pts)}"
    a_pt2, p_pt = eng._poly_area_perim_pts(pts)
    assert abs(a_pt2 / ppf ** 2 - r["area_sf"]) <= r["area_sf"] * 0.005

    # a fabricated leg must be refused — the sheet does not print 13.37
    try:
        eng.dims_outline_evidence(
            page, ppf, [[W, "R"], [13.37, "D"], [W, "L"], [13.37, "U"]], origin)
        raise AssertionError("fabricated leg was accepted")
    except ValueError as exc:
        assert "does not print" in str(exc), exc

    # a walk that does not close must be refused
    try:
        eng.dims_outline_evidence(
            page, ppf, [[W, "R"], [D, "D"], [W - 5.0, "L"], [D, "U"]], origin)
        raise AssertionError("non-closing walk was accepted")
    except ValueError as exc:
        assert "does not close" in str(exc), exc

    # --- cal #68 (Jason's ruling 2026-08-14): a leg the sheet does not print may be
    # marked derived-by-closure. The marker carries ZERO declarative freedom: the
    # value must equal what the other (all chain-verified) legs force through
    # closure (+/-0.05 ft), at most one per axis. ---------------------------------
    r68 = eng.dims_outline_evidence(
        page, ppf, [[W, "R"], [D, "D"], [W, "L"], [D, "U", "derived-by-closure"]],
        origin)
    assert abs(r68["area_sf"] - r["area_sf"]) <= 0.01
    d_checks = [c for c in r68["chain_checks"] if c.get("derived_by_closure")]
    assert len(d_checks) == 1 and d_checks[0]["ok"] \
        and d_checks[0]["printed_ft"] is None, d_checks

    # a derived value that is not the forced one is refused — note the walk still
    # CLOSES within 0.5 ft here, so this isolates the 0.05-ft forced-match gate
    try:
        eng.dims_outline_evidence(
            page, ppf,
            [[W, "R"], [D, "D"], [W, "L"], [D - 0.3, "U", "derived-by-closure"]],
            origin)
        raise AssertionError("non-forced derived leg was accepted")
    except ValueError as exc:
        assert "closure-forced" in str(exc), exc

    # a second derived leg on the same axis is refused
    try:
        eng.dims_outline_evidence(
            page, ppf,
            [[W, "R"], [D, "D", "derived-by-closure"], [W, "L"],
             [D, "U", "derived-by-closure"]], origin)
        raise AssertionError("two derived legs on one axis were accepted")
    except ValueError as exc:
        assert "one derived-by-closure leg per axis" in str(exc), exc

    # an unknown marker is refused, never silently ignored
    try:
        eng.dims_outline_evidence(
            page, ppf, [[W, "R"], [D, "D"], [W, "L"], [D, "U", "eyeballed"]], origin)
        raise AssertionError("unknown marker was accepted")
    except ValueError as exc:
        assert "unknown walk-leg marker" in str(exc), exc

    # allow-lists admit the method + origin (certification can accept dims evidence)
    assert "printed-dimension-chains" in eng._AREA_ENGINE_METHODS
    assert eng._AREA_DIMS_ORIGIN == "jnj_takeoff.plan-printed-dims.v1"
    assert eng._AREA_METHOD_ORIGINS["printed-dimension-chains"] == eng._AREA_DIMS_ORIGIN

    # --- the DISPATCH path (the production route, not the direct call): Roberts'
    # review-confidence scale must be ACCEPTED (leg verification is the scale
    # proof), no clip machinery may run, and the origin comes from the method map.
    # Regression: the pixel-grade scale gate + find_drawing_region once made this
    # path refuse the method on its own motivating fixture.
    import tempfile
    tmp = tempfile.mkdtemp(prefix="dims-dispatch-")
    ev = eng._measure_area_evidence(
        doc, {"page": PAGE, "method": "printed-dims", "walk": walk,
              "origin_pt": origin}, tmp, "dims-dispatch-check")
    assert ev["method"] == "printed-dimension-chains"
    assert ev["origin"] == eng._AREA_DIMS_ORIGIN
    assert ev["clip"] is None, "dims evidence must not carry a pixel clip"
    assert ev["geometry"] and ev["geometry"]["points"], ev.get("geometry_note")
    assert abs(ev["qty"] - r["area_sf"]) < 0.01
    assert os.path.exists(ev["view"]), "dims overlay PNG must exist (gate requires it)"

    # --- cal #69 dispatch: markup-raster measures the registered polygon in page
    # points; the ingest-time landmark oracle is its raster proof and refusing
    # without it is the fail-closed contract. -------------------------------------
    rect = [[origin[0], origin[1]],
            [origin[0] + W * ppf, origin[1]],
            [origin[0] + W * ppf, origin[1] + D * ppf],
            [origin[0], origin[1] + D * ppf]]
    ev2 = eng._measure_area_evidence(
        doc, {"page": PAGE, "method": "markup-raster", "polygon_pts": rect,
              "registration": {"landmark_rate": 1.0, "landmark_n": 50,
                               "landmark_control": 0.2}},
        tmp, "markup-dispatch-check")
    assert ev2["method"] == "markup-raster"
    assert ev2["origin"] == eng._AREA_MARKUP_ORIGIN
    assert abs(ev2["qty"] - W * D) <= W * D * 0.01, (ev2["qty"], W * D)
    assert ev2["clip"] is None, "markup evidence must not carry a pixel clip"
    assert os.path.exists(ev2["view"]), "markup overlay PNG must exist"
    try:
        eng._measure_area_evidence(
            doc, {"page": PAGE, "method": "markup-raster", "polygon_pts": rect},
            tmp, "markup-noproof")
        raise AssertionError("markup without landmark proof was accepted")
    except ValueError as exc:
        assert "landmark" in str(exc), exc
    try:
        eng._measure_area_evidence(
            doc, {"page": PAGE, "method": "markup-raster", "polygon_pts": rect,
                  "registration": {"landmark_rate": 0.5, "landmark_n": 50,
                                   "landmark_control": 0.2}},
            tmp, "markup-weakproof")
        raise AssertionError("markup with a failing landmark oracle was accepted")
    except ValueError as exc:
        assert "landmark oracle" in str(exc), exc

    doc.close()
    print(f"PASS: printed-dims outline on Roberts p{PAGE + 1} — walk {W} x {D} ft from "
          f"the sheet's own chains -> {r['area_sf']} SF anchored in page points; "
          f"axis-checked legs; fabricated leg refused, open walk refused; cal #68 "
          f"derived-by-closure admitted only at the forced value, one per axis; "
          f"dispatch path accepts review-confidence scale with no clip machinery")


if __name__ == "__main__":
    main()
