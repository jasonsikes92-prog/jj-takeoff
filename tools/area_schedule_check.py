"""Compare independent projected geometry with printed areas, without approval."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from viewer.measurement_store import calculate


def compare(references, measurements, tolerance_percent=5):
    if type(tolerance_percent) not in (int, float) or not math.isfinite(tolerance_percent) or tolerance_percent < 0:
        raise ValueError('Tolerance must be a nonnegative finite percentage')
    normalize = lambda label: ' '.join(label.upper().split())
    printed = defaultdict(list)
    geometry = defaultdict(list)
    for reference in references:
        for row in reference['rows']:
            printed[(reference['page'], normalize(row['label']))].append(row)
    for measurement in measurements:
        if measurement.get('source_area_label') and measurement['kind'] == 'area':
            geometry[(measurement['page'], normalize(measurement['source_area_label']))].append(measurement)
    rows = []
    for page, label in sorted(printed.keys() | geometry.keys()):
        sources = printed[(page, label)]
        candidates = geometry[(page, label)]
        row = {'page': page, 'label': label, 'measurement_ids': [m['id'] for m in candidates],
               'printed_sf': None, 'measured_sf': None, 'difference_percent': None}
        if len(sources) > 1 or len(candidates) > 1:
            row['status'] = 'ambiguous_scope'
        elif not sources:
            row['status'] = 'printed_reference_missing'
        elif not candidates:
            row['status'] = 'measurement_missing'
        else:
            value = sources[0]['sqft']
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                row['status'] = 'invalid_printed_reference'
            else:
                # Schedule SF is plan area, never roof slope-adjusted surface area.
                measured = calculate(candidates[0])['projected_area_sf']
                difference = 100 * (measured - value) / value
                row.update(printed_sf=value, measured_sf=measured, difference_percent=difference,
                           status='within_tolerance' if abs(difference) <= tolerance_percent else 'discrepancy')
        rows.append(row)
    fingerprint = hashlib.sha256(json.dumps({'references': references, 'measurements': measurements},
                                           sort_keys=True, allow_nan=False).encode()).hexdigest()
    return {'rows': rows, 'tolerance_percent': tolerance_percent,
            'status': 'no_comparable_scope' if not rows else
                ('within_tolerance' if all(r['status'] == 'within_tolerance' for r in rows) else 'review_required'),
            'input_sha256': fingerprint, 'use': 'comparison_only', 'certified': False,
            'estimate_released': False,
            'remaining': 'Agreement does not approve scope or accuracy. Recompute after geometry or reference edits.'}


def from_folder(folder, state):
    path = Path(folder).parent / 'plan_inventory.json'
    if not path.exists():
        return None
    inventory = json.loads(path.read_text(encoding='utf-8'))
    if inventory['plan_sha256'] != state['plan_sha256']:
        raise ValueError('Printed area inventory belongs to a different drawing revision')
    result = compare(inventory.get('area_schedule_references', []), list(state['measurements'].values()))
    result.update(plan_sha256=state['plan_sha256'], measurement_version=state['version'])
    return result
