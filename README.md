# JJ-Takeoff

The J&J Custom Homes takeoff and estimating program. Reads a residential plan set and produces
the measurements an estimate needs — plus the Level Ground homeowner report that runs on the
same engine.

**Consolidated 2026-08-04** from eleven locations into this one repo. `~\.claude\skills\jnj-estimate-takeoff`
is a junction pointing here, so the `jnj-estimate-takeoff` skill resolves unchanged.

## Prove it works

```bash
python jj.py verify
```

Expect: golden suite **6/6 houses green, 22/22 asserts, 13/13 comparisons**, engine self-test
**ALL PASS**, fixture certification no drift, coverage 0.3% at **0 false positives**.

⚠ Two gates are **red and were red before the consolidation** — the offline system test and
readiness (17/12 vs an 18/11 baseline). Both trace to the 2026-08-03 vision-client landing in
`estimator_accuracy\`, which added a dependency edge the production-engine snapshot rejects.
They test the autonomous track, which is stopped. See `docs\CONSOLIDATION.md`.

## Layout

| | |
|---|---|
| `tools\jnj_takeoff.py` | the measurement authority — 5,626 lines |
| `tools\tests\` | golden regression suite, 6 houses with real ground truth |
| `reference\calibration.md` | **1,619 lines, 63 data points** — the durable memory. Read before changing method |
| `reference\rate_book.json` | locked rates |
| `templates\` | 18-division estimate + measurement sheets |
| `eval\coverage.py` | answered fraction at zero false positives — the metric |
| `eval\scale_sweep.py` | **run at intake.** Flags print-rescaled sets |
| `eval\truth\` | 690 positive truths, 1,167 explicit zeros, sha256-bound |
| `eval\corpus\` | the 10-job evaluation corpus |
| `levelground\` | pre-bid report, market pricing, bid-gap engine, template, site |
| `jobs\` | per-job takeoffs |
| `docs\` | evaluation, lessons, fork plan, consolidation |

## Two rules that cost real money

**1. Never take the scale from the title-block note.** Roughly 1 set in 6 is printed
off-nominal. Roberts says `1/4" = 1'-0"` (18.000 pt/ft) and actually measures **16.714** on 187
dimension votes — trusting the note understates **every area by 14.5%**. Nothing on the sheet
discloses it. `calibrate_scale()` regresses the printed dimensions instead; `eval\scale_sweep.py`
flags a whole-set rescale in seconds.

```bash
python eval/scale_sweep.py
```

**2. Never wrong beats always answers.** A quantity that looks right and is wrong gets bid. All
ten graded jobs terminate `more_information_required` with **zero false positives**. That
property is the product — grow what it answers without ever losing it.

## Before shutting the laptop

```bash
python jj.py save
```

Mirrors this tree and the memory files into the OneDrive-synced `_backup\`, then commits.
This repo lives outside OneDrive, so that mirror and the git remote are its only backups.
