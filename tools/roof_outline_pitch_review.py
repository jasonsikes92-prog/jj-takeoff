"""Resolve native roof outlines using explicitly reviewed source labels."""
import hashlib
import json
import math
import re
from pathlib import Path
import fitz
from shapely.geometry import Polygon
from measurement_store import calculate


def candidate_sha256(measurement):
    source={k:measurement.get(k) for k in ('id','page','points','points_per_foot','surface_factor',
        'source_cad_paths','pitch_candidate','pitch_candidates')}
    return hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()


def read_review(job, plan_sha256):
    path = Path(job)/'roof_outline_pitch_review.json'
    if not path.exists():
        return None
    raw = path.read_bytes()
    review = json.loads(raw)
    if review.get('plan_sha256') != plan_sha256:
        raise ValueError('Roof outline pitch review belongs to another drawing')
    if any(not isinstance(review.get(k), str) or not review[k].strip() for k in ('reviewer', 'basis')):
        raise ValueError('Roof outline pitch review needs reviewer and interpretation basis')
    if not isinstance(review.get('outlines'), list) or not review['outlines']:
        raise ValueError('Roof outline pitch review needs source outlines')
    return {**review, 'review_sha256':hashlib.sha256(raw).hexdigest(), 'reviewer_identity_authenticated':False}


def reviewed_candidates(plan, raw, review, frame):
    if frame is None or not frame.get('points_per_foot'):
        raise ValueError('Roof outline pitch review requires a calibrated roof view')
    if hashlib.sha256(Path(plan).read_bytes()).hexdigest() != review['plan_sha256']:
        raise ValueError('Roof outline pitch review drawing changed')
    available = {o['source_sha256']:o for o in raw.get('unresolved_source_outlines', [])}
    measurements = []
    seen = set()
    replaced = set()
    candidates = {m['id']:m for m in raw.get('measurements', [])}
    with fitz.open(plan) as doc:
        for item in review['outlines']:
            digest = item.get('source_outline_sha256')
            if digest not in available or digest in seen:
                raise ValueError('Reviewed roof outline changed, missing or repeated')
            seen.add(digest)
            source = available[digest]
            if not source['source_style_reviewed'] or source['page'] != frame['page']:
                raise ValueError('Roof outline requires the selected reviewed roof style and page')
            replacements = item.get('superseded_measurements', [])
            conflict_basis = item.get('conflicting_label_basis')
            if source['pitch_labels'] and (not isinstance(conflict_basis, str) or not conflict_basis.strip() or not replacements):
                raise ValueError('Conflicting roof labels require surface partition review')
            if not isinstance(item.get('basis'), str) or not item['basis'].strip():
                raise ValueError('Roof outline requires a source association explanation')
            anchor = item.get('pitch_label', {})
            page = anchor.get('page')
            box = anchor.get('bbox_pt')
            if (type(page) is not int or not 1 <= page <= len(doc) or not isinstance(box, list)
                    or len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)):
                raise ValueError('Roof pitch source requires a page and finite text bounds')
            matches = set()
            for block in doc[page-1].get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    text = ''.join(s['text'] for s in line['spans']).strip()
                    if text == anchor.get('text') and all(abs(a-b) <= .001 for a,b in zip(box, line['bbox'])):
                        matches.add(text)
            if len(matches) != 1:
                raise ValueError('Roof pitch source label changed, missing or ambiguous')
            match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*:\s*12', next(iter(matches)))
            if not match or not 0 < float(match.group(1)) <= 24:
                raise ValueError('Roof pitch source must contain a supported positive pitch')
            rise = float(match.group(1))
            if not isinstance(replacements, list):
                raise ValueError('Roof replacements must identify source candidates')
            for replacement in replacements:
                identity = replacement.get('measurement_id')
                existing = candidates.get(identity)
                if (existing is None or identity in replaced or
                        candidate_sha256(existing) != replacement.get('source_candidate_sha256')):
                    raise ValueError('Superseded roof candidate changed, missing or repeated')
                if (existing['page'] != source['page'] or existing.get('pitch_candidate', {}).get('rise') != rise
                        or not Polygon(source['points']).buffer(.001).covers(Polygon(existing['points']))):
                    raise ValueError('Superseded roof candidate must be a same-pitch subdivision of this outline')
                replaced.add(identity)
            mid = 'roof-reviewed-outline-'+digest[:16]
            measurement = {k:frame[k] for k in ('page', 'points_per_foot', 'width_pt', 'height_pt')}
            measurement.update(id=mid, label=f'Reviewed roof outline {rise:g}:12', kind='area',
                points=source['points'], surface_factor=math.hypot(12, rise)/12, color='#a16207',
                dependent_rows=[], engine_line_ids=[mid], source_cad_paths=source['source_cad_paths'],
                source_method='Native closed roof outline with reviewed source-sheet pitch label',
                source_pitch_evidence={'pitch_is_inferred':True, 'pitch_certified':False,
                    'association_method':'Reviewed correspondence to a source-sheet pitch label',
                    'rise_per_12':rise, 'label':anchor, 'basis':item['basis'],
                    'source_outline_sha256':digest, 'plan_sha256':review['plan_sha256'],
                    **({'superseded_measurements':replacements,'conflicting_label_basis':conflict_basis}
                        if replacements else {})},
                source_pitch_review={k:review[k] for k in
                    ('review_sha256', 'reviewer', 'basis', 'reviewer_identity_authenticated')},
                scope_status='Source label association reviewed; verify exposed boundaries and overlapping roof levels before pricing')
            calculate(measurement)
            measurements.append(measurement)
    return measurements
