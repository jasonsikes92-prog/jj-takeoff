# Saved selections in flooring drafts

Flooring exports now read an optional `flooring_selection_review.json` in the measurement job. Explicit source-bound region links resolve selected Buildern products from a saved selection capture. The exported room item retains product name, brand/SKU/URL when present, selection/item IDs, capture date and source hashes. It does not import source quantities or prices.

Required mapping fields:

```json
{
  "plan_sha256": "actual-plan-hash",
  "project_id": 29093,
  "decisions": [
    {
      "region_id": "actual-region-id",
      "region_sha256": "room_use_review.binding(plan_sha256, region)",
      "source_file": "scope_evidence/selections.json",
      "source_sha256": "actual-capture-file-hash",
      "selection_id": 599316,
      "item_id": 180476
    }
  ]
}
```

The example IDs belong to Roberts; never copy them into another project's mapping. Source capture format is the saved Buildern wrapper with `projectId`, `capturedAt` and `response.data.selections.data`. Both the capture and selected record must match the explicitly mapped project.

A room geometry/label change withholds the selection until its coverage is reviewed. Pending products and conflicting multiple selected items in a SINGLE-option group remain unresolved. Changed file hashes, duplicate links, cross-project evidence and outside-job evidence paths are rejected. The bid exporter tracks nested selection dependencies so changes during export prevent publication.

The room-to-selection mapping is still explicit. Neither a bathroom label nor a product's saved location establishes which finished-floor contour it covers. A resolved product choice does not resolve substrate, finished edges, waste, carton counts, current pricing or complete-house coverage. Saved selection captures are dated evidence, not live confirmation. Later owner corrections must supersede outdated mappings.

Verified on 2026-09-22: 15 targeted selection, flooring and export tests passed. The Roberts replay script joined the saved Luxe Sand Matte Porcelain Tile record to current reviewed primary-bath geometry: 151.141793235 SF. The historical 142.85 selection quantity and historical unit price were not imported. The explicit mapping was checked against the existing row389 product evidence; this was not an automatic matching test or independent measurement validation. Live estimate remained unchanged.
