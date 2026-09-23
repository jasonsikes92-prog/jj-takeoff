"""Derive enclosed boundary candidates from current wall faces and opening reviews."""
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from wall_gap_obstructions import footprint
from wall_run_candidates import from_state
from wall_classification_review import read_review
from wall_alignment_breaks import read_review as alignment_review
from wall_gap_labels import from_plan_state
from opening_schedule import schedule


def candidates(state,runs,gaps,openings):
    for source in (runs,gaps,openings):
        if (source['plan_sha256'],source['measurement_version'])!=(state['plan_sha256'],state['version']):
            raise ValueError('Wall enclosures require one drawing and measurement revision')
    groups={};pieces={};issues=[];bridges=[];junctions=[]
    for run in runs['run_candidates']:
        key=(run['page'],run['points_per_foot']);groups.setdefault(key,[])
        for identity in run['source_measurement_ids']:
            m=state['measurements'][identity];bounds=footprint(m)
            if (m['page'],m['points_per_foot'])!=key:raise ValueError('Wall enclosure scale or page differs from its run')
            if bounds is None:
                issues.append({'measurement_id':identity,'reason':'Wall footprint is unresolved'});continue
            piece={'id':identity,'axis':run['axis'],'bounds':bounds,'key':key}
            pieces[identity]=piece;groups[key].append(box(*bounds))
    # Only wall bodies that physically touch can complete a perpendicular joint.
    # The missing corner rectangle is bounded by the two pairs of drawn faces.
    horizontal=[p for p in pieces.values() if p['axis']=='horizontal']
    vertical=[p for p in pieces.values() if p['axis']=='vertical']
    for h in horizontal:
        a=h['bounds'];y=(a[1]+a[3])/2
        for v in vertical:
            if h['key']!=v['key']:continue
            b=v['bounds'];x=(b[0]+b[2])/2
            if (max(a[0]-x,0,x-a[2])>(b[2]-b[0])/2+1e-6
                    or max(b[1]-y,0,y-b[3])>(a[3]-a[1])/2+1e-6):continue
            joint=box(b[0],a[1],b[2],a[3])
            if joint.difference(unary_union([box(*a),box(*b)])).area<=1e-8:continue
            groups[h['key']].append(joint)
            junctions.append({'source_measurement_ids':[h['id'],v['id']],
                'page':h['key'][0],'points_per_foot':h['key'][1],'bounds_pt':list(joint.bounds),
                'basis':'Perpendicular touching wall faces bound this junction rectangle'})
    by_run={r['id']:r for r in runs['run_candidates']}
    current={o['gap_id']:o for o in openings['openings'] if o['review_status']=='current_source_review'}
    native_windows={o['gap_id']:o for o in openings['openings'] if o['review_status']=='native_symbol_inference'
        and o['role']=='window' and o.get('native_interpretation',{}).get('kind')=='window'
        and o['native_interpretation'].get('evidence',{}).get('plan_sha256')==state['plan_sha256']
        and o['native_interpretation']['evidence'].get('opening_source_sha256')==o.get('source_sha256')}
    symbols={c['opening_id']:c for c in openings.get('door_symbol_candidates',{}).get('candidates',[])
        if c['status']=='candidate_requires_review' and c.get('configuration_candidate') in ('single_hinged','pocket','double_hinged','sliding_pair')}
    native={o['gap_id']:o for o in openings['openings'] if o['review_status']=='role_unreviewed'
        and o['opening_id'] in symbols and symbols[o['opening_id']]['opening_source_sha256']==o['source_sha256']}
    for gap in gaps['gaps']:
        opening=current.get(gap['id']) or native.get(gap['id']) or native_windows.get(gap['id'])
        if opening is None and gap['status'] not in ('wall_junction_candidate','continuous_wall_body_candidate'):continue
        run=by_run[gap['run_id']];axis=0 if run['axis']=='horizontal' else 1
        bounds=[pieces[i]['bounds'] for i in run['source_measurement_ids'] if i in pieces]
        left=[b for b in bounds if abs(b[axis+2]-gap['from_pt'])<1e-6]
        right=[b for b in bounds if abs(b[axis]-gap['to_pt'])<1e-6]
        neighbors=left+right
        if not left or not right or any(max(b[k] for b in neighbors)-min(b[k] for b in neighbors)>1e-6
                for k in (1-axis,3-axis)):
            issues.append({'gap_id':gap['id'],'reason':'Gap wall faces do not agree; no closure inferred'});continue
        lower,upper=neighbors[0][1-axis],neighbors[0][3-axis]
        bounds=([gap['from_pt'],lower,gap['to_pt'],upper] if axis==0
            else [lower,gap['from_pt'],upper,gap['to_pt']])
        groups[(run['page'],run['points_per_foot'])].append(box(*bounds))
        bridges.append({'gap_id':gap['id'],'page':run['page'],'points_per_foot':run['points_per_foot'],
            'bounds_pt':bounds,'axis':run['axis'],'opening_id':opening['opening_id'] if opening else None,
            'basis':'Native window frame footprint closure; estimating hypothesis' if gap['id'] in native_windows else
                'Native door symbol footprint closure; estimating hypothesis' if gap['id'] in native else
                'Reviewed opening footprint closure' if opening else
                'Continuous native wall face and wall-body closure' if gap['status']=='continuous_wall_body_candidate'
                else 'Perpendicular wall-end contact closure'})
    enclosures=[];unenclosed=[];regions=[]
    for (page,ppf),shapes in sorted(groups.items()):
        if not shapes:continue
        merged=unary_union(shapes)
        components=list(merged.geoms) if merged.geom_type=='MultiPolygon' else [merged]
        for component in components:
            if not component.interiors:
                unenclosed.append({'page':page,'points_per_foot':ppf,'bounds_pt':list(component.bounds),
                    'wall_footprint_sf':component.area/ppf**2});continue
            shell=Polygon(component.exterior);points=[list(p) for p in shell.exterior.coords][:-1]
            identity=hashlib.sha256(json.dumps([page,ppf,points]).encode()).hexdigest()[:16]
            enclosures.append({'id':'wall-enclosure-'+identity,'page':page,'points_per_foot':ppf,'points':points,
                'gross_boundary_sf':shell.area/ppf**2,'enclosed_void_count':len(component.interiors),
                'enclosed_void_sf':sum(Polygon(r).area for r in component.interiors)/ppf**2,
                'wall_and_closure_footprint_sf':component.area/ppf**2,
                'source_measurement_ids':sorted(p['id'] for p in pieces.values() if p['key']==(page,ppf)
                    and component.intersects(box(*p['bounds']))),
                'scope_status':'Candidate only; outside-face basis, floor scope and possible courts/voids need review',
                'floor_area':None,'purchase_quantity':None,'certified':False})
        parents=[e for e in enclosures if (e['page'],e['points_per_foot'])==(page,ppf)]
        if parents:
            # Subtract all wall bodies together, including disconnected columns
            # and nested wall rings; their interior spaces must not count twice.
            spaces=unary_union([Polygon(e['points']) for e in parents]).difference(merged)
            for space in ([spaces] if spaces.geom_type=='Polygon' else spaces.geoms):
                if space.is_empty:continue
                points=[list(p) for p in space.exterior.coords][:-1]
                holes=[[list(p) for p in ring.coords][:-1] for ring in space.interiors]
                parent=min((e for e in parents if Polygon(e['points']).covers(space)),key=lambda e:e['gross_boundary_sf'])
                identity=hashlib.sha256(json.dumps([page,ppf,points,holes]).encode()).hexdigest()[:16]
                regions.append({'id':'interior-region-'+identity,'parent_enclosure_id':parent['id'],
                    'page':page,'points_per_foot':ppf,'points':points,'holes':holes,
                    'boundary_area_sf':space.area/ppf**2,'floor_finish_quantity':None,'certified':False,
                    'scope_status':'Unclassified interior space; virtual opening closures, fixtures and finish limits need review'})
    source={'runs':runs,'gaps':gaps,'openings':openings}
    return {'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
        'method':'reviewed_wall_face_enclosures_v1',
        'source_sha256':hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'candidate_enclosures':sorted(enclosures,key=lambda e:(e['page'],-e['gross_boundary_sf'],e['id'])),
        'interior_region_candidates':sorted(regions,key=lambda e:(e['page'],-e['boundary_area_sf'],e['id'])),
        'junction_rectangles':junctions,'gap_closures':bridges,'unclosed_wall_components':unenclosed,
        'unresolved_wall_measurements':runs['unresolved_measurements'],'unresolved_connections':issues,
        'unresolved_wall_sources':[{**u,'current_bounds_pt':footprint(state['measurements'][u['measurement_id']]),
            'page':state['measurements'][u['measurement_id']]['page'],
            'points_per_foot':state['measurements'][u['measurement_id']]['points_per_foot'],
            'original_bounds_pt':state['measurements'][u['measurement_id']].get('source_bounds_pt')}
            for u in runs['unresolved_measurements']],
        'unresolved_gap_ids':[g['id'] for g in gaps['gaps'] if g['status'] not in
            ('wall_junction_candidate','separate_wall_runs','continuous_wall_body_candidate')
            and g['id'] not in current and g['id'] not in native and g['id'] not in native_windows],
        'unresolved_opening_ids':openings['unresolved_opening_ids'],
        'stale_or_missing_label_ids':openings['stale_or_missing_label_ids'],
        'whole_floor_area':None,'purchase_quantity':None,'certified':False,'estimate_released':False,
        'limitations':['Enclosed geometry does not establish conditioned, garage, porch or floor-finish scope.',
            'Closed internal boundaries are not named rooms; opening closures may divide connected living spaces.',
            'Outer rings include wall thickness and enclosed voids; courts, shafts and missing walls require scope review.',
            'Junction rectangles and opening closures describe a boundary hypothesis, not additional framing or finish materials.',
            'Unreviewed wall faces and opening gaps are not silently completed.']}


def from_folder(folder,state):
    folder=Path(folder);walls=read_review(folder);runs=from_state(state,walls)
    gaps=from_plan_state(folder/'plan.pdf',state,walls,alignment_review(folder))
    path=folder/'opening_schedule_review.json'
    review=json.loads(path.read_bytes()) if path.exists() else None
    openings=schedule(state,runs,gaps,review)
    if (folder/'plan.pdf').is_file():
        from door_symbol_candidates import from_plan
        from opening_schedule import withhold_symbol_conflicts
        openings['door_symbol_candidates']=from_plan(folder/'plan.pdf',openings['openings'],state['plan_sha256'])
        openings=withhold_symbol_conflicts(openings)
        from window_symbol_candidates import apply_from_plan as window_symbols
        openings=window_symbols(folder/'plan.pdf',openings)
    return candidates(state,runs,gaps,openings)
