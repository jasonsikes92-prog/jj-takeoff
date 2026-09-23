# Paired door symbols and room interpretation

The recognizer now supports two opposing hinged leaves and two offset sliding panels in a tagged wall opening. It uses actual line, rectangle or quadrilateral edges. Fills alone, invisible/white strokes and dashed lines do not provide door evidence. Rotated, reflected and scaled copies use the same geometric checks.

Two hinged leaves each require the existing circular swing/leaf agreement against half the opening. Their hinges must lie at opposite outer ends, open to the same side and meet at their closed swing tips within 0.25 inch. Each leaf must agree with half the nominal width within one inch. Paired recognition supports nominal openings from 24 to 96 inches wide. The narrower range exposed a previously misclassified interior pair; see [source correction and current verification](NARROW_PAIRED_DOORS.md).

Sliding hypotheses require two four-sided leaf rectangles on adjacent tracks, each within two inches of half the nominal opening width, thickness 0.75–2.25 inches, and a track gap of zero to one inch. Their overlap must be 20–80 percent of half the nominal width; one panel must lie within two inches of an outer jamb, and drawn jambs must bound both tracks at both outer opening ends. These are recognition heuristics, not code or installation tolerances. An unsupported pattern stays unresolved.

The sliding candidate is named `sliding_pair` because its drawing alone does not decide exterior sliding versus interior bypass construction. It may corroborate a compatible current source review. Neither paired symbol independently assigns a door role, a product, hardware or purchase quantities. Distinct competing symbols remain ambiguous; current contradictions are withheld, preserving the prior review as evidence.

Supported symbol footprints now close candidate room boundaries. Existing named-room interpretation can then resolve ordinary doors whose two adjacent room regions are supported. This is an estimating hypothesis with source hashes and review flags, not an assertion that every enclosed region is a complete or correctly finished room.

## Earlier development verification (48-inch minimum)

The Burns copy retains company profile 13 and reviewed sheet/view/style/scale inputs, with no individual wall, opening or room-use answers. It finds 18 door symbols: 11 ordinary swings, two pockets, two paired hinges and three sliding pairs. The five new configurations agree with the previously reviewed development drawing. The resulting 13 room-region candidates let three ordinary door roles resolve automatically: the lower-left bedroom, office and pantry. The office and pantry inherit passage hardware. Thirteen window roles remain inferred; 17 opening roles remain unresolved.

115 focused recognition/integration tests and 57 related room, quantity and LEVEL GROUND tests passed. A real HTTP edit to the wall beside the rear sliding opening withheld the affected symbol and dependent door/hardware interpretations; restoration recovered them. The bid draft carries review flags and no purchase quantities. The source archive, Roberts live snapshot and workbook revision 22 are unchanged.

Evidence: workspace `outputs/multi_panel_door_inference_r2/checks.json`, `opening_schedule.json`, `wall_enclosures.json`, `after_wall_edit.json`, `opening_bid_draft.md` and `estimate_draft.json`. The verifier is `work/phase3/verify_multi_panel_doors.py`. The earlier `outputs/multi_panel_door_inference` attempt stopped because its comparison input had deliberately removed door reviews; it is not completed verification evidence.

This plan has been used for development. Independent accuracy, complete room/door interpretation, material quantities, pricing and whole-house release remain unproven. No bid was sent and no purchase was approved.
