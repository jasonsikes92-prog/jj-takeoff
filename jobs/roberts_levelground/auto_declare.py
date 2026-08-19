#!/usr/bin/env python
"""AUTONOMY LANE v0 — can the engine draw its own lines and take its own measurements?

Jason's goal (2026-08-18): his markup is TRAINING SIGNAL, not the permanent operating
mode. This tool is the first measured step: build each area component's walk with NO
human ink anywhere in the chain —

  SHAPE   from the engine's own paired-wall loop decomposition (foundation_wall_loops,
          the same loops run_prebid uses to LOCATE components — never Jason's markup),
  LENGTHS from the sheet's own printed dimension chains, chosen by a closure-
          constrained solver under cal #68's rules: at most ONE derived leg per axis,
          its value exactly what the printed legs force (±0.05), and if more than one
          distinct assignment closes, the component is AMBIGUOUS and REFUSES,
  GRADE   against Jason's certified declared walks + certified areas (the labeled
          corpus his drawing built).

Report-only: writes auto_walks.json + prints a scoreboard. Never touches
declared_walks.json, evidence, or the engine. Certification admission for auto walks
is a Jason ruling that has NOT been made — this tool exists to earn (or refuse) it
with data.
"""

import json
import os
import sys
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)

import jnj_takeoff as eng  # noqa: E402
from propose_walks import rectilinear_edges  # noqa: E402  (same snapping geometry)

PLAN = os.path.join(ROOT, "tools", "tests", "golden", "roberts", "plan.pdf")

CAND_TOL_FT = 1.6      # printed candidate vs traced leg: inside-face trace sits up to 2 walls (~1.5 ft) inside the dimensioned face
CAND_K = 4             # nearest printed candidates considered per leg
CLOSE_TOL_FT = 0.05    # cal #68: closure enforcement for the solved walk, per axis
DERIVED_TOL_FT = 1.2   # cal #68: a derived leg must stay this close to the traced edge
AGREE_TOL_FT = 0.35    # scoreboard: auto leg counts as agreeing with Jason's within this

DECISIVE_GAP_FT = 0.5  # tie-breaker: best assignment must beat the runner-up by this
                       # much total |printed - traced| or the axis stays AMBIGUOUS

AXIS = {"R": "H", "L": "H", "U": "V", "D": "V"}
SIGN = {"R": 1.0, "L": -1.0, "D": 1.0, "U": -1.0}


def split_small_diagonals(edges, ppf, max_ft=3.0):
    """A short non-axis edge between rectilinear runs is approxPolyDP chamfering a
    jog, not an angled wall. Splitting it into its dx then dy components is a
    faithful transform — the signed axis sums (closure math) are unchanged and the
    area shifts by at most (dx*dy)/2, inches² at this size. Long diagonals still
    refuse — that contract stands."""
    out = []
    for e in edges:
        if e["dir"] != "?":
            out.append(e)
            continue
        (x0, y0), (x1, y1) = e["a"], e["b"]
        dx, dy = (x1 - x0) / ppf, (y1 - y0) / ppf
        if e["len_ft"] > max_ft:
            out.append(e)                      # real angled wall: keep, let it refuse
            continue
        if abs(dx) > 0.05:
            out.append({"len_ft": abs(dx), "dir": "R" if dx > 0 else "L",
                        "a": (x0, y0), "b": (x1, y0)})
        if abs(dy) > 0.05:
            out.append({"len_ft": abs(dy), "dir": "D" if dy > 0 else "U",
                        "a": (x1, y0), "b": (x1, y1)})
    return out


def axis_diagnostics(legs, pool):
    """What the sheet offered each leg — printed on every refusal so a failure
    teaches instead of stonewalling (the Handoff summary-report doctrine)."""
    rows = []
    for idx, d, traced in legs:
        near = sorted(pool, key=lambda v: abs(v - traced))[:3]
        rows.append({"leg": idx, "dir": d, "traced_ft": round(traced, 2),
                     "nearest_printed": [round(v, 2) for v in near]})
    return rows


def solve_axis(legs, pool):
    """legs: [(idx, dir, traced_ft)] one axis. pool: printed values for that axis.
    Returns (solutions, diagnostics). A solution = {idx: value}, allowing at most one
    derived leg whose value is forced by closure. Solutions deduped by value tuple."""
    cand = {}
    for idx, d, traced in legs:
        near = sorted(pool, key=lambda v: abs(v - traced))[:CAND_K]
        cand[idx] = [v for v in near if abs(v - traced) <= CAND_TOL_FT]
    sols, seen = [], set()

    def emit(assign, derived_idx):
        key = tuple(round(assign[i], 2) for i, _, _ in legs)
        if key in seen:
            return
        seen.add(key)
        sols.append({"assign": dict(assign), "derived": derived_idx})

    order = [(idx, d, traced) for idx, d, traced in legs]
    # tier 0: every leg printed
    choices = [cand[idx] for idx, _, _ in order]
    if all(choices):
        for combo in product(*choices):
            s = sum(SIGN[d] * v for (idx, d, t), v in zip(order, combo))
            if abs(s) <= CLOSE_TOL_FT:
                emit({idx: v for (idx, d, t), v in zip(order, combo)}, None)
    if sols:
        return sols, "printed-only"
    # tier 1: exactly one derived leg (cal #68), the rest printed
    for di, (didx, ddir, dtraced) in enumerate(order):
        rest = [o for i, o in enumerate(order) if i != di]
        rchoices = [cand[idx] for idx, _, _ in rest]
        if not all(rchoices):
            continue
        for combo in product(*rchoices):
            partial = sum(SIGN[d] * v for (idx, d, t), v in zip(rest, combo))
            forced = -partial / SIGN[ddir]
            if forced <= 0.1 or abs(forced - dtraced) > DERIVED_TOL_FT:
                continue
            a = {idx: v for (idx, d, t), v in zip(rest, combo)}
            a[didx] = round(forced, 2)
            emit(a, didx)
    return sols, ("one-derived" if sols else "no-solution")


def evaluate_combos(h_sols, v_sols, legs, cap=5000):
    """Every closure-valid (H, V) pairing becomes a candidate WALK, evaluated whole:
    its area, and how far its printed values sit from the drawn geometry. Ambiguity
    is then judged where it matters — the AREA. Two readings a quarter-inch apart are
    the same measurement; two readings 38 SF apart are a real question."""
    traced = {idx: t for idx, _, t in legs}
    out, seen = [], set()
    for h in h_sols:
        for v in v_sols:
            if len(out) >= cap:
                break
            assign = {**h["assign"], **v["assign"]}
            key = tuple(round(assign[i], 2) for i, _, _ in legs)
            if key in seen:
                continue
            seen.add(key)
            derived = {i for i in (h["derived"], v["derived"]) if i is not None}
            walk = []
            for i, d, _t in legs:
                leg = [round(assign[i], 2), d]
                if i in derived:
                    leg.append("derived-by-closure")
                walk.append(leg)
            po = eng.polygon_outline([[val, d] for val, d, *_ in walk])
            score = sum(abs(assign[i] - traced[i]) for i in assign if i not in derived)
            out.append({"walk": walk, "area_sf": po["area_sf"],
                        "closure_ft": po["closure_err_ft"],
                        "derived": sorted(derived), "delta_score_ft": round(score, 2)})
    return sorted(out, key=lambda e: e["delta_score_ft"])


AREA_EQUIV_PCT = 1.0   # readings whose areas agree this closely are one measurement
SCHED_SEL_PCT = 2.0    # schedule cross-check window for selecting the dimensioned face

# component -> printed AREAS-schedule row (sheet 2). The schedule NEVER feeds a
# quantity (its own evidence note says so) — here it only SELECTS which closure-
# valid, all-printed-legs reading is the dimensioned OUTSIDE face, exactly the
# cross-check Jason ran on his own walks (garage vs 707, porch vs 201).
# RULED: cal #71 (Jason, 2026-08-18) — selector yes, quantity never; walks chosen
# this way carry "selected_by" naming the row and window.
SCHEDULE_MAP = {"garage slab": "GARAGE",
                "front porch slab": "FRONT PORCH - COVERED",
                "heated envelope (floor plan)": "HEATED",
                "rear deck (floor plan)": "REAR DECK - COVERED"}


def canon_multiset(walk):
    """Orientation/start-invariant summary: per-axis sorted magnitudes."""
    h = sorted(v for v, d, *_ in walk if AXIS[d] == "H")
    v = sorted(val for val, d, *_ in walk if AXIS[d] == "V")
    return h, v


def compare_to_declared(auto_walk, declared_walk):
    """Greedy per-axis matching within AGREE_TOL_FT (pages differ, prints differ by
    an inch or two — 23.48 vs 23.5 must count as agreement, 16.75 vs 13.43 must not)."""
    ah, av = canon_multiset(auto_walk)
    dh, dv = canon_multiset(declared_walk)
    agree, missed = 0, []
    for mine, his, axis in ((ah, list(dh), "H"), (av, list(dv), "V")):
        for v in mine:
            hit = next((x for x in his if abs(x - v) <= AGREE_TOL_FT), None)
            if hit is not None:
                agree += 1
                his.remove(hit)
            else:
                missed.append((axis, v))
    return {"auto_legs": len(auto_walk), "declared_legs": len(declared_walk),
            "agreeing_legs": agree, "auto_only": missed}


def main():
    import fitz
    ev = json.load(open(os.path.join(HERE, "evidence", "takeoff_evidence.json"),
                        encoding="utf-8"))
    comps = ev["area_certification"]["components"]
    schedule = {}
    for chk in ev.get("checks", []):
        if chk.get("check") == "area_schedule":
            schedule = {r["label"]: r["sqft"] for r in chk.get("rows", [])}
    declared = {}
    dw_path = os.path.join(HERE, "declared_walks.json")
    if os.path.exists(dw_path):
        declared = {w["name"]: w for w in
                    json.load(open(dw_path, encoding="utf-8")).get("walks", [])}

    doc = fitz.open(PLAN)
    ppf_by_page = {c["primary"]["page"]: c["primary"]["ppf"] for c in comps}
    f_page = 3
    f_ppf = ppf_by_page.get(f_page) or 16.646
    loops = eng.foundation_wall_loops(doc[f_page], ppf=f_ppf, close_ft=2.0)
    # run_prebid's own convention: loops arrive largest-first and name in this order
    loop_names = ["crawlspace envelope (foundation footprint)", "garage slab",
                  "front porch slab"]
    loop_by_name = dict(zip(loop_names, loops))

    # The same physical object is dimensioned on BOTH plan-geometry sheets (foundation
    # idx 3, floor plan idx 4) — Jason's own certified garage walk is built from p4
    # values arbitrating a p3 ambiguity. The engine gets the estimator's full desk:
    # chains from both sheets, one pool. (Cross-sheet reading is also exactly what
    # Handoff trains H1 for — "a detail on page 40 changes the quantity on page 12".)
    pool = {"H": set(), "V": set()}
    for pg in (3, 4):
        ppf_pg = ppf_by_page.get(pg) or f_ppf
        for c in eng.read_dimension_chains(doc[pg], ppf_pg):
            pool[c["orient"]].update(c["runs"])
            pool[c["orient"]].add(c["total"])

    out = {"schema": "roberts.auto_walks.v1",
           "origin": "engine-auto.loops+chains.v0",
           "doctrine": "no human ink anywhere in this lane; grade-only vs certified",
           "components": []}
    print("=" * 78)
    print("AUTONOMY LANE v0 — engine-drawn walks, graded against Jason's certified work")
    print("=" * 78)

    for comp in comps:
        name = comp["name"]
        cert_qty = comp["primary"]["qty"]
        his = declared.get(name)
        rec = {"name": name, "certified_sf": cert_qty}
        print(f"\n== {name}  (certified {cert_qty} SF)")

        L = loop_by_name.get(name)
        if L is None:
            rec["status"] = "no-autonomous-shape"
            rec["exception"] = ("wall-loop decomposition resolves no envelope for this "
                                "scope (floor-plan loops top out at closet scale) — "
                                "no engine-drawn shape exists yet")
            print(f"   EXCEPTION  {rec['exception']}")
            out["components"].append(rec)
            continue

        edges = split_small_diagonals(rectilinear_edges(L["polygon_pts"], f_ppf), f_ppf)
        diags = [e for e in edges if e["dir"] == "?"]
        if diags:
            diag_fts = ", ".join("%.1f" % e["len_ft"] for e in diags)
            rec["status"] = "diagonal-in-trace"
            rec["exception"] = (f"{len(diags)} non-axis edge(s) in the engine's own loop "
                                f"(~{diag_fts} ft) — rectilinear solver refuses; "
                                "trace defect or angled wall")
            print(f"   EXCEPTION  {rec['exception']}")
            out["components"].append(rec)
            continue

        legs = [(i, e["dir"], e["len_ft"]) for i, e in enumerate(edges)]
        h_legs = [l for l in legs if AXIS[l[1]] == "H"]
        v_legs = [l for l in legs if AXIS[l[1]] == "V"]
        h_sols, h_tier = solve_axis(h_legs, pool["H"])
        v_sols, v_tier = solve_axis(v_legs, pool["V"])

        if not h_sols or not v_sols:
            rec["status"] = "no-closing-assignment"
            rec["exception"] = (f"H axis: {h_tier} ({len(h_sols)} sol), "
                                f"V axis: {v_tier} ({len(v_sols)} sol) — no assignment of "
                                f"printed values closes within {CLOSE_TOL_FT} ft")
            rec["diagnostics"] = {"H": axis_diagnostics(h_legs, pool["H"]),
                                  "V": axis_diagnostics(v_legs, pool["V"])}
            print(f"   EXCEPTION  {rec['exception']}")
            for ax in ("H", "V"):
                for row in rec["diagnostics"][ax]:
                    print(f"      {ax} leg {row['leg']} {row['dir']} traced "
                          f"{row['traced_ft']:>6.2f}  nearest printed {row['nearest_printed']}")
            out["components"].append(rec)
            continue
        combos = evaluate_combos(h_sols, v_sols, legs)
        areas = [c["area_sf"] for c in combos]
        spread_pct = ((max(areas) - min(areas)) / (sum(areas) / len(areas)) * 100
                      if len(areas) > 1 else 0.0)
        best = combos[0]
        decisive = (len(combos) == 1 or spread_pct <= AREA_EQUIV_PCT or
                    combos[1]["delta_score_ft"] - best["delta_score_ft"] >= DECISIVE_GAP_FT)
        sched_sf = schedule.get(SCHEDULE_MAP.get(name))
        if not decisive and sched_sf:
            near = [c for c in combos
                    if abs(c["area_sf"] - sched_sf) / sched_sf * 100 <= SCHED_SEL_PCT]
            if near:
                # every in-window reading is printed-legs + closure-proven and agrees
                # with the plan's own figure; the pick among them stays GEOMETRY-driven
                # (closest to the drawn loop), never nearest-to-schedule
                combos, best, decisive = near, near[0], True
                rec["selected_by"] = (f"plan-schedule cross-check "
                                      f"({SCHEDULE_MAP[name]} {sched_sf:.0f} SF window "
                                      f"±{SCHED_SEL_PCT}%, {len(near)} readings) — "
                                      f"cal #71")
        if not decisive:
            rec["status"] = "ambiguous"
            rec["exception"] = (f"{len(combos)} closing readings with a real area "
                                f"spread ({min(areas)}–{max(areas)} SF, "
                                f"{spread_pct:.1f}%) — refusing rather than guessing; "
                                f"the sheet does not decide this component alone")
            rec["competing"] = [{"area_sf": c["area_sf"], "walk": c["walk"]}
                                for c in combos[:4]]
            print(f"   EXCEPTION  {rec['exception']}")
            for c in combos[:4]:
                print(f"      candidate {c['area_sf']} SF: "
                      + " ".join(f"{val}{d}" for val, d, *_ in c["walk"]))
            out["components"].append(rec)
            continue

        walk, derived = best["walk"], set(best["derived"])
        area, closure = best["area_sf"], best["closure_ft"]
        if len(combos) > 1:
            rec["equivalent_readings"] = len(combos)
            rec["area_spread_pct"] = round(spread_pct, 2)

        rec.update({
            "status": "auto-declared",
            "page": f_page, "walk": walk,
            "tiers": {"H": h_tier, "V": v_tier},
            "walk_area_sf": area, "walk_closure_ft": closure,
            "loop_inside_face_sf": round(L["area_sf"], 1),
            "delta_vs_certified_pct": round(abs(area - cert_qty) / cert_qty * 100, 2),
        })
        print(f"   walk: {len(walk)} legs ({len(derived)} derived) -> {area} SF, "
              f"closure {closure} ft   [{h_tier}/{v_tier}]")
        if rec.get("selected_by"):
            print(f"   selected by: {rec['selected_by']}")
        print(f"   vs certified {cert_qty} SF: delta {rec['delta_vs_certified_pct']}%   "
              f"(loop inside-face was {rec['loop_inside_face_sf']} SF)")
        if his:
            cmpres = compare_to_declared(walk, his["walk"])
            rec["vs_jason_walk"] = cmpres
            his_area = eng.polygon_outline([[float(v), d] for v, d, *_ in his["walk"]])["area_sf"]
            rec["jason_walk_area_sf"] = his_area
            rec["delta_vs_jason_walk_pct"] = round(abs(area - his_area) / his_area * 100, 2)
            print(f"   vs Jason's walk ({cmpres['declared_legs']} legs, {his_area} SF): "
                  f"{cmpres['agreeing_legs']}/{cmpres['auto_legs']} legs agree "
                  f"(±{AGREE_TOL_FT} ft), area delta {rec['delta_vs_jason_walk_pct']}%")
            if cmpres["auto_only"]:
                print(f"   auto-only legs: " +
                      ", ".join(f"{a} {v:.2f}" for a, v in cmpres["auto_only"]))
        out["components"].append(rec)

    doc.close()
    n_auto = sum(1 for c in out["components"] if c["status"] == "auto-declared")
    n_pass = sum(1 for c in out["components"]
                 if c["status"] == "auto-declared" and c["delta_vs_certified_pct"] <= 2.0)
    out["scoreboard"] = {"components": len(out["components"]),
                         "auto_declared": n_auto,
                         "within_2pct_of_certified": n_pass}
    path = os.path.join(HERE, "auto_walks.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\n" + "=" * 78)
    print(f"SCOREBOARD: {n_auto}/{len(out['components'])} components auto-declared, "
          f"{n_pass} within the 2% certification gate")
    print(f"wrote {path}   (report-only: declared_walks.json untouched)")
    print("=" * 78)


if __name__ == "__main__":
    main()
