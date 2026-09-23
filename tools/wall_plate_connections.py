"""Partial net plate allowances where current wall geometry establishes a connection."""
import math
from wall_gap_obstructions import footprint


def overlaps(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6


def gap_rectangle(run,gap,pieces):
    axis=0 if run['axis']=='horizontal' else 1
    bounds=[pieces[i]['bounds'] for i in run['source_measurement_ids'] if i in pieces]
    left=[b for b in bounds if abs(b[axis+2]-gap['from_pt'])<1e-6]
    right=[b for b in bounds if abs(b[axis]-gap['to_pt'])<1e-6]
    neighbors=left+right
    if not left or not right or any(max(b[k] for b in neighbors)-min(b[k] for b in neighbors)>1e-6 for k in (1-axis,3-axis)):
        return None
    low,high=neighbors[0][1-axis],neighbors[0][3-axis]
    return [gap['from_pt'],low,gap['to_pt'],high] if axis==0 else [low,gap['from_pt'],high,gap['to_pt']]


def calculate(state,runs,gaps,opening_reference,counts):
    for source in (runs,gaps):
        if (source['plan_sha256'],source['measurement_version'])!=(state['plan_sha256'],state['version']):
            raise ValueError('Plate connections require one drawing and measurement revision')
    by_run={r['id']:r for r in runs['run_candidates']};pieces={};candidates=[];pending=[];separate=[];seen=set()
    for run in by_run.values():
        for identity in run['source_measurement_ids']:
            m=state['measurements'][identity]
            if (m['page'],m['points_per_foot'])!=(run['page'],run['points_per_foot']):
                raise ValueError('Connection wall page or scale differs from its run')
            bounds=footprint(m)
            if bounds:pieces[identity]={'bounds':bounds,'page':m['page'],'points_per_foot':m['points_per_foot']}
    opening_ids={o['gap_id'] for o in opening_reference['openings']};opening_bounds=[]
    for gap in gaps['gaps']:
        if gap['id'] in seen:raise ValueError('Duplicate plate connection gap')
        seen.add(gap['id']);run=by_run[gap['run_id']]
        bounds=gap_rectangle(run,gap,pieces)
        if gap['id'] in opening_ids:
            if bounds:opening_bounds.append({'bounds':bounds,'page':run['page'],'points_per_foot':run['points_per_foot']})
            continue
        if gap['status']=='separate_wall_runs':
            separate.append(gap['id']);continue
        if gap['status'] not in ('wall_junction_candidate','continuous_wall_body_candidate'):
            pending.append({'gap_id':gap['id'],'reason':'Opening, passage or wall continuity remains unresolved'});continue
        evidence=gap.get('continuity_source') if gap['status']=='continuous_wall_body_candidate' else gap.get('junction_contacts')
        if bounds is None or not evidence:
            pending.append({'gap_id':gap['id'],'reason':'Matching host wall faces and current connection evidence required'});continue
        length=(gap['to_pt']-gap['from_pt'])/run['points_per_foot']
        candidates.append({'gap_id':gap['id'],'run_id':run['id'],'page':run['page'],
            'points_per_foot':run['points_per_foot'],'bounds_pt':bounds,'axis':run['axis'],
            'connection_type':gap['status'],'source_evidence':evidence,'connection_lf':length,
            'top_plate_reference_lf':None if counts['top'] is None else length*counts['top'],
            'bottom_plate_reference_lf':None if counts['bottom'] is None else length*counts['bottom']})
    # Never allocate the same physical junction to two crossing hosts or add
    # material where an accepted wall/opening already owns the footprint.
    accepted=[]
    for candidate in candidates:
        key=(candidate['page'],candidate['points_per_foot']);bounds=candidate['bounds_pt']
        existing=[p['bounds'] for p in [*pieces.values(),*opening_bounds] if (p['page'],p['points_per_foot'])==key]
        others=[p['bounds_pt'] for p in candidates if p['gap_id']!=candidate['gap_id'] and (p['page'],p['points_per_foot'])==key]
        if any(overlaps(bounds,b) for b in existing+others):
            pending.append({'gap_id':candidate['gap_id'],'reason':'Overlapping wall/opening/connection footprint needs a single plate owner'})
        else:accepted.append(candidate)
    length=math.fsum(c['connection_lf'] for c in accepted) if accepted else None
    return {'connections':accepted,'separate_wall_gap_ids':separate,'pending_gaps':pending,
        'connection_lf':length,
        'top_plate_reference_lf':None if length is None or counts['top'] is None else length*counts['top'],
        'bottom_plate_reference_lf':None if length is None or counts['bottom'] is None else length*counts['bottom'],
        'basis':'Partial net installed allowance across matching host faces at current wall-end contacts or a continuous native wall body. Each gap belongs to its host once; separate walls and overlapping ownership are excluded. End corners, framing applicability, course laps and purchasing cuts remain unresolved.',
        'purchase_quantity':None,'certified':False}
