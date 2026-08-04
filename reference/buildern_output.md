# Output Format — Buildern Import + Working Workbook
J&J estimates must export in a form Jason can **import back into Buildern cleanly** to build the proposal. Always produce BOTH:

## 1. `<Job> - Buildern Import.xlsx` — the clean import (PRIMARY)
Single sheet ("Sheet1"), **flat — leaf line items only** (NO group/assembly/parent rows). Exact column order:

`Name · Cost type · Cost code · Cost title · Quantity · Unit · Unit cost · Markup · Group · Description`

Rules:
- **Cost type**: Material / Labor / Subcontractor / Equipment / Allowance / Fee.
- **Cost code / Cost title / Group**: map from J&J's Buildern cost-code list (`Downloads/"J & J Custom Homes, LLC - Cost Codes.xlsx"`, sheet "Cost Codes": col B Cost Code like `04.15`, col C Title, col E Group). My template's E code = his code without leading zero (`4.15`->`04.15`); match by `round(float(code),2)`. Write code as **text** to preserve leading zeros. If a code's Group is blank, inherit the Group of its category number (01 PRELIMINARY WORKS … 21 CLEANUP).
- **Markup** = **$ amount** = (Quantity × Unit cost) × per-line %: **Material 15 / Labor 7 / Sub 7 / Equipment 7 / Allowance 8 / Fee 15**.
- **NO Overhead/Profit line and NO Contingency line.** Jason applies O&P (his 20%) and contingency in **Buildern's Summary section**. The import carries cost + waste + per-line markup ONLY.
- **Units**: imperial, corrected (see waste_factors.md unit normalization).
- **Quantity**: order qty incl. waste.
- **Description**: **CLIENT-FACING** — a plain-English scope sentence (inclusions), optionally ending with a qty/waste clarifier (e.g. "… — 5,578 SF (incl. 15% waste)"); allowance lines keep allowance language; counts show the count. ⛔ **NEVER** put takeoff math/derivation (`3261 SF x4" ≈ 44.30 CY`, `base 8000 + 23x450 = 20750`, waste/pitch multipliers), internal `SRC:`/`CONFIRM`/`FLAG:` tags, or a **bare quantity echo** (`1 ea`, `4,415 SF`) here — those go on the Measurements/Assumptions tabs. This column rides onto the client proposal (Zegarra 7/8/26: raw takeoff shorthand shipped to the client). Enforced by `lint_buildern_descriptions()` — see the verify step.

## 2. `<Job> - Estimate.xlsx` — working / black-box backup (5 tabs)
1. **Estimate** — granular per-room/element lines (same cost + waste + 15/7/8 markup; NO O&P/contingency lines, just a note that those are in Buildern). Quantity in the Description.
2. **Measurements** — every measured line: `Cost Code · Item · Calc/basis (how derived) · Type · Waste % · Qty · Unit · Plan sheet`. Grossed dims shown in Calc (do NOT net out fixtures/openings — waste absorbs it). This is the black-and-white backup (e.g. master bath floor tile vs shower wall tile, each with its math + plan ref).
3. **Allowances** — every allowance line grouped by room, room subtotals, grand total.
4. **Selections** — `Room · Item · Allowance $ · Selected Product · Vendor · Actual Cost · Variance (live formula) · Change Order? · Approved`. Doubles as the allowance-reconciliation tracker.
5. **Assumptions to Confirm** — selections/rates/judgment calls, biggest $ movers flagged at top.

Verify before delivery: reloaded leaf-N total == in-memory total; **zero Excel error cells**; every import line has a non-blank Cost code + Group; **`lint_buildern_descriptions("<Job> - Buildern Import.xlsx")` returns `[]`** (no takeoff-math / internal-tag / bare-qty leaks in the client Description column — Zegarra 7/8/26 forcing function in `tools/jnj_takeoff.py`). Fix any finding and re-run until zero.
