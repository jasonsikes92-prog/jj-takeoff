#!/usr/bin/env python
"""Normalize the staged Buildern measurement + estimate exports into one
ground-truth corpus (training/ground_truth.json).

Measurement xlsx shape (Group by Category): category rows have no Quantity;
measurement rows carry Quantity ("2935.14 ft2" / "20 unit" / "324.22 ft"),
Waste ("10 %"), Type (Area/Linear/Count/Roof area/Manual), Plan. Child rows
(per-segment) sit under a measurement with indented names — kept as children.

Estimate xlsx shape: Name/Cost Type/Status/Cost Code/Description/.../Quantity/
Unit/Unit Cost/Markup/... Group rows carry no unit cost.
"""

import json
import os
import re
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))

QTY_RE = re.compile(r"^\s*([\d,]+(?:\.\d+)?)\s*(.*)$")


def parse_qty(val):
    if val is None:
        return None, None
    s = str(val).strip()
    m = QTY_RE.match(s)
    if not m:
        return None, s or None
    num = float(m.group(1).replace(",", ""))
    unit = m.group(2).strip() or None
    return num, unit


def parse_measurements(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(c) if c else "" for c in rows[0]]
    idx = {name: i for i, name in enumerate(header)}

    def cell(r, name):
        i = idx.get(name)
        return r[i] if i is not None and i < len(r) else None

    def s(v):
        return str(v).strip() if v is not None else ""

    out, current_cat = [], None
    for r in rows[1:]:
        name = s(cell(r, "Name"))
        if not name:
            continue
        qty_raw, typ = s(cell(r, "Quantity")), s(cell(r, "Type"))
        if not qty_raw and not typ:
            current_cat = name          # category header row
            continue
        qty, _ = parse_qty(qty_raw)
        waste, _ = parse_qty(s(cell(r, "Waste")))
        out.append({
            "category": current_cat, "name": name,
            "qty": qty, "unit": s(cell(r, "Unit")) or None,
            "waste_pct": waste,
            "type": typ or None,
            "plan": s(cell(r, "Plan")) or None,
        })
    return out


def parse_estimate(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(c) if c else "" for c in rows[0]]
    idx = {name: i for i, name in enumerate(header)}

    def cell(r, name):
        i = idx.get(name)
        return r[i] if i is not None and i < len(r) else None

    out = []
    for r in rows[1:]:
        name = cell(r, "Name")
        if not name:
            continue
        unit_cost = cell(r, "Unit Cost")
        qty = cell(r, "Quantity")
        if unit_cost is None and qty is None:
            continue                     # group header
        try:
            unit_cost = float(str(unit_cost).replace("$", "").replace(",", "")) \
                if unit_cost not in (None, "") else None
        except ValueError:
            unit_cost = None
        try:
            qty = float(str(qty).replace(",", "")) if qty not in (None, "") else None
        except ValueError:
            qty = None
        out.append({
            "name": str(name).strip(),
            "cost_type": (str(cell(r, "Cost Type")).strip() or None) if cell(r, "Cost Type") else None,
            "cost_code": (str(cell(r, "Cost Code")).strip() or None) if cell(r, "Cost Code") else None,
            "qty": qty,
            "unit": (str(cell(r, "Unit")).strip() or None) if cell(r, "Unit") else None,
            "unit_cost": unit_cost,
        })
    return out


def main():
    corpus = {}
    for job in sorted(os.listdir(HERE)):
        jd = os.path.join(HERE, job)
        if not os.path.isdir(jd):
            continue
        entry = {}
        mp = os.path.join(jd, "measurements.xlsx")
        ep = os.path.join(jd, "estimate_items.xlsx")
        if os.path.exists(mp):
            entry["measurements"] = parse_measurements(mp)
        if os.path.exists(ep):
            entry["estimate_items"] = parse_estimate(ep)
        pdfs = [f for f in os.listdir(jd) if f.endswith(".pdf")]
        if pdfs:
            entry["plan_pdfs"] = pdfs
        if entry:
            corpus[job] = entry

    path = os.path.join(HERE, "ground_truth.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(corpus, fh, indent=1)

    print(f"{'job':<14} {'meas':>5} {'est':>5}  pdfs  categories")
    for job, e in corpus.items():
        m = e.get("measurements", [])
        cats = sorted({x["category"] for x in m if x["category"]})
        print(f"{job:<14} {len(m):>5} {len(e.get('estimate_items', [])):>5}  "
              f"{len(e.get('plan_pdfs', [])):>4}  {', '.join(cats[:6])}"
              f"{' …' if len(cats) > 6 else ''}")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
