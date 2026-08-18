#!/usr/bin/env python
"""Score the takeoff system against Jason's manual Buildern takeoff (the SPEC).

Jason's ruling of what this system is FOR (2026-08-17): reproduce his manual
takeoff work, load it into his estimate template, then cut sub bid packages.
His complete Roberts takeoff export (31 measurement lines, 8 sheets, his waste
factors, per-segment traces) is the ground truth in
reference/buildern_takeoff_ground_truth.json — this harness grades the system
against it, line by line, and is the metric that says how close "done" is.

Verdicts per line:
  MATCHED       system quantity within 2% of Jason's base (the area-gate bar)
  CLOSE         within 5% — real signal, needs a look before it's trusted
  DISCREPANT    produced, but >5% off — a defect in one of us, named loudly
  NOT_PRODUCED  the system does not measure this yet — the honest backlog

Mappings are EXPLICIT and conservative: a system number only compares against
a Buildern line when the two measure the same scope. Waste is stripped —
comparisons are base-to-base (his Quantity column includes waste; segments do
not). No mapping is invented to make coverage look better.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    with open(os.path.join(HERE, "reference",
                           "buildern_takeoff_ground_truth.json"),
              encoding="utf-8") as fh:
        gt = json.load(fh)
    with open(os.path.join(HERE, "evidence", "takeoff_evidence.json"),
              encoding="utf-8") as fh:
        ev = json.load(fh)
    take = ev.get("takeoff", ev)
    # the evidence schema stores run_takeoff's lines under "measurements"
    lines = {l["trade"]: l for l in
             take.get("measurements", take.get("lines", []))}
    comps = {c["name"]: c for c in
             take.get("area_certification", {}).get("components", [])}
    return gt, lines, comps


def base(entry):
    """Jason's base quantity (waste stripped)."""
    qty = entry.get("qty_sf", entry.get("qty_ft", entry.get("count")))
    if qty is None:
        return None
    if "base_sf" in entry:
        return entry["base_sf"]
    waste = entry.get("waste", 0)
    return qty / (1 + waste) if waste else qty


def main():
    gt, lines, comps = load()
    m = gt["measurements"]

    def comp_qty(name):
        c = comps.get(name)
        return c["qty"] if c else None

    def line_qty(trade):
        l = lines.get(trade)
        return l["qty"] if l else None

    # (sheet, buildern name, jason base, system qty, note)
    rows = []

    def add(sheet, name, jbase, sysq, note=""):
        rows.append({"sheet": sheet, "line": name,
                     "jason_base": round(jbase, 1) if jbase else jbase,
                     "system": round(sysq, 1) if sysq is not None else None,
                     "note": note})

    # --- explicit mappings ---------------------------------------------------
    a = m["areas"]
    add("areas", "SF FIRST FLOOR", base(a["SF FIRST FLOOR"]),
        line_qty("heated_sf"), "certified heated rollup")
    add("areas", "Garage", base(a["Garage"]), comp_qty("garage slab"),
        "certified component (markup primary)")
    add("areas", "Covered Porches [front]", a["Covered Porches"]["segments"][0],
        comp_qty("front porch slab"), "certified component")
    add("areas", "Covered Porches [rear]", a["Covered Porches"]["segments"][1],
        comp_qty("rear deck (floor plan)"),
        "his porch-roof cover over the deck region")
    add("areas", "Total under Roof", base(a["Total under Roof"]),
        line_qty("framing_sf"), "certified framing rollup")
    add("deck_windows", "Deck (floor)", base(m["deck_windows"]["Deck"]),
        comp_qty("rear deck (floor plan)"),
        "same footprint measured as deck framing — bills separately from cover")

    # cal #70: Jason's Buildern shingle lines are FLAT plan traces (legacy
    # convention); the system emits pitch-corrected surface. Convert his bands
    # by the sheet's PRINTED pitch factors before comparing — including the
    # 3:12 the roof plan actually prints where his band label says "5 pitch".
    r = m["roof"]
    factors = {"Shingle 5 pitch": 1.0308,     # printed 3:12, mislabeled 5
               "Shingles 8 Pitch": 1.2019,
               "Shingles 12 Pitch": 1.4142}
    shingle_surface = sum(base(r[k]) * f for k, f in factors.items())
    roof_sq = line_qty("roof_surface_sq")
    add("roof", "Shingles (surface, cal #70)", shingle_surface,
        roof_sq * 100 if roof_sq else None,
        "his flat bands x printed pitch factors vs face-decomposition")
    add("roof", "Roof Insulation", base(r["Roof Insulation"]), None,
        "cross-checks his flat traces (independent, also flat)")

    f = m["foundation"]
    add("foundation", "Footers", base(f["Footers"]),
        line_qty("footer_lf"),
        "crawlspace walk perim + declared-adjacency turndowns; stoops pending")

    # everything else: not produced yet — the honest backlog
    consumed = {"SF FIRST FLOOR", "Garage", "Covered Porches", "Deck",
                "Total under Roof", "Footers", "Roof Insulation",
                "Shingle 5 pitch", "Shingles 8 Pitch", "Shingles 12 Pitch"}
    for sheet, entries in m.items():
        for name, entry in entries.items():
            if name not in consumed:
                add(sheet, name, base(entry), None)

    # --- verdicts ------------------------------------------------------------
    for x in rows:
        if x["system"] is None:
            x["verdict"] = "NOT_PRODUCED"
        else:
            d = abs(x["system"] - x["jason_base"]) / x["jason_base"] * 100
            x["delta_pct"] = round(d, 1)
            x["verdict"] = ("MATCHED" if d <= 2.0 else
                            "CLOSE" if d <= 5.0 else "DISCREPANT")

    order = {"MATCHED": 0, "CLOSE": 1, "DISCREPANT": 2, "NOT_PRODUCED": 3}
    rows.sort(key=lambda x: (order[x["verdict"]], x["sheet"]))
    counts = {}
    for x in rows:
        counts[x["verdict"]] = counts.get(x["verdict"], 0) + 1

    print("=" * 78)
    print("SYSTEM vs JASON'S BUILDERN TAKEOFF — the spec scoreboard")
    print("=" * 78)
    for x in rows:
        d = f"{x.get('delta_pct', ''):>5}%" if "delta_pct" in x else "     -"
        sysq = f"{x['system']:>9}" if x["system"] is not None else "        -"
        print(f"  {x['verdict']:<13} {x['line']:<34} jason {x['jason_base']:>9}"
              f"  system {sysq}  {d}")
        if x["note"]:
            print(f"                {'':<34} {x['note']}")
    total = len(rows)
    print("-" * 78)
    print("  " + "  ".join(f"{k}: {v}" for k, v in sorted(
        counts.items(), key=lambda kv: order[kv[0]])))
    print(f"  coverage: {total - counts.get('NOT_PRODUCED', 0)}/{total} lines"
          f" produced; trusted (MATCHED): {counts.get('MATCHED', 0)}/{total}")
    out = os.path.join(HERE, "buildern_comparison.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "counts": counts}, fh, indent=1)
    print(f"  saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
