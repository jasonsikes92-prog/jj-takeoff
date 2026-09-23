# Returned trade response review

Run `jj.py trade-response --scope <current trade JSON> --workbook <returned XLSX> --current-snapshot <current estimate snapshot SHA256>`.

Use the current published trade export and snapshot, not values copied from the returned workbook. The command reads the `Response` and `Scope details` sheets produced by `work/phase3/build_trade_response_workbooks.mjs` and writes a JSON review to standard output. It does not update estimates, approve prices, send messages or release orders.

Every scope ID and reference quantity must remain present and unchanged; row sorting is supported. Changed headers or reference cells, missing/duplicate IDs, and formula/error cells stop extraction. Keep the original returned workbook as evidence; review its formulas explicitly if the supplier used them.

For a response issued against an earlier estimate snapshot, pass `--issued-scope <original trade JSON>`. The workbook must match that preserved source. The reader compares every trade-content field against the current export, excluding only snapshot and measurement-revision metadata. Drawing, quantities, cost ownership, inclusions, exclusions, unresolved notes and other scope changes require renewed review. An unchanged trade can retain its original answers after an unrelated estimate revision; the report records both revisions and all input hashes. This does not renew the supplier's price validity or approve the quote.

Blank replies remain unanswered. `Included in package` must point to a separately priced scope in the same trade and cannot carry another charge. Cross-trade inclusions, new package ownership and changed billing units need review. A lump-sum quote can be reviewed manually; this reader does not infer it from a line amount with missing quantity/rate fields.

The arithmetic check compares explicitly quoted quantity times rate with line amount, then separately priced lines plus explicitly separate delivery and tax with the quoted total. Narrative extras and unresolved charge treatment withhold the total comparison. These checks do not establish supplier identity, current price validity, material/labor inclusions, code compliance, or complete scope. Original source issues and package inclusions remain in the report for reconciliation.
