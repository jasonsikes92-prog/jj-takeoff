"""Measured trim-route scenarios from explicitly reviewed elevation boundaries."""
import math


def calculate(measurements, mapping):
    segments=[];exclusions={};used=set()
    def source(entry):
        identity=entry['measurement_id'];m=measurements[identity];used.add(identity)
        if len(m['points'])!=entry['point_count'] or m['kind']!=entry['kind']:
            raise ValueError('Trim source topology changed: '+identity)
        if (type(m['points_per_foot']) not in (int,float) or not math.isfinite(m['points_per_foot'])
                or m['points_per_foot']<=0 or m.get('surface_factor',1)!=1 or 'plane_gradients' in m):
            raise ValueError('Trim uses scaled elevation lengths without another roof-slope factor')
        if any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in m['points']):
            raise ValueError('Finite trim points required')
        return m
    def add(identity,group,m,a,b):
        if math.dist(a,b)<=1e-8:raise ValueError('Zero-length trim route')
        segments.append({'id':identity,'group':group,'page':m['page'],'points':[list(a),list(b)],
            'length_lf':math.dist(a,b)/m['points_per_foot'],'source_measurement_id':m['id']})
    horizontal={}
    for entry in mapping['horizontal']:
        m=source(entry);a,b=[m['points'][i] for i in entry['vertices']]
        if len(entry['vertices'])!=2 or abs(a[1]-b[1])>1e-6 or b[0]<=a[0]:
            raise ValueError('Reviewed horizontal trim must stay horizontal and ordered')
        if m['id'] in horizontal:raise ValueError('Duplicate horizontal route')
        horizontal[m['id']]=(m,a,b);exclusions[m['id']]=[]
    for entry in mapping['gables']:
        if type(entry.get('same_wall_plane')) is not bool:
            raise ValueError('Gable projection needs an explicit physical wall-plane relationship')
        m=source(entry);parent,a,b=horizontal[entry['parent_horizontal']]
        if m['page']!=parent['page'] or m['points_per_foot']!=parent['points_per_foot']:
            raise ValueError('Gable and horizontal route need the same elevation and scale')
        for n,(start,end) in enumerate(entry['edges'],1):
            p,q=m['points'][start],m['points'][end]
            if abs(p[0]-q[0])<1e-6 or abs(p[1]-q[1])<1e-6:
                raise ValueError('Reviewed gable edge must remain sloped')
            add(m['id']+f'-rake-{n}','sloped_gable',m,p,q)
        left=min(p[0] for p in m['points']);right=max(p[0] for p in m['points'])
        if left<a[0]-1e-6 or right>b[0]+1e-6:raise ValueError('Gable projects beyond its parent wall')
        if entry['same_wall_plane']:exclusions[parent['id']].append((left,right))
    for identity,(m,a,b) in horizontal.items():
        merged=[]
        for start,end in sorted(exclusions[identity]):
            if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
            else:merged.append([start,end])
        cursor=a[0]
        for n,(start,end) in enumerate(merged,1):
            if start>cursor:add(identity+f'-horizontal-{n}','horizontal_wall_top',m,[cursor,a[1]],[start,a[1]])
            add(identity+f'-base-{n}','gable_base_scope_pending',m,[start,a[1]],[end,a[1]])
            cursor=end
        if cursor<b[0]:add(identity+'-horizontal-end','horizontal_wall_top',m,[cursor,a[1]],b)
    for entry in mapping['returns']:
        m=source(entry)
        if m['kind']!='length' or len(m['points'])!=2:raise ValueError('Return needs one measured span')
        add(m['id']+'-top','recessed_porch_return',m,*m['points'])
    if used!=set(measurements):raise ValueError('Every declared trim source must be used')
    if len({s['id'] for s in segments})!=len(segments):raise ValueError('Duplicate trim segment')
    groups={g:math.fsum(s['length_lf'] for s in segments if s['group']==g) for g in
        ['horizontal_wall_top','sloped_gable','recessed_porch_return','gable_base_scope_pending']}
    route=sum(v for k,v in groups.items() if k!='gable_base_scope_pending')
    return {'segments':segments,'group_lf':groups,'roof_following_route_scenario_lf':route,
        'scenario_including_gable_base_bands_lf':route+groups['gable_base_scope_pending'],
        'final_installed_quantity':None,'purchase_quantity':None,'price_applied':False,
        'separate_plane_gables':[g['measurement_id'] for g in mapping['gables'] if not g['same_wall_plane']],
        'basis':'Only coplanar gable projections replace horizontal spans. A forward porch gable does not remove trim on the wall behind it. Overlapping coplanar projections are merged. Gable-base bands remain a separate scope alternative. Return lengths use their plan-measured spans.',
        'remaining':['Confirm horizontal gable-base band ownership and any porch beam/soffit interfaces.',
            'Resolve overlapping front gable/entry returns and any concealed frieze termination.',
            'References follow cladding faces, not final board centerlines, miters or stock cuts.',
            'Keep fascia, window trim, corner boards, chimney cap trim and flashing separate.']}
