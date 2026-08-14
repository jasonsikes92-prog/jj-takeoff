#!/usr/bin/env python
"""Apply Jason's teach-mode answers: proposed_walks.json + walk_answers.json ->
declared_walks.json, then re-run the takeoff and rebuild the viewer.

Answers shape (written by the viewer's teach panel):
  {"components": {"<name>": {"legs": {"<index>": <printed_ft> | "defect"},
                             "confirmed": true}}}

Rules (fail-closed, same doctrine as everything else):
  - a leg answered with a number must be one of the sheet's printed values — the
    engine re-verifies every leg at run time anyway, so a wrong value refuses there;
  - a leg answered "defect" means the TRACE is wrong there (e.g. the porch diagonal):
    the walk uses the printed neighbors as drawn; if the defect legs make the walk
    incomplete, the component stays UNDECLARED and keeps its all-ink verification;
  - only components marked confirmed are declared. Nothing silent.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def build_declared(proposed, answers):
    walks, skipped = [], []
    for comp in proposed.get("components", []):
        name = comp["name"]
        a = (answers.get("components") or {}).get(name) or {}
        if not a.get("confirmed"):
            skipped.append(f"{name}: not confirmed in teach mode")
            continue
        leg_answers = {int(k): v for k, v in (a.get("legs") or {}).items()}
        walk, bad = [], []
        for i, leg in enumerate(comp.get("legs", [])):
            val = leg_answers.get(i, leg.get("printed_ft"))
            if val == "defect":
                bad.append(i)
                continue
            if val is None or leg["dir"] == "?":
                bad.append(i)
                continue
            walk.append([float(val), leg["dir"]])
        if bad and not a.get("allow_gaps"):
            skipped.append(f"{name}: legs {bad} unresolved — stays all-ink verified")
            continue
        walks.append({"name": name, "page": comp["page"], "walk": walk,
                      "origin_pt": comp["origin_pt"],
                      "confirmed_by": answers.get("reviewed_by", "viewer"),
                      "answered_legs": {str(k): v for k, v in leg_answers.items()}})
    return walks, skipped


def main(rerun=True):
    with open(os.path.join(HERE, "proposed_walks.json"), encoding="utf-8") as fh:
        proposed = json.load(fh)
    ans_path = os.path.join(HERE, "walk_answers.json")
    answers = {}
    if os.path.exists(ans_path):
        with open(ans_path, encoding="utf-8") as fh:
            answers = json.load(fh)
    walks, skipped = build_declared(proposed, answers)
    out = {"schema": "roberts.declared_walks.v1", "walks": walks}
    with open(os.path.join(HERE, "declared_walks.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"declared {len(walks)} walk(s); skipped: {skipped or 'none'}")
    if not rerun:
        return 0
    for cmd in ([sys.executable, os.path.join(HERE, "run_prebid.py")],
                [sys.executable, os.path.join(HERE, "..", "..", "tools", "viewer",
                                              "build_viewer.py"), "--job", HERE]):
        print(f"\n$ {' '.join(os.path.basename(c) for c in cmd)}")
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        tail = (r.stdout or "") + (r.stderr or "")
        print("\n".join(tail.splitlines()[-6:]))
        if r.returncode != 0:
            print(f"FAILED ({r.returncode})")
            return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main(rerun="--no-rerun" not in sys.argv))
