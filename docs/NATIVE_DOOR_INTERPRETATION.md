# Automatic door interpretation

The current engine can use supported native door symbols to close measured wall gaps as room-boundary hypotheses. This removes the prior dependency on a manually classified door before finding its adjacent rooms. These closures add no framing or finish material.

A fresh unreviewed door can receive an estimating role when its symbol is unambiguous and both faces connect to distinct, source-bound interior room interpretations. These can come from supported room names or the limited [equipment enclosure inference](EQUIPMENT_ROOM_INFERENCE.md). The role uses status `native_symbol_inference`, not `current_source_review`. A single swinging leaf becomes an interior door; a pocket leaf or a pair of hinged leaves becomes a special interior door. Paired leaves remain one assembly with two drawn panels and do not inherit ordinary single-door hardware. Garage, exterior, unsupported unnamed, stale, contradictory and ambiguous evidence is not assigned a standard interior role by this rule. Existing owner/project decisions are preserved.

The room-association engine then applies the frozen company core and hardware rules when the served-room class is unambiguous. It does not resolve a bedroom/closet or bathroom/closet distinction merely by ranking room names. Native interpretation evidence travels with the draft door and hardware quantity sources, including zero counts that depend on interpreted openings. The unsent bid labels inferred door types and requests verification. Product fit, supply inclusion, current price, complete plan coverage and purchase authorization remain separate.

A unique ordinary-door swing into a named bedroom, bathroom or toilet room can now corroborate that served-room assignment when the opposite region is shared living/circulation space. The interior arc and outer half of the leaf must stay within the private region and clear the shared region. This is an explicit estimating interpretation; outswing, special-assembly and private-to-private ambiguity is not resolved by the rule. [Method and verification](DOOR_SWING_ROOM_ASSIGNMENT.md).

Printed tags that lose their unique wall-gap association now remain in `unlocated_opening_tags` and the unresolved scope. They appear in the bid's source-review section and withhold aggregate opening/hardware quantities. Previously, an unreviewed automatic opening could disappear from the enumerated count when a geometry edit stopped matching its tag. The actual edit test exposed and reproduced this failure before the fix.

## September 19, 2026 verification

- 105 focused tests passed, plus 23 related room/enclosure/LEVEL GROUND reference tests.
- On a copy of the corrected Burns development case, deleting the office door's saved answer still produced an inferred interior swinging door, hollow core and passage hardware. The actual HTTP draft retained hardware reference counts `[5, 6, 0, 2]` and disclosed the inferred basis.
- A valid wall edit regenerated the interpretation evidence. Moving the endpoint at the actual opening so its width no longer matched the tag retained that tag as unresolved and withheld quantities. Restoring geometry recovered the counts.
- Removing all 13 saved single-hinged/pocket door answers produced six automatic door roles and three resolved passage-hardware functions. Seven door roles remained unresolved, and three inferred roles had ambiguous served-room classes. Aggregate counts stayed withheld.
- The plan's existing wall measurements/classifications and the other 20 opening decisions were retained. This was not a fresh-plan end-to-end test and did not establish independent accuracy.
- Original corrected Burns evidence and the live Roberts snapshot/workbook were unchanged. The existing Roberts review server was not restarted. Inferred records remain outside LEVEL GROUND's confirmed opening-reference totals pending review.

Evidence at workspace root: `outputs/native_door_interpretation_r4/checks.json`, `automatic_office_schedule.json`, `automatic_office_draft.json`, `changed_width_unlocated_tag.json`, `without_13_door_answers.json`, and `opening_bid_DRAFT.md`. The disposable development job retains the 13-answer removal so remaining automation gaps can be investigated directly. Earlier r1–r3 attempts retain the failed checks; r3 reproduced the disappearing-tag defect.

Remaining work includes unnamed-room interpretation, ambiguous served-room use, unsupported door/window assemblies, full-plan enumeration, independent-plan validation, and complete pricing. No overall autonomy or launch-readiness claim is made.
