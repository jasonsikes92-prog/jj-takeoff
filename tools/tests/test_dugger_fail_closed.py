#!/usr/bin/env python
"""End-to-end regression: the old Dugger schedule/hard-code path must fail closed."""

import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
# The vendored .estimate_deps tree was deleted 2026-08-04. It was inserted at sys.path[0],
# so its stale numpy SHADOWED the working system one -- which is what made the sibling
# integration test die on "No module named numpy._core._multiarray_umath". Use the
# installed packages; if an import fails, fix the environment, don't re-vendor.
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402


PLAN = r"C:\Users\jason\Downloads\Dugger Residence 01-20-26 Final.pdf"


def main():
    result = eng.run_takeoff(
        PLAN,
        {"sqft_schedule": 6},
        underroof_sf=6917.7,
    )
    assert result["status"] == "more_information_required", result
    assert result["area_certification"]["ok"] is False, result
    area_lines = [line for line in result["lines"]
                  if line.get("trade") in eng.CORE_AREA_TRADES]
    assert area_lines == [], area_lines
    assert any("ignored legacy underroof_sf" in note
               for note in result["assumptions"]), result["assumptions"]
    assert result["checks"] and result["checks"][0]["role"] == "comparison-only"
    try:
        eng.estimate_from_takeoff(result)
    except ValueError as exc:
        assert "not certified for pricing" in str(exc)
    else:
        raise AssertionError("schedule-only Dugger takeoff reached pricing")
    print("PASS: Dugger schedule/hard-code path returns MORE INFORMATION REQUIRED and cannot price")


if __name__ == "__main__":
    main()
