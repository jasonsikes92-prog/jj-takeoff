"""Reuse reviewed wall runs only in rooms assigned floating flooring."""
import copy
import math


def floating_floor_wall_runs(draft):
    floor=draft['floor_finish_review'];base=draft['baseboard_review']
    ids=floor['remaining_measurement_ids']
    if (not ids or len(ids)!=len(set(ids)) or set(ids)&set(floor['measurement_ids'])
            or floor['plan_sha256']!=draft['plan_sha256']
            or floor['measurement_version']!=draft['measurement_version']
            or base['room_measurement_version']!=draft['measurement_version']):
        raise ValueError('Trim reference needs current, disjoint floor-finish rooms')
    by_id={r['room_id']:r for r in base['rooms']}
    if len(by_id)!=len(base['rooms']) or not set(ids).issubset(by_id):
        raise ValueError('Trim reference needs every selected room exactly once')
    rooms=[copy.deepcopy(by_id[i]) for i in ids]
    for room in rooms:
        values=[room[k] for k in ('finish_perimeter_lf','door_gap_lf','fixed_footprint_lf','remaining_wall_run_lf')]
        lengths=[s['length_lf'] for s in room['segments']]
        if (any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values+lengths)
                or not math.isclose(values[0]-values[1]-values[2],values[3],abs_tol=1e-7)
                or not math.isclose(math.fsum(lengths),values[3],abs_tol=1e-7)):
            raise ValueError('Trim reference wall segments and deductions must reconcile')
    quantity=math.fsum(r['remaining_wall_run_lf'] for r in rooms)
    return {'id':'floating-floor-wall-runs','label':'Quarter-round wall-run reference; incomplete scope',
            'quantity':quantity,'measured_quantity':quantity,'unit':'LF','use':'assembly_input',
            'measurement_ids':list(ids),'rooms':rooms,
            'basis':'Finished wall-face runs in the selected floating-floor rooms, less mapped door gaps and fixed footprints. '
                    'Carpet, primary-bath tile, garage and enclosed fireplace cavity are excluded. '
                    'Room cost divisions do not create trim. This is a partial reference, not installed or purchased trim.',
            'source':{'file':base['source_file'],'sha256':base['source_sha256']},
            'source_dependencies':copy.deepcopy(base['dependencies']),
            'room_measurement_version':base['room_measurement_version'],
            'obstruction_measurement_version':copy.deepcopy(base['obstruction_measurement_version']),
            'remaining':['Confirm actual quarter-round coverage at each finish transition',
                         'Casing widths, terminal returns and exposed cabinet/island fronts',
                         'Unmapped pantry cabinetry and fireplace finish transitions',
                         'Stock lengths, cut layout, joints, waste and whole-stick purchases'],
            'final_installed_quantity':None,'purchase_quantity':None,'certified':False,'order_released':False}
