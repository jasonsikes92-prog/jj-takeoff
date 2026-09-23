# Floor supply pools in new-job exports

After the source-bound company and tile-underlayment reviews, the measurement export now reads optional `floor_supply_purchase_review.json`. Current tile field geometry is converted to feet, retaining its plan origin/page, and feeds the reusable pooled supply calculator. No manually exported geometry file is needed for this path.

Mapping shape:

```json
{
  "plan_sha256": "actual-plan-hash",
  "pools": [
    {
      "id": "shared-bath-supplies",
      "field_ids": ["bath-a", "bath-b"],
      "source_file": "scope_evidence/bath-products.json",
      "source_sha256": "actual-file-hash"
    }
  ]
}
```

The product evidence file must have the same `plan_sha256` and ordered `field_ids`, plus the dated `products` object used by `floor_sundries.calculate_allowance` (board, screw_large, screw_small, bedding, setting, grout and tape). Only fields sharing the same product set belong in a pool. Fields cannot appear twice or across multiple pools. Board pools apply only to the resolved cement-board underlayment practice. If product thickness is supplied as `products.board.thickness_inches`, it must agree with the saved field requirement; absent thickness remains explicitly unverified.

Output is `draft.floor_supply_purchase_review`, containing each pool's cut/layout references, whole-package quantities, dated partial cost, evidence hashes and unassigned field IDs. Boundary edits recalculate it through the existing live snapshot route. It is a review calculation: it does not add cost rows, declare full coverage, release an order or certify supplier pricing. Product compatibility, missing installation components and existing package overlap remain separate requirements.

Verification on 2026-09-22: 36 targeted tests passed, including an actual HTTP boundary edit that changed bedding demand from one bag to two, changed-source rejection, duplicate-field rejection and thickness mismatch. The Roberts geometry replay through fresh intake/live export preserved 711 rows and matched the existing supply calculator at 151.141793235 SF and $443.03 partial pretax allowance. Products were explicitly loaded from the saved dated candidate set; no historical Roberts estimate line costs were inherited. No new-plan geometry extraction was tested by this replay.
