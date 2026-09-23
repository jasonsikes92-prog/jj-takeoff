"""Count source-classified wall connections once with documented allowances."""
import math


def reconcile(corners,connections,corner_connections,runs,settings,points_per_foot,source,*,wall_depth_inches):
    if settings.get('framing.tight_door_corner_quantity_basis')!='documented_estimating_allowances':
        raise ValueError('Documented estimating allowance practice required')
    if not source or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in (points_per_foot,wall_depth_inches)):
        raise ValueError('Source, positive scale and wall depth required')
    detail=settings['framing.solid_backing_assembly_allowance']
    corner_by_id={c['id']:c for c in corners}
    ids=[c['id'] for c in corners+connections+corner_connections]
    if len(ids)!=len(set(ids)):raise ValueError('Source assembly IDs must be unique')
    assigned={key:[] for key in corner_by_id};standalone=[];unresolved=[]
    for connection in corner_connections:
        matches=[c for c in corners if set(c['wall_runs'])==set(connection['exterior_walls'])]
        if len(matches)!=1:raise ValueError('Corner wall-pair assignment must be unique')
        assigned[matches[0]['id']].append({'alias':connection['id'],'interior_run':connection['run']})
    for connection in connections:
        if connection['interior_run'] not in runs:raise ValueError('Connection references an unknown interior run')
        if connection['kind']=='T_connection':
            standalone.append({'id':connection['id'],'aliases':[connection['id']],
                'classification':'T_intersection','interior_runs':[connection['interior_run']],
                'source_point_pt':connection['point_pt'],'whole_assembly_studs':detail['T_intersection']['whole_assembly_studs'],
                'basis':'Three-stud host backing plus branch end; complete assembly allowance, not extra backing on a counted host stud.'})
        elif connection['kind']=='corner_connection':
            # The source classified a corner connection. Locate its named wall's
            # corner within two supplied wall depths, allowing face/center offsets.
            matches=[c for c in corners if connection['exterior_wall'] in c['wall_runs'] and
                math.dist(c['point_pt'],connection['point_pt'])/points_per_foot*12<=2*wall_depth_inches]
            if len(matches)==1:assigned[matches[0]['id']].append({'alias':connection['id'],'interior_run':connection['interior_run']})
            else:unresolved.append({'id':connection['id'],'reason':'Source corner connection has no unique nearby corner on its named wall'})
        else:unresolved.append({'id':connection['id'],'reason':'Connection type needs classification'})
    assemblies=[]
    for identity,corner in corner_by_id.items():
        branches=assigned[identity];branch_runs=sorted({b['interior_run'] for b in branches})
        aliases=sorted({identity,*[b['alias'] for b in branches]})
        if corner['type'] not in ('outside_convex','reentrant'):
            unresolved.append({'id':identity,'aliases':aliases,'reason':'Corner type needs classification'})
            continue
        if any(run not in runs for run in branch_runs):raise ValueError('Corner branch references an unknown interior run')
        if len(branch_runs)>2:
            unresolved.append({'id':identity,'aliases':aliases,'reason':'More than two added branches need a specific assembly allowance'})
            continue
        kind=('L_corner','T_intersection','cross_intersection')[len(branch_runs)]
        count=(settings['framing.outside_corner_studs'] if not branch_runs and corner['type']=='outside_convex'
            else detail[kind]['whole_assembly_studs'])
        assemblies.append({'id':identity,'aliases':aliases,'classification':kind,'corner_type':corner['type'],
            'wall_runs':corner['wall_runs'],'interior_runs':branch_runs,'source_point_pt':corner['point_pt'],
            'whole_assembly_studs':count,
            'basis':'One whole solid-backing corner/branch assembly. Exterior and interior aliases do not add a second corner count.'})
    assemblies+=standalone
    for item in assemblies:item['source']=source
    return {'assemblies':assemblies,'unresolved':unresolved,
        'known_junction_stud_allowance':sum(a['whole_assembly_studs'] for a in assemblies),
        'quantity_basis':'Documented estimating allowance; source-classified topology, not an engineered member layout',
        'scope':'Exterior corners and interior-to-exterior connections only; exclude these assemblies from field/end counts',
        'purchase_order_released':False}
