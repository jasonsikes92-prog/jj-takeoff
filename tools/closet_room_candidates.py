"""Recognize a limited reach-in closet symbol, retaining its native evidence."""
import copy
import hashlib
import itertools
import json
from shapely.geometry import Polygon,LineString,box
from door_symbol_candidates import paths_from_drawings
from room_use_review import binding


def shelf_symbol(region,connection,lines):
    shape=Polygon(region['points'],region['holes']);scale=region['points_per_foot']/12
    if region['holes'] or shape.symmetric_difference(box(*shape.bounds)).area>1e-5:return None
    sides=[s for s in connection['sides'] if s.get('region_id')==region['id'] and s.get('status')=='region_boundary']
    if len(sides)!=1:return None
    face=sides[0]['face_points_pt'];matches=[]
    for axis in (0,1):
        cross=1-axis;low=shape.bounds[axis];high=shape.bounds[axis+2]
        front,back=shape.bounds[cross],shape.bounds[cross+2]
        if not 36<=(high-low)/scale<=120 or not 20<=(back-front)/scale<=40:continue
        if abs(face[0][cross]-face[1][cross])>1e-5:continue
        if abs(face[0][cross]-front)<1e-5:rear=back;sign=-1
        elif abs(face[0][cross]-back)<1e-5:rear=front;sign=1
        else:continue
        if not shape.boundary.covers(LineString(face)):continue
        rails=[];caps=[]
        for line in lines:
            a,b=line['points'];segment=LineString([a,b])
            if not shape.covers(segment):continue
            if abs(a[cross]-b[cross])<1e-5:
                ends=sorted([a[axis],b[axis]])
                if 0<=(ends[0]-low)/scale<=1.25 and 0<=(high-ends[1])/scale<=1.25:
                    rails.append({'depth':sign*(a[cross]-rear)/scale,'ends':ends,'line':line})
            elif abs(a[axis]-b[axis])<1e-5:caps.append(line)
        # A shallow closed shelf rectangle plus two separate rod lines near its front.
        for edge in rails:
            if not 10<=edge['depth']<=16:continue
            rear_edges=[r for r in rails if 0<=r['depth']<=1.25
                and max(abs(a-b) for a,b in zip(r['ends'],edge['ends']))/scale<=.01]
            rod_lines=[r for r in rails if .5<=edge['depth']-r['depth']<=3
                and max(abs(a-b) for a,b in zip(r['ends'],edge['ends']))/scale<=.01]
            for rods in itertools.combinations(rod_lines,2):
                if not .5<=abs(rods[0]['depth']-rods[1]['depth'])<=1.75:continue
                for rear_edge in rear_edges:
                    cap_evidence=[]
                    for end in edge['ends']:
                        expected=sorted([rear+sign*edge['depth']*scale,rear+sign*rear_edge['depth']*scale])
                        found=[l for l in caps if abs(l['points'][0][axis]-end)/scale<=.01
                            and max(abs(a-b) for a,b in zip(sorted(p[cross] for p in l['points']),expected))/scale<=.01]
                        if not found:break
                        cap_evidence.append(found[0])
                    if len(cap_evidence)!=2:continue
                    evidence={'shelf_depth_inches':edge['depth']-rear_edge['depth'],
                        'shelf_lines':[edge['line'],rear_edge['line'],*cap_evidence],
                        'rod_lines':[r['line'] for r in rods],'entry_face_points_pt':face}
                    identity=sorted(tuple(sorted(tuple(p) for p in l['points'])) for l in evidence['shelf_lines']+evidence['rod_lines'])
                    if not any(key==identity for key,_ in matches):matches.append((identity,evidence))
    return matches[0][1] if len(matches)==1 else None


def apply(rooms,document):
    result=copy.deepcopy(rooms);evidence=[]
    pages={p:paths_from_drawings(document[p-1].get_drawings())[0] for p in {r['page'] for r in result['regions']}}
    stale={d['region_id'] for d in result.get('room_use_review',{}).get('unresolved_decisions',[])}
    for region in result['regions']:
        if (region.get('room_use_confirmed') or region['id'] in stale or region.get('boundary_source_issues')
                or region['printed_labels'] or region.get('room_use_inference',{}).get('room_use')):continue
        links=[c for c in result['opening_connections'] if any(s.get('region_id')==region['id'] for s in c['sides'])]
        if (len(links)!=1 or links[0]['status']!='two_region_boundaries'
                or links[0]['page']!=region['page'] or links[0]['points_per_foot']!=region['points_per_foot']):continue
        symbol=shelf_symbol(region,links[0],pages[region['page']])
        if symbol is None:continue
        source={'plan_sha256':result['plan_sha256'],'region_source_sha256':binding(result['plan_sha256'],region),
            'symbol':symbol,'connection':links[0]}
        source['source_sha256']=hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()
        candidate={'region_id':region['id'],'room_use':'closet','status':'shelf_symbol_inference',
            'source_sha256':binding(result['plan_sha256'],region),'shelf_evidence':source,
            'basis':'Native closed shelf and paired rod lines across a narrow rectangular enclosure, opposite its sole interior opening; reach-in closet estimating interpretation.',
            'requires_review':True,'certified':False,'owner_approved':False}
        region['room_use_inference']=candidate;evidence.append(candidate)
    if evidence:
        replacements={c['region_id']:c for c in evidence}
        if 'room_use_candidates' in result:
            result['room_use_candidates']['candidates']=[replacements.get(c['region_id'],c) for c in result['room_use_candidates']['candidates']]
            result['room_use_candidates']['automatic_candidate_count']=sum(c.get('room_use') is not None for c in result['room_use_candidates']['candidates'])
        result['closet_room_candidates']={'candidates':evidence,'shelving_quantity_released':False,'complete_room_interpretation':False}
        result['source_sha256']=hashlib.sha256(json.dumps([rooms['source_sha256'],evidence],sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result
