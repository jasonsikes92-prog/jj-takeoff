# Measurement preparation recovery

New-plan measurement now builds in a separate attempt directory inside its job. The complete directory becomes `draft_takeoff` only after extraction, template mapping, bid drafts and the summary have finished. Relative references to the frozen company intake still resolve, and the engine evidence link points to the published location.

Previously, an exception after creating `draft_takeoff` left partial output at the editable draft location. Further preparation refused that directory, requiring operator intervention. Failed new attempts now retain their files and a failure marker separately. LEVEL GROUND exposes a failure count and offers the existing measurement action again using the current sheet-review revision. The action still requires the authorized case reviewer. There is no unbounded automatic retry loop.

Completed drafts, saved edits and older partial drafts at the stable location are preserved. Interrupted attempt directories are also retained. A separate attempt may be started without deleting them; this does not assert that a process producing another attempt has stopped. A competing completed publication is not replaced.

Verification: 77 targeted tests covered extraction, sheet review, specifications, failure/retry, reviewer authorization, stale revision rejection and preservation. The real Burns extractor was run on a copied, previously reviewed partial plan set. An injected late mapping failure retained its measurement and template files; a subsequent real run published 106 editable candidates and 711 template rows. Its evidence link resolved after publication. Actual editor HTTP save and restore passed, and the original source archive was unchanged.

Evidence: `outputs/measurement_preparation_recovery_r2/checks.json` at the workspace root. Reproduction: `work/phase3/verify_measurement_preparation_recovery.py`, which deliberately refuses to overwrite its output directory. The earlier trial reached publication but its verifier submitted the wrong save-request fields; the corrected second trial passed.

This is operational recovery evidence, not independent measurement accuracy, complete trade coverage, current pricing or approval to release an estimate. Burns retains its missing site sheet and revision issues. Roberts quantities and prices were not changed.
