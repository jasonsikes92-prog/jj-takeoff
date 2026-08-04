"""Level Ground — regenerate the site report samples FROM the one template.

Run this after editing lg_report_template.html so the deployed samples never drift from the
template (that two-copy drift was a real bug once). It produces:
  site/sample-report.html        = the template verbatim (BID_GAP sample; headline reconciles)
  site/sample-prebid-report.html = template + report_from_takeoff() PRE-BID JSON (Phase 1)

Phase 1 pipeline: run_takeoff(plans) -> report_from_takeoff(takeoff, home, region) -> report JSON
-> injected into the template. Only the plans are needed for a pre-bid report; no builder bid.
Usage:  python gen_reports.py
"""
import os, re, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL  = os.path.join(HERE, "lg_report_template.html")
SITE = os.path.join(HERE, "site")
# the takeoff engine (report_from_takeoff lives with run_takeoff)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))   # consolidated 2026-08-04: engine is a sibling
import jnj_takeoff as J


def inject(html, report):
    """Swap the <script id="report-data"> JSON block for `report` (pretty, em-dashed)."""
    block = json.dumps(report, indent=2, ensure_ascii=False).replace("--", "—")
    return re.sub(r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
                  lambda m: m.group(1) + "\n" + block + "\n" + m.group(3),
                  html, count=1, flags=re.S)


def main():
    tpl = open(TPL, encoding="utf-8").read()

    # a realistic run_takeoff() result for a matched sample house (in production this comes from
    # run_takeoff(plans)); shared by both the pre-bid and the bid-gap samples.
    takeoff = {"lines": [
        {"trade": "heated_sf", "qty": 3214, "unit": "SF", "source": "GIVEN-schedule",
         "method": "text-schedule", "confidence": "high", "page": 1, "note": ""},
        {"trade": "framing_sf", "qty": 4400, "unit": "SF", "source": "GIVEN-schedule",
         "method": "text-schedule", "confidence": "high", "page": 1, "note": ""},
        {"trade": "roof_surface_sq", "qty": 48, "unit": "sq", "source": "MEASURED",
         "method": "face-decomposition", "confidence": "high", "page": 3, "note": ""},
        {"trade": "foundation_wall_lf", "qty": 312, "unit": "LF", "source": "MEASURED",
         "method": "enclosed-region", "confidence": "high", "page": 2, "note": ""},
        {"trade": "slab_area_sf", "qty": 3120, "unit": "SF", "source": "MEASURED",
         "method": "two-tracer-agree", "confidence": "high", "page": 2, "note": ""},
    ], "not_measured": [], "assumptions": []}
    home = {"stories": 1.5, "foundation": "slab", "garage": "3-car", "finish_level": "custom",
            "insulation": "spray foam roofline"}
    region = {"state": "GA", "zip3": "310", "market": "Middle Georgia"}

    # 1) BID-GAP sample = ENGINE-GENERATED from a structured builder's bid (Phase 3, end-to-end).
    #    In production the bid comes from ingest_bid_xlsx() / a VLM read; here it's a realistic
    #    summary that's thin on the usual gaps (site under-carried, insulation priced batt vs. the
    #    plan's foam, electrical a lump; gutters / low-voltage / landscaping absent).
    bid = J.ingest_bid([
        {"desc": "Foundation & slab", "amount": 42000},
        {"desc": "Framing labor and materials", "amount": 118000},
        {"desc": "Roofing", "amount": 16000},
        {"desc": "Windows and exterior doors", "amount": 40000},
        {"desc": "Plumbing", "amount": 28000},
        {"desc": "HVAC", "amount": 32000},
        {"desc": "Electrical", "amount": 35000, "is_lump": True},
        {"desc": "Insulation (batt package)", "amount": 8200},
        {"desc": "Drywall, paint and trim", "amount": 62000},
        {"desc": "Cabinets and countertop allowance", "amount": 22000},
        {"desc": "Flooring and tile", "amount": 34000},
        {"desc": "Site work allowance", "amount": 4500},
        {"desc": "Permits and fees", "amount": 9000},
        {"desc": "General conditions and supervision", "amount": 136700},
    ], total=587400)
    bg = J.report_from_takeoff(
        takeoff, home, region, prepared_for="Sample Homeowner",
        property_label="Sample Residence — Lake County, GA",
        report_id="LG-BIDGAP-0001", date="2026-07-06", is_sample=True,
        market_book=J.MARKET_RATE_BOOK, bid=bid)
    open(os.path.join(SITE, "sample-report.html"), "w", encoding="utf-8").write(inject(tpl, bg))

    # 2) PRE-BID sample (plans only, no bid) via the same adapter.
    rep = J.report_from_takeoff(
        takeoff, home, region, prepared_for="Sample Homeowner",
        property_label="Sample Residence — Lake County, GA",
        report_id="LG-PREBID-0001", date="2026-07-06", report_type="pre_bid", is_sample=True,
        market_book=J.MARKET_RATE_BOOK)
    open(os.path.join(SITE, "sample-prebid-report.html"), "w", encoding="utf-8").write(inject(tpl, rep))

    print("wrote site/sample-report.html (bid_gap, engine-generated) + site/sample-prebid-report.html")
    print("bid_gap: total ${:,.0f}, {} findings, {} exposure-priced".format(
        bg["meta"]["bid_total"], len(bg["findings"]),
        sum(1 for f in bg["findings"] if f["realistic_low"] is not None)))
    print("pre_bid:", len(rep["quantities"]), "quantities,", len(rep["findings"]), "checklist findings")


if __name__ == "__main__":
    main()
