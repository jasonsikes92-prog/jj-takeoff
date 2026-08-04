# Start here

**Written 2026-08-04, at the end of the consolidation.** Two goals, in Jason's words: *launch Level Ground*, and *push J&J to a takeoff I can trust*. This says where to work, what to do first, and why in that order.

## Where to work

```
C:\Users\jason\JJ-Takeoff\
```

That is the whole program. `~\.claude\skills\jnj-estimate-takeoff` is a junction pointing here, so the skill still resolves. Prove the system before trusting it:

```bash
python jj.py verify
```

Expect four gates OK. Two are red and **were red before the consolidation** — the offline system test and readiness — both from the 8/3 vision-client landing in the old `estimator_accuracy\`. They test the autonomous track, which is stopped. They do not block anything below.

Before shutting the laptop: `python jj.py save`. This tree is outside OneDrive; the `_backup\` mirror is its safety net until the GitHub remote is live (`eval\push_to_github.ps1`, needs `gh auth login` once).

---

# Goal 1 — Launch Level Ground

## The finding that changes the plan

**A Level Ground pre-bid report needs six numbers.** Not 230.

```
heated_sf           Heated living area
framing_sf          Total area under roof
roof_surface_sq     Roof area
foundation_wall_lf  Foundation / slab edge
slab_area_sf        Slab footprint
basement_area_sf    Basement footprint
```

Everything else in the report is **static advocacy content** — the 8-item `PRE_BID_SCOPE_CHECKLIST` (the scopes builders most often leave out, each with a dollar band and the question to ask) and 4 `STANDARD_UNKNOWNS`. Zero measurement.

**The engine already measures those six at golden-suite accuracy**, on real plan sets, today:

| | measured | Jason / ground truth | delta |
|---|---|---|---|
| `heated_sf` (wilson) | 3,913.6 | 3,913.6 | **0.0%** |
| `framing_sf` (roberts) | 3,431.0 | 3,431.0 | **0.0%** |
| `framing_sf` (wilson) | 5,792.6 | 5,792.6 | **0.0%** |
| `foundation_wall_lf` (wilson) | 155.9 | 156.0 | −0.0% |
| `basement_area_sf` (wilson) | 1,371.5 | 1,372.0 | −0.0% |
| `slab_area_sf` (holbrook) | — | — | +1.7% |

**Level Ground's entire measurement requirement is already solved.** Its remaining blockers are business, not technical. That is the opposite of how this project has been sequenced.

## Do these, in order

### 1. End-to-end dry run on one real plan set — the only untested link ⭐
The six measurements are proven. `report_from_takeoff()` is self-tested. **What has never run is the join**: `gen_reports.py` currently injects a *hardcoded sample* takeoff, not a real `run_takeoff()` result.

Take one golden house — roberts is ideal, it's a real 12-sheet set *and* it's the print-rescaled one, so it proves the scale guard in the same pass — and drive it all the way: `run_takeoff(plan, sheet_map)` → `report_from_takeoff()` → `lg_report_template.html`. Read the output as a homeowner would.

**Exit:** a real rendered report from real plans. Time it. That number is your unit cost per sale.

### 2. Run the scale guard as step zero of every intake
```bash
python eval/scale_sweep.py
```
Roughly 1 set in 6 is printed off-nominal. Roberts says `1/4" = 1'-0"` and measures **16.714** pt/ft — trusting the note understates **every area by 14.5%**. On a homeowner-facing report that is the difference between advocacy and malpractice.

### 3. Stripe live activation — the actual launch blocker
Per `levelground\TODO.md`, the live buy button is still in **test mode**: a real customer cannot pay. LLC and EIN are done (7/27). Remaining: activate live mode, restricted `rk_` key, live webhook endpoint, 4 env vars in Vercel as Sensitive, then one real $99 charge and refund. Steps are in `levelground\STRIPE.md`.

**Until this is done, nothing else about Level Ground matters.**

### 4. Then the bid-gap half
`ingest_bid()` / `findings_from_bid()` are built and self-tested (6 findings on the test bid, `bid_gap $587,400`). This half is **reading and reconciliation — an AI strength** — not pixel measurement. It is the second sale to the same customer and it is close to free.

## What NOT to do
Do not wait for the takeoff engine to get better before launching. Level Ground needs six numbers and it has them.

---

# Goal 2 — A takeoff J&J can trust

Ordered by **dollars**, not by how interesting the problem is.

### 1. The five live rates — Jason, ~15 minutes ⭐⭐
L J Show came in **+17%** over your own estimate. On the 12 comparable lines: quantities **−$11.5k**, rates **+$43.6k**. Framing lumber alone was $33k — template `$14/SF` against your live **$8/SF**.

**The overage was rates, not measuring.** No amount of engine work fixes it. Open Question 1 in `docs\HANDOFF.md` has been unanswered since 7/31:

> framing lumber $/SF · framing labor · electrical $/SF · siding $/sq · drywall $/SF

This is the single highest-value thing on either list, and it is not a coding task.

### 2. Make the plan side agree with itself
Measured on L J Show p5: `window_count()` returns **22**, the reconcile's own parser returns **30 windows / 40 doors** — same page, two parsers, two answers. And 40 doors on a floor plan is plainly wrong; the "suffix-less tag ≥6'6" is a door" rule is over-firing.

**Fix this before the elevation reconciliation.** Reconciling two views while one view disagrees with itself produces alerts nobody can act on.

### 3. Then the opening reconciliation — your ruling, 8/4
> *Reconciled is when the elevations match the plan view. If there is a discrepancy I need to be alerted to look at it. The problem may come from mulled units — a double mulled unit equals 2 windows, a triple 3.*

Measured: elevations **48**, your hand takeoff **46**, plan tags **22**. The elevations are nearly right and the alert already fires. Your mull mechanism is coded (`MULL_LABELS`, `parse_opening_tag`) — but on L J Show **every plan tag came back `basis: single`**: that set carries no mull markers at all, so expansion had nothing to fire on. The two sides also read mulls from different notations — the plan wants a nearby DOUBLE/TRIPLE word, the elevation wants a `(2)` prefix.

**Exit:** openings reconcile to 46 on L J Show with evidence from both views.

### 4. Apply the fixes already built but never shipped
`elevation_opening_count()` returns 43 — the shipped estimate still carries 22. `beam_wrap_lf()` returns 289 against your 291 — not applied. Both self-tested. This is minutes of work sitting on the shelf.

### 5. Register a real holdout
The prospective registry is empty, 0 of 10. Everything to date is historical replay, and the golden fixtures say so in their own comments. Hold 3 jobs the system never sees; score only against those. **Until then, "trust" is unmeasured** — 6/6 green is regression protection, not accuracy evidence.

---

## What I would do Monday

1. **Send yourself the five rates.** 15 minutes, worth ~$43k of error on one job.
2. **Dry-run one Level Ground report end to end** and time it. That is your unit cost, and it tells you whether $99 works.
3. **Finish Stripe live activation.** Then Level Ground is launched.

Everything else is engine work, and the engine is in better shape than the sequencing has assumed.

---

## Still owed by Jason

| # | Decision | Blocks |
|---|---|---|
| 1 | **The five live rates** | every estimate |
| 2 | Selections — short form, infer from finish schedule, or flag? | full sheet population |
| 3 | The other ~18 Buildern measurement sheets | grader ceiling, stuck at 42.85% |
| 4 | Is the 8/3 `anthropic_structured_vision_client` dependency edge intended? | the two red verify gates |
| 5 | `gh auth login`, then run `eval\push_to_github.ps1` | off-machine backup |
