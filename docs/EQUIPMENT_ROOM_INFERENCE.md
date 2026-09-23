# Equipment enclosure inference

The engine can infer utility use for a small otherwise unnamed enclosure containing an exact WH/W.H. label inside a corroborating circular tank symbol. This is an estimating assumption about room use, not proof that the room exclusively serves equipment. It is saved as `equipment_symbol_inference`, carries the source evidence, and requires review. It does not create an equipment purchase quantity or select a heater product.

The recognition rule requires all of the following:

- One wholly contained WH label and one unique closed circular outline enclosing it, with the text near the circle center.
- Circularity of at least 0.85; symbol diameter at plan scale between 12 and 48 inches. These describe the drawing symbol, not a measured tank or a code requirement.
- An enclosure no larger than 60 SF or 10 feet in either bounding dimension, with the circular symbol occupying at least 10% of its area.
- Exactly one interior opening connection; no existing room name, confirmed room-use decision, stale room decision or unresolved boundary source.

The label alone does not determine room use. Large or multi-entry spaces, circles without a WH label, off-center/ambiguous labels, bodies crossing a boundary or hole, and existing room classifications remain outside this rule. Other equipment conventions and unlabeled fixtures still require interpretation. The rule's limits are deliberately visible and need validation across independent plans.

## Boundary source correction

The actual wall-edit test exposed a separate issue: a derived room polygon could remain in its old position because a native drawing-based wall closure reconstructed the boundary after the measured wall's classification became stale. Checking the polygon alone was insufficient.

Wall enclosure results now carry unresolved current and original wall bounds, page and scale. A local unresolved source touching a room boundary becomes `boundary_source_issues`. Those issues change the room-review binding, block native room-name inference and block equipment inference. Sources on another page/scale or away from the boundary do not block the room. Existing source-bound room reviews become stale when a new boundary conflict changes their evidence binding, even if the reconstructed polygon itself remains identical.

## Verified development result, September 19, 2026

The Burns source audit found seven unnamed regions. The water-heater space contains a WH label and circular tank symbol; the toilet, hall and other small spaces are not assigned a room type merely from their appearance or size by this change.

With the same 13 saved door answers removed, the pipeline now resolves seven door roles and four hardware functions, up from six and three. The additional utility-enclosure door resolves as a hollow-core swinging door with passage hardware. Six roles and three served-room assignments remain unresolved, so aggregate hardware quantities remain withheld. Existing wall measurements and 20 other opening decisions are still retained in this development case.

103 focused tests passed. The actual HTTP test moved the enclosure wall through the equipment symbol, verified that automatic interpretation was withheld, restored the geometry and recovered the interpretation. Original development sources and the live Roberts estimate/workbook were unchanged. No current review service was restarted.

Evidence at workspace root: `outputs/equipment_room_inference_r2/checks.json`, `schedule.json`, `rooms.json`, `altered_schedule.json` and `draft.json`. The earlier `outputs/equipment_room_inference` records the failed check that exposed the boundary-source problem. Source crops and the raw label audit are in `outputs/room_label_gap_audit`.

This plan was already used during development. The result does not prove independent-plan accuracy, complete takeoff, whole-house estimating autonomy or LEVEL GROUND launch readiness.
