"""Source-reviewed breaks keep collinear but separate walls in distinct sections."""
import hashlib
import json
from pathlib import Path
from wall_classification_review import source_digest


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def source_binding(state,run,gap):
    return digest({'plan_sha256':state['plan_sha256'],'alignment':run,'gap':gap,
        'measurements':{i:source_digest(state['measurements'][i]) for i in run['source_measurement_ids']}})


def read_review(folder):
    path=Path(folder)/'wall_alignment_breaks.json'
    return json.loads(path.read_bytes()) if path.exists() else None


def apply_review(state,runs,gaps,review):
    by_run={r['id']:r for r in runs['run_candidates']};by_gap={g['id']:g for g in gaps['gaps']}
    decisions=[];accepted=set()
    if review is not None:
        if review.get('plan_sha256')!=state['plan_sha256']:raise ValueError('Alignment breaks belong to another drawing')
        if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():raise ValueError('Alignment break reviewer required')
        if not isinstance(review.get('breaks'),list):raise ValueError('Alignment break records required')
        seen=set()
        for record in review['breaks']:
            identity=record.get('gap_id')
            if not isinstance(identity,str) or identity in seen:raise ValueError('Unique alignment gap IDs required')
            seen.add(identity)
            if not isinstance(record.get('basis'),str) or not record['basis'].strip():raise ValueError('Alignment break needs source interpretation')
            gap=by_gap.get(identity)
            current=bool(gap and gap['status']=='no_aligned_tag' and
                record.get('source_sha256')==source_binding(state,by_run[gap['run_id']],gap))
            decisions.append({**record,'current':current})
            if current:accepted.add(identity)
    sections=[]
    for run in runs['run_candidates']:
        local=[g for g in gaps['gaps'] if g['run_id']==run['id']]
        breaks=sorted((g for g in local if g['id'] in accepted),key=lambda g:g['from_pt'])
        start=run['visible_intervals_pt'][0][0];axis=0 if run['axis']=='horizontal' else 1
        ranges=[]
        for gap in breaks:
            ranges.append((start,gap['from_pt']));start=gap['to_pt']
        ranges.append((start,run['visible_intervals_pt'][-1][1]))
        for low,high in ranges:
            ids=[i for i in run['source_measurement_ids'] if
                min(p[axis] for p in state['measurements'][i]['points'])<high and
                max(p[axis] for p in state['measurements'][i]['points'])>low]
            intervals=[[a,b] for a,b in run['visible_intervals_pt'] if a>=low and b<=high]
            sections.append({'id':'wall-section-'+digest([run['id'],low,high])[:16],
                'alignment_id':run['id'],'page':run['page'],'axis':run['axis'],
                'points_per_foot':run['points_per_foot'],'interval_pt':[low,high],
                'source_measurement_ids':ids,'visible_intervals_pt':intervals,
                'visible_union_lf':sum(b-a for a,b in intervals)/run['points_per_foot'],
                'unresolved_gap_ids':[g['id'] for g in local if g['status']=='no_aligned_tag'
                    and g['id'] not in accepted and low<=g['from_pt'] and g['to_pt']<=high],
                'scope_status':'Layout candidate; openings, junction assemblies and material ownership still require review'})
    for identity in accepted:by_gap[identity]['status']='separate_wall_runs'
    return {'review_sha256':digest(review) if review is not None else None,
        'reviewer':review['reviewer'] if review is not None else None,'reviewer_identity_authenticated':False,
        'decisions':decisions,'candidate_sections':sections,'purchase_quantity':None,'certified':False,
        'limitations':['A reviewed break separates alignments; it does not authorize framing material or wall height.',
            'Unreviewed and stale breaks remain gaps, not hidden additions to wall footage.']}
