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
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # tools/

import jnj_takeoff as eng  # noqa: E402

MAX_RENDER_PX = 6000
THUMB_ZOOM = 0.2


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
        # the ledger enumerates EVERY sheet (doctrine) — only role-mapped pages
        # earn a full-size render; the rest keep thumbnails (PNG-bloat guard,
        # and the serve-mode teach loop rebuilds on every save).
        if entry.get("roles") and isinstance(entry.get("page"), int):
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
    sha = eng.sha256_file(plan)
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
        entry = dict(run_ledger.get(pi) or {"page": pi, "roles": [],
                                            "ppf": None, "scale_method": None,
                                            "scale_confidence": None})
        # the evidence writer freezes each page's detect verdict at takeoff time
        # (sha-pinned, so it cannot change); re-detect only for older evidence
        # files that predate the persisted field — this was 74% of rebuild time.
        if "detect" not in entry:
            try:
                det = eng.detect_scale(page)
                entry["detect"] = {k: det.get(k) for k in
                                   ("ppf", "scale", "confidence", "votes",
                                    "err_pct")}
            except Exception:
                entry["detect"] = None
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

    walks = None
    walks_path = os.path.join(job, "proposed_walks.json")
    if os.path.exists(walks_path):
        with open(walks_path, encoding="utf-8") as fh:
            walks = json.load(fh)
    data = {
        "job": os.path.basename(job),
        "evidence": ev,
        "evidence_rel": "../evidence/takeoff_evidence.json",
        "sheets": sheets,
        "ledger": ledger,
        "roof_colors": {k: _hex(v) for k, v in eng.ROOF_LINE_COLORS.items()},
        "walks": walks,
    }

    template = os.path.join(HERE, "viewer_template.html")
    with open(template, encoding="utf-8") as fh:
        html = fh.read()
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    if html.count("__TAKEOFF_DATA__") != 1:
        raise ValueError("viewer_template.html must contain exactly one "
                         "__TAKEOFF_DATA__ placeholder")
    html = html.replace("__TAKEOFF_DATA__", blob, 1)
    index = os.path.join(out, "index.html")
    with open(index, "w", encoding="utf-8") as fh:
        fh.write(html)
    return index


def serve(job, port=5810):
    """TEACH LOOP without leaving the browser: serve the viewer on localhost and
    accept POST /teach with the walk answers — save them, run the job's
    apply_walks.py (declare walks -> re-run takeoff -> rebuild viewer), and the
    page reloads itself into the new state. Local machine only, fixed argv, no
    request data ever reaches a shell."""
    import http.server
    import subprocess

    job = os.path.abspath(job)
    out = os.path.join(job, "viewer")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=out, **kw)

        def log_message(self, fmt, *a):
            sys.stderr.write("  " + (fmt % a) + "\n")

        def do_POST(self):
            if self.path != "/teach":
                self.send_error(404)
                return
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n)
            try:
                answers = json.loads(body)
            except ValueError:
                self.send_error(400, "answers must be JSON")
                return
            with open(os.path.join(job, "walk_answers.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(answers, fh, indent=1)
            apply_py = os.path.join(job, "apply_walks.py")
            r = subprocess.run([sys.executable, apply_py], capture_output=True,
                               text=True, timeout=900)
            log = ((r.stdout or "") + (r.stderr or ""))[-4000:]
            payload = json.dumps({"ok": r.returncode == 0, "log": log}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"teach loop live: http://localhost:{port}/  (Ctrl+C to stop)")
    httpd.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--job", required=True, help="job folder (contains evidence/)")
    ap.add_argument("--zoom", type=float, default=2.0,
                    help="render zoom for referenced sheets (default 2.0 = 144 dpi)")
    ap.add_argument("--out", default=None, help="output folder (default <job>/viewer)")
    ap.add_argument("--serve", action="store_true",
                    help="serve the viewer with the live teach loop (POST /teach)")
    args = ap.parse_args(argv)
    index = build(args.job, zoom=args.zoom, out=args.out)
    print(f"viewer : {index}")
    print(f"open   : file:///{index.replace(os.sep, '/')}")
    if args.serve:
        serve(args.job)
    return 0


if __name__ == "__main__":
    sys.exit(main())
