#!/usr/bin/env python
"""Build the VIRTUAL TAKEOFF viewer for one job: a self-contained, file://-openable
HTML page where every measured quantity is clickable geometry drawn on the sheet.

    python tools\\viewer\\build_viewer.py --job jobs\\roberts_levelground [--zoom 2.0]

Input : <job>\\evidence\\takeoff_evidence.json  (written by run_takeoff — the substrate)
Output: <job>\\viewer\\index.html + viewer\\sheets\\*.png

Design constraints (docs/EVALUATION.md row 14: "Verification UX is the product"):
  - The plan is pinned: the evidence file's sha256 must match the PDF on disk, or this
    refuses to build — a viewer over the wrong drawing is worse than no viewer.
  - ONE coordinate frame: the SVG viewBox is in PDF points, the same numbers the
    evidence stores, so overlay coordinates need ZERO math in the browser. render_zoom
    is recorded per sheet but nothing depends on it.
  - Only pages the takeoff touched are rendered full-size (PNG-bloat guard, long side
    capped at 6000 px); every page gets a thumbnail so nothing is invisible.
  - Roof colors come FROM the engine (ROOF_LINE_COLORS), not a copy.
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # tools/

import jnj_takeoff as eng  # noqa: E402

MAX_RENDER_PX = 6000
THUMB_ZOOM = 0.2


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _hex(rgb01):
    return "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in rgb01)


def _referenced_pages(ev):
    pages = set()
    for m in ev.get("measurements", []):
        if isinstance(m.get("page"), int):
            pages.add(m["page"])
    for nm in ev.get("not_measured", []):
        if isinstance(nm.get("page"), int):
            pages.add(nm["page"])
    rl = ev.get("roof_lines") or {}
    if isinstance(rl.get("page"), int):
        pages.add(rl["page"])
    cert = ev.get("area_certification") or {}
    for c in cert.get("components", []):
        for side in ("primary", "verification"):
            e = c.get(side) or {}
            if isinstance(e.get("page"), int):
                pages.add(e["page"])
    for entry in ev.get("sheet_ledger", []):
        if isinstance(entry.get("page"), int):
            pages.add(entry["page"])
    return sorted(pages)


def build(job, zoom=2.0, out=None):
    import fitz
    job = os.path.abspath(job)
    ev_path = os.path.join(job, "evidence", "takeoff_evidence.json")
    if not os.path.exists(ev_path):
        raise ValueError(
            f"no takeoff evidence at {ev_path} — run the takeoff with evidence_dir first")
    with open(ev_path, encoding="utf-8") as fh:
        ev = json.load(fh)
    if ev.get("schema") != eng.TAKEOFF_EVIDENCE_SCHEMA:
        raise ValueError(f"unknown evidence schema {ev.get('schema')!r}")
    plan = ev.get("plan")
    if not plan or not os.path.exists(plan):
        raise ValueError(f"plan PDF not found: {plan!r}")
    sha = _sha256(plan)
    if sha != ev.get("plan_sha256"):
        raise ValueError(
            "plan sha256 mismatch — the PDF on disk is not the drawing this takeoff "
            f"measured (evidence {str(ev.get('plan_sha256'))[:12]}…, disk {sha[:12]}…). "
            "Re-run the takeoff; refusing to draw geometry on the wrong plan.")

    out = os.path.abspath(out or os.path.join(job, "viewer"))
    sheets_dir = os.path.join(out, "sheets")
    os.makedirs(sheets_dir, exist_ok=True)

    doc = fitz.open(plan)
    run_ledger = {e["page"]: e for e in ev.get("sheet_ledger", [])
                  if isinstance(e.get("page"), int)}
    referenced = set(_referenced_pages(ev))
    sheets, ledger = {}, []
    for pi in range(len(doc)):
        page = doc[pi]
        W, H = page.rect.width, page.rect.height
        # independent scale read for EVERY page (votes/err_pct feed the badge; the
        # run's own solved scale, when present, stays authoritative)
        try:
            det = eng.detect_scale(page)
        except Exception:
            det = None
        entry = dict(run_ledger.get(pi) or {"page": pi, "roles": [],
                                            "ppf": None, "scale_method": None,
                                            "scale_confidence": None})
        entry["detect"] = ({"ppf": det.get("ppf"), "scale": det.get("scale"),
                            "confidence": det.get("confidence"),
                            "votes": det.get("votes"), "err_pct": det.get("err_pct")}
                           if det else None)
        ledger.append(entry)

        thumb = f"sheets/thumb_{pi}.png"
        page.get_pixmap(matrix=fitz.Matrix(THUMB_ZOOM, THUMB_ZOOM)).save(
            os.path.join(out, *thumb.split("/")))
        rec = {"width_pt": round(W, 2), "height_pt": round(H, 2), "thumb": thumb}
        if pi in referenced:
            z = min(zoom, MAX_RENDER_PX / max(W, H))
            png = f"sheets/sheet_{pi}.png"
            page.get_pixmap(matrix=fitz.Matrix(z, z)).save(
                os.path.join(out, *png.split("/")))
            rec.update({"png": png, "render_zoom": round(z, 4)})
        sheets[str(pi)] = rec
    doc.close()

    data = {
        "job": os.path.basename(job),
        "evidence": ev,
        "evidence_rel": "../evidence/takeoff_evidence.json",
        "sheets": sheets,
        "ledger": ledger,
        "roof_colors": {k: _hex(v) for k, v in eng.ROOF_LINE_COLORS.items()},
    }

    template = os.path.join(HERE, "viewer_template.html")
    with open(template, encoding="utf-8") as fh:
        html = fh.read()
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html, n = re.subn(
        r'(<script id="takeoff-data" type="application/json">)(.*?)(</script>)',
        lambda m: m.group(1) + blob + m.group(3), html, count=1, flags=re.S)
    if n != 1:
        raise ValueError("viewer_template.html has no takeoff-data script block")
    index = os.path.join(out, "index.html")
    with open(index, "w", encoding="utf-8") as fh:
        fh.write(html)
    return index


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--job", required=True, help="job folder (contains evidence/)")
    ap.add_argument("--zoom", type=float, default=2.0,
                    help="render zoom for referenced sheets (default 2.0 = 144 dpi)")
    ap.add_argument("--out", default=None, help="output folder (default <job>/viewer)")
    args = ap.parse_args(argv)
    index = build(args.job, zoom=args.zoom, out=args.out)
    print(f"viewer : {index}")
    print(f"open   : file:///{index.replace(os.sep, '/')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
