# Automatic hardware purchase setup

Reviewed hardware counts can now feed separate purchase cost owners without writing four mapping files by hand:

```powershell
python jj.py hardware-purchases --job-dir <draft_takeoff> --snapshot <export_snapshot.json> --scope-review <job/hardware_supply_review.json>
```

Use the review server's `/api/export-snapshot` output. The job must have `hardware_quantity_review`, created by the existing opening/room/function workflow, and the same plan and template sources. The four functions are privacy, passage, pocket privacy and pocket passage.

The scope review is job-specific. It records `plan_sha256`, `hardware_review_sha256` (from `hardware_purchase_setup.digest(draft['hardware_quantity_review'])`), `reviewer`, `basis`, `applies_to: "hardware_function_supply"`, original `source_files` with job-relative `file` and SHA256, and `items` containing `input_id` and `supply_status`.

Supported input IDs are `opening-hardware-privacy`, `opening-hardware-passage`, `opening-hardware-pocket-privacy` and `opening-hardware-pocket-passage`. Supply statuses are `separate`, `included` and `unknown`. Missing decisions remain unknown. The reviewer must establish supplier scope from the actual job evidence; do not reuse another house's exclusion as proof.

For separate supply, the command creates a source-bound each-unit mapping and merges it with existing purchase mappings. The engine reads current quantities and the template's markup on every calculation. No quantities, products, prices or installation inclusions are copied from a previous job. Known zero and unresolved counts remain distinct. Product selection and dated pricing use the existing purchase/price review afterward.

Included and unknown functions create no extra cost owner. Included scope still needs its package owner reconciled. The command preserves existing mappings, rejects duplicate owners and conflicting priced rows, and requires a review-server restart after configuration changes. Existing output evidence is never overwritten. Original supplier evidence and the scope review remain live dependencies; changing either rejects dependent purchases until reviewed again.

Verification: 70 focused tests and actual CLI/HTTP execution on an isolated Burns copy. Four mappings produced 5 privacy, 7 passage, 0 pocket privacy and 1 pocket passage references. A wall edit withheld all four counts; restoration recovered them. Changing source evidence rejected the draft, and rerunning setup preserved existing mapping files. The supply exclusion in this test is explicitly synthetic: it establishes workflow behavior, not Burns supplier inclusion, independent takeoff accuracy or unattended operation. Roberts remains unchanged.
