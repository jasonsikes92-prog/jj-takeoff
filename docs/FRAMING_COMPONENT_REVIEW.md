# Reviewed partial wall components

When a measurement job contains `framing_component_review.json`, the estimate server adds partial wall component inputs after the linked quantities and saved trade snapshots, before pricing. The configuration specifies a plan hash, one material `template_row`, hash-bound local evidence references named `field_inputs`, `assembly_inputs` and `profile`, and geometry `dependencies`.

Each dependency contains a job-relative review path and a map of measurement IDs to `geometry_digest` values. The current job may use `.`. Wrong-plan dependencies are rejected. Edited or missing measurements withhold the five component inputs and add a pending quantity reason. Restoring exact geometry permits recalculation. Missing/altered evidence or startup configuration produces an explicit API error.

Field stations are recalculated by `field_stud_layout.layout`; source-classified assembly counts use `framing_assemblies.calculate`. Quantities are appended separately in EA as assembly inputs, while the template purchasing quantity and cost remain unchanged. Reserved station counts are not purchase pieces. Component provenance and unquantified assembly IDs remain in `wall_component_review`.

Reviewed dependencies must cover the geometry used to prepare the source evidence. The importer verifies those declared dependencies; it does not automatically infer a complete dependency graph or regenerate topology after edits. The current Roberts installation binds all 24 interior runs plus its editable opening and enclosure references. Complete heights, stock cuts, remaining components and pricing are not supplied by this adapter.
