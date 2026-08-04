# Fork Plan

**Written:** 2026-08-04 · Based on [EVALUATION.md](EVALUATION.md) and [LESSONS_FROM_V1.md](LESSONS_FROM_V1.md)
**Relationship to `ROADMAP.md`:** that document tracks the autonomous engine's phases and stays valid for what it covers. This one changes which program those phases apply to.

---

## The recommendation, in one line

**Do not fork OpenTakeoff as the base. Keep v1-supervised as the spine and adopt three things from OpenTakeoff into it.**

The brief assumed v1 was too far gone and OpenTakeoff was the sound foundation. The measurements invert that on the one capability that decides bid accuracy. v1 *measures* the scale by regressing the printed dimension strings; OpenTakeoff *reads* it off the title block. Across the 6 golden houses that is right 5 times and wrong once — and the once costs **−14.5% on every area in the set**, with nothing on the sheet to warn you. You cannot build a bid-grade takeoff on a 1-in-6 silent 14% miss, and you cannot fix it by tuning: it is an architectural stance about what counts as evidence.

Everything else in OpenTakeoff is genuinely better than v1's equivalent, and three parts of it are worth real money.

---

## The seam — why this integrates cleanly

OpenTakeoff's `set_scale` accepts four mutually exclusive forms. One of them is:

```
set_scale { sheet, upp }      // upp = real feet per image px at render scale 2.0
```

v1's `calibrate_scale()` returns `pt_per_ft`. The conversion is one line:

```python
upp = 1.0 / (ppf * 2.0)      # render scale 2.0 → image px = 2 × PDF points
```

**That single call eliminates OpenTakeoff's only disqualifying flaw on these plans.** v1 keeps measurement authority; OpenTakeoff gets a scale it could never have derived, then does the tracing and the verification UX far better than v1 ever will. This is not a hack — `set_scale {upp}` is a first-class documented input, exactly the socket for an external calibrator.

The rest of the integration follows the same shape: **v1 decides, OpenTakeoff renders and traces.**

---

## Repo layout

Keep the two products separate, one shared core. Do **not** merge the OpenTakeoff clone into the OneDrive workspace — it is a live upstream and needs to stay rebaseable.

```
C:\Users\jason\Projects\                        (new — NOT OneDrive; see §Durability)
├── opentakeoff\                                git remote = upstream, branch j-and-j
│   └── (only additive changes; see "Upstream discipline")
│
└── jnj-takeoff\                                the spine — promoted out of ~/.claude/skills
    ├── engine\        jnj_takeoff.py           measurement authority, unchanged
    ├── bridge\        ot_bridge.py             ← NEW: v1 scale → OT set_scale, OT traces → v1 certify
    ├── reference\     calibration.md (63 pts), rate_book.json, waste_factors.md
    ├── templates\     estimate-template.xlsx, measurements-template.xlsx
    ├── eval\          run_golden.py, coverage.py, golden\<6 houses>, truth\
    └── levelground\   report engine + lg_report_template.html + site\
```

**Why promote the skill out of `~/.claude/skills`:** HANDOFF §2 flags it — `C:\Users\jason\.claude\` is not OneDrive-synced, and it holds the engine, `calibration.md`, and every memory file. `jj.py backup` mirrors it, but one disk failure between backups loses the 63-data-point ledger. Moving the spine into a git repo makes the backup structural rather than a habit.

**Symlink or shim `~/.claude/skills/jnj-estimate-takeoff` back at it** so the `jnj-estimate-takeoff` skill keeps working unchanged. Nothing in Jason's daily loop should break.

---

## What comes across, exactly

| From OpenTakeoff | Why | Effort |
|---|---|---|
| **The verification canvas** — `view_sheet {overlay}`, `edit_shape`, `mark_verdict`, `export_marked_pdf` | The brief's own strongest point: "a tool that can't show *which* numbers to distrust saves zero time." v1 has static PNGs. This is the biggest single win | Medium — it is a React app; run it as-is |
| **The tracer** — `oneclick.ts`, `detectRooms.ts`, `rastermask.ts` | Sealed flood + contour + vertex snapping beats v1's tracing, and `rastermask` gives scanned plans for free. Fixes v1's dashed-linework hole (L J Show sheet 4) | Low — drive via MCP, no port needed |
| **The MCP surface** — 38 journaled tools with provenance | Turns "Claude reads plans" into a tool loop with an audit trail and `undo_last` | Low — it already runs |

| Stays in v1 | Why |
|---|---|
| `calibrate_scale` + dimension reading | §3 of EVALUATION. Non-negotiable |
| `calibration.md`, 63 data points | Irreplaceable |
| 18-division Buildern output + markup + `lint_buildern_descriptions()` | OpenTakeoff has none and upstream's planned worksheet is generic |
| Level Ground engine + privacy bridge | Built and tested |
| The four reconciliation/certification functions | OpenTakeoff has none |
| The eval harnesses | Better than anything a fork would start with |

| Dropped |
|---|
| `trace_footprint_clean`, `trace_enclosed_region`, `roof_zone_surface` — measured unreliable, superseded |
| Static PNG overlay review |
| **v1-autonomous as a build target** — harvest the corpus, truth file, grader, page-role work and linework extraction; stop funding the 66K-line race to full autonomy |

---

## Milestones, in dependency order

Each has an exit criterion that is a number, not a feeling. **Nothing ships without a score against the corpus** — that rule from the brief stands, and v1 already has the harness to enforce it.

### M0 — Move and prove (½ day)
Promote the skill into `Projects\jnj-takeoff`, git init, symlink back, clone OpenTakeoff to `Projects\opentakeoff` on branch `j-and-j`.
**Exit:** `python jj.py verify` still returns GREEN across all five gates from the new location.

### M1 — The bridge (1–2 days) ⭐ start here
`bridge/ot_bridge.py`: load a plan into OpenTakeoff's MCP → for each sheet, compute `ppf` with v1's `calibrate_scale()` → `set_scale {upp}` → trace → pull `area_sf`/`perimeter_lf` back → run through v1's `certify_area_measurements()`.
**Exit:** on all 6 golden houses, bridged areas land within the existing tolerances (0.5% deterministic / 3.5% geometry) and `run_golden.py` stays 6/6 green. **This is the whole thesis in one milestone** — if the bridge holds, the architecture is right.

**Already de-risked:** `opentakeoff_eval\bench_area.mjs` does exactly this mechanism today — it pushes v1's measured `16.714` pt/ft into OpenTakeoff as `upp` and traces at it. The MCP accepted it and returned areas scaled precisely by `(16.714/18)²` against the note-derived run. **The seam works.** M1 is wiring and scoring, not discovery.

### ✅ M2 — Scale-comparison sweep — **DONE 2026-08-04**
Swept all 6 golden houses, 28 pages clearing 25 votes. Result in [EVALUATION.md §3e](EVALUATION.md).
**Outcome:** whole-set print rescaling is **1 of 6 houses** (Roberts, −14.5% area), not the norm. Isolated mixed-scale sheets are common (11 of 28 pages, 5 houses) but all sit on low vote support and read as detail/section sheets. M1's priority stands — you cannot tell a rescaled set from a true one without running the regression.
**Follow-on (30 min, not done):** open the low-vote off-nominal pages (holbrook p17, pack p5, wilson p2/p10/p12, burns p4) and confirm they are detail/section sheets. If so, vote count becomes a usable confidence signal rather than an observation.

**Shipped as a reusable guard:** `opentakeoff_eval\scale_sweep.py` runs the sweep on any set and separates the two failure modes — it flags `WHOLE-SET RESCALED` with the area-error figure, versus `isolated mixed-scale pages`. **Wire this into intake.** It is a few seconds per set and it is the difference between catching a Roberts and bidding one.

```bash
python "C:/Users/jason/OneDrive/Desktop/Claude/opentakeoff_eval/scale_sweep.py"
```

### M3 — Residential sheet taxonomy (2–3 days)
Extend `sheetgraph.ts`'s `SheetRole` from `plan|schedule|legend|detail|elevation|demolition|unknown` to the residential set: cover, site, foundation, floor, framing, roof, elevation, section, electrical, schedule, detail. Feed it v1's `SheetLedger` discipline so a role cannot be asserted absent until every page is enumerated.
**Exit:** correct roles on all 6 golden houses + the 10-job corpus, with `assert_absent()` refusing on any un-enumerated set.

### M4 — Window/door schedule semantics (2–3 days)
Extend `scheduleParse.ts` (token→row, already generic) to window and door schedules. Cross-check against v1's `parse_opening_tag()` — J&J's WWHH encoding (`10080` = 10'×8', not 1'×8').
**Exit:** schedule counts reconcile with `window_count()` on all 6 houses, and divergences are *flagged*, never auto-resolved.

### M5 — Cross-sheet reconciliation (1–2 weeks) — the missing layer in both codebases
Still the real prize, and the thing neither engine has. First target is **openings**, because we know the answer: L J Show returns 22 from plan tags and 46 from elevations, both functions working correctly, nothing reconciling them.
Constraints to enforce: room areas sum to heated SF · roof footprint × pitch factor = roof surface · wall perimeter × ceiling height = wall area · every opening appears in plan **and** elevation.
**Exit:** openings reconcile to 46 on L J Show with evidence from both views, and hold across the 7 graded houses.

**✅ RULING — Jason, 2026-08-04, decision #3 closed:**
> *"Reconciled is when the elevations match the plan view. If there is a discrepancy then I need to be alerted to look at it. The problem may come from mulled units, especially on windows. A double mulled unit actually equals 2 windows, a triple mulled unit would be 3."*

Three things follow, and the third is a bug this ruling exposed:
1. **Match = reconciled. Mismatch = alert Jason, never auto-resolve.** No preferring one view. The system already does this — `elevation_opening_count()` returns `ok=False` with a message naming both numbers.
2. **Mull expansion is the first hypothesis in the alert text.** Double = 2, triple = 3. Already coded as `MULL_LABELS` and `parse_opening_tag`'s `(N)` prefix.
3. ⛔ **The plan side does not agree with itself, and that must be fixed before any reconciliation is meaningful.** Measured on L J Show p5 today: `window_count()` returns **22**, while the reconcile's internal `parse_opening_tag` sweep of the *same page* returns **30 windows / 40 doors**. Two parsers, two answers, one page. Detail in the note below.

#### M5 note — measured evidence for the opening counts (2026-08-04, L J Show)

Ran both counters on `Downloads\L J show BID SET (1).pdf`:

| Source | Windows | Doors |
|---|---|---|
| Floor plan p5, `window_count()` | **22** | — |
| Floor plan p5, `parse_opening_tag` sweep (inside the reconcile) | **30** | 40 |
| Elevations p2/p8/p9/p11, `elevation_opening_count()` | **48** | 14 |
| **Jason's hand takeoff** | **46** | — |

- **The elevations are nearly right** — 48 against Jason's 46. The reconcile already fires: `ok=False`, *"window count disagrees: elevations 48 vs floor plan 30 (38%)."*
- **Jason's mull hypothesis is confirmed as a mechanism but not as the cause on this set.** All 22 plan tags came back `basis: single` — this floor plan carries **no mull markers at all**, no `MU` suffix and no nearby DOUBLE/TRIPLE label. So mull expansion had nothing to fire on. The two sides read mull multiplicity from *different notations*: the plan side wants a nearby word, the elevation side wants a `(N)` prefix. On a set that uses neither, the plan side silently counts assemblies as singles.
- **40 "doors" on a floor plan is obviously wrong.** `parse_opening_tag` classifies a suffix-less tag ≥6'6" tall as a door; that rule is over-firing.

**Order of work:** make the plan side self-consistent *first* (one parser, one classification rule), then reconcile against elevations. Reconciling two views while one view disagrees with itself produces alerts nobody can act on.

### M6 — Level Ground on the canvas (1 week)
The engine is done. What is missing is the front half: a homeowner uploads plans and gets a report. OpenTakeoff runs **fully client-side, no upload** — which is also the cleanest answer to the brief §7 copyright/ToS concern, since the architect's plans never leave the homeowner's browser.
**Exit:** a homeowner-supplied PDF produces the existing `report_from_takeoff()` JSON end-to-end, rendered by `lg_report_template.html`, with `gen_reports.py` still regenerating both samples from the one template.

### M7 — Prospective holdout (ongoing)
The prospective registry is empty — 0 of 10 registered. Everything to date is historical replay, which the contract itself flags as not a strict holdout.
**Exit:** hold 3 jobs the system never sees. Score only against those.

---

## Level Ground integration points

| Piece | Where it is now | Where it goes |
|---|---|---|
| `report_from_takeoff()` | `jnj_takeoff.py:4839` | unchanged, spine |
| `PRE_BID_SCOPE_CHECKLIST` (8 entries, the advocacy IP) | `jnj_takeoff.py:4488` | unchanged |
| `price_report()` + `MARKET_RATE_BOOK` | `jnj_takeoff.py:4702` / `:4571` | unchanged. It correctly refuses to price an uncalibrated market — keep that |
| `ingest_bid()` / `findings_from_bid()` | `jnj_takeoff.py:4753` / `:4800` | unchanged |
| Privacy bridge | `estimator_accuracy\export_level_ground_bridge_v1.mjs` + contract | **carry the contract forward verbatim** — it is the thing stopping J&J rates, costs, markup, vendor and QBO data from reaching a homeowner |
| `lg_report_template.html` + `gen_reports.py` | `Desktop\Level Ground\` | into `jnj-takeoff\levelground\` |
| Vercel site + Stripe | `Desktop\Level Ground\site\` | leave alone. Its blocker is Stripe live activation, not this project |

**One thing the brief is right about that is not yet done:** the `jnj-risk-report` skill's three-version structure (Internal / Prospect / Client) is a better fit for Level Ground's output than a single report type. The Prospect version — plain language, per-item dollar-exposure ranges, "Addressed in Scope" vs "Needs Discussion", total unmitigated exposure — is close to what `report_from_takeoff()` emits but not identical. Worth reconciling the two formats before M6, not after.

---

## Upstream discipline

OpenTakeoff moved the same day I cloned it. Apache-2.0 permits a hard fork at any time; the cost is losing improvements. So:

- Branch `j-and-j`, **additive changes only** where possible — new files, new `SheetRole` entries, new adapters. `AGENTS.md` and `FEATURES.md` are written for agents extending the codebase; follow their patterns.
- **Put the residential taxonomy and window/door schedule work upstream as PRs.** They are generically useful, the maintainer is active, and merged code is code you no longer maintain.
- **Never upstream:** the rate book, `calibration.md`, market bands, the Buildern mapping, anything Level Ground. That is the moat.
- Pin a known-good commit; rebase deliberately, and re-run `run_golden.py` after every rebase.

---

## The eval harness

The brief says build it first if it does not exist. **It exists, three times over, and is better than what a fresh build would produce:**

```bash
python jj.py verify
```

runs all five gates — golden measurement suite (6 houses, 22 asserts, 13 comparisons), engine self-test (~25 assertions each pinned to a real Jason number), fixture certification, offline system test, readiness. Verified GREEN today.

Two gaps worth closing, both already identified in `ROADMAP.md` Phase 0:

1. **Separate "differs from Jason" from "is wrong."** Jason's Inputs-block truth comes off the printed SQFT schedule, so a traced 5,529.8 against his 5,529 currently scores as an error. The ruling is settled (*measurement is the authority, schedule is the cross-check*) but not yet implemented. **This must land with M1** or the first bridged measurements get graded as failures and the system learns to copy the schedule.
2. **Permutation-invariant room scoring.** Plans routinely label three bathrooms all "BATH"; there is no numbering rule to learn. Score the *set* of bath-vectors against the set of truth bath-vectors. Baths 2/3/4 carry the same item set (21/21/20 rows), so a permutation among them is genuinely neutral; Full Bath 1 is different (22 rows) and is identified on its own merits.

---

## Decisions owed by Jason

Carried from `ROADMAP.md`, plus new ones this evaluation raises.

| # | Decision | Blocks | Status |
|---|---|---|---|
| 1 | Paid vision calls, per-run quoted | v1-autonomous Phase 1 | ✅ approved 2026-08-03 — but see #6, this may no longer be the right spend |
| 2 | Room numbering rule | scoring | ✅ resolved — no rule exists; score permutation-invariantly |
| 3 | **What "reconciled" means** when plan and elevation disagree | **M5** | ✅ **resolved 2026-08-04** — match = reconciled; mismatch = alert Jason, never auto-resolve; mulls are the first hypothesis. See the M5 ruling |
| 4 | Selections — short form, infer from finish schedule, or flag? | M6 | ⬜ owed |
| 5 | The other ~18 Buildern measurement sheets | grader ceiling (42.85%) | ⬜ owed — still the highest-leverage thing Jason could hand over |
| 6 | Does v1-autonomous keep getting funded? | everything | ✅ **resolved 2026-08-04** — no. Harvest the corpus, truth, grader and source; archive the 13 GB of run exhaust. See [CONSOLIDATION.md](CONSOLIDATION.md) |
| 7 | Does Level Ground run client-side on the OpenTakeoff canvas? | M6, plan copyright | ✅ **resolved 2026-08-04** — Jason: *"doesn't matter, whatever is best."* **Decision: client-side.** The architect's plans never leave the homeowner's browser, which retires the copyright/ToS exposure in EVALUATION §7 at zero cost; no upload path, no storage liability, no per-report infra; and it reuses the canvas being adopted anyway |
| 8 | Promote the spine out of `~/.claude/skills` into a git repo? | M0 | ✅ **resolved 2026-08-04** — yes, folded into [CONSOLIDATION.md](CONSOLIDATION.md) Step 1 |

---

## What I would do first, if it were one thing

**M1.** M2 is already done — the finding held, in a narrower form than first stated. M1 is the thesis: if v1's scale feeding OpenTakeoff's tracer holds 6/6 green on the golden suite, the architecture is settled and everything after it is ordinary work.

If the bridge does *not* hold, that is worth knowing in two days rather than two months — and it would be a real argument for the brief's original plan.

---

## Ground rules, carried forward unchanged

- **Printed dimensions are truth; pixels are a cross-check.** Never measure pixels when a dimension string, schedule, or SF table exists.
- Every number carries **source (sheet + location) and confidence**. Low confidence → REVIEW, never a silent guess.
- Conflicts are **flagged, never auto-resolved**.
- Output maps 1:1 to the estimating template's line items and units (internal) or the risk-report format (Level Ground).
- **Holdout jobs stay held out** — and currently there are none. M7 fixes that.
- **Never wrong beats always answers.** Both codebases independently arrived at this. Do not trade it for coverage.
