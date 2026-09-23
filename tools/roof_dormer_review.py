"""Apply explicit source-bound dormer pitch interpretations during new intake."""
import hashlib
import json
import math
from pathlib import Path
import fitz
from shapely.geometry import LineString,Polygon
from roof_dormer_candidates import component_candidates


def group_sha256(group):
    return hashlib.sha256(json.dumps(group,sort_keys=True,allow_nan=False).encode()).hexdigest()


def read_review(job,plan_sha256):
    path=Path(job)/'roof_dormer_pitch_review.json'
    if not path.exists():return None
    raw=path.read_bytes();review=json.loads(raw)
    if review.get('plan_sha256')!=plan_sha256:raise ValueError('Dormer pitch review belongs to another drawing')
    if any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Dormer pitch review needs reviewer and interpretation basis')
    if type(review.get('page')) is not int or review['page']<1:raise ValueError('Dormer review page required')
    if not isinstance(review.get('groups'),list) or not review['groups']:
        raise ValueError('Dormer pitch review needs source groups')
    return {**review,'review_sha256':hashlib.sha256(raw).hexdigest(),'reviewer_identity_authenticated':False}


def reviewed_candidates(plan,raw,review,frame):
    if frame is None or review['page']!=frame['page']:
        raise ValueError('Dormer review requires the calibrated selected roof view')
    available=[g for network in raw.get('edge_network_diagnostics',[])
        for g in network.get('unpitched_interior_faces',[])]
    by_hash={group_sha256(g):g for g in available}
    groups=[];seen=set()
    with fitz.open(plan) as doc:
        drawings=doc[frame['page']-1].get_drawings()
        for item in review['groups']:
            key=item.get('source_group_sha256')
            if key not in by_hash or key in seen:raise ValueError('Dormer geometry changed, missing or repeated')
            seen.add(key);source=by_hash[key];parent=item.get('parent',{})
            if parent.get('rise')!=source['parent_pitch_label_for_location_only']['rise']:
                raise ValueError('Reviewed parent pitch disagrees with source label')
            paths=parent.get('arrow_paths')
            if (not isinstance(paths,list) or len(paths)!=3 or len(set(paths))!=3 or
                    any(type(p) is not int or not 0<=p<len(drawings) for p in paths)):
                raise ValueError('Parent arrow needs one shaft and two source wing paths')
            selected=[drawings[p] for p in paths]
            if any(d.get('type')!='s' or d.get('stroke_opacity',1)<=0 or d.get('color') is None
                    or d.get('dashes') not in ('[] 0',None) or len(d['items'])!=1
                    or d['items'][0][0]!='l' for d in selected):
                raise ValueError('Parent arrow paths must be visible solid line segments')
            if len({(d['color'],d['width']) for d in selected})!=1:
                raise ValueError('Parent arrow paths must have matching styles')
            lines=[[tuple(point) for point in d['items'][0][1:]] for d in selected]
            heads=[p for p in lines[0] if all(p in wing for wing in lines[1:])]
            if len(heads)!=1:raise ValueError('Parent arrow has no unique shared head')
            head=heads[0];tail=next(p for p in lines[0] if p!=head)
            delta=[head[i]-tail[i] for i in range(2)];length=math.hypot(*delta)
            if length<=.001:raise ValueError('Parent arrow shaft has no direction')
            direction=[v/length for v in delta];normal=[-direction[1],direction[0]]
            wings=[next(p for p in wing if p!=head) for wing in lines[1:]]
            behind=[sum((p[i]-head[i])*direction[i] for i in range(2)) for p in wings]
            side=[sum((p[i]-head[i])*normal[i] for i in range(2)) for p in wings]
            if not all(v<0 for v in behind) or side[0]*side[1]>=0:
                raise ValueError('Arrow wings do not point along the shaft')
            down=parent.get('downslope')
            if (not isinstance(down,list) or len(down)!=2 or any(type(v) not in (int,float)
                    or not math.isfinite(v) for v in down) or math.hypot(*down)==0 or
                    any(abs(down[i]/math.hypot(*down)-direction[i])>1e-6 for i in range(2))):
                raise ValueError('Reviewed downslope disagrees with the source arrow')
            parents=[f for f in raw.get('complex_face_candidates',[])
                if any(Polygon(h).equals(Polygon(source['interior_ring_points'])) for h in f['holes'])]
            if len(parents)!=1:raise ValueError('Dormer requires one identified parent face')
            polygon=Polygon(parents[0]['points'],parents[0]['holes'])
            if not all(polygon.contains(LineString(line)) for line in lines):
                raise ValueError('Parent arrow lies outside its roof face')
            result=component_candidates(source,parent,frame)
            for measurement in result['measurements']:
                measurement['source_pitch_review']={k:review[k] for k in
                    ('review_sha256','reviewer','basis','reviewer_identity_authenticated')}
            groups.append(result)
    return groups
