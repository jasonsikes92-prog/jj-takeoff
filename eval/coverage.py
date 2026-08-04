#!/usr/bin/env python
"""Phase 0 -- the progress metric: ANSWERED FRACTION AT ZERO FALSE POSITIVES.

    python estimator_accuracy/coverage.py

WHY THIS EXISTS
    The release contract scores accuracy against a 98% target. That number reads 0.00%
    whether the engine answered nothing or answered half the sheet perfectly, because
    unanswered fields score as zero. Every improvement looks identical to no improvement,
    so there is nothing to steer by. This reports what the engine actually committed to.

THE TWO NUMBERS
    ANSWERED  -- the engine put a value on the row: MEASURED / COUNTED / VERIFIED_ZERO /
                 INTAKE. It is on the hook for it.
    DECLINED  -- it fail-closed: MORE_INFORMATION_REQUIRED / DECLINED.

    Coverage is only meaningful next to the false-positive count. A confident wrong number
    is worse than a blank -- Jason would bid it and never catch it. Never trade a false
    positive for coverage.

    Answered splits into POSITIVE (a real quantity) and ZERO (a proven absence). Zeros are
    63% of the sheet and are the false-positive check set, so they are tracked separately:
    coverage that comes only from zeros is real progress, but it is not the same progress.
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, 'phase1_registered_inputs')
SCORE = os.path.join(HERE, 'phase1_takeoff_score_v3.json')

ANSWERED = {'MEASURED', 'COUNTED', 'VERIFIED_ZERO', 'INTAKE'}
DECLINED = {'MORE_INFORMATION_REQUIRED', 'DECLINED'}


def job_coverage(path):
    """Return (answered_positive, answered_zero, declined, total, terminal) for one job."""
    p = json.load(open(path, encoding='utf-8'))
    pos = zero = dec = 0
    for m in p.get('measurements', []):
        st = m.get('status')
        if st in ANSWERED:
            q = m.get('quantity')
            if st == 'VERIFIED_ZERO' or q in (0, 0.0):
                zero += 1
            else:
                pos += 1
        elif st in DECLINED:
            dec += 1
    total = len(p.get('measurements', []))
    return pos, zero, dec, total, p.get('terminalStatus')


def main():
    rows, tot = [], collections.Counter()
    for d in sorted(glob.glob(os.path.join(INPUTS, 'PR-*'))):
        f = os.path.join(d, 'output', 'prediction.json')
        if not os.path.exists(f):
            continue
        pos, zero, dec, total, term = job_coverage(f)
        rows.append((os.path.basename(d), pos, zero, dec, total, term))
        tot['pos'] += pos; tot['zero'] += zero; tot['dec'] += dec; tot['total'] += total

    fp = fc = None
    if os.path.exists(SCORE):
        s = json.load(open(SCORE, encoding='utf-8'))
        fp, fc = s.get('falsePositiveCount'), s.get('falseCertificationCount')

    print('COVERAGE - answered fraction at zero false positives\n')
    print(f"  {'JOB':9}{'answered':>9}{'positive':>10}{'zero':>7}{'declined':>10}{'total':>7}  terminal")
    for j, pos, zero, dec, total, term in rows:
        a = pos + zero
        print(f'  {j:9}{a/total:8.1%}{pos:10}{zero:7}{dec:10}{total:7}  {term}')

    answered = tot['pos'] + tot['zero']
    print(f"\n  {'COHORT':9}{answered/max(tot['total'],1):8.1%}"
          f"{tot['pos']:10}{tot['zero']:7}{tot['dec']:10}{tot['total']:7}")

    print(f"\n  answered            {answered} of {tot['total']}"
          f"  ({answered/max(tot['total'],1):.1%})")
    print(f"  false positives     {fp if fp is not None else 'unknown - scorer not run'}"
          f"{'   <-- THE CONSTRAINT. Must stay 0.' if fp == 0 else ''}")
    if fc is not None:
        print(f"  false certifications {fc}")
    print('\n  Reference: Handoff H1 81.6% / experienced human estimator 77-78%'
          '\n  (different benchmark and scoring method - directional only, not comparable)')

    if fp:
        print('\n  REGRESSION: a false positive appeared. Coverage gained this way is not'
              '\n  progress -- a confident wrong quantity is worse than a blank.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
