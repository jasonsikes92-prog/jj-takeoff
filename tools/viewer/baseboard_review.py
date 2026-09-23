"""Refine a partial baseboard reference from live room and fixed-footprint sources."""
import copy
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from floor_finish_faces import reviewed_finish_faces
from baseboard_geometry import baseboard_runs


def apply_baseboard(draft, state, config, folder):
    root = Path(folder).resolve()
    source = (root/config['source_file']).resolve()
    if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest() != config['source_sha256']:
        raise ValueError('Baseboard scope evidence changed')
    proof = json.loads(source.read_bytes())
    if proof['plan_sha256'] != state['plan_sha256'] or draft['measurement_version'] != state['version']:
        raise ValueError('Baseboard needs the current source drawing and measurement revision')
    faces = proof['finish_faces']
    reviewed_finish_faces(state, faces, root)
    combined = {'plan_sha256': state['plan_sha256'], 'version': {}, 'measurements': {}}
    dependencies = []
    for item in proof['footprint_sources']:
        job = (root/item['job']).resolve()
        if not (job/'measurement_edits.sqlite3').is_file():
            raise ValueError('Baseboard footprints need saved measurement history')
        store = MeasurementStore(job)
        if store.config_hash != item['config_sha256']:
            raise ValueError('Baseboard footprint mapping changed')
        current = store.read()
        if current['plan_sha256'] != state['plan_sha256']:
            raise ValueError('Baseboard footprints belong to another drawing')
        ids = item['measurement_ids']
        if not ids or len(set(ids)) != len(ids) or set(ids) & set(combined['measurements']):
            raise ValueError('Baseboard footprints need unique identities')
        combined['measurements'].update({key: current['measurements'][key] for key in ids})
        combined['version'][item['job']] = current['version']
        dependencies.append({**item, 'measurement_version': current['version']})
    result = baseboard_runs(state, faces['room_ids'], faces['passages'], faces['wall_finish_thickness_inches'],
                           combined, list(combined['measurements']))
    result.update(source_file=str(source), source_sha256=config['source_sha256'],
                  basis=proof['basis'], dependencies=dependencies)
    owners = [row for row in draft['rows'] if any(q['id'] == proof['assembly_id'] for q in row.get('assembly_inputs', []))]
    if {r['row_id'] for r in owners} != set(proof['cost_owner_ids']) or not owners:
        raise ValueError('Baseboard reference cost owners changed')
    expected = set(faces['room_ids']) | {p['measurement_id'] for p in faces['passages']}
    for row in owners:
        parts = [p for p in row['assembly_inputs'] if p['id'] == proof['assembly_id']]
        if len(parts) != 1 or set(parts[0]['measurement_ids']) != expected or parts[0]['use'] != 'assembly_input':
            raise ValueError('Baseboard reference no longer matches its reviewed scope')
    for row in owners:
        part = next(p for p in row['assembly_inputs'] if p['id'] == proof['assembly_id'])
        part.update(quantity=result['remaining_wall_run_lf'], measured_quantity=result['remaining_wall_run_lf'],
                    gross_quantity=sum(r['finish_perimeter_lf'] for r in result['rooms']),
                    label='House baseboard after mapped finish exclusions; partial reference',
                    basis=proof['basis'], remaining=copy.deepcopy(result['remaining']),
                    baseboard_review=copy.deepcopy(result), certified=False, order_released=False)
    draft['baseboard_review'] = result
