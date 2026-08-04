from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(r"C:\Users\jason\OneDrive\Desktop\Claude")
DEPS = ROOT / ".estimate_deps"
SKILL = Path(r"C:\Users\jason\.claude\skills\jnj-estimate-takeoff")
PLAN = Path(r"C:\Users\jason\Downloads\Dugger Residence 01-20-26 Final.pdf")
WORK = ROOT / "dugger_estimate"
RENDERS = WORK / "sheet_renders"

sys.path.insert(0, str(DEPS))
sys.path.insert(0, str(SKILL / "tools"))

import fitz  # noqa: E402
from jnj_takeoff import SheetLedger, render_all_sheets  # noqa: E402


INDEX = [
    ("A-000", "Cover Sheet"),
    ("A-001", "Site Plan (By Others)"),
    ("A-002", "Grading Plan (By Others)"),
    ("A-100a", "Proposed Foundation Plan"),
    ("A-100b", "Foundation Details"),
    ("A-101", "Proposed Floor Plan"),
    ("A-102", "Proposed Dimensioned Floor Plan"),
    ("A-103", "Proposed Electrical Plan"),
    ("A-104", "Proposed Reflected Ceiling Plan"),
    ("A-105", "Proposed Roof Plan"),
    ("A-200", "West & South Exterior Elevations"),
    ("A-201", "East & North Exterior Elevations"),
    ("A-250", "Workshop - Floor Plan & Elevations"),
    ("A-300", "General Construction Recommendations"),
    ("A-301", "General Specifications: Construction Methods, Materials & Notes"),
    ("A-302", "General Construction Details & Notations"),
]


PAGE_CLASSIFICATIONS = [
    ("cover", "A-000 Cover Sheet", "Cover index inspected."),
    ("site", "A-001 Site Plan", "House, workshop, septic, water meter, and driveway shown."),
    ("site", "A-002 Grading Plan", "Erosion-control and grading plan."),
    ("foundation", "A-100a Proposed Foundation Plan", "Main crawlspace; garage and screened patio slab on grade."),
    ("detail", "A-100b Foundation Details", "Crawl stem wall and turned-down garage/workshop slab details."),
    ("floor_plan", "A-101 Proposed Floor Plan", "Room, opening, and fixture layout."),
    ("floor_plan", "A-102 Proposed Dimensioned Floor Plan", "Primary plan dimensions; printed 5,164 SF."),
    ("electrical", "A-103 Proposed Electrical Plan", "Receptacle layout."),
    ("other", "A-104 Reflected Ceiling Plan - Heights", "Ceiling heights and fan locations."),
    ("electrical", "A-104 Reflected Ceiling Plan - Lighting", "Second A-104 page with lighting layout."),
    ("roof_plan", "A-105 Proposed Roof Plan", "All house roof planes labeled 10:12 shingle."),
    ("elevation", "A-200 West & South Exterior Elevations", "Brick elevations and roof/soffit heights."),
    ("elevation", "A-201 East & North Exterior Elevations", "Brick elevations and roof/soffit heights."),
    ("floor_plan", "A-250 Workshop Floor Plan & Elevations", "30 x 16 workshop, 10-ft gypsum ceiling, mini-split, 10:12 roof."),
    ("notes", "A-300 General Construction Recommendations", "General code recommendations."),
    ("notes", "A-301 General Specifications", "Construction methods, materials, and notes."),
    ("detail", "A-302 General Construction Details & Notations", "Brick, wood, roof, and fireplace details."),
]


def certify_sheet_ledger() -> dict:
    WORK.mkdir(parents=True, exist_ok=True)
    renders = render_all_sheets(str(PLAN), str(RENDERS), zoom=0.75)
    page_count = fitz.open(PLAN).page_count
    if page_count != len(PAGE_CLASSIFICATIONS):
        raise RuntimeError(f"Expected {len(PAGE_CLASSIFICATIONS)} pages, found {page_count}")
    if len(renders) != page_count:
        raise RuntimeError(f"Rendered {len(renders)} of {page_count} pages")

    ledger = SheetLedger(str(PLAN), page_count).set_index(INDEX)
    for page_i, (role, title, note) in enumerate(PAGE_CLASSIFICATIONS):
        ledger.examine(page_i, role, renders[page_i][1], title=title, note=note)
    ok, report = ledger.certify()
    payload = {
        "ok": ok,
        "page_count": page_count,
        "index_count": len(INDEX),
        "unexamined": ledger.unexamined(),
        "report": report,
        "pages": ledger.pages,
    }
    (WORK / "sheet_ledger.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (WORK / "sheet_ledger.txt").write_text(report, encoding="utf-8")
    if not ok:
        raise RuntimeError(report)
    return payload


if __name__ == "__main__":
    result = certify_sheet_ledger()
    print(result["report"])
