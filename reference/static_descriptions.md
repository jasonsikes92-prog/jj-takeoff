# Client-Facing Descriptions — Static vs. Dynamic

The estimate **Description column (O)** is read by the CLIENT. It states scope/inclusions, never takeoff math (that goes in the Takeoff Notes tab). Two kinds of lines:

## STATIC — same every job (pull from the template, leave unchanged)
These already exist in Jason's template and should be preserved verbatim. Do not overwrite. Examples:
- **Allowance disclaimer** (appears on allowance lines): "JJCH cannot be sure on exact [x], so this is an allowance. Anything above and beyond estimated will be billed at cost plus 20% via a change order. Invoice/receipt will be provided at your request."
- **Well:** the full 6"/300 ft drilling terms, casing, pump, upgrade adders, dry-well clause.
- **Septic:** "Septic system will be installed by a GA licensed septic contractor, per county specs."
- **Permits:** "JJCH cannot be sure on exact permit costs, so this is an allowance…"
- **Generic labor/process scope:** "Labor to frame the home - floor system, walls, and roof structure." · "Drywall hung, taped, and finished (Level 4) throughout, including ceilings." · "Rough-in and set each plumbing fixture." · "Temporary electric, water, and gas service during construction."

If a line is blank in the template, write a neutral static description from this style for generic items (toilets, mirrors, drain kits, form boards, mortar, sand, labor lines, etc.).

## DYNAMIC — changes with THIS plan's selections (write fresh each job)
Build these from the plan's redlines + window/door/cabinet schedules + the selections confirmed in intake. **Never copy a prior job's brand/color.** If unspecified, write generic + flag.

| Line | Roberts (example only — regenerate) | Source |
|---|---|---|
| Brick | "River Shoals brick veneer by General Shale (material)." | redline |
| Windows | "Single-hung vinyl, black exterior / white interior, Low-E double-pane, 3-over-0 grid." | redline + schedule |
| Front door | "Double wood front entry door." | door schedule + elevation |
| Rear slider | "Exterior sliding glass door to rear deck; black exterior / white interior." | redline |
| Countertops | "Estimate includes quartz or granite countertops, fabricated and installed." | selection |
| Flooring | "LVP in living areas and bedrooms; tile in master bath." | redline |
| Roof | "GAF HDZ 30-yr architectural shingles, turnkey installed." (or metal if specified) | roof note |
| Siding | "Fiber-cement board-and-batten + lap siding." | elevation |
| Tubs | "Freestanding soaking tub (master); alcove tub (hall)." | bath plan |
| Fireplace | "42\" gas fireplace with wood mantel." | floor plan note |
| Interior doors | "Hollow-core hinged; solid-core at master; pocket at closets." | door schedule |

## Voice
Concise, inclusions-focused, homeowner-readable. Format: [material/brand if selected] + [what's included] + [installed]. One line each. No prices, no math, no jargon.

## ⛔ BANNED — never in a client description (Zegarra 7/8/26)
The Buildern Import Description column rides onto the client proposal. On Zegarra it shipped raw takeoff shorthand. NEVER put here:
- **Takeoff math / derivation** — `3261 SF x4" ≈ 44.30 CY`, `base 8000 + 23x450 + 6x400 = 20750`, waste/pitch multipliers, any `=`/`x1.15`/`≈`. → Measurements tab.
- **Internal tags** — `SRC:`, `CONFIRM`, `FLAG:`, `UNLOCKED RATE`, rate-strategy notes, cross-job references. → Assumptions-to-Confirm tab.
- **Bare quantity echo** — `1 ea`, `4,415 SF`, `24.50 CY`. The qty already has its own Quantity + Unit columns; a description that is *only* a number+unit adds nothing. A scope sentence that ENDS with a qty clarifier is fine.

**Forcing function:** run `lint_buildern_descriptions("<Job> - Buildern Import.xlsx")` (`tools/jnj_takeoff.py`) before delivery; ship only at zero findings.
