# J&J Takeoff — Engineering Handoff (Virtual Takeoff era)

**Written:** 2026-08-14 14:24 EDT · **Repo:** `C:\Users\jason\JJ-Takeoff` · **Branch:** `virtual-takeoff` @ `9d1b2a0`
**Prior handoff:** `HANDOFF-archive-2026-08-14-1424.md` (still the best source for repo layout, the `jj.py verify` gate meanings, and the 2026-08-04 consolidation history)

---

## 1. Mission

Turn the takeoff engine into a **virtual takeoff**: every measured quantity is clickable
geometry drawn on the plan sheet, Jason reviews and *teaches* by drawing colored markup
(never forms), and the area gate certifies honestly from two independent inputs. This is
our answer to Handoff.ai's pitch — same glass cockpit, but on our locked rate book, our
fail-closed gates, our calibration. Doctrine stands: supervised v1 ships; autonomous
stays defunded.

## 2. Current State

**Verified right now (all run 2026-08-14 ~14:30 EDT, this exact tree):**
- Engine self-test: **ALL PASS** (43 OK lines, incl. geometry round-trip, evidence
  writer, Unicode-fraction parse). Unit battery: **7/7 PASS** (`test_area_certification,
  area_measurement_integration, build_viewer, dims_outline, dugger_fail_closed,
  slab_boundary_style, takeoff_evidence`). Golden suite after the last engine change:
  **6/6 houses, 22/22 asserts, 13/13 comparisons, exit 0, deltas unchanged.** Fixture
  certification RE-CERTIFIED 2026-08-14T17:54:32Z (engine untouched since).
- **Evidence layer** (Phase A): every `run_takeoff` line carries a content-stable `id`
  and, where a tracer produced one, its polygon in PDF points, self-checked two ways
  (shoelace reproduces the qty; vertices inside the trace clip). Per-job
  `evidence/takeoff_evidence.json` pins the plan by sha256; ledger enumerates every
  sheet with frozen `detect_scale` verdicts.
- **Viewer** (Phase B): `jobs\roberts_levelground\viewer\index.html` — SVG viewBox in
  PDF points over sheet PNGs, bidirectional click sync, roof roles in engine colors,
  per-sheet print-rescale badges, honest uncertified banner. No frameworks; works from
  `file://`.
- **Printed-dims verification** (Phase D, cal #66): `dims_outline_evidence()` — declared
  walk, every leg must exist in the sheet's own chains ON ITS AXIS, closure ≤ 0.5 ft;
  origin/method coupled via `_AREA_METHOD_ORIGINS` so relabeled evidence can never
  self-verify (bypass was reproduced in review, now refused + regression-tested).
- **Teach loop**: `TEACH-ROBERTS.bat` (one click) or
  `python tools\viewer\build_viewer.py --job jobs\roberts_levelground --serve` →
  localhost:5810, teach cards, Save → `apply_walks.py` → re-run → auto-reload.
- **Jason's first drawn teaching is consumed**: his magenta footprint (screenshot
  `Screenshot 2026-08-14 140952.png` in `OneDrive\Pictures\Screenshots`) →
  `ingest_pink_markup.py` → **declared walk, 12 printed legs, 2,129.4 SF, closure
  0.48 ft** (1.9% from the pixel trace, 1.5% from the plan's heated figure), parked in
  `declared_walks.json` as **"crawlspace envelope (foundation footprint)"**.

**Half-built / superseded:**
- The dropdown teach cards work but are the WRONG interface (Jason: "not sure how to
  make your teach function work", then drew the answer). Markup-first is the design
  now; the cards stay as verification detail only.
- Edit mode (vertex drag / redraw / `apply_takeoff_review`) **not built** — Phase C's
  remaining half.
- Garage + porch walks undeclared (Jason will pink them the same way).

**Blocked, honestly:** Roberts certification. `run_prebid.py` still certifies against
the old component model; per **cal #67 (Jason's ruling): a crawlspace is NOT heated** —
the "heated crawlspace envelope" component certified heated_sf from a foundation scope.
The declared pink walk deliberately does NOT wire in under the old name. Heated must be
measured from the **floor plan (page index 4)** before the heated line certifies.

**Exact next action — DONE 2026-08-14 ~18:50 EDT (same day, follow-on session):**
run_prebid.py restructured per cal #67. Crawlspace component renamed to the declared
walk's exact name, class `foundation` (new engine class, feeds neither rollup); pink
walk wired as its verification — **first input-independent certified component:
pixel 2,169.9 vs printed-dims 2,129.4 = 1.9% delta, inside the gate.** Second engine
one-liner: certify-side `_area_evidence_errors` was refusing "review"-tier scale even
for printed-dims, contradicting cal #66 on its motivating case — now admits review for
dims-method evidence only (keyed via `_AREA_METHOD_ORIGINS`; regression-tested, 7
tests in test_area_certification.py). `proposed_walks.json` regenerated (stale
"heated crawlspace envelope" teach cards); viewer rebuilt + verified live: banner
fails on exactly garage 2.6% / porch 7.7% / no heated component. Gates green
(golden 6/6, self-test, battery, cert re-pinned 18:47Z). **Next:** Jason's garage +
porch magenta → generalize `ingest_pink_markup.py`; heated awaits the Buildern watch
session (open question 1). BOTH engine one-liners + this restructure are UNCOMMITTED
awaiting Jason's ratify (`todo_takeoff_engine_ratify_0814` on Waiting-on-You).

## 3. Decisions Made (and Why)

| Decision | Alternatives | Reason | Reversibility |
|---|---|---|---|
| **PDF points + 0-based page index** for ALL persisted geometry | normalized coords (v3 corpus), pixels | identical to SVG's model → zero math in the browser; the roof review already chose it | load-bearing |
| **cal #66:** printed dimension chains admitted as area-gate verification; walks are DECLARED inputs | auto-classified walks; widening the 2% tolerance | the three pixel methods measure different envelopes and can never agree; classifiers overfit (see #65); printed-vs-pixels is what a human checks | Jason's ruling — settled |
| **cal #67:** crawlspace ≠ heated; heated is a floor-plan scope | keep the foundation-trace proxy (numbers nearly matched) | right number, wrong SCOPE is the proxy variant of right-number-wrong-shape | Jason's ruling — settled |
| **Markup-first teaching** — ingest colored marker on screenshots; forms demoted | dropdown teach cards (built first, rejected same day) | Jason answers geometry by drawing (roof review precedent; pink footprint) | settled by direct feedback |
| `_AREA_METHOD_ORIGINS` single map drives evidence stamp + independence + pricing cross-check | separate allow-lists | one place a new method must declare its origin; relabeled dicts can't self-verify (reproduced exploit) | load-bearing |
| Viewer = vanilla HTML/SVG, `file://`-safe, no build step | React/pdf.js | repo has no JS toolchain; sha-pinned static artifact | easy to change later |
| Geometry that fails self-check ships as `null` + flagged check, never wrong | ship best-effort geometry | a wrong overlay invites wrong corrections | load-bearing |
| Handoff-H1 benchmark **parked** until after the viewer; then load their output into OUR viewer vs golden truth | trial immediately | viewer is source-agnostic; better tooling to judge them with | revisit any time |
| Full renders only for role-mapped sheets; thumbs for the rest | render all 12 | teach-save reruns the build; render cost ×4 otherwise | trivial |

## 4. Architecture & Key Files

**Created this session:**
- `tools\viewer\build_viewer.py` — evidence → viewer builder; sha gate; `--serve` =
  localhost:5810 teach loop (POST `/teach` → save answers → `apply_walks.py` → rebuild).
- `tools\viewer\viewer_template.html` — the whole UI (CSS+JS, one file): canvas,
  panel, teach cards, `__TAKEOFF_DATA__` placeholder filled by str.replace.
- `tools\tests\test_takeoff_evidence.py · test_build_viewer.py · test_dims_outline.py`
- `jobs\roberts_levelground\`: `propose_walks.py` (trace topology + chain snapping →
  `proposed_walks.json` incl. per-axis printed pools), `apply_walks.py` (answers →
  `declared_walks.json` → rerun), `ingest_pink_markup.py` (Jason's marker → registered,
  chain-verified walk), `TEACH-ROBERTS.bat`, `declared_walks.json` (the pink walk).

**Modified significantly:**
- `tools\jnj_takeoff.py` (+~700 lines, all additive): `parse_dim` reads CAD fraction
  artifacts; `_px_poly_to_page_pts/_poly_area_perim_pts/_geometry_record/_measurement_id`;
  tracers return `polygon_pts`; `dims_outline_evidence`; `_measure_area_evidence`
  per-method scale/clip policy; `sha256_file`; `write_takeoff_evidence`; `run_takeoff`
  geometry attachment + `roof_lines` block (honors `roof_clip`); rollup
  `component_ids`; self-tests.
- `jj.py` — `verify` now runs every `tools\tests\test_*.py` as a gate.
- `reference\calibration.md` — #65 (slab boundary declared), #66, #67. **Next is #68.**
- `jobs\roberts_levelground\run_prebid.py` — consumes `declared_walks.json` for
  verification sides.
- Outside this repo: `Desktop\Claude\.claude\launch.json` gained `takeoff-viewer`
  (static :5800) and `takeoff-teach` (:5810) entries — session preview only; the
  durable path is the `.bat`.

**Looks touchable, isn't:** `Desktop\Claude\estimator_accuracy\` (stopped autonomous
track — harvest-only); `tools\tests\golden\*\expected.yaml` asserted values and
tolerances (add keys only, never edit values; every fixture edit forces cert refresh).

## 5. Gotchas & Hard-Won Knowledge

- **CAD dimension text lies twice:** Unicode vulgar fractions (`60'-10¼"` as one
  codepoint) AND dropped slashes (`13'-6 1 4"`). `parse_dim` now normalizes both;
  before the fix the Roberts foundation sheet showed 9 chains, after: 25. Any "the
  sheet doesn't print that dim" claim must survive this check first.
- **Registering Jason's screenshots:** grayscale/desaturation both fail (the plan's own
  linework is BLUE). Use the **inverted red channel** (blue ink dark in R; his magenta
  and the plan's red scribbles self-erase at R≈255), then verify with the **landmark
  oracle** — dimension-label positions must land on ink (100% of 50 vs 22% shifted
  control). Correlation score alone is blur-limited garbage on an 800px upload.
- **His marker is pure magenta (255,128,255)**, not pastel pink — sample the file, don't
  guess colors.
- **Area is translation-invariant:** a shoelace self-check can't catch a missed clip
  offset — that's why `_geometry_record` also enforces vertex-in-clip containment.
- **pt vs ft units bite:** the dims closing-vertex dedup once compared 0.5 *points*
  against a 0.5 *foot* gate and silently stripped geometry from legal walks.
- `setPointerCapture` retargets `pointerup` to the svg — canvas clicks must use the
  element captured at `pointerdown`.
- `npx serve` clean-URLs strip the trailing slash and break relative paths — always
  open `/viewer/`, not `/viewer/index.html`.
- **`_page_scale` "review" on Roberts is CORRECT** (print-rescaled ~7.5% off standard,
  86–187 votes). The dims path accepts it because leg verification IS the scale proof;
  the pixel path still demands high/good or explicit checks.
- `jj.py save` commits the **Desktop\Claude** workspace repo (`WORKSPACE`), not this
  one — commit here explicitly.
- Preview servers (:5800/:5810) die with the Claude session; `TEACH-ROBERTS.bat` is
  the durable launcher.
- After ANY `tools\jnj_takeoff.py` edit:
  `python Desktop\Claude\estimator_accuracy\refresh_golden_fixture_certification.py --write`
  (refuses unless golden is green — that's the point).

## 6. Conventions In Play

- Gates after every engine change: golden 6/6 + self-test ALL PASS + unit battery +
  cert refresh. `jj.py verify` runs all of it now.
- Additive keys only in engine dicts — no signature breaks; consumers read by key.
- Fail-closed everywhere: refuse loudly, never guess, never silently price
  (`estimate_from_takeoff` `unpriced`, gate errors verbatim in the viewer).
- **Declared inputs over inference** for anything a human reads in seconds
  (`slab_boundary`, `pitch_calls`, walks — cal #43/#65/#66).
- Function-local imports in the engine; comments say WHY, never WHAT.
- Calibration entries are numbered and append-only (`## Data point #NN — TITLE (date)`).
- Commits: descriptive first line, body of consequences, end with
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- `jobs\**\viewer\` and `graphify-out\` are generated → gitignored. Job PNGs/PDFs stay
  out of git by doctrine (see `.gitignore` header).
- Governing rules: `~\.claude\CLAUDE.md` (simplicity/surgical/verified),
  `Desktop\Claude\CLAUDE.md` (working map), this file.

## 7. Open Questions

1. **How does Jason derive heated SF on the floor plan?** Which boundary/face, which
   exclusions? Best answered in the planned Buildern watch session — do NOT guess a
   proxy again (cal #67).
2. **Garage + porch walks** — awaiting Jason's magenta on viewer screenshots; then
   generalize `ingest_pink_markup.py` (it currently declares one hardcoded component).
3. Does certification for Roberts ultimately pair pink-walk (markup) verifications with
   pixel primaries per component, or printed-dims? Both are input-independent of
   pixels; markup is Jason-authoritative. Likely: markup confirms shape, chains confirm
   lengths (already how ingest works) — formalize as the standard verification.
4. `opentakeoff_eval\` — 3 stray source files flagged by `jj.py save` lint since before
   this session: track, ignore-with-reason, or delete? (Jason's call, low stakes.)
5. `roof_surface_sq` still has no geometry (face decomposition emits zones, not
   polygons) — worth persisting zone outlines for the viewer later.
6. Phase E (wire `slab_area_sf` → `slab_concrete` in `RATE_BOOK`) waits until an area
   certification actually passes.

## 8. Do Not Touch

- Golden `expected.yaml` asserted values/tolerances; the 2% reconciliation; the
  fail-closed refusals (undeclared slab boundary, unverified scale, unprinted legs).
- `_AREA_METHOD_ORIGINS` coupling — adding a method WITHOUT declaring its origin must
  stay impossible.
- The declared pink walk's name **"crawlspace envelope (foundation footprint)"** — do
  not rewire it under "heated" to make certification pass (that's the exact wrong-scope
  disease cal #67 forbids).
- `HANDOFF-archive-*.md`, `docs\HANDOFF-2026-08-03.md` — history, not litter.
- `estimator_accuracy\` source — harvest-only.
- The dropdown teach cards: leave them as verification detail; don't "finish" them into
  the primary interface — markup-first is settled.

## 9. Resume Command

> Read `HANDOFF.md`. Then restructure `jobs\roberts_levelground\run_prebid.py`'s
> component model per cal #67 (crawlspace envelope = foundation scope; heated components
> measured from floor plan index 4) and wire `declared_walks.json` as the crawlspace
> verification; re-run `python jobs\roberts_levelground\run_prebid.py` and rebuild the
> viewer. Run the full gates before and after any engine edit. Do not relabel the pink
> walk as "heated", do not edit golden fixture values, and confirm with Jason before
> changing anything outside `jobs\roberts_levelground\` + `tools\viewer\`. When his
> garage/porch magenta screenshots appear in `OneDrive\Pictures\Screenshots`,
> generalize `ingest_pink_markup.py` and ingest them the same way.
