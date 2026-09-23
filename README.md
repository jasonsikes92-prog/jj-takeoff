# JJ-Takeoff

The J&J Custom Homes takeoff and estimating program. Reads a residential plan set and produces
the measurements an estimate needs — plus the Level Ground homeowner report that runs on the
same engine.

**Consolidated 2026-08-04** from eleven locations into this one repo. `~\.claude\skills\jnj-estimate-takeoff`
is a junction pointing here, so the `jnj-estimate-takeoff` skill resolves unchanged.

> ## ➡ Start with [HANDOFF.md](HANDOFF.md)
> Current state, what changed, what to do next, and what's owed. This README is just the map.

## Prove it works

For a fresh plan, use `python jj.py new-plan --plan <plan.pdf> --job-dir <new-job-folder>`.
Optional `--project-inputs <inputs.json>` supplies project facts, overrides, door schedule and jurisdiction.
This saves the original plan, company-profile snapshot and sheet inventory; it does not produce a completed estimate.
After source-bound sheet/view review, run `python jj.py measure-plan --job <new-job-folder>`.
Required reviews are enforced, existing jobs/drafts are preserved, and quantities/prices are not copied from another house.

Calculate that job with `python jj.py estimate --job <new-job-folder>/draft_takeoff --output <new-snapshot.json>`.
This exports the same JSON draft and unresolved-scope report as the local measurement review; it does not declare the estimate complete.
Add `--workbook <new-workbook.xlsx> --template templates/estimate-template.xlsx --node <node-executable>` to calculate and export Excel in one command. The exporter receives that exact newly calculated snapshot. If Excel export fails, the command fails and retains the snapshot so export can be retried without recalculating.
An explicit job is required, and existing output files are never overwritten. The output directory must already exist.
For older jobs with their own three `Takeoff` scripts, use `python jj.py estimate --job <legacy-job-folder> --legacy`.

Generate a current opening quote request with `python jj.py opening-bid --job <new-job-folder>/draft_takeoff --output <new-bid-directory>`.
This saves `request_DRAFT.md`, `scope.json` and a dated source manifest. Window installation follows the saved individual-unit policy; door assemblies, hardware and exterior trim have separate scope responses. Unknown selections and inferred openings remain visible. The command sends nothing, preserves existing outputs and refuses publication if the job changes during generation.

Generate a drywall quote request with `python jj.py drywall-bid --job <new-job-folder>/draft_takeoff --output <new-bid-directory>`.
It exports reviewed wall and ceiling references, mixed-ceiling breakdowns where reviewed, saved estimating practices and explicit missing quantities. Finish selections, complete coverage and pricing still require review. It sends nothing and preserves existing outputs.

For a job with a validated trade-routing index and published estimate, run `python jj.py trade-scopes --index <bid-index.json> --output <new-directory>`.
This generates an unpriced current scope schedule for every indexed trade, including supplemental items, package ownership and unresolved work. Historical working drafts remain source references. These schedules require review before issuing bids; no messages are sent.

For a new measured job, run `python jj.py job-bids --job <draft_takeoff> --output <new-directory>` to export its supported scopes together with a linked index. Available opening, opening-framing, drywall, roofing and company-practice requests retain their individual source fingerprints. Missing prerequisite reviews appear in the index. Company additions supplement the related trade scope; reconcile overlap before pricing. This is incomplete trade coverage, not a complete-house bid book. Existing exports are preserved and nothing is sent.

An optional `roof_edge_review.json` links a separate editable edge review within the same job to the current roof faces. Roofing requests then include LF references separately from roof-face SF. Edge edits recalculate; changed roof faces or linked configuration require reconciliation. Linked source files are checked during export and case retrieval. These references do not establish accessory coverage, laps or whole-stock purchasing.

The LEVEL GROUND reviewer case workflow also returns a drywall bid draft when the job has a saved drywall-practice mapping. It carries current room wall/ceiling references, the frozen opening-deduction and billing-waste practices, and unmeasured surfaces. Source changes invalidate retrieval; no whole-house drywall total, material order or homeowner release is inferred.

Export Excel with `python jj.py export-workbook --snapshot <new-snapshot.json> --template templates/estimate-template.xlsx --output <new-workbook.xlsx> --node <node-executable>`.
The Node runtime must provide `@oai/artifact-tool`. This preserves template markups, clears unused template prices, includes supplemental cost owners and exports source notes and unresolved work.
The workbook is a draft snapshot. Quantity/rate changes withhold dependent prices until the job is recalculated and exported again; editing Excel does not update the saved takeoff.
`--check-only` reconciles every exported quantity and cost in memory without saving. Native Excel recalculation and a complete house estimate remain separate verification steps.

The current new-plan workflow also extracts editable native wall candidates and
retains unmarked company scope allowances. See [method and limits](docs/NEW_PLAN_WALL_CANDIDATES.md).
This does not establish complete room geometry or wall material quantities.

The new-plan roof overlap audit requires the pinned geometry dependency:
`python -m pip install -r tools/requirements-geometry.txt`.
It measures overlap and surface-area bounds without changing source geometry;
an independently reviewed roof outline is still needed to assess missing scope.

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
