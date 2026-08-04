# Lessons from v1

**Compiled:** 2026-08-04 · Companion to [EVALUATION.md](EVALUATION.md)

The brief asked for "every rule/heuristic found in v1 and the failure it was patching," on the theory that v1's rules are bad and only the lessons survive. **Reading the code changed that framing.** Most of these rules are not patches over bad code — they are encoded results of closed-loop cold tests, each one a real number that came back wrong once. A fork that does not carry them forward will rediscover every one of them the same way: on a live bid.

Two things already do this job better than a fresh extraction could, and they should be read first:

- **`~\.claude\skills\jnj-estimate-takeoff\reference\calibration.md`** — 1,619 lines, **63 numbered data points**, many of them jobs committed cold from plans and *then* graded against QBO actuals. This is the durable memory. It is not a lessons file waiting to be written; it is the lessons file.
- **`HANDOFF.md` §5 and the archived handoffs** — the per-session gotchas.

What follows is the **engine-level** rule inventory: the heuristics, thresholds and special cases living in code, each with the failure it exists to prevent, and a verdict on whether it transfers.

**Transfer key:** 🟢 must port · 🟡 port the lesson, rewrite the code · 🔴 obsolete, drop

---

## 1. Scale — the highest-value rules in the codebase

### 🟢 R1. Never trust the printed scale note. Regress it.
`calibrate_scale()` · `_cluster_mode()`

For every dimension *text* on the page, emit all plausible `drawn_span / stated_value` ratios from **two independent geometric signals** — the dimension line the text is centered on, *and* the witness-line pair straddling it — then take the densest cluster. Real scale is reinforced by many independent dimensions landing on the same pt/ft; junk matches scatter.

**Failure it prevents:** the Roberts set's title block says `1/4" = 1'-0"` (18.000 pt/ft). The set is printed at ~92.5% of nominal; the true value is **16.714** pt/ft on 187 votes. Taking the note under-states **every area by 13.8%** and every length by 7.1%. Measured today — [EVALUATION.md §3](EVALUATION.md).

**Transfer:** mandatory, and it is the reason not to adopt an engine that reads the note.

### 🟢 R2. Dimension lines are broken around their centered text.
A naive read returns half the span. Full span = leftmost run start → rightmost run end.
**Failure:** made every sheet look mis-scaled — ~8.8 pt/ft against a true 18.0.

### 🟢 R3. Regress span-vs-feet *per sheet*, and separate slope from intercept.
The regression separates true scale (slope) from a constant end-tick shortfall (measured: 13.4 pt on p5, 6.7 on p4, ~0 on p6). All sheets were at printed nominal with R² ≥ 0.99999 — but that was *proven*, not assumed.
**Failure:** a constant offset masquerading as a scale error, and vice versa.

### 🟢 R4. Scales differ page to page within one set.
`_page_scale()` runs per page. Roberts p6 is 3/16" where p4/p5/p7 are 1/4".
**Failure:** carrying one page's scale to another. (Also memory: `feedback_verify_scale_per_page`.)

### 🟡 R5. Cluster half-width ±2%, minimum dimension 2.0 ft.
Tuned thresholds (`half=0.02`, `min_ft=2.0`, `band=35.0`, `near_k=4`). Port the *approach*; re-tune against the corpus.

---

## 2. Tracing and area — where v1 lost, and knows it

### 🔴 R6. `trace_footprint_clean` / `trace_enclosed_region` are unreliable on dashed linework.
Returned **80–99 SF for a 5,500 SF building**. `trace_footprint` (all-ink) converged across three sheets to 0.6%.
**Transfer:** drop the code, keep the lesson — *dashed slab edges defeat contour tracing; seal first or flood the complement.* L J Show sheet 4 (SLAB PLAN, ~406 dash segments) is still untraceable and all foundation geometry proxies off sheet-2 area polygons. This is an open, unsolved bug.

### 🔴 R7. `roof_zone_surface()` does not work on J&J sets.
Solved ppf 19.94 against a verified 18.00 and left 61% of area unassigned.
**Transfer:** drop. Roof comes off the roof plan.

### 🟢 R8. Search a *generous* y-window for elevation grade lines.
**Failure:** the first pass cut off the rear/right base and locked onto a **roof** line 208 pt up — so the "wall band" sampled roof, not wall.

### 🟢 R9. A 45°-rotated wing foreshortens by 0.7071 on *both* cardinal elevations.
10'-0" garage doors measure 7.06 ft as drawn. Measuring cladding straight off elevations under-counts that wing by **29%**. Caught only because the doors appear in two views.
**Transfer:** mandatory, and it is an argument for cross-sheet reconciliation as a *correctness* mechanism, not a nicety.

---

## 3. Classification — the silent-drop family

### 🟢 R10. Classifiers must report coverage, and unclassified area must be filled — never dropped.
`cladding_completeness()` asserts every measured SF lands in a material bucket (±3%).
**Failure:** texture classifiers silently dropped what they could not classify. That is an **invisible under-bid** — the number looks clean and is short. Jason caught this live. The self-test still asserts it catches 563 SF being dropped.
**Transfer:** this is a *design principle*, not a function. Anything that buckets must account for 100% or flag the remainder.

### 🟢 R11. Shingle vs lap siding cannot be split by hatch orientation.
Both are horizontal. Use horizontal-run **continuity**: lap runs unbroken, shingle breaks into tabs. Even then, lighter-shaded roof planes misclassify.

### 🟢 R12. `"uncovered"` contains the substring `"covered"`.
`framed_under_roof_sf()` guards it explicitly.
**Failure:** a naive `"covered" in label` frames an *uncovered* slab patio as under-roof.
**Transfer:** trivially small, catastrophic if missed, and exactly the class of bug a rewrite reintroduces.

### 🟢 R13. Never sum TOTAL/summary rows with their components.
**Failure:** the 2× framing double-count.

### 🟢 R14. Never count windows off an elevation sheet.
`window_count()` refuses. Elevations draw the same opening in more than one view — **26 tags for 13 real windows on burns**.
**⚠ And its exact inverse is also true:** `elevation_opening_count()` exists because the floor plan *under*-counts — L J Show returned **22 from plan tags and 46 from elevations**, both functions working correctly. Neither view is authoritative alone. This is the single clearest argument that cross-sheet reconciliation is the missing layer.

---

## 4. Roof

### 🟢 R15. Collapse duplicate strokes before measuring.
A raw roof-line length is roughly **double**. (`golden/burns/expected.yaml` still carries `roof_line_ft: 624` against a real unique length of ~426 — a passing assertion measuring double-drawn linework.)

### 🟢 R16. Split roof line into EAVE / RAKE / RIDGE / HIP_VALLEY, in that geometric order.
Boundary vs interior by perpendicular probe; interior axis-aligned → ridge, diagonal → hip/valley; boundary parallel to nearest ridge → eave, perpendicular → rake.
**Why it matters commercially:** gutters run on eaves; fascia on eave+rake; drip edge on eave+rake; hip-and-ridge cap on ridge+hip. Without the split, four trades collapse into one undifferentiated perimeter and all four are wrong.

### 🟢 R17. Roof footprint must reconcile to under-roof area + *measured* overhang.
`reconcile_roof_footprint()` flags too-small **and** too-large traces.
**Failure:** Jason's implied 7,758 SF footprint implies a **5.54 ft** overhang against a measured mode of 1.50 ft — not physical. A trace that is too large is as wrong as one too small, and only the reconciliation catches it.

---

## 5. Pricing and output — the traps that cost real money

### 🟢 R18. Key rate-book lookups by line **index**, never by name.
**Failure:** `q('Windows','Windows',…)` matched an **ASSEMBLY** row priced at $0 and silently zeroed **$8,800**. ASSEMBLY rows must carry qty 0. `price_lines()` now raises on unknown names rather than dropping them.

### 🟢 R19. Template unit labels lie. Trust the $/unit basis.
**Failure:** `#4 Rebar 20" Sticks` prices **per 20-ft stick** despite a "LF" unit label — ordered **775 sticks instead of 39**.

### 🟢 R20. Compare raw-to-raw. Waste lives in its own column.
Jason's takeoff quantities are raw with waste separate. Grading a waste-loaded number against a raw one manufactures phantom errors. *(This is the brief's own "measured vs purchased" point — already live in v1.)*

### 🟢 R21. Client-facing Descriptions carry no takeoff math, internal tags, or bare quantity echoes.
`lint_buildern_descriptions()` must return 0 before shipping. Self-tested: catches 9/9 leaks, 0 false positives on 7 good lines.

### 🟢 R22. Reading a Buildern export: exclude GROUP + ASSEMBLY rows and "Don't calculate" lines; reconcile to *Builder Fixed Cost + Allowances*, never a raw sum.
**Failure:** a live `Footer Labor` line parented to *Crawlspace: Block walls* is a crawl artifact — $12,700 of phantom scope on a slab house.

### 🟢 R23. Size a disagreement in dollars before chasing it.
**Failure:** three hypotheses spent on a footer gap worth **$686 (0.089%)** while a 6% framing-lumber error worth **$4,600** sat unexamined.

### 🟢 R24. Rates, not measurements, are usually the variance.
L J Show came in **+17%** over Jason's estimate. On the 12 comparable lines: quantities −$11.5k, **rates +$43.6k**. Framing lumber alone was $33k — template $14/SF against his live **$8/SF**.
**Transfer:** the loudest lesson in the whole project. Before blaming the takeoff, difference the rate book. *(Memory: `feedback_use_decoded_sub_rates`.)*

---

## 6. Process rules — the ones that are really about discipline

### 🟢 R25. Enumerate every sheet before asserting a sheet type is absent.
`SheetLedger` is a forcing function: `examine()` every page, `set_index()` from the cover, then `certify()`. `assert_absent()` refuses until the whole set is enumerated.
**Failure:** claiming "no roof plan in this set" from a partial look. *(Memory: `feedback_enumerate_every_sheet`.)*

### 🟢 R26. Primary and verification measurements must be genuinely independent.
`certify_area_measurements()` requires a different method, sheet, or overlay, both carrying real overlay files, reconciling within 2%. Aggregate TOTAL labels are prohibited as components. **Schedule rows are recorded as comparisons only and never influence the certified number.**
**Transfer:** this encodes the ruling *measurement is the authority, the printed schedule is a cross-check* — and it is what stops a system from learning to just copy the schedule.

### 🟢 R27. Matching the human's number is not the same as being right.
`footer_lf()` — two earlier versions hit Jason's number **by accident**: one double-counted every house↔porch step and omitted the house↔garage step, two errors cancelling. The current version is deliberately 6.1% off his raw and structurally correct.
**Transfer:** the single most important epistemic rule in the codebase. A fork that tunes to match ground truth without checking structure will bake in cancelling errors that fail on the next geometry.

### 🟢 R28. Confirm foundation type. Never infer it from boilerplate notes.
**Failure:** the Martin job — inferred from boilerplate, wrong, caught by Jason. *(Memory: `feedback_confirm_foundation_type`.)*

### 🟢 R29. Fail closed. A blank beats a confident wrong number.
All 10 autonomous-cohort jobs terminate `more_information_required` with **zero false positives**. `ROADMAP.md` names this correctly: *"A wrong quantity that looks right is worse than a blank — Jason would bid it."*
**Transfer:** this is the product, not a limitation. Any fork must preserve it — and note that OpenTakeoff independently arrived at the same doctrine ("Reported, never counted"), which is the strongest signal the two codebases are philosophically compatible.

### 🟡 R30. Check the calibration data-point number before appending.
Collided with an existing #55. Housekeeping, but it cost a renumber across 6 docstrings and 2 memory files.

---

## 7. The meta-lesson

The brief says v1 failed because "rules accumulated with no way to measure whether rule #47 broke what rule #12 fixed." **That is not what the disk shows.** v1 has three independent harnesses — `run_golden.py` (6 houses against real ground truth), `_verify_selftest()` (~25 assertions each pinned to a real Jason number), and `coverage.py` (answered fraction at zero false positives) — and one command, `python jj.py verify`, that runs all five gates. Every new engine function ships with a self-test line by convention. That is better instrumentation than most production codebases have.

The actual failure is different, and worth naming precisely:

> **Two tracks ran in parallel and the working one was treated as the prototype.**

The supervised path prices houses today — 6/6 golden houses green, a complete 253-line estimate delivered, quantities matching Jason's own hand takeoff at 0.0% on three categories. The autonomous path has 66,378 lines and answers 0.3% of the sheet. Effort followed the autonomous track because it was the "real" program, while the one that actually works was framed as a stopgap.

The lesson that matters most for whatever comes next is not about rules. It is: **ship the supervised loop, instrument it, and let autonomy grow inside a system that is already delivering value** — rather than building autonomy first and hoping it arrives before patience runs out.
