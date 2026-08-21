import sys, os, json
sys.path.insert(0, "tools")
import fitz
import jnj_takeoff as eng

OUT = "training/readability_scorecard.json"
results = {}
if os.path.exists(OUT):
    results = json.load(open(OUT))
jobs = ["roberts","davis","guarino_v3","show","watkins","dugger","pace_kinards","burns","holbrook","mason","zegarra"]
for job in jobs:
    if job in results:
        continue
    p = "tools/tests/golden/roberts/plan.pdf" if job == "roberts" else f"training/{job}/plan.pdf"
    if not os.path.exists(p):
        continue
    try:
        doc = fitz.open(p)
    except Exception as e:
        results[job] = {"error": str(e)}
        continue
    per = []
    for i in range(doc.page_count):
        page = doc[i]
        has_text = bool(page.get_text().strip())
        sc = None
        try:
            sc = eng._page_scale(page)
        except Exception:
            pass
        nch = 0
        if sc:
            try:
                nch = len(eng.read_dimension_chains(page, sc["ppf"]))
            except Exception:
                nch = -1
        per.append({"i": i, "text": has_text, "ppf": round(sc["ppf"], 2) if sc else None,
                    "conf": sc["confidence"] if sc else None, "chains": nch})
    doc.close()
    results[job] = per
    json.dump(results, open(OUT, "w"), indent=1)
    v = sum(1 for r in per if r["text"]); s = sum(1 for r in per if r["ppf"])
    c = sum(max(r["chains"], 0) for r in per)
    print(f"{job}: {len(per)} pages, {v} with text, {s} scaled, {c} chains", flush=True)
print("DONE")
