# Handoff.ai / H1 — competitor intel for the virtual takeoff build

*Recon date: 2026-08-18. Sources: hands-on session in Jason's Handoff app account
(app.handoff.ai, J & J CUSTOM HOMES org), handoff.ai marketing + blog, YC launch page,
PR Newswire H1 release, Bricks & Bytes interview. Written for the JJ-Takeoff
virtual-takeoff effort — what they do, how, and what's worth cloning.*

---

## 1. What Handoff is

YC-backed "AI teammate for residential construction" aimed at **remodelers and
handymen**, not custom-home builders. Chat-first app ("Handy" agent) that produces
estimates, proposals, invoices, schedules, and — on the top plan — **AI takeoffs from
plan PDFs**. Pricing: Flex $119–149/mo, Pro $239–299/mo, **Scale $719–899/mo
(12-month commitment) is the only tier with AI Takeoffs** — i.e. the market prices
plan-reading takeoffs at roughly **$9–11k/yr**. H1 is also sold as an Enterprise API.

## 2. H1 — their takeoff engine

- **Positioning:** "first AI model for autonomous blueprint takeoffs" (launched 7/21/26).
  Raw plan PDF in → complete per-trade material takeoff out, ~**2 hours**, capped at
  **residential ≤ 5,000 SF**.
- **Architecture (as disclosed):** three layers —
  1. **Scope analysis**: trade-by-trade breakdown of what the project involves, read
     from the drawings;
  2. **Takeoff with quantities**: per-trade material list with units;
  3. **Localized costs**: pricing by ZIP.
  Inside layer 2 they run **specialized agents per trade** ("trained to interpret
  drawings the way an experienced estimator does"), reading the **full set together**
  ("a detail on page 40 changes the quantity on page 12"), with waste factors applied.
- **Training data:** the founders did customer takeoffs manually and **hand-marked
  thousands of blueprints** to build the labeled corpus; marketing claims training on
  100,000+ completed residential estimates.
- **Five measurement types:** Count (EA), Length (LF), Area (SF), Volume (CY),
  **Pitch area** for sloped roofs.
- **Turnaround honesty:** 2 hours, batch, notify-when-done. Not interactive.

## 3. Takeoff deliverables (their contract with the user)

Every takeoff returns exactly three artifacts:
1. **Color-coded takeoff drawings** — the plan set marked up per scope with a legend;
   "every measurement is marked… so you can check the AI's work line by line."
2. **Estimate** — built from the takeoff quantities (pricing applied only at this step).
3. **Summary report** — scope covered, **assumptions made**, **missing information**,
   and **plan clashes/inconsistencies between sheets** ("clash detection").

Their doctrine, verbatim: "You know exactly what was counted, how it was counted, and
what to double-check." **There is no in-app editor to correct AI measurements** — review
is against a static PDF; corrections happen in the estimate rows, not the drawing.

## 4. TakeoffBench-V1 (the "H1 benchmark")

- **15 real, permissioned, PII-stripped residential blueprint sets**, each paired with a
  **consensus-validated expert takeoff** as ground truth.
- Scores: **H1 81.6%** · **human estimators with takeoff software 77.6%** · best
  frontier model (Claude Fable) **61.4%** · eight major AI models cluster ~50–56%.
- **Access:** "The TakeoffBench-V1 evaluation harness is publicly available through the
  OpenHarbor framework; blueprint sets and ground truth are available upon research
  request." No direct repo link published — getting the data means a research request
  to Handoff.
- Note for us: the benchmark measures **autonomous** plan reading. Our method (Jason's
  drawn strokes → deterministic measurement against per-page calibrated scale) is a
  different category — human-guided — so a straight score comparison flatters neither;
  but their ground-truth sets would be excellent certification fixtures if obtainable.

## 5. The estimate engine (observed live in the app)

Ran "Estimate a 200 sq ft kitchen remodel" in Jason's account and captured the full
agent trace:

- **Pre-estimate context pack** (streamed steps): recent projects → org memories →
  markup/tax/below-the-line presets → past conversation history → **reference estimates
  with a "why it matches" justification** → "reusable pattern candidates" (consistent
  manual overrides that could become defaults).
- **Intake before drafting:** proposed a scope carried from the closest past job, then
  asked exactly **3 clarifying questions targeted at the biggest cost swings** (finish
  level, appliance package, layout moves) and waited.
- **Parametric quantity heuristics** from one number (200 SF floor): walls 800 SF,
  ceiling 200 SF, base cabinets 18 LF, uppers 12 LF, counters 30 SF, backsplash 35 SF,
  baseboard 55 LF, drywall patch 250 SF. All stated in the trace, all editable.
- **Its internal KB:** "labor in HRS using KB productivity rates and localized labor
  rates" — productivity (hrs/unit) × local wage, separate from material.
- **Self-narrated tradeoffs:** it explained that keeping the template's bundled
  "installed" pricing means "no discrete material rows to localize to a supplier."
- **Closing move:** listed every assumption, offered to accept Jason's real numbers
  ("labor rates, markup, supplier preferences, typical crew sizes") and **save them as
  org defaults**, and offered photo/plan refinement "to lock in real cabinet runs."

## 6. Money model

- Per line: Quantity · Unit · Unit cost · **Cost type (Material/Labor/Other)** ·
  Builder cost · Markup% · Client total. Markup editable per line as % or $, with
  **"Copy to group"** propagation; **profit margin (price basis) also editable per
  line** — two-way linked with markup.
- Estimate-level breakdown: cost by type → **per-type markup %** → **"below the line
  markup"** (contingency/overhead buffer) → discount → tax → total, with **profit
  margin displayed price-basis** (20% markup shown as 16.7% margin).
- Presets: default markups vs **"keep last used values"** (sticky), same for tax and
  below-the-line. Same shape as our 15/7/8 + Buildern-summary O&P.

## 7. Catalogs & rates

- **Supplier catalogs, updated daily:** Home Depot (with **"Connect to Pro account"**),
  Ferguson (plumbing/HVAC), ABC Supply (roofing/siding, login-gated). Claim of pricing
  against **60M+ SKUs**.
- **Custom catalogs outrank supplier catalogs**; suppliers are the fallback for rates
  you haven't set. Line-item panel has **"Pull catalog rate"** and **"Save rate"**
  (write-back to your own catalog) — a two-way rate book.
- Org-level **instruction presets per artifact type** (estimates, proposals, documents,
  change orders, schedules): standing prompts injected into every AI generation.

## 8. What they can and can't read off plans (their own account)

CAN: room dimensions/SF from floor plans; symbol counts across the full set (doors,
windows, outlets, fixtures — "nothing gets missed because it sat on page 14");
door/window **schedules, finish callouts, margin notes** tied to line items;
multi-trade sets (arch/structural/elevations/foundation); cross-sheet clashes.
Hand-drawn plans OK "if legible."

CAN'T: unwritten engineering values (snow loads, member sizing — deferred to stamped
calcs); custom/specialty pricing judgment (their example: $200k custom deck).

## 9. Head-to-head vs our virtual takeoff

| Dimension | Handoff H1 | Ours (JJ-Takeoff virtual takeoff) |
|---|---|---|
| Paradigm | Autonomous batch (~2 hrs), review after | Interactive: Jason draws, engine measures live |
| Accuracy authority | Model + expert-validated consensus | The sheets' own dimension chains (0.5–1.4% on Roberts) |
| Correction loop | None on the drawing; edit estimate rows | Edit-mode planned = re-stroke → re-measure |
| Scale handling | "Understands scale" (opaque) | Per-page calibration + print-rescale sweep (measured) |
| Scope ceiling | ≤5,000 SF residential | Whatever Jason draws (Roberts 3,356 SF framing certified) |
| Trade pricing | ZIP-localized generic + supplier SKUs | Decoded actual vendor rates (calibration.md, LOCKED) |
| Provenance | Color-coded PDF + assumptions report | MEASURED vs ASSUMED tags + cert pipeline |
| Cost | $719–899/mo | In-house |

Their real edges over us today: (a) **autonomous symbol counting across a full set**,
(b) **clash detection between sheets**, (c) supplier catalogs refreshed daily,
(d) the packaged three-artifact deliverable that makes the takeoff *legible* to a
non-estimator.

## 10. Components worth cloning (ranked)

1. **The three-artifact output contract** — every certified area emits (i) the
   color-coded overlay per scope with a legend, (ii) the quantities/estimate, (iii) a
   **summary report: scope, ASSUMED items, missing info, cross-sheet clashes**. We
   already have (i) and (ii) in pieces; formalizing (iii) as a required emission per
   cert run is cheap and matches the senior-estimator mandate ("done = checked twice").
2. **Clash detection as a named stage** — we already diff strokes vs the sheets' own
   chains; extend to schedule-vs-elevation counts (window/door schedule vs elevations —
   directly attacks the 22-vs-46 failure class) and report clashes explicitly.
3. **Reference-estimate grounding + "why it matches"** — before pricing a new job, pull
   the nearest past J&J estimate and state why it's comparable + what scaled. We have
   Guarino/Roberts/Davis as anchors.
4. **Targeted intake: 3 questions aimed at the biggest cost swings** — their intake asks
   only what moves the number most. Sharpen our Ask-Don't-Assume intake to rank
   questions by dollar swing.
5. **Two-way rate book UX** — "pull catalog rate / save rate" per line; our calibration
   file is the custom catalog; a per-line "save to rate book" affordance closes the loop.
6. **Parametric heuristic layer, tagged ASSUMED** — their 200 SF → 18 LF cabinets trick
   is a fast first-pass scaffold. Useful for pre-bid ballparks ONLY with our existing
   ASSUMED tag + confirm-before-cert gate (heuristics are exactly what our mandates ban
   as final numbers).
7. **Waste factors as explicit, per-trade, visible assumptions** in the summary report.
8. **Sticky "last used" presets** for markup/tax at estimate creation.
9. **(Later) TakeoffBench-V1** — research request to Handoff for the 15 sets + ground
   truth; even a subset makes an external cert fixture beyond Roberts.

## 11. What NOT to copy

- **Batch-and-wait autonomy as the core loop.** Their 2-hour black box, no drawing
  editor, and 5,000 SF cap are the cost of autonomous reading. Our stroke-driven method
  is the differentiator — it keeps the senior estimator's judgment in the loop and has
  no size ceiling.
- **Generic ZIP pricing as the default.** Their regional cost data is the placeholder
  tier; our decoded vendor rates are strictly better where we have them. Their design
  agrees — custom catalogs outrank suppliers.
- **Bundled "installed" line items** for client-facing work — collapses the
  material/labor split our markup structure and bid packages depend on.

## 12. Account facts (for future sessions)

- Jason has a working login (Chrome session), org "J & J CUSTOM HOMES", trial tier,
  onboarding 1/5. AI Takeoffs NOT enabled (Scale-plan gate → "Talk to sales").
- Recon leftovers in the account: project **PRJ-10002 / estimate EST-10002** ("200 SF
  Kitchen Remodel - Alcovy Shores", $28,134.48 draft, 17 items) created 8/18 from the
  canned sample prompt, next to the pre-seeded demo "Kitchen Renovation"
  (PRJ-10000/EST-10000). Harmless; delete if the account goes live.
