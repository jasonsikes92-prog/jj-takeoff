#!/usr/bin/env python
"""cal #72 (Jason's ruling 2026-08-21, "ratify both"): foundation_wall_loops also
emits the OUTER face of each component — the component grown one max wall
thickness into its own sealed band, contoured. The dim strings on his plans run
to outside faces even on shared walls (garage 26'-8" = inner 25.25 + 2 walls),
so the outer polygon is the seed that lets the closure solver reach the
dimensioned figures; the whole zero-ink envelope scoreboard rides on these keys.

Until now the only proof was the mutable, gitignored training scorecard — a
green golden suite could not notice the outer keys going missing or wrong
(review finding P2-1, 2026-08-21). This pins the capability on the real Roberts
foundation sheet:

  - every loop carries outer_polygon_pts (a real polygon, >= 4 points) and
    outer_area_sf, and the area IS its own polygon's shoelace at the page
    frame — one geometry, two views, no drift between them;
  - the outer face strictly contains the inner face (outer_area_sf > area_sf);
  - the largest loop's outer face lands within 2% of Jason's hand-certified
    Roberts heated envelope, 2,127.25 SF — the INDEPENDENT side, his number,
    not an engine echo. (Certified 8/17; the zero-ink walk later read 2,126.)

Raster rendering is deterministic for a pinned PDF, so these tolerances are
stable, not flaky.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)

import jnj_takeoff as eng  # noqa: E402

ROBERTS = os.path.join(HERE, "golden", "roberts", "plan.pdf")
PAGE = 3            # foundation/slab sheet
PPF = 16.646        # certified page scale (area_certification primary)
HIS_ENVELOPE_SF = 2127.25   # Jason's hand-entered Buildern heated SF (ground truth)


def shoelace_sf(pts, ppf):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0 / ppf ** 2


def main():
    import fitz
    doc = fitz.open(ROBERTS)
    loops = eng.foundation_wall_loops(doc[PAGE], ppf=PPF, close_ft=2.0)
    assert len(loops) >= 3, f"expected the 3 Roberts components, got {len(loops)}"

    for L in loops:
        pts = L.get("outer_polygon_pts")
        outer = L.get("outer_area_sf")
        assert pts and len(pts) >= 4, f"outer_polygon_pts missing/degenerate: {pts!r}"
        assert outer and outer > L["area_sf"], (
            f"outer face must strictly contain inner: outer {outer} vs inner {L['area_sf']}")
        poly_sf = shoelace_sf(pts, PPF)
        assert abs(poly_sf - outer) / outer < 0.001, (
            f"outer_area_sf {outer} is not its own polygon's area {poly_sf:.1f}")

    crawl = max(loops, key=lambda L: L["area_sf"])
    delta = abs(crawl["outer_area_sf"] - HIS_ENVELOPE_SF) / HIS_ENVELOPE_SF * 100
    assert delta <= 2.0, (
        f"crawlspace outer face {crawl['outer_area_sf']} SF vs Jason's certified "
        f"{HIS_ENVELOPE_SF} SF = {delta:.2f}% (>2%)")

    print(f"PASS: {len(loops)} loops each emit a self-consistent outer face; "
          f"crawlspace outer {crawl['outer_area_sf']} SF vs Jason's certified "
          f"{HIS_ENVELOPE_SF} SF = {delta:.2f}% (<=2%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
