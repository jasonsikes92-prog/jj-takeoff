#!/usr/bin/env python
"""cal #46: the slab tracer is chosen by DECLARED BOUNDARY STYLE, not by disagreement.

Two real sheets, two ground truths, opposite boundary styles:

  holbrook p6 SLAB PLAN   -- short-dash slab edge. Every dash is under the clean tracer's
                             1.2-ft segment floor, so the classified-segment canvas never
                             contains the boundary and the clean trace lands 26.5% low.
                             all-ink seals the dashes: 3,175 SF vs GEO flatwork invoice
                             3,122 = +1.7%.  (cal #24/#26/#46)
  roberts  p4 FOUNDATION  -- solid drawn walls, fully dimensioned. all-ink locks onto the
                             outer DIMENSION-LINE rectangle: 5,033 SF against a whole
                             under-roof of 3,431. The clean tracer is right: 3,066.7 vs the
                             sheet's own heated + garage + front porch = 3,069 = -0.1%.

The old code read "tracers disagree" as "dashed boundary suspected" and took all-ink both
times -- correct on holbrook by luck, 64% high on roberts. Declaring the style fixes both.
Undeclared must fail closed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402

GOLDEN = os.path.join(HERE, "golden")
HOLBROOK = os.path.join(GOLDEN, "holbrook", "plan.pdf")
ROBERTS = os.path.join(GOLDEN, "roberts", "plan.pdf")


def slab_line(result):
    return next((ln for ln in result["lines"] if ln["trade"] == "slab_area_sf"), None)


def not_measured(result):
    return next((nm for nm in result["not_measured"] if nm["trade"] == "slab_area_sf"), None)


def main():
    # --- holbrook: DASHED slab edge -> all-ink, +1.7% vs the GEO flatwork invoice --------
    r = eng.run_takeoff(HOLBROOK, {"slab": 5, "slab_boundary": "dashed"})
    ln = slab_line(r)
    assert ln, r["not_measured"]
    assert ln["method"] == "all-ink-tracer", ln
    err = (ln["qty"] - 3122) / 3122 * 100
    assert abs(err) <= 3.0, f"holbrook slab {ln['qty']} vs GEO 3,122 = {err:+.1f}%"

    # --- roberts: SOLID drawn walls -> clean tracer, -0.1% vs the sheet's own areas ------
    r = eng.run_takeoff(ROBERTS, {"slab": 3, "slab_boundary": "solid"})
    ln = slab_line(r)
    assert ln, r["not_measured"]
    assert ln["method"] == "clean-tracer", ln
    err = (ln["qty"] - 3069) / 3069 * 100
    assert abs(err) <= 2.0, f"roberts footprint {ln['qty']} vs plan 3,069 = {err:+.1f}%"

    # --- the old bug: undeclared style + disagreeing tracers must NOT answer -------------
    r = eng.run_takeoff(ROBERTS, {"slab": 3})
    assert slab_line(r) is None, "undeclared boundary style still produced a slab quantity"
    nm = not_measured(r)
    assert nm and "slab_boundary" in nm["why"], nm
    # and both readings stay visible for audit
    chk = next(c for c in r["checks"] if c.get("check") == "slab_tracers")
    assert chk["clean_sf"] and chk["all_ink_sf"], chk

    # --- declaring the WRONG style must change the answer, not be silently corrected -----
    r = eng.run_takeoff(ROBERTS, {"slab": 3, "slab_boundary": "dashed"})
    ln = slab_line(r)
    assert ln and ln["method"] == "all-ink-tracer" and ln["qty"] > 4500, ln

    print("PASS: slab tracer follows the DECLARED boundary style -- holbrook dashed "
          "-> all-ink +1.7% vs invoice, roberts solid -> clean -0.1% vs plan, "
          "undeclared -> more information required")


if __name__ == "__main__":
    main()
