"""Bind draft wall-face interpretations to current source geometry and evidence."""
import hashlib
import json
from pathlib import Path

STROKE_METHODS=('native_parallel_wall_strokes_v1','native_parallel_wall_strokes_v2','native_parallel_wall_strokes_v3',
                'native_parallel_diagonal_wall_strokes_v1')


def source_digest(measurement):
    fields=('id','page','kind','points','points_per_foot','width_pt','height_pt',
        'source_method','source_cad_paths','source_edges','source_bounds_pt',
        'drawn_thickness_inches','view_bounds_pt','wall_depth_basis','source_outline_pt','source_direction')
    return hashlib.sha256(json.dumps({k:measurement[k] for k in fields if k in measurement},
        sort_keys=True,allow_nan=False).encode()).hexdigest()


def read_review(folder):
    path=Path(folder)/'wall_classification_review.json'
    return json.loads(path.read_bytes()) if path.exists() else None


def resolve(state,review):
    if review is None:return {},None
    if review.get('plan_sha256')!=state['plan_sha256']:
        raise ValueError('Wall classifications belong to another drawing')
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():
        raise ValueError('Wall classification reviewer required')
    if not isinstance(review.get('decisions'),list):
        raise ValueError('Wall classification decisions required')
    decisions={}
    for record in review['decisions']:
        identity=record.get('measurement_id');m=state['measurements'].get(identity)
        if identity in decisions or m is None or m.get('source_method') not in (*STROKE_METHODS,'native_filled_wall_rectangles_v1'):
            raise ValueError('Wall classification needs a unique current wall candidate')
        if record.get('decision') not in ('wall_faces','not_wall_faces','uncertain'):
            raise ValueError('Unknown wall classification decision')
        if not isinstance(record.get('basis'),str) or not record['basis'].strip():
            raise ValueError('Wall classification needs source interpretation')
        if 'axis' in record and (record['axis'] not in ('horizontal','vertical') or record['decision']!='wall_faces'):
            raise ValueError('Reviewed short-piece axis requires a wall-face decision')
        decisions[identity]={**record,'current':record.get('source_sha256')==source_digest(m)}
    return decisions,hashlib.sha256(json.dumps(review,sort_keys=True,allow_nan=False).encode()).hexdigest()
