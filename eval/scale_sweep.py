"""Scale sweep — measured ppf vs printed-note nominal, every page of every golden house.

The check behind EVALUATION.md §3e. Answers: is this plan set print-rescaled?
A set whose title block says 1/4"=1'-0" but was printed at 92.5% measures 16.71 pt/ft,
not 18.00 — and every area comes out 14.5% short with nothing on the sheet to warn you.

Run:  python scale_sweep.py
"""
import sys, os, glob, warnings

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.expanduser(r"~\.claude\skills\jnj-estimate-takeoff\tools"))

import fitz
import jnj_takeoff as J

GOLDEN = os.path.expanduser(r"~\.claude\skills\jnj-estimate-takeoff\tools\tests\golden\*\plan.pdf")
STD = [6.75, 9.0, 13.5, 18.0, 27.0, 36.0, 72.0]   # pt/ft for 3/32,1/8,3/16,1/4,3/8,1/2,1"
MIN_VOTES = 25          # below this the fit is not well supported
OFF_TOL = 0.02          # >2% from nominal counts as off


def main():
    print(f"{'house':10} {'pg':>3} {'measured ppf':>13} {'votes':>6} {'nominal':>8} {'meas/nom':>9}  flag")
    print("-" * 66)
    rows = []
    for path in sorted(glob.glob(GOLDEN)):
        house = os.path.basename(os.path.dirname(path))
        doc = fitz.open(path)
        for i in range(doc.page_count):
            try:
                ppf, votes, _cand, _members = J.calibrate_scale(doc[i])
            except Exception:
                continue
            if not ppf or votes < MIN_VOTES:
                continue
            std = min(STD, key=lambda s: abs(s - ppf))
            ratio = ppf / std
            if not (0.80 < ratio < 1.25):
                continue                      # nearest-standard match is not credible
            off = abs(ratio - 1.0) > OFF_TOL
            rows.append((house, i + 1, ppf, votes, std, ratio, off))
            print(f"{house:10} {i+1:>3} {ppf:>13.3f} {votes:>6} {std:>8.2f} {ratio:>9.4f}  {'OFF' if off else ''}")
        doc.close()

    print("-" * 66)
    for house in sorted({r[0] for r in rows}):
        hr = [r for r in rows if r[0] == house]
        off = [r for r in hr if r[6]]
        # a WHOLE-SET rescale = every well-supported page off by the SAME ratio.
        # isolated off pages are mixed-scale detail sheets, a different problem.
        whole_set = len(off) == len(hr) and len(hr) >= 3 and (max(r[5] for r in off) - min(r[5] for r in off)) < 0.03
        verdict = "WHOLE-SET RESCALED" if whole_set else ("isolated mixed-scale pages" if off else "nominal")
        note = ""
        if whole_set:
            mean = sum(r[5] for r in off) / len(off)
            note = f"  => area error if you trust the note: {(mean**2 - 1) * 100:+.1f}%"
        print(f"  {house:10} {len(off)}/{len(hr)} pages off   {verdict}{note}")


if __name__ == "__main__":
    main()
