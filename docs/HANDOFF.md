# J&J Senior Estimator — Engineering Handoff

Last verified: **2026-08-03**, America/New_York
Workspace: `C:\Users\jason\OneDrive\Desktop\Claude`
Prior handoff archived as `HANDOFF-archive-2026-07-30-1153.md` (supersedes wherever it conflicts; that file still holds the deep vendor-extraction and roof-topology detail this one compresses).

---

## 1. Mission

Build a takeoff engine that reads a residential plan PDF and produces the measurements a J&J estimate needs, so Skip stops burning 5–8 hours per job on hand takeoffs. It has to be *provably* right, not plausibly right — every method ruling ships as a test assertion graded against real ground truth.

Two tracks run in parallel and get conflated constantly. Be clear which you're in:

- **Supervised path** — Claude reads plans using the `jnj-estimate-takeoff` skill + `calibration.md`. **This is what would price a house tomorrow.** This session ran it end-to-end on a live job and graded it against Jason's own takeoff.
- **Autonomous engine** (`estimator_accuracy\`, `jnj_takeoff.py`) — strict complete-field coverage is **9 of 154** truth fields. Long game.

---

## 2. Current State

### Verified green (re-run these; they should reproduce)

```bash
# Golden measurement suite — VERIFIED 2026-07-31 after this session's engine edits
cd C:\Users\jason\.claude\skills\jnj-estimate-takeoff
python tools\tests\run_golden.py
# -> 6 houses green, 22/22 asserts, 13/13 comparison, 0 skips, 0 errors

# Engine inline self-test — VERIFIED 2026-07-31
python tools\jnj_takeoff.py
# -> ALL PASS (includes 6 new guards added this session)
```

### One command proves all of it

```bash
cd C:\Users\jason\OneDrive\Desktop\Claude
python jj.py verify        # -> VERIFY: GREEN
```
Verified 2026-07-31, all five gates:
- golden measurement suite — 6 houses green, 22/22 asserts, 13/13 comparison
- engine self-test — ALL PASS
- fixture certification — refreshed, no drift
- offline system test — exit 0, no network, no API key
- readiness — **not_ready, 18 passed / 11 failed** = the expected baseline, not a failure

`golden_fixture_certification_2026-07-20.json` **was refreshed** after the engine edits (engine sha `D848A35…` → `6A2093D2…`; runner unchanged). Backup at `.json.bak`.

### ⚠ DURABILITY — read this first, it's a laptop

The workspace is OneDrive-synced. **`C:\Users\jason\.claude\` is NOT** — and that is where the engine, `calibration.md` (1,619 lines of method rulings) and every memory file live. One disk failure loses all of it.

- **`python jj.py backup`** mirrors those into `_backup\skill` and `_backup\memory` inside the synced tree, with sha256 fingerprints in `_backup\BACKUP_MANIFEST.json`. Last run 2026-07-31: 39 skill files + 59 memory files, fingerprints verified against source.
- **Run it before the laptop is shut down or moved, and let OneDrive finish syncing.**
- ✅ **Version control is live** (Jason authorised 2026-08-03). Initial commit `6857b39`, 704 files / 10.9 MB. `.gitignore` is **deny-by-default**: git versions the code, `calibration.md` and memory — not the ~14 GB of plan sets, production runs and artifacts. **`python jj.py save` = backup + commit in one step. Run it before shutting the laptop.**

### Delivered this session — L J Show Residence (Spalding Co., GA)

Full supervised run on a 12-sheet set: `Desktop\PR-000 - L J Show Residence\`.
- `Estimate\` — Buildern Import (flat, 10 cols) + 5-tab working workbook. 253 lines.
- **Direct $705,924 · markup $64,239 · subtotal $770,163 · $139.28/under-roof SF · $237.29/heated SF.** `lint_buildern_descriptions()` = **0**. Zero real Excel errors.
- `Takeoff\` — 40 scripts, 19 JSON intermediates, 17 evidence overlays. Reproducible: `build_estimate.py` → `addendum.py` → `write_books.py`.

### The head-to-head grade (the real output of this session)

Jason supplied **his own takeoff + estimate for the same house**. First true head-to-head.

Mine **$705,924 direct** vs his **$603,556** = **+17%**. On the 12 comparable lines the split is **quantities −$11.5k, rates +$43.6k**. Framing lumber alone was $33k — template $14/SF vs his live **$8/SF**. **The overage is rates, not measuring.**

Measurements that matched (his in parens): under-roof/framing 5,529.8 (5,529, **0.0%**) · porch ceiling 1,370.2 (1,370.7, **0.0%**) · electrical SF 4,284.2 (4,284, **0.0%**) · slab 5,529.8 (5,473.8, +1%) · interior doors 27 (26) · fascia 456.2 (421, +8%).

### Known-wrong, fix built but NOT applied to the shipped estimate

| Miss | Mine | Jason | Fix |
|---|---|---|---|
| Windows | 22 | **46** | `elevation_opening_count()` now returns **43**; estimate still carries 22 |
| Masonry SF | 562 | **1,105** | none built |
| Beam wrap LF | 121 | **291** | `beam_wrap_lf()` exists; not applied |
| Drywall | +14% over | — | room perimeter 1,527 vs his 1,220 LF |

### Blocked
- **Site work is placeholder** — no site plan in the set (the plat is a 2023 lot-division survey). Driveway/silt fence/clearing/permanent power are assumptions worth ±$30k.
- **Sheet 4 (SLAB PLAN) can't be traced** — edge is ~406 dash segments. All foundation geometry currently proxies off the sheet-2 SQFT area polygons.

### ✅ TASK 1 DONE 2026-08-03 — untracked-source guard in `jj.py save`

`_untracked_sources()` ships in `jj.py`; `.gitignore` header now states the trap. Steady state is **0 flagged, exit 0, silent**. Three corrections to the original spec, all load-bearing:

- **The specced exclusion list was wrong.** It named `production_runs/`, `certification_artifacts/`, `private/` — but the real bulk is `phase1_replay_history/` (8,379), `phase1_registered_inputs/` (2,972), `.video-tools/` (2,748), `.estimate_deps/` (2,374), `production_run_attempts/` (1,465). As specced the guard printed **18,061 paths**. The corrected list is `DELIBERATE` in `jj.py`, each entry carrying its reason.
- **The specced probe path `estimator_accuracy\_guard_probe.py` is not ignored** — `.gitignore` `!estimator_accuracy/*.py` un-ignores it, so `git add -A` just commits it and the test proves nothing. Use a path the deny-by-default net actually catches (root `*.py`, or a `.ps1` anywhere).
- **The guard must not be a blocking preflight.** It runs *after* the mirror and commit and reports by exit code only. A lint finding must never be why the laptop got shut without a backup.

Two flags found in the git plumbing while doing it: `-c core.quotepath=false` (else a mangled filename reports as octal gibberish) and `-uall` (else git collapses a wholly-untracked directory to one `?? dir/` line and a whole new folder of source slips the extension filter).

**Backlog it exposed: 117 invisible source files, resolved.** 84 committed (`d54258f`) — root build scripts, `guarino_takeoff/`, `dugger_estimate/`, `lead-reconcile/`, `estimator_accuracy/templates/`. Excluded with stated reasons: `jnj_estimator_hardening/` (1.2 MB of engine rollback copies that duplicate `_backup/skill/`) and `dugger_estimate/INVALID_DO_NOT_USE/`. Deleted `C:WindowsTemprules.json`, a 17-byte `{"giveaway":null}` written to a mangled path 2026-06-09.

### Exact next action — TASK 2: correct the L J Show estimate
**Ask Jason for the five live rates (§7 Q1) before re-pricing** — otherwise you reproduce the +17%. Then set `WINDOWS = 43` in `Takeoff\build_estimate.py`, apply `beam_wrap_lf()`, run `python jj.py estimate`, confirm `lint_buildern_descriptions()` returns 0.

### Known, not fixed (both pre-existing, neither urgent)
- **`.gitignore` line 32 `!*.md` is un-anchored**, so it un-ignores every `.md` at any depth. 49 vendored `LICENSE.md`/`README.md` files under `.video-tools/`, `.estimate_deps/` and `jnj_estimator_hardening/` rode into the **initial commit `6857b39`** on it. Harmless text, but the rule has unintended reach; un-tracking needs `git rm --cached`.
- **`jj.py save` can never report "nothing to commit"** — `cmd_backup()` rewrites `BACKUP_MANIFEST.json` with a fresh timestamp every run, so every save produces a commit even when nothing changed.

---

## 3. Decisions Made (and Why)

**Decision:** Split the roof — shingle on 6:12 only, standing-seam metal on 1:12/2:12/3:12/4:12.
**Alternatives:** Price it all as shingle, as the template assumes.
**Reason:** The low-slope planes are drawn with down-slope ribs and exposed rafter tails, and 1:12/2:12 are below code minimum for asphalt. Jason's own takeoff independently split metal by the same pitches.
**Reversibility:** Load-bearing (~$18.9k of metal). Don't revisit without re-reading sheets 8/9.

**Decision:** Keep my roof footprint (6,159 SF) over Jason's implied 7,758 SF.
**Alternatives:** Defer to his number as ground truth.
**Reason:** Mine implies a **1.57 ft** overhang against the **1.50 ft** measured as the mode of roof-edge-to-wall distance. His implies **5.54 ft**, which isn't physical — his roof-plane polygons likely overlap.
**Reversibility:** Reversible with evidence only. Grading against an *estimate* is not grading against *actuals*.

**Decision:** Mono-slab footer = **material only, no footer labor**. LF = whole-slab outer perimeter + every internal step counted **once**. **16×18 section, 3 sticks rebar** as standing defaults.
**Alternatives:** Carry nothing (first pass); a 1.64× perimeter ratio; envelope + full porch outlines.
**Reason:** Jason's rules, confirmed over four exchanges. Footer material books the thickened edge's extra concrete/steel; labor is already in `Labor - Monolithic slab` $/SF.
**Reversibility:** Settled. Encoded in `footer_lf()` and memory.

**Decision:** Corrected a footer formula that matched Jason's number to within a foot.
**Alternatives:** Keep 635.88 since it agreed.
**Reason:** It double-counted every house↔porch step and omitted the house↔garage step — two errors cancelling. Would fail on different porch geometry.
**Reversibility:** **Do not revert. Matching the number is not the same as being right.**

**Decision:** Cladding from per-wall elevation sampling (32 walls + 13 gables, 100% silhouette coverage).
**Alternatives:** Global material ratios; get a Southern quote.
**Reason:** Jason required each material measured independently per elevation. Ratios silently dropped unclassified area.
**Reversibility:** Method sound; the *masonry* output is known low (−49%) and needs work.

**Decision:** Renumbered my calibration entry from #55 → **#63**.
**Reason:** #55–#62 already existed; my entry collided. Caught during handoff verification, not during the work.
**Reversibility:** Done. `cal #63` references updated in 6 engine docstrings and 2 memory files.

---

## 4. Architecture & Key Files

**Git is live as of 2026-08-03** (initial commit `6857b39`). Before that the workspace held an *empty* `.git` stub — which is why the session environment reported "Is a git repository: true" while `git status` said otherwise. `.gitignore` is deny-by-default, so **if you add a new source file, confirm it is actually tracked.**

### Modified this session
- **`~\.claude\skills\jnj-estimate-takeoff\tools\jnj_takeoff.py`** — six new functions, each with a self-test asserting against a real Jason number. Backup `jnj_takeoff.py.bak` predates the session.
  - `parse_opening_tag()` / `_split_wh()` — J&J opening tags. `10080`=10'×8' (was misread as 1'×8'), `80100`=8'×10', `(2)3060SH`=2 lites, `1260` sidelight preserved.
  - `elevation_opening_count()` — counts openings off **every elevation**, derives trim LF from the same count, `ok=False` when plan and elevation counts diverge >20%.
  - `reconcile_roof_footprint()` — footprint must reconcile to under-roof + measured overhang; flags too-small **and** too-large traces.
  - `cladding_completeness()` — every measured SF must land in a material bucket.
  - `footer_lf()` — outer perimeter + every internal step, each counted once.
  - `beam_wrap_lf()` — includes verticals down every porch post.
- **`~\.claude\skills\jnj-estimate-takeoff\reference\calibration.md`** — now **1,619 lines**; added **data point #63** (L J Show head-to-head, ~90 lines).

### Created this session
- **`jj.py`** (workspace root) — the single entry point. `verify` proves all five gates,
  `backup` mirrors the un-synced assets, `status` shows what's at risk, `estimate` rebuilds
  the active job. **Start here.**
- **`estimator_accuracyefresh_golden_fixture_certification.py`** — re-certifies after an
  engine/runner change. **Refuses to certify unless the golden suite is green right now** —
  a certification that outruns a passing suite is worse than a stale one. Previously manual,
  which is why it silently never happened.
- **`Desktop\PR-000 - L J Show Residence\Estimate\`** — both workbooks.
- **`Desktop\PR-000 - L J Show Residence\Takeoff\`** — full reproducible pipeline. `build_estimate.py` (measured quantities → rate-book match) → `addendum.py` (fills missed scope, keyed by line **index** to dodge name collisions) → `write_books.py` (prices, markup, writes workbooks). Evidence overlays under `Takeoff\evidence\`.
- **Memory:** `feedback_count_openings_on_elevations.md` (new); `feedback_confirm_foundation_type.md` and `project_passive_income_venture.md` (appended — the latter carries the new **Level Ground code-minimum checker** design); `MEMORY.md` index updated.

### Looks touchable but isn't
- **`jnj_takeoff.py.bak`** — rollback point.
- **`Downloads\Show Residence - *.xlsx / .pdf`** — Jason's ground truth. Read-only.
- **`estimator_accuracy\SENIOR_ESTIMATOR_V3_HANDOFF_2026-07-26.md`** — good context, **stale on pricing**.
- **`golden\burns\expected.yaml` `roof_line_ft: 624`** — measures double-drawn linework; real unique length ~426. Passing assertion; changing it needs its own verification.
- **`estimator_accuracy\production_runs\`** — 170+ immutable runs. Never edit in place.

---

## 5. Gotchas & Hard-Won Knowledge

*(Prior sessions' gotchas remain in the archived handoff. These are new.)*

- **A 45°-rotated wing foreshortens by 0.7071 on *both* cardinal elevations.** The 10'-0" garage doors measure 7.06 ft as drawn. Measuring cladding straight off elevations under-counts that wing 29%. Caught only because the doors appear in two views.
- **Dimension lines are broken around their centered text.** A naive read returns half. Full span = leftmost run start → rightmost run end. Made every sheet look mis-scaled (~8.8 pts/ft vs the true 18.0).
- **Regress span-vs-feet per sheet**; it separates true scale from a constant end-tick shortfall (13.4 pts on p5, 6.7 on p4, ~0 on p6). All sheets were at printed nominal, R² ≥ 0.99999.
- **Search a generous y-window for elevation grade lines.** First pass cut off the rear/right base and locked onto a *roof* line 208 pts high, so the "wall band" sampled roof.
- **Texture classifiers silently drop what they can't classify** — invisible under-bid. Always report coverage %; fill unclassified from nearest neighbour. Jason caught this live.
- **Shingle vs lap can't be split by hatch orientation** (both horizontal). Use horizontal-run *continuity* — lap runs unbroken, shingle breaks into tabs. Even then lighter-shaded roof planes misclassify, which is why roof comes off the roof plan.
- **`roof_zone_surface()` solved ppf 19.94 against a verified 18.00** and left 61% unassigned. Don't trust it on this kind of set.
- **`trace_footprint_clean` / `trace_enclosed_region` are unreliable on dashed linework** — returned 80–99 SF for a 5,500 SF building. `trace_footprint` (all-ink) converged across three sheets to 0.6%.
- **Rate-book name collisions.** `q('Windows','Windows',…)` matched an **ASSEMBLY** row at $0 and silently zeroed $8,800. Key by line **index**. ASSEMBLY rows must carry qty 0.
- **Template unit labels lie.** `#4 Rebar 20" Sticks` prices **per 20-ft stick** despite a "LF" unit — I ordered 775 sticks instead of 39. Trust the $/unit basis, not the label or the group name.
- **Reading Jason's Buildern export:** exclude GROUP + ASSEMBLY rows and "Don't calculate" lines, reconcile to his stated **Builder Fixed Cost + Allowances**, never a raw sum. A live `Footer Labor` parented to *Crawlspace: Block walls* is a crawl artifact ($12,700 here).
- **His takeoff quantities are RAW with waste in a separate column. Compare raw-to-raw.**
- **Size a disagreement in dollars before chasing it.** I spent three hypotheses on a footer gap worth **$686 (0.089%)** while a 6% error on framing lumber was worth $4,600.
- **Check calibration data-point numbering before appending.** I collided with an existing #55.

---

## 6. Conventions In Play

- **Address Jason by name at the start of every response** (`~\.claude\CLAUDE.md` §10).
- Global `CLAUDE.md` governs: surgical changes, re-read before editing, verified completion ("done" needs proof), never iterate blind on visual work.
- **`calibration.md` is the durable memory.** Every method ruling and cold-test result goes there as a numbered data point. **Now at #63 — check the max before appending.**
- **Every new engine function ships with a self-test line** in `_verify_selftest()` asserting against a real Jason number. `python jnj_takeoff.py` must print `ALL PASS`.
- Probes wired in `run_golden.py`, expected values in `golden\<house>\expected.yaml`, **each carrying inline provenance**. Tolerances: 0.0–0.5% deterministic, ~3.5% geometry. A tolerance wide enough to never fail is worse than no assertion.
- **Refresh `golden_fixture_certification_2026-07-20.json` after any engine or runner change** or the readiness guard fails. *(Outstanding — see §2.)*
- **Client-facing Descriptions carry no takeoff math, internal tags, or bare quantity echoes.** `lint_buildern_descriptions()` must return 0 before shipping.
- Per-line markup **15/7/7/7/8/15**; **no O&P or contingency lines** (Buildern summary handles those). Waste: shingle/metal +15%, concrete/siding/masonry/insulation/drywall/tile +10%, counts +0%.
- Zero paid API calls. Keep `OPENAI_API_KEY` unset for verification. No subagents unless Jason asks.

---

## 7. Open Questions

1. **What are the live rates for framing lumber ($/SF), framing labor, electrical $/SF, siding $/sq, drywall $/SF?** His file shows $8/SF lumber vs the template's $14. **Ask before re-pricing** — this is the whole +17%.
2. **How do you pick up interior bearing lines without a framing plan?** My footer carries zero interior bearing; area polygons can't show a step inside the heated area.
3. **Does J&J's footer section vary by span, or is 16×18 universal?**
4. **Should foundation quantities come off sheet 4 rather than the sheet-2 area polygons?** Needs dashed-edge tracing solved.
5. **Three findings raised in Jason's own estimate, unconfirmed:** metal roof carries 264 SF against his takeoff's 2,113 SF (~$14.8k); shingle waste dropped at the handoff (~$3.5k); footer concrete 32 CY where 16×18 over 635 LF needs 47 CY (~$2.9k).
6. **Level Ground code-checker:** which jurisdictions at launch, and what's the authoritative source for adopted code + local amendments? (Design is in `project_passive_income_venture.md`.)
7. Still owed from intake: well distance, dumpster count, which pre-con soft costs to drop, porch column count, Selections-tab items.
8. *(Carried)* **Will Jason export the other ~18 Buildern measurement sheets?** Highest-leverage thing he could hand over.

---

## 8. Do Not Touch

**From this session**
- **Roof footprint (6,159 SF) and the shingle/metal split.** Settled on physical evidence. Don't "fix" toward his 8,434 SF surface.
- **`footer_lf()`'s formula.** Two earlier versions hit his number by accident and were structurally wrong. The current one is deliberately 6.1% off his raw and correct.
- **Drywall at $1.44/SF (V3).** His file uses $1.35; V3 was approved 2026-07-15.
- **Per-line markup rates and the absence of O&P/contingency lines.** J&J convention.

**Carried forward**
- **Do not modify** `templates\estimate-template.xlsx` or `reference\rate_book.json`. Regenerate normalized copies.
- **Do not edit completed folders** under `estimator_accuracy\production_runs\`.
- **Do not re-litigate** the pricing-priority design (template rates at priority 5 is deliberate).
- **Do not reintroduce color or `roof_line_review_json`** into production roof classification.
- **Do not wire `interior_door_count`.** Size tags can't distinguish hollow/solid/pocket.
- **Do not apply plane-bound arrows universally** — restricted to audited topology-refinement cases.
- **Do not initialize the prospective registry.** It fails closed by design.
- **Do not claim 98% accuracy** or call historical plans holdouts.
- **Do not make paid OpenAI calls** without an explicit call cap and USD cap; `v3_model_pricing.json` expired 2026-07-25.
- **Do not commit the big data.** `.gitignore` deliberately excludes golden fixture plan sets (226 MB), `production_runs/`, `certification_artifacts/`, `private/`, `JARVIS/`, and all xlsx/pdf/png. Git is history, not disk-loss backup — `jj.py backup` covers that.

---

## 9. Resume Command

> Read `HANDOFF.md`. Then `cd C:\Users\jason\OneDrive\Desktop\Claude && python jj.py verify` — expect **VERIFY: GREEN** across all five gates. `not_ready, 18 passed / 11 failed` on the readiness gate is the correct baseline, not a failure.
>
> **TASK 1 (untracked-source guard) is done** — see §2. `python jj.py save` now exits 0 silently; if it ever names a file, that file is genuinely not in history and needs a decision.
>
> **Run `python jj.py save` before the laptop is shut down or moved** — it mirrors the un-synced engine and memory into OneDrive and commits, in one step.
>
> The live work is the L J Show estimate at `Desktop\PR-000 - L J Show Residence\`. **Ask Jason for the five live rates in Open Question 1 before re-pricing anything** — the estimate is +17% over his and it's almost entirely stale template rates, not measurement error. Then set `WINDOWS = 43` in `Takeoff\build_estimate.py`, apply `beam_wrap_lf()`, run `build_estimate.py → addendum.py → write_books.py`, and confirm `lint_buildern_descriptions()` returns 0.
>
> Do not revisit the roof footprint, the shingle/metal split, or `footer_lf()` — all settled in §8. Do not re-derive measurements; the JSON in `Takeoff\` are the certified inputs. Confirm with Jason before changing anything outside `PR-000 - L J Show Residence\`.
