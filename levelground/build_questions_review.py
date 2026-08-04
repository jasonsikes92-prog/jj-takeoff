#!/usr/bin/env python3
"""Render data/jurisdiction-questions.json into a readable review page.

Source of truth is the JSON. Re-run this after editing it.
    python build_questions_review.py
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "data" / "jurisdiction-questions.json"
OUT = ROOT / "questions-review.html"

SIGNAL = {"low": "Low", "moderate": "Moderate", "high": "High", "very_high": "Very high"}

CSS = """
:root{--navy:#0E2233;--steel:#5C90AC;--paper:#F4EFE4;--offwhite:#FBF9F4;--red:#D63A2B;--ink:#15242F;--muted:#6E7E88}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);font-family:"Inter",system-ui,sans-serif;color:var(--ink);line-height:1.6}
.top{background:var(--navy);color:#fff;padding:26px 24px}
.top .in{max-width:880px;margin:0 auto}
.top b{font-family:"Oswald",sans-serif;letter-spacing:.16em;text-transform:uppercase}
.top p{margin:.4em 0 0;color:#AFCBDD;font-size:.9rem}
.wrap{max-width:880px;margin:0 auto;padding:36px 24px 90px}
h2{font-family:"Fraunces",Georgia,serif;font-weight:500;font-size:1.5rem;margin:44px 0 2px}
h2 .g{display:block;font-family:"Inter",sans-serif;font-size:.85rem;font-weight:400;color:var(--muted);margin-top:4px}
.q{background:var(--offwhite);border:1px solid #E2D8C4;border-radius:6px;padding:22px 24px;margin:16px 0}
.q.p1{border-left:4px solid var(--red)}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;align-items:center}
.tag{font-family:"Oswald",sans-serif;text-transform:uppercase;letter-spacing:.1em;font-size:.6rem;padding:3px 8px;border-radius:2px;background:#E7DFCE;color:#4a5f6b}
.tag.p1{background:var(--red);color:#fff}
.tag.vh{background:#8C1D12;color:#fff}.tag.h{background:var(--navy);color:#fff}
.id{font-family:ui-monospace,monospace;font-size:.7rem;color:var(--muted);margin-left:auto}
.ask{font-family:"Fraunces",Georgia,serif;font-size:1.12rem;margin:0 0 8px}
.why{color:var(--muted);font-size:.9rem;margin:0 0 12px}
.blder{border-left:3px solid var(--steel);padding:8px 0 8px 14px;margin:0 0 16px;font-size:.92rem}
.blder span{font-family:"Oswald",sans-serif;text-transform:uppercase;letter-spacing:.1em;font-size:.6rem;color:#3c6379;display:block;margin-bottom:3px}
details{border-top:1px solid #E2D8C4;padding:10px 0 0}
summary{cursor:pointer;font-weight:600;font-size:.92rem;padding:4px 0}
summary::marker{color:var(--steel)}
details p{margin:6px 0 12px;font-size:.93rem;color:#33454f}
.foot{max-width:880px;margin:0 auto;padding:0 24px 60px;color:var(--muted);font-size:.85rem}
"""


def render_question(q):
    sig = q["cost_signal"]
    sig_cls = {"very_high": "vh", "high": "h"}.get(sig, "")
    tags = []
    if q["priority"] == 1:
        tags.append('<span class="tag p1">Core &mdash; call sheet</span>')
    else:
        tags.append('<span class="tag">Extended</span>')
    tags.append(f'<span class="tag {sig_cls}">{SIGNAL[sig]} cost</span>')

    branches = "".join(
        f'<details><summary>{html.escape(a["label"])}</summary>'
        f'<p>{html.escape(a["next_steps"])}</p></details>'
        for a in q["answers"]
    )
    return (
        f'<div class="q p{q["priority"]}">'
        f'<div class="tags">{"".join(tags)}<span class="id">{q["id"]}</span></div>'
        f'<p class="ask">&ldquo;{html.escape(q["ask_county"])}&rdquo;</p>'
        f'<p class="why">{html.escape(q["why"])}</p>'
        f'<div class="blder"><span>Then ask the builder</span>{html.escape(q["ask_builder"])}</div>'
        f"{branches}</div>"
    )


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    qs = data["questions"]
    body = []
    for g in data["groups"]:
        in_group = [q for q in qs if q["group"] == g["id"]]
        if not in_group:
            continue
        in_group.sort(key=lambda q: q["priority"])
        body.append(f'<h2>{html.escape(g["title"])}<span class="g">{html.escape(g["blurb"])}</span></h2>')
        body.extend(render_question(q) for q in in_group)

    core = sum(1 for q in qs if q["priority"] == 1)
    branch_count = sum(len(q["answers"]) for q in qs)

    OUT.write_text(
        "<!doctype html><html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        "<title>Jurisdiction questions &mdash; review</title>"
        '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500'
        '&family=Inter:wght@400;500;600&family=Oswald:wght@500;600;700&display=swap" rel=stylesheet>'
        f"<style>{CSS}</style></head><body>"
        f'<div class="top"><div class="in"><b>Level Ground</b>'
        f"<p>Jurisdiction question set &amp; answer tree &mdash; v{data['version']}, "
        f"{len(qs)} questions ({core} core), {branch_count} next-step blocks. "
        f"Generated from data/jurisdiction-questions.json &mdash; edit the JSON, not this page.</p></div></div>"
        f'<div class="wrap">{"".join(body)}</div>'
        f'<div class="foot">Click any answer to read the next-step block a homeowner sees when they report that answer back.</div>'
        "</body></html>",
        encoding="utf-8",
    )
    print(f"Wrote {OUT.name}: {len(qs)} questions, {core} core, {branch_count} next-step blocks")


if __name__ == "__main__":
    main()
