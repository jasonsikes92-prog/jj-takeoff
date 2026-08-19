# Overnight self-calibration — run state

**Mandate (Jason 2026-08-18):** pull every Buildern takeoff; cross-reference my
measurements vs his (his hand measurements = ground truth); cross-reference pricing
vs POs/bids/actuals (QBO) + sub invoices (his Gmail + Keli's IMAP); fix what's wrong;
keep going until each thing works. Deliverable: clickable per-job viewers + scorecards.
Output style: brief. Relay rule: ~60% context → handoff + fresh session.

## Access (all verified 8/18 evening)
- Buildern: Jason's Chrome, logged in (app.buildern.com). Fallback: JARVIS BUILDERN_* env.
- QuickBooks: QBO MCP connector (J & J Custom Homes, LLC).
- Jason Gmail: MCP connector. ~201 invoice threads/60d.
- Keli mailbox: JARVIS `agent/email-tool.js` + KELI_IMAP_USER/PASSWORD in JARVIS/.env
  (read-only IMAP; pass {user, pass} to resolveAccount).

## Rules
- Read-only in Buildern/QBO/email. No sends, no approvals, no external posts.
- Engine fixes: allowed, gates green after every change (golden 6/6 + self-test +
  battery + cert refresh), each committed with evidence for morning ratify.
- Rate-book VALUES: proposals only, never edited.
- His-vs-mine mismatch: classify DEFECT / CONVENTION (cal #70 template) / MY-ERROR.
- cal #71 approved: schedule as face-selector, never quantity.

## Phase status
- [x] Workspace + gitignore (`training/` raw, `docs/training/` committed)
- [ ] A. ACQUIRE — Buildern: enumerate projects → per job: measurements export,
      takeoff, estimate, budget+actuals, bids, approved POs, plan PDFs → `training/<job>/`
- [ ] A2. QBO per-job actuals (watch duplicate-project zeroing)
- [ ] A3. Email sweeps (Jason MCP + Keli IMAP) → sub invoices per job
- [ ] B. MEASURE — engine takeoff per job vs his measurements → scorecards
      (MATCHED/CLOSE/DISCREPANT/NOT_PRODUCED; compare_to_buildern.py pattern)
- [ ] C. PRICE — estimate vs bid vs PO vs actual vs invoice per trade → rate ledger
- [ ] D. FIX — defects → engine patches, gates, commits
- [ ] E. DELIVER — per-job viewers + master index + morning report

## Buildern acquisition pattern (PROVEN on Roberts 8/18)
- Projects list: `/projects/list` → toolbar download icon → "Download Excel"
  (⚠ clear any leftover search filter first — box persisted "rober" once).
- Per project (internal id from the row link; Roberts = 29093):
  - `/projects/<id>/takeoff/measurements` → download icon → Download Excel
    (566 rows Roberts: Name/Quantity/Unit/Waste/Type/Plan)
  - `/projects/<id>/estimate/<estId>` (Estimate in left rail opens it) → download icon
    (602 rows Roberts: Name/CostType/CostCode/Qty/Unit/UnitCost/Markup/...)
  - Takeoff → "Plans" tab = plan PDFs; Files = documents; Budget, Bid Requests,
    PO and Subcontracts per project as needed.
- Downloads land in `C:\Users\jason\Downloads` → copy to `training/<job>/`.
- SPA is slow: screenshots time out while loading — wait + retry, don't re-click.
- "All Items" global exports: POs ✓ done. Bills/Client Invoices have NO export UI —
  use QBO MCP instead (bills are QB-synced).
- A Buildern update modal appears on fresh dashboard loads — "Try it out now"
  dismisses it (Escape does not).

## Staged so far (training/)
- buildern_projects.xlsx — 69 projects (16 cols incl. contract/actuals/profit)
- buildern_purchase_orders.xlsx — 167 POs, $2.08M approved
- roberts/measurements.xlsx (566 rows) + roberts/estimate_items.xlsx (602 rows)
- Also in Downloads already (Jason's own exports): "Measurements - Roberts
  Residence (1).xlsx", "Roberts Residence - Mon Aug 17 2026.pdf" (takeoff PDF),
  Peterson profitability xlsx.

## Priority jobs (real activity: WIP%>0 or known estimates)
Roberts PR-051 ✓staged · Waddell PR-041 · Thomas PR-050 · Villanueva PR-054 ·
Miller PR-066 · Hernandez PR-042 · Holbrook PR-043 · Pace Kinards PR-095 ·
Burns PR-091 · Watkins PR-067 · Lankford PR-046 · Peterson PR-049 · Wilson PR-077 +
PR-044 · Talbot PR-048 · Stiggers PR-102 · Mason PR-116 · Bouchard PR-039 ·
Hetherington PR-065 · Bozeman PR-093 · estimates-only: Davis PR-109 ·
Zegarra PR-114 · Guarino V3 PR-111 · Show PR-097 · Dugger PR-108 · Dolsen PR-038.

## Log
- 8/18 eve: run initialized. cal #71 committed (9ddbb19). Autonomy lane v0 committed
  (a7f501b): garage zero-ink 0.22%; gaps = outer-face shape, floor-plan envelope,
  independent second side.
- 8/18 night: access verified ×4 (Buildern Chrome, QBO MCP, Jason Gmail MCP, Keli
  IMAP via JARVIS env). Projects + POs + Roberts measurements/estimate staged.
  Jason mid-run: BRIEF output only; nothing else needed from him; machine stays on.
- NEXT: loop the priority jobs through the acquisition pattern (collect internal
  project ids from the list rows), then Phase A2 QBO, A3 email sweeps, then B.
- 8/19 ~00:20: acquisition progress — **staged m+e: Roberts (29093), Pace Kinards
  (51861, basement house, full takeoff), Mason (65138, 5 measurements incl. exterior
  wall 2935 ft² / roof 3379 ft² — estimate lines consume the takeoff quantities at
  his composite rates, e.g. framing material $2.50/ft² wall, roof $1.75/ft², dry-in
  labor $32.5k lump).** Estimate-only staged: Waddell (26293), Thomas (28956),
  Villanueva (29560), Miller (37524), Hernandez (26530), Holbrook (26989), Stiggers
  (58690). No-takeoff confirmed: Waddell, Thomas, Villanueva, Miller, Holbrook,
  Stiggers. **Queue: Davis, Zegarra, Guarino V3, Show, Dugger (active-estimate
  cluster — likely takeoffs), Burns, Watkins, Wilson×2, Dolsen, then Lankford,
  Peterson, Talbot, Bouchard, Hetherington, Bozeman (pricing-only era).**
  Reliability notes: search box needs find→form_input (never type); row click only
  after a screenshot confirms the row; project lands on its last-open module —
  takeoff-era jobs land in the plan viewer (URL /takeoff/<planId>), navigate to
  /takeoff/measurements directly. Chrome extension dropped once (~00:05) and
  recovered on retry — if it drops again, JARVIS BUILDERN_* creds are the fallback.
  Measurements download menu: the icon row is columns(1407)/copy(1445)/download(1484)
  at y=136; menu item "Download Excel" at (1443,187). If the first click lands during
  page load the menu doesn't open — retry the pair.
- 8/19 ~01:00 STRETCH 1 COMPLETE. **Measurement-rich corpus staged (m+e): Roberts
  566 rows, Pace Kinards 707 (51861), Mason 59 (65138), Davis 745 (63248), Zegarra
  745 (64238), Guarino V3 561 (63505), Show 789 (53711), Dugger 752 (63242).**
  Estimate-only: Waddell 26293, Thomas 28956, Villanueva 29560, Miller 37524,
  Hernandez 26530, Holbrook 26989, Stiggers 58690, Davis/Dugger/Guarino/Zegarra/Show
  estimates too. All takeoff-era jobs share the category template (Inputs 14 / Site
  Work 3 / Foundation 4 / Shingles 8 / Metal 7 / Windows+Doors 27 / Trim 8 / ...).
  Guarino V3 Inputs expose the driver model (SF FIRST FLOOR 2637 manual, Room
  Perimeters 1067.6 ft traced on "Areas" plan). Mason estimate proves the
  takeoff→estimate quantity wiring at his composite rates.
- 8/19 ~01:45 STRETCH 1b: **Burns (45687) m+e staged — full takeoff, $423,795.70
  estimate. Watkins (37525) m+e staged (2 trim measurements: fascia 86.26 ft,
  crown 344.46 ft on "Watkins (2-4-26)" plans).** Corpus: 10 jobs with
  measurements, 17 estimates total.
- **Plan-drawing PDFs staged:** Roberts (Jason's 8/17 export), Davis 83MB@300dpi
  12 sheets, Pace 23MB 5 sheets. Export recipe: Takeoff→Plans → Select→Select all
  → download icon → dialog: header checkbox, All drawings, 300 DPI, Show sizes
  breakdown → Download. ⛔ DO NOT navigate away while "Preparing download" toast
  is live — a forced navigation killed Mason's render (redo Mason). QBO per-job
  revenue snapshot saved (training/qbo_sales_by_customer.json, 31 jobs).
- 8/19 ~02:30 STRETCH 2: **ground_truth.json built — 5,400+ measurement rows
  normalized across 8 full-takeoff jobs** (parse_corpus.py committed; categories =
  the room-scoped template incl. Bath 2/3/4, Bedrooms, 6'8/8' Doors...). Inputs
  driver table cross-checks memory (Davis 3551 ✓, Zegarra 2127+2020 ✓, Roberts
  2127.25 = his hand number ✓, Pace has basement 1957.85). Zegarra plans staged
  (4 sets now: roberts/davis/pace/zegarra). Wilson PR-077 estimate staged
  (wilson_pope). Guarino V3 plan render IN FLIGHT on tab 1 (watcher bm72aizo9) —
  stage from Downloads when it lands ("Guarino Residence V3 - Wed Aug 19*.pdf" or
  similar). Naive qty-matching of measurements→estimate lines = mostly
  coincidence on small ints; REAL matches need name+qty joint keys (works: Roberts
  driveway 894.7 @ $1.75/LF, silt 1005.5 @ $3.50/LF, Dugger 59 windows @ $686.90
  ASSEMBLY). ⭐ cost types seen: MATERIAL/LABOR/SUBCONTRACTOR/EQUIPMENT/FEE/
  ALLOWANCE/ASSEMBLY.
- NEXT STRETCH (in order):
  1. Stage Guarino plan PDF when landed; then renders for Show 53711, Dugger
     63242, Burns 45687, Mason 65138 (redo — killed by navigation). Recipe in
     "Buildern acquisition pattern" above; dialog dance: Select→Select all→
     download icon→header checkbox→300 DPI→sizes breakdown→Download; STAY on page.
  2. Remaining estimates (lower priority): Wilson PR-044, Dolsen PR-038, Lankford,
     Peterson, Talbot, Bouchard, Hetherington, Bozeman, Guarino V1 PR-098.
  3. Per-project Budget exports (actuals by cost code) for the 10 m+e jobs.
  4. A3: email sweeps (Jason Gmail MCP + Keli via JARVIS email-tool KELI_IMAP_*).
  5. B: engine runs on staged plan PDFs vs ground_truth.json → per-job scorecards
     (DEFECT/CONVENTION/MY-ERROR). Note: plan PDFs are RASTER exports with
     drawings burned in — for pristine vector sets check project Files section;
     the "No drawings" export option gives clean rasters.
  6. C: rate learning — name+qty joint match measurements→estimate lines →
     composite rate table with provenance; then vs POs/bids/QBO actuals.
  7. E: per-job viewers + morning report + memory/HANDOFF updates.
