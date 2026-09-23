"""Enumerate field-stud stations outside source-reviewed assembly reservations.

Runs and reservation intervals use the same drawing-point coordinate system.
The local increasing-coordinate datum is an estimating assumption, not a field
layout approval. Reserved stations are not material quantities or waste credits.
"""
import math
from collections import defaultdict


def layout(runs, zones, *, points_per_foot, spacing_inches, first_center_inches):
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    if (not all(finite(v) for v in (points_per_foot, spacing_inches, first_center_inches))
            or points_per_foot <= 0 or spacing_inches <= 0
            or not 0 <= first_center_inches < spacing_inches):
        raise ValueError('Positive scale/spacing and an explicit datum within one spacing required')
    by_run = {}
    for run in runs:
        if (not isinstance(run.get('id'), str) or not run['id'].strip()
                or run['id'] in by_run or not isinstance(run.get('source'), str)
                or not run['source'].strip()):
            raise ValueError('Unique run identity and source required')
        if (run.get('orientation') not in ('horizontal', 'vertical')
                or not all(finite(run.get(k)) for k in ('start_pt', 'end_pt', 'coordinate_pt'))
                or run['start_pt'] >= run['end_pt']):
            raise ValueError('Ordered straight run geometry required')
        by_run[run['id']] = run
    if not by_run:
        raise ValueError('At least one measured run required')
    reserved = defaultdict(list)
    for zone in zones:
        interval = zone.get('interval')
        if (zone.get('run') not in by_run
                or any(not isinstance(zone.get(k), str) or not zone[k].strip()
                       for k in ('assembly', 'source'))
                or not isinstance(interval, (list, tuple)) or len(interval) != 2
                or not all(finite(v) for v in interval) or interval[0] > interval[1]):
            raise ValueError('Source-linked reservation on a known run required')
        run = by_run[zone['run']]
        if interval[1] < run['start_pt'] or interval[0] > run['end_pt']:
            raise ValueError('Reservation does not intersect its run; review geometry')
        reserved[zone['run']].append(zone)
    field, excluded, summaries = [], [], []
    inch = points_per_foot / 12
    for identity, run in by_run.items():
        run_zones = reserved[identity]
        for end in (run['start_pt'], run['end_pt']):
            if not any(z['interval'][0] <= end <= z['interval'][1] for z in run_zones):
                raise ValueError('Both run ends need reviewed assembly reservations: ' + identity)
        count = max(0, math.floor(((run['end_pt']-run['start_pt'])/inch-first_center_inches)
                                  / spacing_inches + 1e-10) + 1)
        field_count = 0
        for index in range(count):
            position = run['start_pt'] + (first_center_inches + index*spacing_inches)*inch
            owners = sorted({z['assembly'] for z in run_zones
                             if z['interval'][0] <= position <= z['interval'][1]})
            point = ([position, run['coordinate_pt']] if run['orientation'] == 'horizontal'
                     else [run['coordinate_pt'], position])
            station = {'id': f'{identity}-S{index+1:03}', 'run': identity,
                       'along_pt': position, 'point_pt': point, 'source': run['source'],
                       'assembly_owners': owners}
            (excluded if owners else field).append(station)
            field_count += not owners
        summaries.append({'run': identity, 'stations': count, 'field_candidates': field_count,
                          'reserved_stations': count-field_count})
    return {'runs': summaries, 'field_studs': field, 'reserved_stations': excluded,
            'field_count': len(field), 'reserved_count': len(excluded),
            'spacing_inches': spacing_inches, 'first_center_inches': first_center_inches,
            'points_per_foot': points_per_foot, 'purchase_quantity': None,
            'basis': 'Source-reviewed assembly exclusions with an explicit estimating layout datum',
            'remaining': ['Assign member heights and stock cuts.',
                          'Complete reserved assemblies, opening cripples and special-height framing.',
                          'Reconcile actual assembly footprints and end-to-field spacing before ordering.']}


def main(argv=None):
    import argparse
    import hashlib
    import json
    from pathlib import Path
    if __package__:
        from .company_profile import DEFAULT_PROFILE, resolve
    else:
        from company_profile import DEFAULT_PROFILE, resolve
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--profile', default=str(DEFAULT_PROFILE))
    args = parser.parse_args(argv)
    raw = Path(args.input).read_bytes(); inputs = json.loads(raw)
    profile_raw = Path(args.profile).read_bytes()
    resolved = resolve(json.loads(profile_raw), project_overrides=inputs.get('project_overrides'))
    key = 'framing.stud_spacing_inches'
    result = layout(inputs['runs'], inputs['zones'], points_per_foot=inputs['points_per_foot'],
                    spacing_inches=resolved['settings'][key],
                    first_center_inches=inputs['first_center_inches'])
    result.update(input_sha256=hashlib.sha256(raw).hexdigest(),
                  company_profile_sha256=hashlib.sha256(profile_raw).hexdigest(),
                  spacing_provenance=resolved['provenance'][key],
                  profile_conflicts=resolved['resolved_conflicts'])
    with Path(args.output).open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'field_candidates':result['field_count'],
                      'reserved_stations':result['reserved_count'], 'purchase_quantity':None}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
