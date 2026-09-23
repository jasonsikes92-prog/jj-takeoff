# Multiple floor levels

Run `tools/multilevel_takeoff.py --job JOB` after the complete sheet review.
The job's `multilevel_review.json` binds the plan and sheet-review SHA256 hashes,
and assigns every reviewed floor page exactly once:

```json
{
  "plan_sha256": "current plan hash",
  "sheet_review_sha256": "current sheet review hash",
  "levels": [{"id": "basement", "page": 8}, {"id": "main", "page": 9}],
  "scope_files": {
    "main": {
      "floor_wall_view_review.json": {
        "file": "scope_reviews/main-wall.json", "sha256": "review file hash"
      }
    },
    "shared": {
      "roof_view_review.json": {
        "file": "scope_reviews/roof.json", "sha256": "review file hash"
      }
    }
  }
}
```

Each level receives its own measurement job. Unambiguous non-floor roles run
once in the shared job. Ambiguous elevations/site pages still need routing;
this operation does not establish whole-plan measurement coverage.
View files are copied only to their assigned scope, validated by the existing
extractor, and included in the final source-change check. Paths must remain
inside the job. Existing results are preserved: use a new job revision to rerun.

For a wall view containing both filled rectangles and outlined walls, set
`extraction_method` to `filled_and_stroked` in its wall-view review. Exact
duplicates retain both sources on one candidate; overlapping alternatives
are saved separately for review. This does not certify either source as a wall.

The combined measurement file keeps level-prefixed IDs and original source IDs.
Do not sum child estimate rows, company allowances, or bid scopes: these repeat
the template. Financial consolidation and complete measurement review remain
required before a whole-house estimate can be released.

The shared roof scope also accepts `roof_dormer_pitch_review.json` and
`roof_coverage_review.json` through `scope_files`. These retain explicit
geometric pitch assumptions and the independently traced source contour.
Coverage agreement alone does not certify pitch, wall quantities, or pricing.

`summary.json.project_allowances` consolidates allowances explicitly marked
`quantity_scope: project`. The four-hose-bibb default remains four for the
whole house, with each contributing scope listed as provenance. Conflicting
copies fail publication. Legacy or unknown allowance scopes remain in
`unresolved_scope_items`; they are not silently treated as project-wide.
This consolidation does not yet consolidate financial template rows.
