# Opening/header width review

`tools/opening_header_review.py` provides `review(state, bindings, headers, products)` and `from_folder(folder, state)`. The measurement editor serves the latter at `GET /api/opening-headers` when the job contains `opening_header_review.json`; otherwise it returns 404.

The configuration binds `plan_sha256`, `bindings`, and `headers`/`products` evidence references. Each evidence reference has a job-relative `path` and expected `sha256`. Header evidence contains `sha256` for its source drawing and a `headers` list with stable `id` and positive `length_inches`. Product evidence contains an `openings` list with stable `opening_id`, positive `rough_opening_width_in` and a source citation.

Bindings contain `opening_id`, `header_id`, `measurement_id`, `measurement_page` and `source`. Header or measurement IDs may be null when that source is genuinely missing. A linked measurement must be a two-point length on the specified sheet; a missing referenced ID is an error. Duplicate opening/header/product identities and evidence outside the job are rejected.

Results preserve drawn and product widths independently and compare the larger with header cut length. Negative remaining length flags an undersized length reference; zero leaves no length for end support; positive remaining length still leaves support unverified. Missing header or opening width is explicit. All outputs retain unknown king/jack counts and false structural/purchase release flags.

Current measurement version, geometry digest, mapping hash and evidence hashes bind the result to its inputs. No quantities, price rows or geometry are changed. Tests cover altered points, restoration in the real Roberts HTTP trial, evidence tampering, wrong plans, invalid dimensions, missing products, unlinked geometry and missing headers.

This is a geometric consistency check, not a header-sizing or support-count calculator. Plan/header association remains source-reviewed; the module does not infer a structural load path or approve a supplier selection.

The measurement editor displays these results in the Opening/header checks panel below the sheet selector. Linked-opening buttons select and focus the editable measurement. Unsaved edits are labeled and navigation buttons are disabled until save or discard. Saving reloads the check against the saved measurement version; old response sequences are ignored and failures replace prior results with an explicit unavailable message. Missing job configuration hides the panel. The current Roberts layout was approved by Jason on September 17, 2026.
