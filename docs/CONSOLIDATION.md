# Consolidation — one program, one place

**Jason's call, 2026-08-04:** *"Everything needs to be combined to one file or place that it can be found so there is no confusion. We need to get rid of whatever is not useful and start fresh. This is day one. Let's use what genuinely built good and get rid of what's not."*

This is the list. **Nothing here has been executed** — it needs your yes, and the deletion column needs a separate yes from the move column.

---

## Why it sprawled

You built this across several AI systems. Each one started where it could see, not where the program was. The result is one program in eleven places, plus **13.2 GB** of run artifacts from the track that answers 0.3%.

| Where | Size | Files | Code | Last touched | What it actually is |
|---|---|---|---|---|---|
| `estimator_accuracy\` | **11,665 MB** | 89,040 | 321 | 08-04 | autonomous engine + its run exhaust |
| `.estimate_deps\` | 410 MB | 6,274 | 2,369 | 07-24 | vendored Python packages |
| `jnj_estimator_hardening\` | 298 MB | 80 | 12 | 07-22 | engine rollback copies |
| `_backup\` | 227 MB | 100 | 5 | 08-04 | the durability mirror |
| `~\.claude\skills\jnj-estimate-takeoff\` | 227 MB | 46 | — | 08-04 | **the working engine** |
| `.estimate_runtime\` | 76 MB | 141 | 0 | 07-22 | runtime deps |
| `tmp\` | 67 MB | 236 | 4 | 07-24 | scratch |
| `dugger_estimate\` | 37 MB | 83 | 7 | 07-17 | one job's takeoff |
| `Desktop\Level Ground\` | 22 MB | 1,464 | — | 07-30 | the second product |
| `outputs\` + `output\` | 20 MB | 29 | 3 | 07-30 | scratch |
| `guarino_takeoff\` | 16 MB | 82 | 49 | 06-25 | one job's takeoff |

Inside `estimator_accuracy`, the 11.7 GB breaks down as:

| | |
|---|---|
| `production_runs\` | **10,710 MB / 74,108 files** — immutable run artifacts |
| `private\` | 460 MB — **contains the 1.87 MB ground-truth file, the crown jewel** |
| `phase1_registered_inputs\` | 239 MB — the 10-job plan corpus |
| `production_run_attempts\` | 155 MB |
| `phase1_replay_history\` | 64 MB / 8,408 files |

**The program worth keeping is about 250 MB. The exhaust is 13 GB.**

---

## The one place

```
C:\Users\jason\JJ-Takeoff\                    ← git repo, THE program, ~250 MB
├── engine\
│   └── jnj_takeoff.py                        5,626 lines — the measurement authority
├── reference\
│   ├── calibration.md                        1,619 lines, 63 data points — the memory
│   ├── rate_book.json
│   └── waste_factors.md
├── templates\
│   ├── estimate-template.xlsx
│   ├── measurements-template.xlsx
│   └── pre-estimate-intake-form.xlsx
├── eval\
│   ├── run_golden.py                         6-house suite
│   ├── coverage.py                           answered fraction @ 0 false positives
│   ├── scale_sweep.py                        print-rescale guard (run at intake)
│   ├── golden\                               6 houses: plan.pdf + expected.yaml
│   └── truth\measurement_truth_v3.json       690 positive truths, 1,167 zeros
├── bridge\
│   └── ot_bridge.py                          the OpenTakeoff seam (to build)
├── levelground\                              report engine + template + site
├── jobs\                                     PR-### per-job takeoffs
└── jj.py                                     verify · backup · save · estimate
```

**Why not OneDrive:** 13 GB of run artifacts is what makes the sync slow and the tree confusing. The *program* is small enough to live in git, where history is real and disk failure is survivable. `~\.claude\skills\` gets a symlink pointing here so the `jnj-estimate-takeoff` skill keeps working with zero changes to your daily loop.

---

## Step 1 — MOVE (zero deletion, fully reversible)

Nothing is destroyed. Everything below is copied into the new tree; the originals stay where they are until Step 3.

| Move | From | Why it's a keeper |
|---|---|---|
| `jnj_takeoff.py` | `~\.claude\skills\...\tools\` | 6/6 golden houses green, ALL PASS self-test, priced L J Show |
| `calibration.md` | same | 63 numbered data points, many closed-loop cold tests vs QBO actuals. Exists nowhere else on earth |
| rate book, templates, waste factors | same | the 18-division output |
| 6 golden houses | same `tools\tests\golden\` | the only real accuracy evidence |
| `measurement_truth_v3.json` | `estimator_accuracy\private\` | 690 positive truths, 1,167 explicit zeros, sha256-bound to each plan |
| 10-job plan corpus | `phase1_registered_inputs\` | the evaluation corpus |
| `coverage.py` | `estimator_accuracy\` | correct metric, correctly chosen |
| Level Ground everything | `Desktop\Level Ground\` | live product; the report + bid-gap engine already works |
| `jj.py` | workspace root | the one command that proves all five gates |
| L J Show + Guarino + Dugger takeoffs | scattered | worked examples; each is a reproducible pipeline |

**Exit test:** `python jj.py verify` returns GREEN from the new location. If it doesn't, nothing has been lost — the originals are untouched.

---

## Step 2 — ARCHIVE (moved out of the way, not deleted)

Cold storage on the external/OneDrive archive, out of the working tree. Recoverable, just not in the way.

| Archive | Size | Why |
|---|---|---|
| `production_runs\` | 10,710 MB | 170+ immutable runs from a track that answers 0.3%. Historical record, zero daily value |
| `production_run_attempts\` | 155 MB | failed runs of the same |
| `phase1_replay_history\` | 64 MB | 8,408 replay files |
| `certification_artifacts\`, `artifacts\` | 20 MB | superseded certifications |
| `estimator_accuracy\` remaining `.mjs`/`.py` | ~10 MB | 321 code files. **Keep the source** — there is real work in the page-role and linework extraction that may get harvested later. Just not in the working tree |

**This is the "stop funding it" decision made physical.** The autonomous engine's source is preserved and readable; it simply stops being the thing you trip over.

---

## Step 3 — DELETE (needs its own explicit yes)

Only after Steps 1–2 are proven green. Every item here is either regenerable or a duplicate.

| Delete | Size | Why it's safe |
|---|---|---|
| `.estimate_deps\` | 410 MB | vendored Python packages — `pip install -r requirements.txt` rebuilds it |
| `.estimate_runtime\` | 76 MB | same |
| `jnj_estimator_hardening\` | 298 MB | engine rollback copies that duplicate `_backup\skill\`. HANDOFF already flagged these as excluded-with-reason |
| `tmp\`, `output\`, `outputs\` | 87 MB | scratch |
| every `__pycache__\` | ~1 MB | regenerated on import |
| `dugger_estimate\INVALID_DO_NOT_USE\` | — | named for what it is |

**Recovered: ~870 MB, plus 13 GB moved out of the working tree.**

### Not touched, on purpose
`.video-tools\` (366 MB), `JARVIS\`, `bezerks-*\`, `Turtle Cove POA Website\`, `_ARCHIVE\`, `_backup\`, the PR-### job folders on Desktop, and every `.xlsx`/`.pdf` on Desktop. Different projects, or your actual business records. **`_backup\` in particular stays** — it is the durability mirror for the un-synced `~\.claude\` tree.

---

## What "start fresh" means here

Not a rewrite. The measurement engine is the one thing that's genuinely good, and rewriting it would throw away 63 calibration data points and six green houses to reproduce the same code with new bugs.

**Fresh means one location, one entry point, one set of tests, and one program instead of two.** The engine keeps its history. What ends is the confusion about which copy is real.

---

## Order of operations

1. **Step 1 move** — I can do this now on your word. Zero risk, fully reversible.
2. **Prove it** — `python jj.py verify` GREEN from the new tree, golden suite 6/6.
3. **Symlink** `~\.claude\skills\jnj-estimate-takeoff` → new location so nothing in your daily loop changes.
4. **Step 2 archive** — after 2 passes.
5. **Step 3 delete** — separate yes, after you've worked out of the new tree for a few days and nothing bit you.
