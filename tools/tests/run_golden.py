#!/usr/bin/env python
"""
J&J Takeoff Engine — GOLDEN REGRESSION HARNESS  (Deliverable A of DEV_SPEC)

WHAT IT DOES
    Runs the takeoff engine against a set of KNOWN houses (completed jobs / clean
    actuals / Jason's own takeoff) and asserts each engine result against the
    calibration.md ground truth within a documented tolerance. Certified geometry
    regressions report PASS/FAIL. Schedule reads and schedule-seeded legacy math report
    CHECK-PASS/CHECK-FAIL and never count as measured V3 quantities. Exit code is
    NON-ZERO if either class falls outside tolerance, any fixture/probe is skipped,
    or any documented known gap remains.

DEPENDENCIES (once; OCR probes also require the Tesseract executable on PATH)
    python -m pip install -r tools/tests/requirements-golden.txt

ONE-COMMAND INVOCATION
    python tools/tests/run_golden.py            # run every wired house
    python tools/tests/run_golden.py pack        # run one house
    python tools/tests/run_golden.py --list      # list fixtures + status

DESIGN
    - Dependency-light: no pytest, no PyYAML (engine only uses fitz/cv2/skimage/numpy).
      expected.yaml is a small flat subset parsed by _load_yaml() below.
    - Each house dir under tools/tests/golden/<house>/ holds:
        plan.pdf        — the immutable source plan, bound by plan_sha256.
        expected.yaml   — the asserted quantities (trade, quantity, unit, tolerance_pct,
                          source, page_ref, assertion_type) + fixture metadata.
    - The MEASUREMENT for each (house, trade) is produced by a probe function in
      PROBES below. A probe returns a float (the measured value) or None (not
      measurable — reported as SKIP and fails the suite). Probes call the real engine
      functions so a regression in the engine shows up here.
    - Each fixture carries its own plan.pdf plus plan_sha256. The runner refuses a
      missing or changed plan before executing any probe.
    - `assertion_type: comparison` is required for schedule-derived or otherwise
      non-certifying probes. Those checks execute and enforce tolerance, but can never
      be represented as measured-area PASS results.
    - A fixture flagged `plan_missing: true` has NO plan PDF on this machine; its
      expected values are recorded from calibration.md and reported as NEEDS-PLAN.
      NEEDS-PLAN is incomplete fixture coverage and therefore fails the suite.

GROUND-TRUTH SOURCES  (every expected value traces to calibration.md — none invented)
    pack     — data point #39 (Jason's hand takeoff; job not yet built) + #34/#35
    wilson   — data points #18-23 (GV/GEO/FFCI contracted actuals) + SQFT schedule
    burns    — data points #12/#12c (Southern POs + J&J manual takeoff) + schedule
    holbrook — data point #24 (GV/GEO/SRM actuals)
    lankford — data points #27/#29 (GV wall invoice + CGS waterproofing actual)
    peterson — data point #13 (Southern roofing actual)
    roberts  — data point #1 (Jason's fixture-local reference estimate)
"""
import hashlib
import json
import os
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
GOLDEN = os.path.join(HERE, "golden")
sys.path.insert(0, TOOLS)

import fitz  # noqa: E402
import jnj_takeoff as eng  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal YAML reader — supports exactly what expected.yaml uses:
#   top-level  key: value
#   a list under `asserts:` of `- {k: v, k: v, ...}` one-line flow maps
# No external dependency (engine doesn't ship PyYAML).
# ---------------------------------------------------------------------------
def _coerce(v):
    v = v.strip()
    if v == "" or v.lower() in ("null", "none", "~"):
        return None
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if (v[0] == v[-1]) and v[0] in ("'", '"'):
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _parse_flow_map(s):
    # s is the inside of  {a: 1, b: 'x, y', c: 2}  — split on commas not inside quotes
    out, buf, q = {}, "", None
    parts = []
    for ch in s:
        if q:
            buf += ch
            if ch == q:
                q = None
        elif ch in ("'", '"'):
            q = ch
            buf += ch
        elif ch == ",":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf)
    for p in parts:
        if ":" not in p:
            continue
        k, _, v = p.partition(":")
        out[k.strip()] = _coerce(v)
    return out


def _load_yaml(path):
    meta, asserts, in_asserts = {}, [], False
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.strip() == "asserts:":
                in_asserts = True
                continue
            stripped = line.strip()
            if in_asserts and stripped.startswith("-"):
                body = stripped[1:].strip()
                if body.startswith("{") and body.endswith("}"):
                    asserts.append(_parse_flow_map(body[1:-1]))
                continue
            if not line.startswith(" ") and ":" in line:  # top-level meta
                in_asserts = False
                k, _, v = line.partition(":")
                meta[k.strip()] = _coerce(v)
    meta["asserts"] = asserts
    return meta


# ---------------------------------------------------------------------------
# PROBES — measure a trade with the real engine. Return float or None (=SKIP).
# Each probe opens the plan lazily and caches the document per path.
# Clips/scales are the vision-verified regions documented in calibration.md.
# ---------------------------------------------------------------------------
_DOC_CACHE = {}


def _doc(path):
    if path not in _DOC_CACHE:
        _DOC_CACHE[path] = fitz.open(path)
    return _DOC_CACHE[path]


def _framed_under_roof(page):
    """Under-roof framed SF -- delegates to the engine's canonical rule so this harness and
    run_takeoff can NEVER drift again. That drift was a real bug: run_takeoff double-counted a
    TOTAL UNDER ROOF row and mis-added 'uncovered' patios (both fixed 7/6/26); the engine now
    owns the one rule (framed_under_roof_sf: framed + covered-back, minus totals/uncovered)."""
    return eng.framed_under_roof_sf(eng.read_sqft_schedule(page))


def probe_pack_framing_sf(plan):
    # Sheet 4 "SQFT SHEET" = page index 0 carries the schedule.
    return _framed_under_roof(_doc(plan)[0])


def probe_pack_cabinet_kitchen_lf(plan):
    p = _doc(plan)[6]  # MAIN FLOOR PLAN (sheet 7) — kitchen casework
    # Whole-page clip on purpose: the kitchen cluster is AUTO-ISOLATED (no hand-tuned clip).
    r = eng.cabinet_run_lf(p, clip=(0, 0, p.rect.width, p.rect.height), room="kitchen")
    if not r.get("island_captured"):   # island MUST be captured to trust a cabinet number
        return None
    return r.get("base_run_lf")


def probe_wilson_framing_sf(plan):
    return _framed_under_roof(_doc(plan)[3])  # SQFT AREAS page


def _wilson_foundation_auto(plan):
    """FULLY AUTONOMOUS: auto scale (detect_scale) + auto region (find_drawing_region) +
    no side hint (prefer='largest'). Validated 7/5/26: 155.9 LF / 1,372 SF == GV invoice
    exactly — the Phase 1 autonomy gate. No hand-fed clip= or ppf= anywhere."""
    p = _doc(plan)[4]  # FOUNDATION WALL PLAN, 1/4"=1'
    r = eng.find_drawing_region(p)
    if r is None:
        return None
    return eng.trace_enclosed_region(p, r["clip"], ppf=r["ppf"], prefer="largest")


def probe_wilson_framing_labor_cost(plan):
    # Legacy comparison only: schedule read x the calibration-locked rate. Calling
    # estimate_from_takeoff() here would correctly fail the current core-area gate.
    #
    # 2026-08-04: the framer bills per framed LAYER, not per footprint (Jason). A COVERED
    # DECK is a framed floor AND a framed roof, so it bills twice. The deck SF is READ OFF
    # THE SCHEDULE by label -- not hardcoded -- so this probe fails if the reader stops
    # finding it, which is the whole point of a regression test.
    rows = eng.read_sqft_schedule(_doc(plan)[3])
    qty = probe_wilson_framing_sf(plan)
    deck, _matched, _review = eng.covered_deck_sf(rows)
    spec = eng.RATE_BOOK["framing_sf"][0]
    line = {"cost_type": spec["cost_type"], "qty": qty + deck,   # deck's 2nd layer
            "unit_cost": spec["unit_cost"], "markup_pct": 0}
    return eng.assemble_estimate([line])["builder_cost"]


def probe_wilson_foundation_lf(plan):
    r = _wilson_foundation_auto(plan)
    return r["perimeter_lf"] if r else None


def probe_wilson_heated_sf(plan):
    rows = eng.read_sqft_schedule(_doc(plan)[3])
    return sum(r["sqft"] for r in rows
               if "htd" in r["label"].lower() or "heated" in r["label"].lower())


def probe_wilson_basement_area_sf(plan):
    r = _wilson_foundation_auto(plan)
    return r["area_sf"] if r else None


def probe_pack_heated_sf(plan):
    for r in eng.read_sqft_schedule(_doc(plan)[0]):
        if "heated" in r["label"].lower():
            return r["sqft"]
    return None


def probe_burns_heated_sf(plan):
    # p2 carries the clean SQFT schedule (HEATED AREA 1951)
    rows = eng.read_sqft_schedule(_doc(plan)[2])
    for r in rows:
        if "heated" in r["label"].lower():
            return r["sqft"]
    return None


def probe_roberts_heated_sf(plan):
    # p2 SQFT sheet of the "Precon notes Jefferies" set (= Roberts Residence, title-block
    # verified). Plan-printed heated = 2,161 (calibration #1 carried 2,127 — discrepancy
    # logged in expected.yaml, reconcile with Jason).
    for r in eng.read_sqft_schedule(_doc(plan)[2]):
        if "heated" in r["label"].lower():
            return r["sqft"]
    return None


def probe_roberts_framing_sf(plan):
    return _framed_under_roof(_doc(plan)[2])


def probe_peterson_heated_sf(plan):
    # NO-text-layer set -> OCR schedule reader (Phase 2, landed 7/5/26). Jason's heated
    # basis = FIRST FLOOR HEATED + FUTURE EXPANSION (bonus built out; Jason confirmed).
    r = eng.read_sqft_schedule_ocr(_doc(plan)[2])
    if not r:
        return None
    heated = sum(x["sqft"] for x in r["rows"]
                 if x["sqft"] and ("HEATED" in x["label"].upper()
                                   or "EXPANSION" in x["label"].upper()))
    return heated or None


def probe_roberts_estimate_amount(plan):
    # ESTIMATE-ASSEMBLY probe (7/6/26): read Jason's reference estimate's own inputs
    # (qty, unit cost, the line's markup %) and reproduce the priced total in CODE via
    # assemble_estimate. Proves the pricing pipeline (line math + markup by cost type +
    # rollup); the measurement probes prove the geometry. Ground truth = the file's own
    # verified line-level total (cal #49): amount 516,589. NOTE sell_total 591,341 stays
    # SKIP -- cal #49 discrepancy (file footer says 649,312; 591,341 not in file).
    import openpyxl
    xlsx = os.path.join(os.path.dirname(plan), "reference-estimate.xlsx")
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb["Estimate"]
    lines = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        ct = r[2]
        if ct in (None, "GROUP") or not isinstance(ct, str):
            continue  # groups + the numeric footer block
        def _f(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
        lines.append({"cost_type": ct, "qty": _f(r[6]), "unit_cost": _f(r[7]),
                      "markup_pct": _f(r[10]), "group": r[1]})
    return eng.assemble_estimate(lines)["amount"]


PETERSON_CALLS = [
    (861.7, 420.1, 16), (1006.6, 420.1, 16), (640.9, 492.6, 6), (672.0, 613.3, 12),
    (1172.2, 654.7, 12), (509.8, 723.7, 12), (672.0, 772.0, 16), (475.3, 910.0, 3),
    (654.7, 906.5, 6), (854.8, 861.7, 12), (1196.3, 861.7, 12), (1037.7, 885.9, 6),
    (803.0, 956.2, 16), (1251.5, 942.4, 16), (903.1, 899.6, 16), (1455.1, 1154.9, 16),
    (489.1, 1072.2, 12), (485.6, 1186.0, 12), (630.5, 1206.7, 16), (730.6, 1175.7, 16),
    (1424.0, 1179.1, 16), (1339.8, 1132.9, 16)]  # eye-verified 7/5/26 (cal #43/#44)


def probe_peterson_roof_surface_sq(plan):
    # Face decomposition + eye-verified pitch callouts (landed 7/5/26, cal #44). Scale is
    # SOLVED from the sheet itself: printed under-roof 2,792 SF (schedule TOTAL 3,198 minus
    # 406 upstairs FUTURE EXPANSION, OCR-verified) + measured eave perimeter + printed
    # 12"/17" overhangs. Pitch callouts are EYE-READ off the rendered overlay in abs PDF
    # points — never raw OCR ("16/12 P." OCRs as "12/12", cal #43 trap). The last call is
    # an interior point of the bottom-right wing whose own arrow sits across the ridge on
    # its twin face (same 16/12 read).
    r = eng.roof_zone_surface(_doc(plan)[4], fitz.Rect(220, 220, 1600, 1500),
                              PETERSON_CALLS, underroof_sf=2792,
                              overhang_in=(12.0, 17.0))
    return float(r["squares"]) if r else None


def probe_peterson_roofing_total(plan):
    # SECOND FULL-CHAIN grade (7/6/26): plan -> roof_zone_surface (measured 46.5 sq) ->
    # RATE_BOOK $227.70/sq (= $1.98/SF all-in x 1.15 waste, cal #13) -> builder cost,
    # vs Southern Expert Roofing ACTUAL $11,204. Measurement reads ~-5% (cal #44 bias:
    # unmodeled bellcast flares), so expect ~-5.6%.
    qty = probe_peterson_roof_surface_sq(plan)
    if qty is None:
        return None
    spec = eng.RATE_BOOK["roof_surface_sq"][0]
    line = {"cost_type": spec["cost_type"], "qty": qty,
            "unit_cost": spec["unit_cost"], "markup_pct": 0}
    return eng.assemble_estimate([line])["builder_cost"]


def probe_holbrook_slab_sf(plan):
    # FULLY AUTONOMOUS (7/5/26, gap CLOSED): auto scale + auto region + the ALL-INK
    # trace_footprint. On this sheet the slab boundary is SHORT-DASH linework (each dash
    # under the clean tracer's 1.2-ft floor), so trace_footprint_clean tops out at 2,294
    # SF -- the all-ink tracer seals the dashes and hits the #26b clip-invariant plateau:
    # 3,175 SF (+1.7% vs GEO 3,122), IDENTICAL for any clip pad 3-15 ft. pad_ft=8 because
    # find_drawing_region's default 2-ft pad clips the dashed edge (2,848 = -8.8%).
    # RULE: pick the tracer by boundary style -- solid walls -> clean tracer;
    # dashed/below-grade boundary -> all-ink + sealing.
    p = _doc(plan)[5]  # SLAB PLAN, 1/4"=1'
    sc = eng.detect_scale(p)
    r = eng.find_drawing_region(p, ppf=sc["ppf"], pad_ft=8.0)
    if r is None:
        return None
    t = eng.trace_footprint(p, r["clip"], ppf=sc["ppf"])
    return t["area_sf"] if t else None


def probe_lankford_foundation_lf(plan):
    # FULLY AUTONOMOUS scope trace (7/22/26): the architectural foundation sheet's
    # 259.1-LF loop includes basement walls plus garage/frost/brick-ledge runs. The lower
    # floor sheet isolates the actual basement-wall scope. At zoom 4 its own dimension
    # chains solve ppf 12.500 with 0.3% spread; trace_enclosed_region returns 197.685 LF,
    # invariant at 2/8/15-ft clip pads and -0.16% vs GV invoice #1211's 198 LF.
    p = _doc(plan)[3]  # LOWER FLOOR PLAN, sheet 4of8
    sc = eng.detect_scale_ocr(p, zoom=4.0)
    if not sc:
        return None
    measured = []
    for pad_ft in (2.0, 8.0, 15.0):
        region = eng.find_drawing_region(p, ppf=sc["ppf"], pad_ft=pad_ft)
        if region is None:
            return None
        trace = eng.trace_enclosed_region(
            p, region["clip"], ppf=sc["ppf"], prefer="largest"
        )
        if trace is None:
            return None
        measured.append(trace["perimeter_lf"])
    if (max(measured) - min(measured)) / min(measured) > 0.005:
        raise ValueError(f"Lankford foundation scope is not clip-invariant: {measured}")
    return sum(measured) / len(measured)


def probe_lankford_waterproofing_lf(plan):
    # Comparison-only plan proxy for CGS's "left + right elevations" scope: twice the
    # main basement loop's measured side depth. Production scope still requires two
    # independent proofs; this probe cannot certify a target-job waterproofing quantity.
    p = _doc(plan)[5]
    sc = eng.detect_scale_ocr(p)
    if not sc:
        return None
    loops = eng.foundation_wall_loops(p, ppf=sc["ppf"])
    if not loops:
        return None
    return 2 * min(loops[0]["bbox_ft"])


# --- Burns: classify_lines / roof_footprint / roofing+siding pricing vs Southern actuals ------
def probe_burns_roof_line_ft(plan):
    # classify_lines isolates the roof by its olive-green color+weight signature on the roof sheet
    return eng.classify_lines(_doc(plan)[6])["lengths_ft"]["roof"]


def probe_burns_roof_footprint_sf(plan):
    # vision-guided footprint from the isolated roof lines (2,678 clean vs 1,915 blind)
    return eng.roof_footprint(_doc(plan)[6]).get("area_sf")


def probe_burns_roofing_total(plan):
    # roofing_estimate reproduces Southern Expert Roofing's actual $8,052.92 from Burns' measured
    # surface (#13: 6/8/10 zones = 3,644 SF raw) + accessories, at their billed 40.33-sq waste.
    z = [{"footprint_sf": 772 / eng.pitch_factor(6), "pitch": 6},
         {"footprint_sf": 2376 / eng.pitch_factor(8), "pitch": 8},
         {"footprint_sf": 496 / eng.pitch_factor(10), "pitch": 10}]
    return eng.roofing_estimate(z, hip_ridge_lf=110, drip_edge_lf=280, n_pipe_boots=1,
                                field_rate=174, waste=40.33 / 36.44 - 1)["total"]


def probe_burns_siding_total(plan):
    # siding_estimate reproduces Southern Siding & Gutters' actual $18,962.50 from their line qtys
    lines = [{"item": "lap_smooth_7", "sf": 1582}, {"item": "bnb", "sf": 600},
             {"item": "porch_tg_wood", "sf": 850}, {"item": "sf_narrow", "lf": 280, "rate": 11},
             {"item": "beam_cedar", "lf": 92}, {"item": "frieze", "lf": 212},
             {"item": "opening_std", "count": 16, "rate": 65}, {"item": "water_table", "lf": 185}]
    return eng.siding_estimate(lines, field_waste=0)["total"]


# maps expected.yaml `trade` -> probe fn.  Missing entry => SKIP (no probe yet).
def probe_roberts_window_count(plan):
    # Windows are counted off the FLOOR PLAN only. The elevation sheets (p9, p10) draw the
    # same opening on more than one view -- they read 24 and 6 against a real 23 -- so a
    # probe pointed at an elevation is roughly 100%% high. Jason's rule (2026-07-27): a
    # mulled unit is separate windows, so 6062MU labelled DOUBLE is 2 and 9062MU labelled
    # TRIPLE is 3.
    count, _detail = eng.window_count(_doc(plan)[4])
    return count


def probe_burns_window_count(plan):
    # Floor plan is p6. Elevations (p9) read 26 for the same 13-14 real openings.
    count, _detail = eng.window_count(_doc(plan)[5])
    return count


def probe_burns_recessed_cans(plan):
    # Electrical sheet p8. Recessed cans ONLY (R4 tags). Jason 2026-07-27: vanity lights and
    # single room fixtures are separate lines -- the manual takeoff's 32 folded them in.
    count, _detail = eng.recessed_can_count(_doc(plan)[7])
    return count


def probe_roberts_fascia_lf(plan):
    # Fascia = EAVE + RAKE off the roof plan (p7), rake slope-corrected by the sheet's own
    # pitch callouts. Roof linework is isolated by pitch-callout enclosure (not colour, which
    # is a drafter's choice), boundary vs interior by exterior flood fill, and eave/rake/
    # ridge/shed by the SLOPE ARROWS -- the four splits Jason verified on the overlay.
    return _autonomous_roberts_roof(plan)["fascia_lf"]


_ROBERTS_AUTONOMOUS_ROOF_CACHE = {}


def _autonomous_roberts_roof(plan):
    if plan not in _ROBERTS_AUTONOMOUS_ROOF_CACHE:
        _ROBERTS_AUTONOMOUS_ROOF_CACHE[plan] = eng.classify_roof_lines(_doc(plan)[6])
    return _ROBERTS_AUTONOMOUS_ROOF_CACHE[plan]


def probe_roberts_roof_autonomous_match_pct(plan):
    """Grade the base classifier against every reviewed segment without applying the review."""
    meta = _load_yaml(os.path.join(os.path.dirname(plan), "expected.yaml"))
    corrections = json.loads(meta["roof_line_review_json"])
    result = _autonomous_roberts_roof(plan)
    roles = ("eave", "rake", "ridge", "hip_valley", "transition")

    def match(items, target, tol=1.0):
        tx1, ty1, tx2, ty2 = (float(v) for v in target)
        for item in items:
            x1, y1, x2, y2 = item["seg"]
            direct = max(abs(x1 - tx1), abs(y1 - ty1), abs(x2 - tx2), abs(y2 - ty2))
            reverse = max(abs(x1 - tx2), abs(y1 - ty2), abs(x2 - tx1), abs(y2 - ty1))
            if min(direct, reverse) <= tol:
                return True
        return False

    passed = 0
    for correction in corrections:
        target = correction["segment"]
        hits = {role for role in roles if match(result.get(role, []), target)}
        if correction["action"] == "remove":
            passed += not hits
        else:
            passed += hits == {correction["role"]}
    return 100.0 * passed / len(corrections)


def probe_roberts_eave_lf(plan):
    return _autonomous_roberts_roof(plan)["eave_lf"]


def probe_roberts_rake_lf(plan):
    return _autonomous_roberts_roof(plan)["rake_lf"]


def probe_roberts_ridge_lf(plan):
    return _autonomous_roberts_roof(plan)["ridge_lf"]


def probe_roberts_hip_valley_lf(plan):
    return _autonomous_roberts_roof(plan)["hip_valley_lf"]


def probe_roberts_transition_lf(plan):
    return _autonomous_roberts_roof(plan)["transition_lf"]


def probe_burns_window_trim_lf(plan):
    return eng.window_trim_lf(_doc(plan)[5])[0]


def probe_roberts_window_trim_lf(plan):
    return eng.window_trim_lf(_doc(plan)[4])[0]


PROBES = {
    ("pack", "framing_sf"): probe_pack_framing_sf,
    ("pack", "heated_sf"): probe_pack_heated_sf,
    ("pack", "cabinet_kitchen_base_lf"): probe_pack_cabinet_kitchen_lf,
    ("wilson", "framing_sf"): probe_wilson_framing_sf,
    ("wilson", "heated_sf"): probe_wilson_heated_sf,
    ("wilson", "basement_area_sf"): probe_wilson_basement_area_sf,
    ("wilson", "foundation_wall_lf"): probe_wilson_foundation_lf,
    ("wilson", "framing_labor_cost_usd"): probe_wilson_framing_labor_cost,
    ("burns", "heated_sf"): probe_burns_heated_sf,
    ("burns", "roof_line_ft"): probe_burns_roof_line_ft,
    ("burns", "roof_footprint_sf"): probe_burns_roof_footprint_sf,
    ("burns", "roofing_total_usd"): probe_burns_roofing_total,
    ("burns", "siding_total_usd"): probe_burns_siding_total,
    ("burns", "window_count"): probe_burns_window_count,
    ("burns", "recessed_can_count"): probe_burns_recessed_cans,
    ("burns", "window_trim_lf"): probe_burns_window_trim_lf,
    ("holbrook", "slab_area_sf"): probe_holbrook_slab_sf,
    ("lankford", "foundation_wall_lf"): probe_lankford_foundation_lf,
    ("lankford", "waterproofing_lf"): probe_lankford_waterproofing_lf,
    ("roberts", "heated_sf"): probe_roberts_heated_sf,
    ("roberts", "framing_sf"): probe_roberts_framing_sf,
    ("roberts", "estimate_amount_usd"): probe_roberts_estimate_amount,
    ("roberts", "window_count"): probe_roberts_window_count,
    ("roberts", "fascia_lf"): probe_roberts_fascia_lf,
    ("roberts", "fascia_vendor_lf"): probe_roberts_fascia_lf,
    ("roberts", "roof_line_autonomous_match_pct"): probe_roberts_roof_autonomous_match_pct,
    ("roberts", "autonomous_eave_lf"): probe_roberts_eave_lf,
    ("roberts", "autonomous_rake_lf"): probe_roberts_rake_lf,
    ("roberts", "autonomous_ridge_lf"): probe_roberts_ridge_lf,
    ("roberts", "autonomous_hip_valley_lf"): probe_roberts_hip_valley_lf,
    ("roberts", "autonomous_transition_lf"): probe_roberts_transition_lf,
    ("roberts", "window_trim_lf"): probe_roberts_window_trim_lf,
    ("peterson", "heated_sf"): probe_peterson_heated_sf,
    ("peterson", "roof_surface_sq"): probe_peterson_roof_surface_sq,
    ("peterson", "roofing_total_usd"): probe_peterson_roofing_total,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
class Result:
    def __init__(self, house, trade, unit, expected, tol, measured, status, note=""):
        self.house, self.trade, self.unit = house, trade, unit
        self.expected, self.tol, self.measured = expected, tol, measured
        self.status, self.note = status, note

    @property
    def delta_pct(self):
        if self.measured is None or not self.expected:
            return None
        return (self.measured - self.expected) / self.expected * 100


def _resolve_plan(meta, house_dir):
    p = meta.get("plan")
    if not p:
        return None
    if not os.path.isabs(p):
        p = os.path.join(house_dir, p)
    if "*" in p:
        hits = glob.glob(p)
        p = hits[0] if hits else p
    return p if os.path.exists(p) else None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run_house(house):
    house_dir = os.path.join(GOLDEN, house)
    yml = os.path.join(house_dir, "expected.yaml")
    if not os.path.exists(yml):
        return []
    meta = _load_yaml(yml)
    plan_missing = bool(meta.get("plan_missing"))
    plan = None if plan_missing else _resolve_plan(meta, house_dir)
    results = []
    expected_plan_hash = str(meta.get("plan_sha256") or "").upper()
    plan_hash_error = None
    if plan and expected_plan_hash:
        actual_plan_hash = _sha256(plan)
        if actual_plan_hash != expected_plan_hash:
            plan_hash_error = (f"plan SHA-256 mismatch: expected {expected_plan_hash}, "
                               f"got {actual_plan_hash}")
    fixture_asset_error = None
    reference_estimate = meta.get("reference_estimate")
    if reference_estimate:
        reference_path = os.path.join(house_dir, reference_estimate)
        expected_reference_hash = str(meta.get("reference_estimate_sha256") or "").upper()
        if not os.path.exists(reference_path):
            fixture_asset_error = f"missing fixture asset: {reference_path}"
        elif expected_reference_hash and _sha256(reference_path) != expected_reference_hash:
            fixture_asset_error = f"fixture SHA-256 mismatch: {reference_path}"
    for a in meta["asserts"]:
        trade = a.get("trade")
        unit = a.get("unit", "")
        exp = a.get("quantity")
        tol = a.get("tolerance_pct", 8)
        if plan_missing:
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "NEEDS-PLAN", meta.get("plan_note", "plan not on disk")))
            continue
        if plan is None:
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "NO-PLAN-FILE", f"expected at {meta.get('plan')}"))
            continue
        if plan_hash_error or fixture_asset_error:
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "ERROR", plan_hash_error or fixture_asset_error))
            continue
        probe = PROBES.get((house, trade))
        if probe is None:
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "SKIP", "no probe wired"))
            continue
        try:
            measured = probe(plan)
        except Exception as e:  # a probe crash is a real failure, not a pass
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "ERROR", f"{type(e).__name__}: {e}"))
            continue
        if measured is None:
            results.append(Result(house, trade, unit, exp, tol, None,
                                  "SKIP", "probe returned None (not measurable)"))
            continue
        in_tol = measured is not None and exp and abs((measured - exp) / exp * 100) <= tol
        comparison = a.get("assertion_type") == "comparison"
        r = Result(house, trade, unit, exp, tol, measured,
                   "CHECK-PASS" if comparison else "PASS")
        if a.get("known_gap"):
            # Keep the delta visible, but a known gap is incomplete product coverage and
            # therefore fails the command until it is either closed or made an explicit
            # fail-closed MORE INFORMATION REQUIRED terminal outside this harness.
            r.status = "GAP-CLOSED" if in_tol else "KNOWN-GAP"
            r.note = a.get("gap_note", "documented engine gap — see final report")
        elif not in_tol:
            r.status = "CHECK-FAIL" if comparison else "FAIL"
        results.append(r)
    return results


def main(argv):
    if "--list" in argv:
        for h in sorted(os.listdir(GOLDEN)):
            yml = os.path.join(GOLDEN, h, "expected.yaml")
            if os.path.exists(yml):
                m = _load_yaml(yml)
                flag = "  [PLAN MISSING]" if m.get("plan_missing") else ""
                print(f"  {h:10s} {len(m['asserts'])} asserts{flag}")
        return 0

    houses = [a for a in argv[1:] if not a.startswith("-")]
    if not houses:
        houses = sorted(d for d in os.listdir(GOLDEN)
                        if os.path.exists(os.path.join(GOLDEN, d, "expected.yaml")))

    all_res = []
    print("=" * 78)
    print("J&J TAKEOFF ENGINE — GOLDEN REGRESSION SUITE")
    print("=" * 78)
    for house in houses:
        res = run_house(house)
        if not res:
            continue
        all_res += res
        print(f"\n### {house.upper()}")
        print(f"  {'trade':<26}{'measured':>11}{'expected':>11}{'delta%':>9}  status")
        print("  " + "-" * 70)
        for r in res:
            meas = "-" if r.measured is None else f"{r.measured:,.1f}"
            exp = "-" if r.expected is None else f"{r.expected:,.1f}"
            dp = "-" if r.delta_pct is None else f"{r.delta_pct:+.1f}"
            line = f"  {r.trade:<26}{meas:>11}{exp:>11}{dp:>9}  {r.status}"
            print(line)
            if r.note and r.status not in ("PASS", "CHECK-PASS"):
                print(f"      -> {r.note}")

    # summary
    graded = [r for r in all_res if r.status in ("PASS", "FAIL")]
    fails = [r for r in graded if r.status == "FAIL"]
    checks = [r for r in all_res if r.status in ("CHECK-PASS", "CHECK-FAIL")]
    check_fails = [r for r in checks if r.status == "CHECK-FAIL"]
    gaps = [r for r in all_res if r.status in ("KNOWN-GAP", "GAP-CLOSED")]
    skips = [r for r in all_res if r.status in ("SKIP", "NEEDS-PLAN", "NO-PLAN-FILE")]
    errs = [r for r in all_res if r.status == "ERROR"]
    houses_graded = sorted({r.house for r in graded})
    houses_pass = sorted({r.house for r in graded
                          if all(x.status == "PASS" for x in graded if x.house == r.house)})
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"  houses graded : {len(houses_graded)}  ({', '.join(houses_graded)})")
    print(f"  houses green  : {len(houses_pass)}  ({', '.join(houses_pass)})")
    print(f"  asserts graded: {len(graded)}   PASS {len(graded)-len(fails)}   FAIL {len(fails)}")
    print(f"  comparison checks: {len(checks)}   PASS {len(checks)-len(check_fails)}   "
          f"FAIL {len(check_fails)}")
    print(f"  known-gaps: {len(gaps)}    skipped/needs-plan: {len(skips)}    errors: {len(errs)}")
    if gaps:
        for r in gaps:
            dp = "-" if r.delta_pct is None else f"{r.delta_pct:+.1f}%"
            print(f"    [{r.status}] {r.house}/{r.trade}: {dp} (tol +/-{r.tol}%) — {r.note}")
    if graded:
        worst = sorted((r for r in graded if r.delta_pct is not None),
                       key=lambda r: -abs(r.delta_pct))[:5]
        print("  worst deltas:")
        for r in worst:
            print(f"    {r.house:9s} {r.trade:<26} {r.delta_pct:+6.1f}%  {r.status}")
    if fails or check_fails:
        print("\n  FAILURES:")
        for r in fails + check_fails:
            print(f"    {r.house} / {r.trade}: {r.measured:,.1f} vs {r.expected:,.1f} "
                  f"({r.delta_pct:+.1f}%, tol +/-{r.tol}%)")
    if errs:
        print("\n  ERRORS:")
        for r in errs:
            print(f"    {r.house} / {r.trade}: {r.note}")
    print()
    if gaps:
        return 1
    return 1 if (fails or check_fails or skips or errs) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
