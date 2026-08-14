#!/usr/bin/env python
"""ROBERTS -> LEVEL GROUND PRE-BID: the first end-to-end run of the real chain.

Until now `run_takeoff()` had exactly one call site in this repo -- test_dugger_fail_closed.py,
which asserts it REFUSES to answer -- and `levelground/gen_reports.py` injected a hardcoded
sample takeoff. So `run_takeoff -> report_from_takeoff` had never executed on a real plan set.
This script is that run.

Roberts is the right set for it: a real 12-sheet vector set that is ALSO the print-rescaled one
(p5 measures 16.714 pt/ft while its own title block says 1/4"=1' = 18.0), so a single pass
exercises the scale guard, the sheet ledger, the area gate, and the report adapter.

Everything printed is measured at runtime. Nothing here is hand-fed except WHERE to look
(sheet indices, component clips derived from the engine's own wall-loop decomposition) and the
roof pitch callouts, which cal #43 forbids taking from raw OCR -- these are read from the
sheet's TEXT layer and eye-verified against the rendered sheet.

Usage:  python jobs/roberts_levelground/run_prebid.py [--evidence DIR]
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))

import fitz  # noqa: E402
import jnj_takeoff as eng  # noqa: E402

PLAN = os.path.join(REPO, "tools", "tests", "golden", "roberts", "plan.pdf")

# --- SHEET LEDGER ---------------------------------------------------------------------
# Every page examined and classified before anything is measured (feedback: enumerate every
# sheet; never claim a scope is absent from a partial look). Page numbers here are 0-BASED
# INDICES -- the fixture's expected.yaml comments use the same convention despite saying "pN".
SHEET_LEDGER = {
    0: "cover / index of drawings / project summary",
    1: "site plan (topo, gravel drive)",
    2: "SQFT PLANS -- the AREAS table (comparison-only) + colour-coded area diagram",
    3: "FOUNDATION WALL PLAN -- crawlspace + slab garage + slab porch",
    4: "MASTER FLOOR PLAN (redlined)",
    5: "framing / header schedule",
    6: "ROOF PLAN",
    7: "electrical",
    8: "elevations -- front / rear",
    9: "elevations -- right / left",
    10: "interior elevations + cabinet elevations",
    11: "renderings",
}

SHEET_MAP = {
    "sqft_schedule": 2,
    "foundation": 3,
    "roof": 6,
    "floor_area": 4,  # MASTER FLOOR PLAN — the sheet heated SF must come from (cal #67)
    # NO "slab" key on purpose, and the reason is SCOPE, not the tracer. Roberts is a
    # CRAWLSPACE house with a slab garage and a slab porch -- its slab scope is 707 + 201 SF,
    # not a whole-footprint sheet. Pointing "slab" at the foundation sheet traces the entire
    # building and calls it slab area: the wrong QUANTITY even now that the trace is right.
    # The tracer-choice bug this run exposed (FINDINGS.md defect 1) is FIXED -- cal #46 is now
    # a declared `slab_boundary` input, proven on both houses in
    # tools/tests/test_slab_boundary_style.py. Declaring "solid" here would return 3,066.7 SF,
    # a correct measurement of the whole foundation footprint.
}

NOMINAL_PPF = 18.0  # what the title block claims (1/4"=1'). NEVER measure with it -- see below.


def sheet_ledger(doc):
    """Examine every page: classification + the scale the sheet's own dimensions support."""
    rows = []
    for i in range(doc.page_count):
        sc = eng._page_scale(doc[i])
        rows.append({
            "index": i,
            "sheet": SHEET_LEDGER.get(i, "UNCLASSIFIED"),
            "ppf": round(sc["ppf"], 3) if sc else None,
            "scale_confidence": sc["confidence"] if sc else None,
            "scale_method": sc["method"] if sc else None,
        })
    unclassified = [r for r in rows if r["sheet"] == "UNCLASSIFIED"]
    if unclassified:
        raise SystemExit(f"sheet ledger incomplete: {[r['index'] for r in unclassified]}")
    return rows


def scale_guard(rows):
    """The print-rescale check. 1 set in 6 is printed off-nominal and nothing discloses it."""
    out = []
    for r in rows:
        if not r["ppf"]:
            continue
        # Measuring with the nominal 18.0 divides by too large a scale, so every area comes
        # out SHORT. Report the shortfall you would ship, signed the way it hurts.
        shortfall = (r["ppf"] / NOMINAL_PPF) ** 2 - 1.0
        out.append({**r, "area_shortfall_pct_if_nominal": round(shortfall * 100, 1)})
    return out


def scale_checks(page, ppf, want=2, min_ft=10.0):
    """Two printed dimensions whose drawn span reproduces `ppf` -> certify_explicit_scale().

    This is a CONSISTENCY proof, not an independent derivation: ppf comes from the sheet's own
    multi-vote dimension cluster (calibrate_scale), and each check confirms that a specific
    named printed dimension measures what that ppf says it should. That is the fail-closed
    requirement for a sheet whose measured scale does not snap to a standard one.
    """
    segs = eng._lines(page)
    H = [(min(s[0], s[2]), max(s[0], s[2]), s[1]) for s in segs if abs(s[3] - s[1]) < 1.0]
    V = [(min(s[1], s[3]), max(s[1], s[3]), s[0]) for s in segs if abs(s[2] - s[0]) < 1.0]
    found = []
    for w in page.get_text("words"):
        val = eng.parse_dim(w[4])
        if not val or val < min_ft:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        best = None
        # horizontal: nearest vertical witness ticks straddling the text
        left = sorted((cx - x, x) for lo, hi, x in V if lo - 4 <= cy <= hi + 4 and x < cx)
        right = sorted((x - cx, x) for lo, hi, x in V if lo - 4 <= cy <= hi + 4 and x > cx)
        for _, xl in left[:4]:
            for _, xr in right[:4]:
                span = xr - xl
                if span > 3 and (best is None or abs(span / val - ppf) < abs(best / val - ppf)):
                    best = span
        # vertical: nearest horizontal witness ticks above/below
        up = sorted((cy - y, y) for lo, hi, y in H if lo - 4 <= cx <= hi + 4 and y < cy)
        dn = sorted((y - cy, y) for lo, hi, y in H if lo - 4 <= cx <= hi + 4 and y > cy)
        for _, yu in up[:4]:
            for _, yd in dn[:4]:
                span = yd - yu
                if span > 3 and (best is None or abs(span / val - ppf) < abs(best / val - ppf)):
                    best = span
        if best is None:
            continue
        err = abs(best / val - ppf) / ppf
        if err <= 0.01:
            found.append({"label": w[4].strip(), "printed_ft": val, "measured_points": round(best, 2),
                          "err_pct": round(err * 100, 2)})
    found.sort(key=lambda c: -c["printed_ft"])          # longest dims are the most reliable
    return [{k: c[k] for k in ("label", "printed_ft", "measured_points")} for c in found[:want]]


def area_components(doc, page_index, ppf, pad_ft=1.5):
    """WHERE each area component is -- from the engine's own paired-wall loop decomposition,
    not from an eyeballed rectangle. Returns [(name, classification, clip)] largest first."""
    page = doc[page_index]
    base = eng.find_drawing_region(page, ppf=ppf, pad_ft=2.0)["clip"]
    loops = eng.foundation_wall_loops(page, ppf=ppf, close_ft=2.0)
    # This set's foundation sheet resolves exactly three enclosed loops, in area order:
    # the crawlspace envelope, the garage slab, the front porch slab.
    # cal #67: everything this sheet yields is FOUNDATION/slab scope. The crawlspace
    # envelope was previously classified "heated" — right number (1.5% from the plan's
    # figure), wrong SCOPE. Heated SF must come off the floor plan (SHEET_MAP
    # "floor_area"), and HOW Jason reads heated off that sheet is undeclared teach-mode
    # work — so no heated component exists yet and the area gate reports it honestly.
    # The component name matches declared_walks.json exactly, so Jason's pink-markup
    # walk wires in as the printed-dims verification below.
    naming = [("crawlspace envelope (foundation footprint)", "foundation"),
              ("garage slab", "garage"),
              ("front porch slab", "covered")]
    out = []
    for (name, klass), L in zip(naming, loops):
        cx, cy = L["centroid_ft"]
        w, h = L["bbox_ft"]
        clip = [base.x0 + (cx - w / 2 - pad_ft) * ppf, base.y0 + (cy - h / 2 - pad_ft) * ppf,
                base.x0 + (cx + w / 2 + pad_ft) * ppf, base.y0 + (cy + h / 2 + pad_ft) * ppf]
        out.append({"name": name, "classification": klass, "clip": clip,
                    "inside_face_sf": round(L["area_sf"], 1), "loop_perim_lf": round(L["perim_lf"], 1)})
    return out


def evidence_sweep(doc, page_index, ppf, comps):
    """What each certification-accepted tracer returns for each component, at three clip pads.
    Clip-invariance is the plateau test the engine already uses (holbrook cal #26b, lankford)."""
    page = doc[page_index]
    base = eng.find_drawing_region(page, ppf=ppf, pad_ft=2.0)["clip"]
    loops = eng.foundation_wall_loops(page, ppf=ppf, close_ft=2.0)
    table = []
    for comp, L in zip(comps, loops):
        cx, cy = L["centroid_ft"]
        w, h = L["bbox_ft"]
        row = {"component": comp["name"], "inside_face_sf": comp["inside_face_sf"], "by_pad": {}}
        for pad in (1.5, 3.0, 5.0):
            clip = fitz.Rect(base.x0 + (cx - w / 2 - pad) * ppf, base.y0 + (cy - h / 2 - pad) * ppf,
                             base.x0 + (cx + w / 2 + pad) * ppf, base.y0 + (cy + h / 2 + pad) * ppf)
            cell = {}
            for tag, fn in (("clean", lambda c: eng.trace_footprint_clean(page, clip=c, ppf=ppf)),
                            ("all-ink", lambda c: eng.trace_footprint(page, c, ppf=ppf)),
                            ("enclosed", lambda c: eng.trace_enclosed_region(page, c, ppf=ppf,
                                                                            prefer="largest"))):
                try:
                    r = fn(clip)
                    cell[tag] = round(r["area_sf"], 1) if r else None
                except Exception as exc:                       # a tracer that dies is data too
                    cell[tag] = f"ERR {type(exc).__name__}"
            row["by_pad"][str(pad)] = cell
        table.append(row)
    return table


def pitch_calls(doc, page_index):
    """Roof pitch callouts from the sheet's TEXT layer, with positions, as
    [(x_pt, y_pt, rise_over_12)]. cal #43 forbids raw OCR here; this set carries real text,
    and the values were eye-verified against the rendered roof plan (12:12 majority, three
    8:12, one 3:12 -- note the fixture comment says only '12:12 + 8:12')."""
    page = doc[page_index]
    calls, pending = [], []
    for w in page.get_text("words"):
        pending.append(w)
    text_items = []
    for w in pending:
        t = w[4].strip()
        if t.isdigit():
            text_items.append((int(t), (w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
    # callouts render as three words: rise, ':', 12  -- pair a rise with the '12' to its right
    for rise, x, y in text_items:
        if rise == 12 and any(abs(y - y2) < 3 and 0 < x - x2 < 40 and r2 != 12
                              for r2, x2, y2 in text_items):
            continue
        near_run = [(r2, x2, y2) for r2, x2, y2 in text_items
                    if r2 == 12 and abs(y - y2) < 3 and 0 < x2 - x < 40]
        if near_run and rise in (3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16):
            calls.append((round(x, 1), round(y, 1), rise))
    return calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=os.path.join(HERE, "evidence"))
    args = ap.parse_args()
    os.makedirs(args.evidence, exist_ok=True)

    t_start = time.time()
    doc = fitz.open(PLAN)

    print("=" * 78)
    print("SHEET LEDGER -- every page examined before anything is measured")
    print("=" * 78)
    rows = sheet_ledger(doc)
    for r in rows:
        ppf = f"{r['ppf']:.3f}" if r["ppf"] else "   --  "
        print(f"  idx {r['index']:>2}  ppf {ppf}  {str(r['scale_confidence'] or '-'):<7}  {r['sheet']}")

    print("\n" + "=" * 78)
    print("SCALE GUARD -- what trusting the 1/4\"=1' title block would cost")
    print("=" * 78)
    guarded = scale_guard(rows)
    for g in guarded:
        print(f"  idx {g['index']:>2}  measured {g['ppf']:.3f} pt/ft   "
              f"areas land {g['area_shortfall_pct_if_nominal']:+.1f}% if measured at 18.000")

    f_idx = SHEET_MAP["foundation"]
    f_ppf = next(r["ppf"] for r in rows if r["index"] == f_idx)
    checks = scale_checks(doc[f_idx], f_ppf)
    print(f"\n  foundation sheet explicit-scale checks (idx {f_idx}, ppf {f_ppf:.3f}):")
    for c in checks:
        print(f"    {c['label']:<14} printed {c['printed_ft']:.2f} ft  "
              f"drawn {c['measured_points']:.2f} pt  -> {c['measured_points']/c['printed_ft']:.3f} pt/ft")
    verdict = eng.certify_explicit_scale(f_ppf, checks)
    print(f"    certify_explicit_scale: ok={verdict['ok']}  {verdict.get('errors') or ''}")

    print("\n" + "=" * 78)
    print("AREA COMPONENTS -- located by the engine's own wall-loop decomposition")
    print("=" * 78)
    comps = area_components(doc, f_idx, f_ppf)
    for c in comps:
        print(f"  {c['name']:<28} {c['classification']:<8} inside-face {c['inside_face_sf']:>7.1f} sf "
              f"({c['loop_perim_lf']:.1f} LF loop)")

    print("\n  tracer evidence (clip-invariance is the plateau test):")
    table = evidence_sweep(doc, f_idx, f_ppf, comps)
    for row in table:
        print(f"    {row['component']}")
        for pad, cell in row["by_pad"].items():
            print(f"      pad {pad:>4} ft   " + "   ".join(f"{k}={v}" for k, v in cell.items()))

    # --- the specs the plan actually supports -----------------------------------------
    # primary = clean tracer (outside face, wall-segment mask); verification = all-ink tracer
    # on the same clip. Different METHOD, which is what the gate calls independent.
    specs = []
    for c in comps:
        common = {"page": f_idx, "sheet": f"idx {f_idx} FOUNDATION WALL PLAN",
                  "clip": c["clip"], "ppf": f_ppf, "scale_checks": checks}
        specs.append({"name": c["name"], "classification": c["classification"],
                      "primary": {**common, "method": "clean-tracer"},
                      "verification": {**common, "method": "all-ink"}})

    # --- cal #66: DECLARED walks upgrade the verification side -------------------------
    # declared_walks.json is written by apply_walks.py from Jason's teach-mode answers
    # in the viewer. A declared walk replaces the all-ink verification with the sheet's
    # own printed dimension chains — input-independent of the pixel primary, and every
    # leg re-verified against the page at run time (a wrong answer refuses, never lies).
    walks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "declared_walks.json")
    if os.path.exists(walks_path):
        with open(walks_path, encoding="utf-8") as fh:
            declared = {w["name"]: w for w in json.load(fh).get("walks", [])}
        for s in specs:
            w = declared.get(s["name"])
            if w:
                s["verification"] = {
                    "page": w.get("page", f_idx),
                    "sheet": f"idx {w.get('page', f_idx)} printed dimension chains",
                    "method": "printed-dims",
                    "walk": w["walk"], "origin_pt": w["origin_pt"],
                    "ppf": f_ppf, "scale_checks": checks,
                }
                print(f"  declared walk: {s['name']} <- {len(w['walk'])} printed legs "
                      f"(teach-mode, {w.get('confirmed_by', 'unconfirmed')})")

    # cal #67: no heated spec exists until Jason declares how heated SF reads off the
    # floor plan. The gate must fail on exactly that — not on a relabeled proxy.
    if not any(s["classification"] in ("heated", "conditioned_accessory") for s in specs):
        print(f"  heated: no component declared -- heated SF is a floor-plan scope "
              f"(idx {SHEET_MAP['floor_area']}); awaiting teach-mode declaration")

    print("\n" + "=" * 78)
    print("RUN_TAKEOFF -- the real chain, on a real plan set")
    print("=" * 78)
    t0 = time.time()
    takeoff = eng.run_takeoff(
        PLAN, SHEET_MAP,
        pitch_calls=pitch_calls(doc, SHEET_MAP["roof"]),
        area_specs=specs,
        evidence_dir=args.evidence,
    )
    t_takeoff = time.time() - t0
    print(f"  status: {takeoff['status']}   ({t_takeoff:.1f}s)")
    cert = takeoff["area_certification"]
    print(f"  area certification: ok={cert['ok']}")
    for e in cert["errors"]:
        print(f"    - {e}")
    for comp in cert["components"]:
        print(f"    {comp['name']:<28} primary {comp['qty']:>7.1f} / verification "
              f"{comp['verification_qty']:>7.1f}  delta {comp['delta_pct']:.1f}% "
              f"(limit {cert['tolerance_pct']:.1f}%)")
    print("  measured lines:")
    for ln in takeoff["lines"]:
        print(f"    {ln['trade']:<24} {ln['qty']:>9,.1f} {ln['unit']:<3} {ln['source']:<9} "
              f"{ln['method']:<26} conf={ln['confidence']}")
    print("  could NOT measure:")
    for nm in takeoff["not_measured"]:
        print(f"    {nm['trade']:<24} {nm['why']}")
    for chk in takeoff["checks"]:
        if chk.get("check") == "area_schedule":
            print("  schedule (comparison-only):",
                  ", ".join(f"{r['label']}={r['sqft']:.0f}" for r in chk["rows"]))
    for chk in cert.get("schedule_checks", []):
        print(f"  schedule check {chk['trade']}: schedule {chk['schedule_qty']} vs measured "
              f"{chk['measured_qty']}")

    print("\n" + "=" * 78)
    print("REPORT_FROM_TAKEOFF -- the Level Ground pre-bid adapter")
    print("=" * 78)
    home = {"stories": 1, "foundation": "crawlspace + slab garage", "garage": "2-car",
            "finish_level": "mid", "insulation": "spray foam roofline"}
    region = {"state": "GA", "zip3": "310", "market": "Middle Georgia"}
    t0 = time.time()
    report = eng.report_from_takeoff(
        takeoff, home, region, prepared_for="Roberts (fixture dry run)",
        property_label="Roberts Residence -- Jasper County, GA",
        report_id="LG-DRYRUN-ROBERTS", date="2026-08-06", report_type="pre_bid",
        is_sample=True, market_book=eng.MARKET_RATE_BOOK)
    t_report = time.time() - t0
    print(f"  report built in {t_report:.2f}s")
    print(f"  quantities on the report: {len(report['quantities'])}")
    for q in report["quantities"]:
        print(f"    {q['item']:<28} {q['qty']:>9} {q['unit']:<4} {q['source']}  [{q['confidence']}]")
    print(f"  findings: {len(report['findings'])}   questions: {len(report['questions'])}   "
          f"unknowns: {len(report['unknowns'])}")
    for u in report["unknowns"][len(eng.STANDARD_UNKNOWNS):]:
        print(f"    ! {u}")

    # the six numbers a pre-bid report needs
    SIX = ["heated_sf", "framing_sf", "roof_surface_sq", "foundation_wall_lf",
           "slab_area_sf", "basement_area_sf"]
    got = {ln["trade"] for ln in takeoff["lines"]}
    print("\n  the six pre-bid numbers:")
    for trade in SIX:
        print(f"    {trade:<20} {'MEASURED' if trade in got else 'not produced'}")

    out_json = os.path.join(HERE, "roberts_prebid_report.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    tpl_path = os.path.join(REPO, "levelground", "lg_report_template.html")
    html_out = os.path.join(HERE, "roberts_prebid_report.html")
    sys.path.insert(0, os.path.join(REPO, "levelground"))
    import gen_reports  # noqa: E402  (reuse the one injector, no second copy)
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()
    with open(html_out, "w", encoding="utf-8") as fh:
        fh.write(gen_reports.inject(tpl, report))

    evidence_json = os.path.join(HERE, "measurement_evidence.json")
    with open(evidence_json, "w", encoding="utf-8") as fh:
        json.dump({"plan": PLAN, "sheet_ledger": rows, "scale_guard": guarded,
                   "scale_checks": checks, "components": comps, "tracer_sweep": table,
                   "takeoff_status": takeoff["status"],
                   "area_certification_errors": cert["errors"],
                   "seconds": {"takeoff": round(t_takeoff, 2), "report": round(t_report, 2)}},
                  fh, indent=2)

    doc.close()
    total = time.time() - t_start
    print("\n" + "=" * 78)
    print(f"TOTAL {total:.1f}s  (takeoff {t_takeoff:.1f}s, report {t_report:.2f}s)")
    print(f"  report json : {out_json}")
    print(f"  report html : {html_out}")
    print(f"  evidence    : {evidence_json}")
    print(f"  overlays    : {args.evidence}")
    print("=" * 78)


if __name__ == "__main__":
    main()
