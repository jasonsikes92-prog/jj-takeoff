#!/usr/bin/env python
"""Interpret auto_areas_scorecard.json honestly.

A loop only GRADES against a target if it lands within 10% of it — the harness's
best-match column otherwise pairs one declared loop with every target and reads
as failure when the truth is "not produced". Buckets: MATCHED <=2 (the cert
gate), CLOSE <=5, NEAR <=10, else NOT PRODUCED.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def bucket(d):
    return "MATCHED" if d <= 2.0 else "CLOSE" if d <= 5.0 else "NEAR" if d <= 10.0 else None


def main():
    sc = json.load(open(os.path.join(HERE, "auto_areas_scorecard.json"),
                        encoding="utf-8"))
    counts = {"MATCHED": 0, "CLOSE": 0, "NEAR": 0, "NOT PRODUCED": 0}
    lines = []
    for job, e in sc.items():
        declared = [s for s in e.get("solved", []) if s.get("status") == "auto-declared"]
        used = set()
        for tname, g in sorted(e.get("grades", {}).items()):
            d = g["delta_pct"]
            b = bucket(d)
            if b is None or (g["auto_sf"] in used and b != "MATCHED"):
                counts["NOT PRODUCED"] += 1
                lines.append((job, tname, g["his_sf"], None, None, "NOT PRODUCED"))
                continue
            used.add(g["auto_sf"])
            counts[b] += 1
            lines.append((job, tname, g["his_sf"], g["auto_sf"], d, b))
        refused = [s for s in e.get("solved", []) if s.get("status") != "auto-declared"]
        lines.append((job, f"[{len(declared)} declared / {len(refused)} refused "
                           f"of {e.get('loops_considered', 0)} loops]",
                      None, None, None, ""))

    print(f"{'job':<13} {'target':<38} {'his SF':>9} {'auto SF':>9} {'delta':>7}  verdict")
    for job, t, his, auto, d, v in lines:
        hs = f"{his:,.0f}" if his else ""
        au = f"{auto:,.0f}" if auto else ""
        ds = f"{d:.1f}%" if d is not None else ""
        print(f"{job:<13} {t:<38} {hs:>9} {au:>9} {ds:>7}  {v}")
    total = sum(counts.values())
    print("\nZERO-INK AREA SCOREBOARD:", ", ".join(f"{k} {v}" for k, v in counts.items()),
          f"(of {total} graded targets)")


if __name__ == "__main__":
    main()
