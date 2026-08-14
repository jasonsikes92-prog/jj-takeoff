#!/usr/bin/env python
"""Regression tests for the measured-area pricing gate."""

import os
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402


class AreaCertificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _view(self, name):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as handle:
            handle.write(b"geometry-overlay")
        return path

    def _component(self, name, classification, qty, verify_qty=None, index=0):
        verify_qty = qty if verify_qty is None else verify_qty
        return {
            "name": name,
            "classification": classification,
            "primary": {
                "qty": qty,
                "unit": "SF",
                "source": "MEASURED",
                "sheet": "A-102",
                "view": self._view(f"{index}-primary.png"),
                "method": "trace-footprint-clean",
                "confidence": "high",
            },
            "verification": {
                "qty": verify_qty,
                "unit": "SF",
                "source": "MEASURED",
                "sheet": "A-100a",
                "view": self._view(f"{index}-verification.png"),
                "method": "trace-enclosed-region",
                "confidence": "high",
            },
        }

    def _dugger_components(self):
        return [
            self._component("Conditioned residence", "heated", 3938, 3940, 1),
            self._component("Garage", "garage", 612, 613, 2),
            self._component("Covered screened patio", "covered", 614, 614, 3),
            self._component("Detached workshop", "workshop", 480, 480, 4),
        ]

    def test_dugger_total_is_derived_once_and_schedule_is_check_only(self):
        schedule = [{
            "label": "SF TOTAL FRAMED",
            "sqft": 5164,
            "klass": "framed",
        }]
        result = eng.certify_area_measurements(
            self._dugger_components(), schedule_rows=schedule
        )
        self.assertTrue(result["ok"], result["errors"])
        by_trade = {line["trade"]: line for line in result["lines"]}
        self.assertEqual(by_trade["heated_sf"]["qty"], 3938.0)
        self.assertEqual(by_trade["framing_sf"]["qty"], 5644.0)
        self.assertNotEqual(by_trade["framing_sf"]["qty"], 6917.7)
        self.assertEqual(result["schedule_checks"][0]["schedule_qty"], 5164.0)
        self.assertEqual(result["schedule_checks"][0]["role"], "comparison-only")

        # The fixtures prove roll-up math, but cannot price because they did not
        # come from a recognized measurement engine (plan-pixel or printed-dims).
        takeoff = {"area_certification": result, "lines": result["lines"]}
        with self.assertRaisesRegex(ValueError, "recognized measurement engine"):
            eng.estimate_from_takeoff(takeoff)

    def test_relabeled_origin_cannot_self_verify(self):
        # cal #66 hardening: origins grant "input independence" ONLY when each
        # side's origin matches what its METHOD implies. A measurement duplicated
        # verbatim with just the origin string edited must NOT certify as its own
        # 0.0%-delta verification (this exact bypass was reproduced in review).
        comp = self._component("Conditioned residence", "heated", 3938, 3938, 9)
        same_view = comp["primary"]["view"]
        comp["verification"] = dict(comp["primary"])
        comp["verification"]["view"] = same_view
        comp["primary"]["origin"] = eng._AREA_ENGINE_ORIGIN
        comp["verification"]["origin"] = eng._AREA_DIMS_ORIGIN  # relabel only
        result = eng.certify_area_measurements([comp])
        self.assertFalse(result["ok"], result)
        self.assertTrue(
            any("not independent" in e for e in result["errors"]), result["errors"])
        # and the pricing gate independently refuses the origin/method mismatch
        takeoff = {"area_certification": dict(result, ok=True, status="certified"),
                   "lines": result["lines"]}
        certified, errors = eng.certify_takeoff_for_pricing(takeoff)
        self.assertFalse(certified)
        self.assertTrue(any("origin does not match its method" in e for e in errors),
                        errors)

    def test_total_or_under_roof_cannot_be_a_component(self):
        components = self._dugger_components()
        components.append(
            self._component("TOTAL UNDER ROOF", "covered", 5164, 5164, 5)
        )
        result = eng.certify_area_measurements(components)
        self.assertFalse(result["ok"])
        self.assertTrue(any("cannot be components" in error for error in result["errors"]))
        self.assertEqual(result["lines"], [])

    def test_missing_overlay_or_failed_reconciliation_blocks_certification(self):
        components = self._dugger_components()
        components[0]["primary"]["view"] = os.path.join(self.tmp.name, "missing.png")
        components[1]["verification"]["qty"] = 700
        result = eng.certify_area_measurements(components)
        self.assertFalse(result["ok"])
        self.assertTrue(any("does not exist" in error for error in result["errors"]))
        self.assertTrue(any("differ by" in error for error in result["errors"]))
        self.assertEqual(result["status"], "more_information_required")

    def test_schedule_sourced_or_plain_hardcoded_areas_cannot_be_priced(self):
        schedule_takeoff = {
            "area_certification": {"ok": True, "status": "certified"},
            "lines": [
                {"trade": "heated_sf", "qty": 5164, "source": "GIVEN-schedule",
                 "method": "text-schedule", "certified": True, "proof": ["fake"]},
                {"trade": "framing_sf", "qty": 6917.7, "source": "MEASURED",
                 "method": "hardcoded-rollup", "certified": True, "proof": ["fake"]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "not certified for pricing"):
            eng.estimate_from_takeoff(schedule_takeoff)

        hardcoded_takeoff = {
            "lines": [
                {"trade": "heated_sf", "qty": 5164, "source": "MEASURED"},
                {"trade": "framing_sf", "qty": 6917.7, "source": "MEASURED"},
            ]
        }
        with self.assertRaisesRegex(ValueError, "core area certification"):
            eng.estimate_from_takeoff(hardcoded_takeoff)

    def test_raster_scale_requires_two_reconciling_printed_dimensions(self):
        dugger_scale = eng.certify_explicit_scale(18.2, [
            {"label": "overall width", "printed_ft": 110, "measured_points": 1991},
            {"label": "top dimension chain", "printed_ft": 60, "measured_points": 1098},
        ])
        self.assertTrue(dugger_scale["ok"], dugger_scale["errors"])
        self.assertEqual(dugger_scale["confidence"], "high")

        one_check = eng.certify_explicit_scale(
            18.2, [{"printed_ft": 110, "measured_points": 1991}]
        )
        self.assertFalse(one_check["ok"])

        bad_scale = eng.certify_explicit_scale(16.0, [
            {"printed_ft": 110, "measured_points": 1991},
            {"printed_ft": 60, "measured_points": 1098},
        ])
        self.assertFalse(bad_scale["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
