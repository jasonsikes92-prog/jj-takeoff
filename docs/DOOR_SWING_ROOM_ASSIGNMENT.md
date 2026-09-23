# Door swing evidence for a served-room assignment

Some correctly located ordinary doors connect a private room to a shared living region. Room names alone previously left their class ambiguous. The engine now uses a unique current single-leaf swing as additional evidence when one side is a named bedroom, bathroom or toilet room and the other is living, kitchen, dining, combined living/kitchen/dining or circulation space.

The middle 80 percent of the drawn arc and outer half of its leaf must be continuously contained in the private room polygon and must not intersect the shared room polygon. This avoids hinge/closed-tip wall coordinates while testing more than one probe point. Holes, conflicting source hashes, ambiguous symbols, missing room evidence and overlapping room regions prevent assignment. An outswing into the shared room does not cause a hollow-core or passage guess. Bedroom-to-closet and bathroom-to-closet distinctions remain unresolved by this rule. Explicit room classes and sourced project core/hardware selections retain precedence.

The assignment is labeled `resolved_from_native_swing_and_room_evidence`, with the room, opening and symbol hashes plus the actual arc/leaf portions used. Saved company rules then supply the corresponding core and hardware references. Policies, draft quantity sources and bid scopes retain the automatic room-assignment evidence and review flags, including when the opening role itself was previously reviewed. No product fit or purchase approval is implied.

## Verified development case

The Burns case without individual wall/opening/room-use answers resolves three bedroom entries and one bathroom entry through swing evidence. Those four reference doors inherit solid cores and privacy hardware. Four other ordinary doors retain passage-hardware references. Eleven door roles and 13 window roles remain inferred; nine opening roles and complete scope remain unresolved.

125 targeted tests passed, including outswing rejection, private-to-private ambiguity, stale symbol and room evidence, polygon holes/overlap, project precedence and inference provenance through policy, quantities and bids. A real HTTP wall edit withholds the affected room assignment, core and hardware; restoration recovers all four swing-supported assignments. Source archive hashes and Roberts' live snapshot/workbook revision 22 are unchanged.

Evidence: workspace `outputs/door_swing_room_inference/checks.json`, `opening_schedule.json`, `after_wall_edit.json`, `opening_bid_scope.json`, `opening_bid_draft.md`, and `estimate_draft.json`. Verifier: `work/phase3/verify_door_swing_rooms.py`.

This is a development-plan estimating interpretation. It does not establish independent accuracy, full door/room coverage, selected products, current prices or whole-house completion. The bid remains unsent and purchasing remains unapproved.
