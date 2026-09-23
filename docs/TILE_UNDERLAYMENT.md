# Measured tile underlayment

The company-scope pipeline now reads optional `draft_takeoff/tile_underlayment_review.json` on every export. It joins the job's frozen `tile.floor_underlayment_by_substrate` decision to current calibrated area measurements. `/api/export-snapshot` retains the calculation and `/api/company-scope-bids` includes the fields in the unsent tile scope. Geometry changes recalculate areas and change the scope digest, invalidating quotes tied to the former scope.

This requires explicitly reviewed room/substrate assignments. Automatic tile-room classification, complete house coverage, board layout, purchase quantities and pricing are not provided by this connection.

Example mapping (replace all identifiers and hashes with actual job evidence):

```json
{
  "plan_sha256": "actual-plan-hash",
  "source_file": "scope_evidence/tile-substrates.json",
  "source_sha256": "actual-evidence-hash",
  "groups": [
    {
      "id": "bath-floor",
      "measurement_ids": ["bath-finished-floor"],
      "deduction_ids": ["shower-envelope"],
      "substrate": "wood_floor",
      "basis": "Reviewed finish-floor boundary; shower excluded, cabinets retained."
    }
  ]
}
```

The source evidence JSON must contain matching `plan_sha256` and `groups`. It can carry additional owner-answer and geometry-review evidence. Each group must have unique IDs, flat calibrated areas on one sheet and a source basis. Supported substrates are `wood_floor` and `concrete_slab`; each must exist in the job's resolved specification. A project override replaces the inherited specification; membrane overrides do not inherit cement-board thickness.

Overlapping floor groups and overlapping deductions are rejected. Deductions must be inside the field unless the reviewed group explicitly sets `clip_deductions_to_field: true` with an explanatory basis. That option subtracts only the intersection, records the area outside the field and still rejects unrelated nonintersecting deductions. Use it for reviewed envelope/finished-face differences, not to hide incorrect assignments.

No material waste is added to installed area. No sheet/box count or price is inferred. Existing jobs without this mapping retain their prior behavior.

Verification: `test_tile_underlayment_review`, `test_company_scope_review`, and `test_company_scope_bids` passed 27 tests on 2026-09-22. The Roberts replay in `work/phase3/audit_measured_underlayment_20260922.py` passed through fresh intake and real HTTP exports using existing reviewed geometry. It returned 151.141793235 SF and the saved 1/4-inch cement-board practice, preserving all 711 template rows without inheriting Roberts prices. This replay is not a new-plan extraction or independent accuracy test.
