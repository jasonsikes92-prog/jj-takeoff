#!/usr/bin/env python
"""Generalized autonomy harness — the engine draws its own lines on EVERY vector
job in the training corpus and takes its own measurements, graded against Jason's
Buildern Inputs (his hand-entered ground truth).

Per job:  loops from foundation_wall_loops on every scaled page (shape, no human
ink) -> cross-page printed-chain pools -> cal #68 closure solver (auto_declare
machinery, verbatim import) -> cal #71 schedule window (read_sqft_schedule) ->
grade vs Inputs (SF FIRST FLOOR / Garage / Covered Porches).

Report-only. Writes training/auto_areas_scorecard.json.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "jobs", "roberts_levelground"))

import fitz  # noqa: E402
import jnj_takeoff as eng  # noqa: E402
from auto_declare import (  # noqa: E402  (proven Roberts machinery, unchanged)
    split_small_diagonals, solve_axis, evaluate_combos, AXIS,
    AREA_EQUIV_PCT, DECISIVE_GAP_FT, SCHED_SEL_PCT,
)
from propose_walks import rectilinear_edges  # noqa: E402

MIN_LOOP_SF = 300
MAX_LOOP_SF = 9000
MAX_LOOPS_PER_JOB = 8

JOBS = ["roberts", "davis", "guarino_v3", "show", "watkins", "dugger",
        "pace_kinards", "burns", "holbrook", "zegarra"]


def plan_path(job):
    if job == "roberts":
        return os.path.join(ROOT, "tools", "tests", "golden", "roberts", "plan.pdf")
    return os.path.join(HERE, job, "plan.pdf")


def his_inputs(gt, job):
    e = gt.get(job, {})
    return {m["name"]: m["qty"] for m in e.get("measurements", [])
            if m.get("category") == "Inputs"}


def main():
    gt = json.load(open(os.path.join(HERE, "ground_truth.json"), encoding="utf-8"))
    readab = json.load(open(os.path.join(HERE, "readability_scorecard.json"),
                            encoding="utf-8"))
    out = {}
    for job in JOBS:
        pages = readab.get(job)
        pp = plan_path(job)
        if not isinstance(pages, list) or not os.path.exists(pp):
            continue
        doc = fitz.open(pp)
        scaled = [r for r in pages if r.get("ppf")]

        # 1. schedule rows (any text page; keep the page with the most rows)
        sched_rows = []
        for r in pages:
            if not r.get("text"):
                continue
            try:
                rows = eng.read_sqft_schedule(doc[r["i"]])
            except Exception:
                rows = []
            if len(rows) > len(sched_rows):
                sched_rows = rows
        sched = {row["label"]: row["sqft"] for row in sched_rows}

        # 2. chains pool across scaled pages
        pool = {"H": set(), "V": set()}
        for r in scaled:
            try:
                for c in eng.read_dimension_chains(doc[r["i"]], r["ppf"]):
                    pool[c["orient"]].update(c["runs"])
                    pool[c["orient"]].add(c["total"])
            except Exception:
                pass

        # 3. loops on every scaled page
        loops = []
        for r in scaled:
            try:
                for L in eng.foundation_wall_loops(doc[r["i"]], ppf=r["ppf"],
                                                  close_ft=2.0):
                    if MIN_LOOP_SF <= L["area_sf"] <= MAX_LOOP_SF:
                        loops.append((r["i"], r["ppf"], L))
            except Exception:
                pass
        loops.sort(key=lambda t: -t[2]["area_sf"])
        loops = loops[:MAX_LOOPS_PER_JOB]

        # 4. solve each loop
        solved = []
        for pgi, ppf, L in loops:
            edges = split_small_diagonals(rectilinear_edges(L["polygon_pts"], ppf), ppf)
            if any(e["dir"] == "?" for e in edges):
                solved.append({"page": pgi, "loop_sf": round(L["area_sf"], 1),
                               "status": "diagonal"})
                continue
            legs = [(i, e["dir"], e["len_ft"]) for i, e in enumerate(edges)]
            h = [l for l in legs if AXIS[l[1]] == "H"]
            v = [l for l in legs if AXIS[l[1]] == "V"]

            # complexity guard: dense chain pools give every leg a full candidate
            # slate; 4^17 tier-0 products are a runaway, not a measurement. Refuse
            # loudly like every other undecidable case.
            def complexity(axis_legs, axis_pool):
                prod = 1
                for _i, _d, t in axis_legs:
                    n = sum(1 for val in axis_pool if abs(val - t) <= 1.6)
                    prod *= max(1, min(n, 4))
                    if prod > 300000:
                        return prod
                return prod
            if (complexity(h, pool["H"]) > 300000 or
                    complexity(v, pool["V"]) > 300000 or len(legs) > 14):
                solved.append({"page": pgi, "loop_sf": round(L["area_sf"], 1),
                               "status": "too-complex",
                               "legs": len(legs)})
                continue
            hs, _ = solve_axis(h, pool["H"])
            vs, _ = solve_axis(v, pool["V"])
            if not hs or not vs:
                solved.append({"page": pgi, "loop_sf": round(L["area_sf"], 1),
                               "status": "no-solution"})
                continue
            combos = evaluate_combos(hs, vs, legs)
            areas = [c["area_sf"] for c in combos]
            spread = ((max(areas) - min(areas)) / (sum(areas) / len(areas)) * 100
                      if len(areas) > 1 else 0.0)
            best = combos[0]
            decisive = (len(combos) == 1 or spread <= AREA_EQUIV_PCT or
                        combos[1]["delta_score_ft"] - best["delta_score_ft"]
                        >= DECISIVE_GAP_FT)
            sel = None
            if not decisive and sched:
                for label, ssf in sched.items():
                    near = [c for c in combos
                            if abs(c["area_sf"] - ssf) / ssf * 100 <= SCHED_SEL_PCT]
                    if near:
                        combos, best, decisive, sel = near, near[0], True, label
                        break
            solved.append({
                "page": pgi, "loop_sf": round(L["area_sf"], 1),
                "status": "auto-declared" if decisive else "ambiguous",
                "walk_area_sf": best["area_sf"] if decisive else None,
                "closure_ft": best["closure_ft"] if decisive else None,
                "legs": len(best["walk"]) if decisive else None,
                "derived": len(best["derived"]) if decisive else None,
                "readings": len(combos), "spread_pct": round(spread, 2),
                "schedule_selected": sel,
            })
        doc.close()

        # 5. grade vs his Inputs
        his = his_inputs(gt, job)
        targets = {"SF FIRST FLOOR": his.get("SF FIRST FLOOR"),
                   "Garage": his.get("Garage"),
                   "Covered Porches": his.get("Covered Porches")}
        grades = {}
        declared = [s for s in solved if s["status"] == "auto-declared"]
        for tname, tval in targets.items():
            if not tval or tval <= 0:
                continue
            best_match = None
            for s in declared:
                d = abs(s["walk_area_sf"] - tval) / tval * 100
                if best_match is None or d < best_match["delta_pct"]:
                    best_match = {"delta_pct": round(d, 2),
                                  "auto_sf": s["walk_area_sf"], "page": s["page"]}
            if best_match:
                grades[tname] = {"his_sf": tval, **best_match}
        out[job] = {"schedule": sched, "pool_sizes": {k: len(v) for k, v in pool.items()},
                    "loops_considered": len(loops), "solved": solved, "grades": grades}
        json.dump(out, open(os.path.join(HERE, "auto_areas_scorecard.json"), "w"),
                  indent=1)
        n_dec = len(declared)
        g = ", ".join(f"{k.split()[-1]}: his {v['his_sf']:.0f} vs auto "
                      f"{v['auto_sf']:.0f} ({v['delta_pct']}%)"
                      for k, v in grades.items())
        print(f"{job:<13} loops {len(loops)}, declared {n_dec} | {g or 'no grades'}",
              flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
