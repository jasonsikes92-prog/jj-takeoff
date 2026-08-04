# DEV SPEC — Takeoff Engine: Golden Test Harness + Cabinet Detector Rebuild

**For:** dev-agent
**Owner:** Jason (J&J senior estimator)
**Engine:** `skills/jnj-estimate-takeoff/tools/jnj_takeoff.py` (996+ lines)
**Calibration ground truth:** `skills/jnj-estimate-takeoff/reference/calibration.md` (data points #1–#39)
**Goal:** make the takeoff engine (a) as accurate as possible and (b) provably non-regressing on every change. Accuracy comes from redundancy + calibration; reliability comes from a golden test suite that runs on every edit. This is also the proof-of-accuracy backbone for the "Level Ground" homeowner product.

---

## Guardrails (apply to ALL work here — do not violate)
1. **Measured and verified geometry beats schedules.** Harvest tables/schedules/callouts as comparison and specification evidence, but never use them as estimate quantities. Core areas must come from two reconciled geometry measurements with saved overlays; a printed total can never be added to its components.
2. **Two independent methods per quantity, reconcile.** Every measured quantity must be computable two ways and cross-checked (see `Quantity.reconcile`). Agreement within tolerance → confident; divergence → FLAG for human, never silently pick one.
3. **Rates are invoice-sourced + date-stamped, never the stale template.** (Roofing was $32k wrong from a template rate; the real Southern rate $175/sq was in calibration.md.) Do not hardcode a rate that isn't traceable to a real invoice/actual in calibration.md.
4. **Per-page scale.** Calibrate scale on each page from its own dimensions (`detect_scale`); never carry one page's scale to another.
5. **Never invent scope; gate the un-measurable.** If a quantity needs external info (foundation type, selections, HVAC quote, cabinet split from blank elevations), the engine DETECTS the gap and surfaces it — it does not guess.
6. **Calibrate only against CLEAN actuals** (see calibration.md "SOURCE HYGIENE"): never grade against an estimate, an over-budget job, an owner-self-funded job, or a one-off self-performed trade. On in-progress jobs grade only 100%-complete trades.

---

## DELIVERABLE A — Golden Test Harness (build FIRST)

### A1. Purpose
A regression suite of completed/known houses. Engine runs each plan set → compares each trade quantity/cost to the known ground truth → asserts within tolerance. Any engine change re-runs the whole suite; a change that improves trade X but breaks house Y is caught immediately.

### A2. Data inventory — source the fixtures from calibration.md
Build fixtures from houses that have BOTH a plan set AND clean ground truth. Confirm each against calibration.md before use:
| House | Ground-truth type | Strongest trades to assert |
|---|---|---|
| Roberts (#1) | Jason's sell price (reference estimate in `examples/`) | full-estimate total (reproduced +1.4%) |
| Wilson (#18–22) | Contracted actuals — GV foundation, GEO flatwork, Southern siding | foundation wall LF, slab area/CY, siding sq |
| Burns/Bethanie (#12–13) | Southern roofing + siding POs + J&J manual takeoff | roof surface sq, siding sq, brick |
| Peterson (#13) | Southern roofing actual | roof surface sq (steep 16:12) |
| Holbrook (#23) | GV foundation actual | slab area, footing/wall LF |
| Lankford | Waterproofing/french-drain actual | waterproofing LF |
| Pack (#39) | Jason's takeoff quantities (job not built) | quantity reconciliation only (framing/brick/footing/roof/drywall) |

**Do NOT use** as graded fixtures (calibration source hygiene): Sailview (over budget), McLaughlin (owner self-funded), Grotsky HVAC (self-performed) — may be included as NEGATIVE/skip cases only.

### A3. Structure
- `tools/tests/golden/` — one subdir per house: the plan PDF (or a path reference if large), plus `expected.yaml`.
- `expected.yaml` per house: each asserted quantity = `{trade, quantity, unit, tolerance_pct, source:"invoice/takeoff/sell", page_ref}`. Tolerances: geometry ±8% (roof/slab/masonry/footing/drywall), certified core-area component reconciliation ±2%, schedule comparisons ±1% (checks only, never measurement PASS), full-cost ±10% (against a clean sell).
- `tools/tests/run_golden.py` — loads each fixture, runs the relevant engine functions, prints a per-house per-trade table: `measured | expected | delta% | PASS/FAIL`, plus a summary (houses passing, worst deltas). Exit non-zero on any FAIL outside tolerance.
- Keep it dependency-light (the engine already uses fitz/cv2/skimage/numpy). Use `pytest` OR a plain runner — match whatever the repo already leans on.

### A4. Acceptance criteria
- Runner executes all fixtures headless and produces the pass/fail table.
- At least **5 houses** wired with ≥3 asserted trades each.
- Core heated/framing SF asserts GREEN only when produced from two geometry proofs; schedule-derived fixtures remain SKIP/comparison-only. Other currently-passing trades assert GREEN at their documented deltas — if a fixture can't hit tolerance, that's a real finding: log it, don't loosen the tolerance to force green.
- A one-command invocation (`python tools/tests/run_golden.py`) documented in the engine README/docstring.

---

## DELIVERABLE B — Rebuild `cabinet_run_lf()` (build against the golden set)

### B1. Current state (why it fails — already in the docstring)
`cabinet_run_lf()` exists as a scaffold. On the Pack kitchen it returns **~19 LF** (offset band tight — misses the island, under-connects) or **~900 LF** (band loose — eats the floor-tile hatch). Root cause: the flattened redline PDF puts base-cabinet faces in the SAME pixel/vector layer as the floor hatch and dimension lines, so a bare "segment offset ~24" from a wall" filter cannot separate them.

### B2. Approach (in priority order — stop at the first that passes the golden set)
1. **Isolate the casework, not bare offset lines.** Cabinets are drawn as a SYMBOL/poché (rectangle with the base-cabinet fill/X, uppers dashed), on a distinct lineweight/color in the vector. Filter `get_drawings()` by the casework layer's stroke width/color, or detect the cabinet-rectangle poché, rather than any 24"-offset line.
2. **Connect collinear fragments into runs.** The tight version returned 2–3 ft fragments (individual boxes). Merge collinear, near-abutting face segments into continuous runs before summing.
3. **Classify island vs perimeter vs tall.** Perimeter run = one long face + a wall behind it. Island = a closed rectangle with interior on BOTH long faces (no wall). Tall (fridge/oven/pantry) = ~24" deep but the plan block is deeper/labeled — may need the label. Return LF split by class where determinable; where not (upper/lower split needs the elevations), return total run LF and FLAG the split as elevation-dependent.
4. **Hatch rejection that generalizes.** Reject dense parallel sets (a hatch field has many equal-spaced parallels; a cabinet run does not). Validate the rejection on ≥3 different kitchens so it isn't Pack-specific.

### B3. Validation — REQUIRED before shipping any cabinet number
- Add cabinet LF assertions to the golden set for ≥3 houses that have a real cabinet takeoff (Pack kitchen ≈ 51 LF base run per Jason's takeoff: lowers 17 + island 25 + tall 9; add Roberts/Wilson kitchens if their cabinet LF is known).
- `cabinet_run_lf` must land within **±10%** on all 3, with the island captured, before it is allowed to feed an estimate.
- Until it passes: the function must keep returning `calibrated: False` and the estimate must fall back to a hand-traced number (do NOT auto-ship an uncalibrated cabinet number — this is the same class of error as the roofing placeholder).

### B4. Acceptance criteria
- `cabinet_run_lf` passes the golden cabinet assertions (±10%, island captured) on ≥3 kitchens.
- Flips `calibrated: True` only when the golden assertions pass.
- Docstring updated with the calibrated method + the houses it was validated on (mirror the siding/roofing calibration style).

---

## Definition of done
1. `python tools/tests/run_golden.py` runs green on ≥5 houses.
2. `cabinet_run_lf` passes ±10% on ≥3 kitchens with the island captured, and self-reports `calibrated: True`.
3. New/changed rates trace to an invoice in calibration.md (none invented).
4. calibration.md gets a short data-point note on what was validated (feed the loop).
5. No tolerance was loosened to force a pass — any fixture that can't hit tolerance is logged as a real finding for Jason.
6. `estimate_from_takeoff()` refuses schedule-sourced, hard-coded, missing-overlay, failed-reconciliation, or altered core-area quantities.
