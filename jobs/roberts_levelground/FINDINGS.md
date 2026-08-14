# Roberts → Level Ground pre-bid: first end-to-end run of the real chain

**2026-08-06.** Reproduce with `python jobs/roberts_levelground/run_prebid.py`.

Before today `run_takeoff()` had one call site in this repo — `test_dugger_fail_closed.py`, which
asserts it *refuses* to answer — and `levelground/gen_reports.py` injected a hardcoded sample
takeoff. `run_takeoff → report_from_takeoff` had never executed on a real plan set. It has now.

**Cost per report: 6.9 s of compute for the takeoff, under 0.01 s for the report adapter**
(33.6 s for the whole script, which also runs a nine-cell tracer evidence sweep that a
production run would not). Compute is not what makes a $99 report expensive.

---

## What worked

| Step | Result |
|---|---|
| Sheet ledger | 12 of 12 pages examined and classified before anything was measured |
| Scale guard | foundation 16.646, floor plan 16.714, roof 16.549 pt/ft — every area lands **−14.5%** if measured at the title block's 1/4"=1' (18.000). Independently reproduces the documented Roberts figure |
| Explicit scale certification | passed on the foundation sheet: printed 64'-3¾" measures 16.685 pt/ft, printed 60'-10¼" measures 16.683, both within 1% of the 86-vote consensus 16.646 |
| Component location | `foundation_wall_loops` resolved exactly three enclosed loops, stable at `close_ft` 1.0 and 2.0: crawlspace 1,962.0 SF / garage 654.9 / front porch 177.4 (inside face) |
| Fail-closed | `heated_sf`, `framing_sf`, `roof_surface_sq` all refused, and the report said so to the reader in plain English |

## What blocked, and why

No component produced two measurements inside the 2% gate:

| Component | primary (clean) | verification (all-ink) | delta | limit |
|---|---|---|---|---|
| heated crawlspace envelope | 2,169.9 | 2,766.3 | 21.6% | 2.0% |
| garage slab | 732.2 | 751.4 | 2.5% | 2.0% |
| front porch slab | 226.7 | 245.4 | 7.7% | 2.0% |

**Root cause: the three certification-accepted methods do not measure the same thing.**
`trace-footprint-clean` takes the outside face of wall-like segments, `trace-footprint-all-ink`
thresholds every stroke including dimension lines, `trace-enclosed-region` takes the inside face.
Requiring any two of them to agree within 2% cannot pass on a drawing that has wall thickness and
printed dimensions. `test_area_measurement_integration.py` passes only because its "building" is a
single-stroke rectangle — no wall thickness, no dimension lines — at a widened 3% tolerance.

⛔ **The near-miss is a mirage.** The heated primary, 2,169.9 SF, sits +0.4% from the plan's own
2,161 SF heated figure. `evidence/heated-crawlspace-envelope-primary.png` shows the polygon it
actually traced: it cuts a diagonal across the front porch and omits the garage. Right number,
wrong shape — the same failure as `footer_lf` and the $6.50 framing rate. Do not tune a clip pad
until this "agrees."

## Defects this run surfaced

1. ✅ **FIXED 2026-08-06 — a wrong quantity reached the client-facing report.** With `slab` mapped to the foundation
   sheet, `run_takeoff` shipped `slab_area_sf = 5,033.2 SF` as `MEASURED` on a house whose entire
   under-roof area is 3,431 SF. The all-ink tracer had traced the outer **dimension-line
   rectangle** — see `evidence/slab_allink.png` versus `evidence/slab_clean.png`. The clean
   tracer's 3,066.7 SF is the true footprint (−0.07% against the plan's own heated + garage +
   front porch = 3,069, and identical at clip pads 2/8/15 ft). `run_takeoff` (jnj_takeoff.py
   ~4442-4454) saw the 39% disagreement and applied cal #46's *"tracers disagree → dashed-boundary
   sheet suspected → report the all-ink number."* On a fully dimensioned sheet that rule picks the
   contaminated side.

   **The fix (Jason's call, 2026-08-06): boundary style is now a DECLARED input**, not something
   the code infers — `sheet_map["slab_boundary"] = "solid" | "dashed"`, exactly like `pitch_calls`
   under cal #43. Undeclared plus disagreeing tracers is now `more_information_required`, and both
   tracer readings are recorded in `checks` for audit either way. Proven on both houses in
   `tools/tests/test_slab_boundary_style.py`: holbrook `dashed` → all-ink **3,174.7 vs the GEO
   flatwork invoice 3,122 = +1.7%**; roberts `solid` → clean **3,066.7 vs the sheet's own
   heated+garage+porch 3,069 = −0.1%**; roberts undeclared → refuses to answer.

   ⛔ **Why it is declared and not detected:** five candidate auto-classifiers were tested against
   these two sheets — global segment-length statistics, dashed-flag population, extreme-run
   solid/dashed classification, dash-tolerance growth (re-tracing with the 1.2-ft floor dropped to
   0.2 ft, which recovered only +0.8% on holbrook — the dashes are not simply below the floor), and
   the traced-area-to-ink-envelope ratio (49.4% vs 51.6% — no separation). None separated the two
   without fitting a threshold to exactly these two houses, which is the `footer_lf` failure mode.
   Two examples cannot validate a classifier. Boundary style is a two-second read off the sheet.

   This harness still does not map `slab` — Roberts' slab scope is the garage and porch (908 SF),
   not a whole-footprint sheet. That reason is independent of the tracer bug.
2. **The report stamps every quantity `confidence: "measured"`** regardless of the line's real
   confidence (`report_from_takeoff`, jnj_takeoff.py:4959). The 5,033 line carried confidence
   `review` and a *"tracers disagree"* note; the homeowner-facing report showed it as measured and
   dropped the note.
3. **`basement_area_sf` is emitted unconditionally** from the foundation trace, so the report
   prints *"Basement footprint 1,885 sq ft"* for a crawlspace house with no basement.
4. **The gate's independence test cannot fail.** `certify_area_measurements` accepts *different
   method **or** sheet **or** overlay path*, and `measure_and_certify_area_components` generates
   overlay paths from the component label (`name-primary`, `name-verification`), so the paths always
   differ. The only real teeth are the 2% reconciliation.

## One claim that needs a footnote

"The golden suite already proves those six at 0.0–1.7% on real plan sets" is true for four of them.
`heated_sf` and `framing_sf` are **read off the printed SQFT schedule** in every house that asserts
them (burns, pack, roberts, wilson) — and `run_takeoff` explicitly forbids a schedule value from
reaching a priced quantity. Genuinely measured from geometry: `foundation_wall_lf` (lankford,
wilson), `slab_area_sf` (holbrook), `basement_area_sf` (wilson). `roof_surface_sq` is asserted only
on peterson, which is not one of the six green houses.

## Recommended next step

Give the gate a second signal that is genuinely independent of pixels: the sheet's **own printed
dimension chains** walked into a rectilinear outline (`read_dimension_chains` + `polygon_outline`,
which `trace_footprint_clean`'s own docstring already calls the primary method on cut-up slabs).
Printed numbers versus traced pixels is a comparison a 2% gate can actually pass, and it is how a
human estimator checks the work. It is not in `_AREA_ENGINE_METHODS` today — adding it is a
doctrine change, so it is Jason's call, not a patch.

## Owed by Jason

1. What counts as the second independent measurement of an area component — dimension chains,
   a second sheet, or something else?
2. ~~cal #46's tracer-choice rule~~ — **ruled 2026-08-06: test boundary style. Done, see defect 1.**
3. Fix the confidence stamp and the basement scope? Both are small and clearly correct, but they
   change the engine and will drift fixture certification, which then needs re-running.

## Incidental

The roof sheet's text layer carries a **3:12** callout alongside the 12:12 and 8:12 zones. The
fixture comment in `expected.yaml` says only "12:12 + 8:12".
