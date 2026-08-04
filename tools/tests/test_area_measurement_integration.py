#!/usr/bin/env python
"""Integration proof: plan pixels -> two tracers -> certified area -> pricing."""

import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
DEPS = r"C:\Users\jason\OneDrive\Desktop\Claude\.estimate_deps"
sys.path.insert(0, DEPS)
sys.path.insert(0, TOOLS)

import fitz  # noqa: E402
import jnj_takeoff as eng  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        plan = os.path.join(tmp, "synthetic-plan.pdf")
        evidence = os.path.join(tmp, "evidence")
        doc = fitz.open()
        page = doc.new_page(width=600, height=600)
        page.draw_rect(fitz.Rect(100, 100, 300, 300), color=(0, 0, 0), width=1)
        doc.save(plan)
        doc.close()

        scale = {
            "ppf": 10,
            "scale_checks": [
                {"label": "overall width", "printed_ft": 20, "measured_points": 200},
                {"label": "half width", "printed_ft": 10, "measured_points": 100},
            ],
        }
        specs = [{
            "name": "Conditioned rectangle",
            "classification": "heated",
            "primary": {
                "page": 0,
                "sheet": "Synthetic A-101",
                "clip": [80, 80, 320, 320],
                "method": "clean-tracer",
                **scale,
            },
            "verification": {
                "page": 0,
                "sheet": "Synthetic A-101",
                "clip": [80, 80, 320, 320],
                "method": "enclosed-region",
                **scale,
            },
        }]
        result = eng.measure_and_certify_area_components(
            plan, specs, evidence, tolerance_pct=3.0
        )
        assert result["ok"], {"errors": result["errors"], "components": result["components"]}
        by_trade = {line["trade"]: line for line in result["lines"]}
        assert abs(by_trade["heated_sf"]["qty"] - 400) <= 12, by_trade
        assert abs(by_trade["framing_sf"]["qty"] - 400) <= 12, by_trade
        takeoff = {
            "status": "certified",
            "area_certification": result,
            "lines": result["lines"],
            "not_measured": [],
        }
        priced = eng.estimate_from_takeoff(takeoff)
        assert priced["n_priced"] == 2, priced
        print(
            "PASS: synthetic plan pixels measured twice, reconciled, certified, and priced "
            f"at {by_trade['heated_sf']['qty']:.1f} SF"
        )


if __name__ == "__main__":
    main()
