#!/usr/bin/env python
"""Viewer generator (Phase B): builds a self-contained page from takeoff_evidence.json.

What must hold:
  - the built index.html carries ONE injected takeoff-data JSON block that parses and
    round-trips the evidence (same measurement ids, same coordinate frame);
  - every referenced sheet PNG exists and its pixel size equals page_pt x render_zoom
    (the recorded zoom is informational — overlay coordinates never depend on it, but a
    lying record would still mislead a reader);
  - a tampered evidence file (wrong plan sha) is REFUSED — a viewer drawing geometry on
    the wrong plan is worse than no viewer.
"""

import json
import os
import re
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(TOOLS, "viewer"))

import build_viewer  # noqa: E402

JOB = os.path.join(os.path.dirname(TOOLS), "jobs", "roberts_levelground")


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", head[16:24])


def main():
    tmp = tempfile.mkdtemp(prefix="viewer-build-")
    index = build_viewer.build(JOB, zoom=2.0, out=os.path.join(tmp, "viewer"))
    assert os.path.exists(index), "index.html was not written"
    with open(index, encoding="utf-8") as fh:
        html = fh.read()
    blocks = re.findall(
        r'<script id="takeoff-data" type="application/json">(.*?)</script>', html, re.S)
    assert len(blocks) == 1, f"expected exactly one takeoff-data block, got {len(blocks)}"
    data = json.loads(blocks[0].replace("<\\/", "</"))
    for key in ("job", "evidence", "sheets", "ledger", "roof_colors"):
        assert key in data, f"viewer data missing {key!r}"
    ev = data["evidence"]
    assert ev["coordinate_frame"].startswith("pdf-points")

    # evidence round-trips: the built page holds the same measurements, ids intact
    with open(os.path.join(JOB, "evidence", "takeoff_evidence.json"),
              encoding="utf-8") as fh:
        src = json.load(fh)
    assert [m["id"] for m in ev["measurements"]] == \
           [m["id"] for m in src["measurements"]]

    # sheet PNGs: exist, and pixel dims match the recorded page_pt x render_zoom
    rendered = 0
    for pi, rec in data["sheets"].items():
        thumb = os.path.join(tmp, "viewer", *rec["thumb"].split("/"))
        assert os.path.exists(thumb), f"missing {rec['thumb']}"
        if "png" not in rec:
            continue
        rendered += 1
        png = os.path.join(tmp, "viewer", *rec["png"].split("/"))
        w, h = png_size(png)
        assert abs(w - rec["width_pt"] * rec["render_zoom"]) <= 2, \
            f"sheet {pi}: PNG {w}px vs {rec['width_pt']}pt x {rec['render_zoom']}"
        assert abs(h - rec["height_pt"] * rec["render_zoom"]) <= 2
        assert max(w, h) <= build_viewer.MAX_RENDER_PX + 2, "render cap violated"
    assert rendered >= 2, f"only {rendered} sheets rendered — expected the takeoff pages"

    # roof colors came from the engine, as hex
    assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in data["roof_colors"].values())

    # tampered evidence must be refused
    fake = tempfile.mkdtemp(prefix="viewer-tamper-")
    os.makedirs(os.path.join(fake, "evidence"))
    bad = dict(src)
    bad["plan_sha256"] = "0" * 64
    with open(os.path.join(fake, "evidence", "takeoff_evidence.json"), "w",
              encoding="utf-8") as fh:
        json.dump(bad, fh)
    try:
        build_viewer.build(fake, out=os.path.join(fake, "viewer"))
        raise AssertionError("tampered plan_sha256 was accepted")
    except ValueError as exc:
        assert "sha256 mismatch" in str(exc), exc
    shutil.rmtree(fake, ignore_errors=True)

    print(f"PASS: viewer builds from evidence — {rendered} sheets rendered at recorded "
          f"zoom, JSON block round-trips {len(ev['measurements'])} measurements, "
          f"tampered evidence refused")


if __name__ == "__main__":
    main()
