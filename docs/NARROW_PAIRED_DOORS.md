# Narrow paired doors and a source-review correction

The 3068 primary-bath opening on Burns PDF page 5 / printed Sheet 6 was previously described as a bifold. Native geometry and the enlarged source drawing show two separate hinges at opposite jambs. Each leaf has its own circular swing, and the two closed swing tips meet at the middle. This is a paired hinged symbol. The earlier visual interpretation mistook the two angled leaves for connected folding panels.

Paired-swing recognition now supports nominal widths from 24 to 96 inches. The existing leaf/radius, hinge-location and meeting-arc checks remain in force. A small numerical epsilon prevents exact minimum/maximum radii from failing only because of floating-point rotation. It does not widen the physical recognition tolerances.

An interior pair can now be represented as `special_interior_door` / `double_hinged`. When two distinct named interior regions and an unambiguous two-leaf symbol support it, the automatic interpreter assigns that estimating role. It remains one referenced assembly with two drawn leaves. No ordinary single-door hardware sets, product selections or purchase quantities are assigned to the pair.

## Verification and source preservation

152 targeted tests passed, including narrow paired swings, conflicting bifold reviews, room/source invalidation, bid references, quantity rules and special-assembly hardware withholding. The original reviewed Burns case now exposes the old bifold decision as `symbol_conflict_requires_review` instead of treating it as current usable scope. A copied source-review job records the corrected configuration; the original archive is preserved. This is a drawing interpretation, not an owner product selection.

The job without individual wall/opening/room-use answers now finds 19 native door symbols and infers six door roles: four ordinary interior doors and two special assemblies. It retains 13 inferred windows, leaves 14 opening roles unresolved and creates 14 candidate room regions. The primary bedroom and bathroom become separate named regions; their connecting pair and the bathroom/closet pocket acquire supported interior roles. Only the office and pantry have resolved passage-hardware functions. Ambiguous served-room classes remain unknown.

A real HTTP trial verifies the conflicting review, corrected review, one-assembly/two-leaf bid reference, and wall-edit withholding/restoration of dependent door roles. The source archives and Roberts live snapshot/workbook revision 22 remain unchanged. These are development and behavior checks, not independent estimating accuracy or full-plan completion.

Evidence is at workspace `outputs/narrow_paired_door_inference`: `checks.json`, `source_correction.json`, `source_paired_hinges.png`, `contradicted_review_schedule.json`, `corrected_review_schedule.json`, `opening_schedule.json`, `after_wall_edit.json`, and `opening_bid_draft.md`. The corrected full source-review fixture is `corrected_source_review_job`; the no-individual-answer inference fixture is `burns_job`. Use the corrected review for future source comparisons, preserving older fixtures as historical evidence.

Complete opening coverage, unnamed/ambiguous room interpretation, assembly quantities, purchasing, pricing and independent takeoff validation remain unfinished. No estimate or purchase is released.
