"""Derive plan-perimeter runs from the current outline and located opening gaps."""
import math
from measurement_store import calculate as measurement_value
from trim_lengths import net_run


def calculate(measurements, outline_id, deduction_ids):
    ids=[outline_id,*deduction_ids]
    if not ids or any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Boundary route needs distinct outline and deduction identities')
    if set(ids)!=set(measurements):raise ValueError('Boundary route must use exactly its declared measurements')
    outline=measurements[outline_id]
    if outline['kind']!='area':raise ValueError('Boundary route needs a closed plan outline')
    for identity in ids:
        m=measurements[identity];measurement_value(m)
        if any(m.get(k)!=outline.get(k) for k in ('page','width_pt','height_pt','points_per_foot')):
            raise ValueError('Boundary and gaps must share one sheet, scale and coordinate system')
        if m.get('surface_factor',1)!=1 or 'plane_gradients' in m:
            raise ValueError('Boundary route uses flat plan geometry only')
        if identity!=outline_id and (m['kind']!='length' or len(m['points'])!=2):
            raise ValueError('Each boundary gap must be one straight opening span')
    points=outline['points'];scale=outline['points_per_foot']
    # Only floating-point noise is tolerated. No drafting-distance snapping.
    epsilon=1e-7
    walls=[]
    for index,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
        length=math.dist(a,b)
        if length<=epsilon:raise ValueError('Boundary contains a zero-length edge')
        walls.append({'edge_index':index,'a':a,'b':b,'length_pt':length,'deductions':[]})
    gaps=[]
    for identity in deduction_ids:
        gap=measurements[identity];p,q=gap['points'];length=math.dist(p,q)
        if length<=epsilon:raise ValueError('Boundary gap must have positive length')
        pieces=[]
        for wall in walls:
            a,b=wall['a'],wall['b'];size=wall['length_pt'];dx=b[0]-a[0];dy=b[1]-a[1]
            distances=[abs(dx*(v[1]-a[1])-dy*(v[0]-a[0]))/size for v in (p,q)]
            if max(distances)>epsilon:continue
            positions=sorted(((v[0]-a[0])*dx+(v[1]-a[1])*dy)/size for v in (p,q))
            start=max(0,positions[0]);end=min(size,positions[1])
            if end-start<=epsilon:continue
            piece={'id':identity,'start_ft':start/scale,'end_ft':end/scale}
            wall['deductions'].append(piece)
            pieces.append({'edge_index':wall['edge_index'],**piece})
        covered=math.fsum((p['end_ft']-p['start_ft'])*scale for p in pieces)
        if not math.isclose(covered,length,rel_tol=0,abs_tol=epsilon*max(1,len(pieces))):
            raise ValueError('Opening gap is not wholly on the current outline: '+identity)
        gaps.append({'measurement_id':identity,'points':gap['points'],'length_lf':length/scale,'edge_spans':pieces})
    segments=[];gross=0;deducted=0
    for wall in walls:
        ordered=sorted(wall['deductions'],key=lambda p:p['start_ft'])
        for previous,current in zip(ordered,ordered[1:]):
            if previous['end_ft']-current['start_ft']>epsilon/scale:
                raise ValueError('Opening gaps overlap on the outline: '+previous['id']+' and '+current['id'])
        result=net_run(wall['length_pt']/scale,wall['deductions'])
        gross+=result['gross_lf'];deducted+=result['deducted_lf']
        for index,span in enumerate(result['retained']):
            def point(distance):
                t=distance*scale/wall['length_pt']
                return [wall['a'][axis]+t*(wall['b'][axis]-wall['a'][axis]) for axis in (0,1)]
            segments.append({'edge_index':wall['edge_index'],'segment_index':index,
                'points':[point(span['start_ft']),point(span['end_ft'])],
                'length_lf':span['end_ft']-span['start_ft']})
    return {'outline_measurement_id':outline_id,'deduction_measurement_ids':list(deduction_ids),
        'page':outline['page'],'points_per_foot':scale,'gross_lf':gross,'deductions_lf':deducted,
        'net_lf':math.fsum(s['length_lf'] for s in segments),'segments':segments,'gaps':gaps,
        'quantity_basis':'Plan-projected outline less located opening gaps, removed once',
        'coordinate_tolerance_pt':epsilon,'purchase_quantity':None}
