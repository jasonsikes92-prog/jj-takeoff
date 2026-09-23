# Field-stud layout

`tools/field_stud_layout.py` enumerates field stations outside source-reviewed assembly reservations. It requires explicit measured straight runs, matching drawing-point intervals, scale and an estimating layout datum. Every run needs reserved end assemblies. Orphan reservations, invalid dimensions and duplicate run IDs are rejected. Overlapping reservations identify all assembly owners while excluding the station only once.

Python entry point: `layout(runs, zones, points_per_foot=..., spacing_inches=..., first_center_inches=...)`.

Command:

```powershell
python tools/field_stud_layout.py --input reviewed_framing_inputs.json --output field_stud_result.json
```

Input keys are `runs`, `zones`, `points_per_foot`, `first_center_inches` and optional `project_overrides`. Each run contains `id`, `orientation` (`horizontal` or `vertical`), `coordinate_pt`, `start_pt`, `end_pt` and `source`. Each zone contains `assembly`, `run`, `interval` and `source`. Coordinates increase from start to end; interval boundaries are inclusive. The command resolves `framing.stud_spacing_inches` from the company profile, with project overrides taking precedence. `--profile` selects another profile. Existing output files are preserved.

Output retains every field and reserved station, per-run counts, settings and input/profile hashes. Reservations remain separate from assembly piece quantities. `purchase_quantity` is null: member heights, stock cuts, assembly footprints, cripples and special framing remain distinct work. The calculator does not infer openings or junctions and must be rerun with newly reviewed inputs after geometry changes. Its hashes identify inputs; they are not independent evidence that source geometry is correct.
