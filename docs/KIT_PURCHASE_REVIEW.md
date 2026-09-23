# Whole-kit purchase mapping

The combined estimate can load `kit_purchase_review.json`. Each `purchases` entry references a hashed JSON file inside the job. That evidence names the plan, selected product/model, original template row, its real parent group or assembly, one existing EA assembly-input ID, the supplemental cost ID, and the one-kit-per-count basis.

`viewer/kit_purchase_review.py` reads the current linked count, retains the template unit and markup, and gives the supplemental kit row sole cost ownership. It accepts whole nonnegative counts, including zero. Pending scope review leaves the kit quantity unknown; missing or duplicate references fail. Already priced, excluded or separately owned targets fail. Price application rejects a different product ID or model. Scope and price certification remain separate; this mapping never releases an order or whole-house estimate.

The mapper reuses existing measured inputs. It does not automatically identify kits from a new plan or import Roberts products into another job. New jobs need their own plan-bound selection and count mapping. A product change requires revised reviewed evidence and matching dated pricing.

Roberts maps `hall-tub-surround-count` to `JJ-HALL-TUB-SURROUND-KIT`, preserving square-foot row 445 as an unpriced reference. The actual copied-job HTTP test changes the PF08 count from one to two and restores it; the purchase quantity and cost follow. Unit tests cover missing/pending references, count units, invalid quantities, source/drawing changes, duplicate costs, parent ownership and mismatched prices.
