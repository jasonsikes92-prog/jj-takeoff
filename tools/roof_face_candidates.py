"""Find closed vector roof-face candidates with agreeing embedded pitch labels.

No project-specific path ranges or colors. This produces draft candidates, not
verified pitch, independent scale evidence, overlap resolution or roof orders.
"""
import hashlib
import itertools
import json
import math
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from measurement_store import calculate


def contains(points,point):
    x,y=point;inside=False
    for a,b in zip(points,points[1:]+points[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def pitch_labels(face):
    return face.get('pitch_candidates',[face['pitch_candidate']])


def closed_cad_loops(group):
    adjacency={};nodes={};refs=[];edges=[];invalid=False
    for index,drawing in group:
        refs.append(index)
        if drawing.get('type')!='s' or drawing.get('dashes') not in ('[] 0',None):invalid=True;continue
        segments=[]
        for item in drawing['items']:
            if item[0]=='l':segments.append(item[1:])
            elif item[0] in ('re','qu'):
                shape=item[1]
                points=([shape.tl,shape.tr,shape.br,shape.bl] if item[0]=='re'
                        else [shape.ul,shape.ur,shape.lr,shape.ll])
                segments.extend(zip(points,points[1:]+points[:1]))
            else:invalid=True
        for a,b in segments:
            if math.dist(a,b)<.001:continue
            ka,kb=tuple(round(v,3) for v in a),tuple(round(v,3) for v in b)
            edges.append((ka,kb,index));nodes[ka]=list(a);nodes[kb]=list(b)
            adjacency.setdefault(ka,set()).add(kb);adjacency.setdefault(kb,set()).add(ka)
    if invalid:return [],[],refs
    loops=[]
    remaining=set(nodes) if len(nodes)>=3 and all(len(v)==2 for v in adjacency.values()) else set()
    while remaining:
        first=min(remaining);order=[first];previous=None;current=first
        while True:
            nxt=next(v for v in sorted(adjacency[current]) if v!=previous)
            if nxt==first:break
            if nxt in order:raise ValueError('Invalid closed vector traversal')
            order.append(nxt);previous,current=current,nxt
        remaining.difference_update(order)
        loops.append({'points':[nodes[n] for n in order],'identity_points':sorted(order),
            'source_cad_paths':refs,'source_method':'style-run closed CAD loop and embedded pitch text'})
    return loops,edges,refs


def candidates(page,points_per_foot,view_bounds_pt=None,allowed_styles=None):
    if type(points_per_foot) not in (int,float) or not math.isfinite(points_per_foot) or points_per_foot<=0:
        raise ValueError('Positive finite roof scale required')
    if allowed_styles is not None and (not allowed_styles or view_bounds_pt is None):
        raise ValueError('Roof style selection requires nonempty styles and a reviewed view')
    styles=None if allowed_styles is None else {(tuple(s['color']),round(s['width_pt'],5)) for s in allowed_styles}
    if view_bounds_pt is not None:
        if (not isinstance(view_bounds_pt,(list,tuple)) or len(view_bounds_pt)!=4
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in view_bounds_pt)):
            raise ValueError('Roof view requires finite rectangle coordinates')
        a,b,c,d=view_bounds_pt
        if not 0<=a<c<=page.rect.width or not 0<=b<d<=page.rect.height:
            raise ValueError('Roof view is outside the drawing')
    def inside(box):
        return view_bounds_pt is None or (a<=box[0]<=box[2]<=c and b<=box[1]<=box[3]<=d)
    labels=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            if not inside(line['bbox']):continue
            text=''.join(s['text'] for s in line['spans']).strip()
            match=re.fullmatch(r'(\d+(?:\.\d+)?)\s*:\s*12',text)
            if not match:continue
            rise=float(match.group(1));box=line['bbox']
            if not 0<rise<=24:continue
            label={'text':text,'rise':rise,'point_pt':[(box[0]+box[2])/2,(box[1]+box[3])/2]}
            if label not in labels:labels.append(label)
    drawings=[(index,drawing) for index,drawing in enumerate(page.get_drawings()) if inside(drawing['rect'])]
    found=[];seen=set();complex_faces=[];networks=[];alternatives=[];unresolved=[]
    def style(pair):
        d=pair[1];return (d.get('type'),d.get('color'),d.get('width'),d.get('dashes'))
    loops=[];style_edges={}
    for key,group in itertools.groupby(drawings,style):
        # Keep excluded styles as source-run separators; filtering first merges provenance.
        if styles is not None:
            if key[1] is None or key[2] is None or (tuple(key[1]),round(key[2],5)) not in styles:continue
            group=[pair for pair in group if pair[1].get('stroke_opacity',1)>0]
        closed,edges,refs=closed_cad_loops(group)
        for loop in closed:
            matched=[label for label in labels if contains(loop['points'],label['point_pt'])]
            if matched and len({label['rise'] for label in matched})==1:
                loops.append({**loop,'pitch_candidate':matched[0],
                    **({'pitch_candidates':matched} if len(matched)>1 else {})})
            else:
                source={key:loop[key] for key in ('points','source_cad_paths','source_method')}
                source.update(page=page.number+1,pitch_labels=matched)
                identity=hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()
                unresolved.append({**source,'id':'roof-outline-'+identity[:16],'source_sha256':identity,
                    'source_style_reviewed':styles is not None,
                    'reason':'Conflicting embedded pitch labels' if matched else 'No embedded pitch label',
                    'physical_quantity':None})
        if edges:style_edges.setdefault(key,[]).extend(edges)
    if view_bounds_pt is not None:
        from shapely.geometry import Polygon
        from roof_edge_network import network_faces
        native=list(loops)
        for edges in style_edges.values():
            recovered,complex_result,diagnostic=network_faces(edges,labels)
            complex_faces.extend([{**face,'page':page.number+1,'source_view_bounds_pt':list(view_bounds_pt)} for face in complex_result])
            networks.append({**diagnostic,'source_cad_paths':sorted({ref for _,_,ref in edges})})
            for loop in recovered:
                explicit=[row for row in native if any(label in pitch_labels(row) for label in pitch_labels(loop))]
                if not explicit:loops.append(loop)
                elif not any(Polygon(row['points']).hausdorff_distance(Polygon(loop['points']))<=.001 for row in explicit):
                    alternatives.append({**loop,'physical_quantity':None,
                        'reason':'Network subdivision differs from a closed source outline; retained for review only'})
    for loop in loops:
        points=loop['points']
        matched=[label for label in labels if contains(points,label['point_pt'])]
        if not matched or len({label['rise'] for label in matched})!=1:continue
        identity=hashlib.sha256(json.dumps(loop.get('identity_points',sorted(points))).encode()).hexdigest()[:16]
        if identity in seen:continue
        measurement={'id':'roof-candidate-'+identity,'label':'Roof face '+matched[0]['text'],
            'page':page.number+1,'kind':'area','points':points,'points_per_foot':points_per_foot,
            'width_pt':page.rect.width,'height_pt':page.rect.height,'color':'#0e7490',
            'surface_factor':math.hypot(12,matched[0]['rise'])/12,'dependent_rows':[],
            'engine_line_ids':['roof-vector-'+identity],'source_method':loop['source_method'],
            'source_cad_paths':loop['source_cad_paths'],'pitch_candidate':matched[0],
            'scope_status':'Verify pitch, scale, face coverage and overlaps before estimate use'}
        if len(matched)>1:
            measurement['pitch_candidates']=matched
            measurement['scope_status']='Repeated agreeing pitch labels; verify their roof-face ownership, scale, coverage and overlaps before estimate use'
        try:calculate(measurement)
        except ValueError:continue
        if view_bounds_pt is not None:measurement['source_view_bounds_pt']=list(view_bounds_pt)
        seen.add(identity);found.append(measurement)
    # A second style's simple outline cannot resolve a cutout found at the same label.
    cutout_conflicts=[m for m in found if any(
        any(label in pitch_labels(face) for label in pitch_labels(m)) for face in complex_faces)]
    found=[m for m in found if m not in cutout_conflicts]
    overlaps=[]
    if view_bounds_pt is not None:
        for first,second in itertools.combinations(found,2):
            area=Polygon(first['points']).intersection(Polygon(second['points'])).area
            if area>.001:
                overlaps.append({'candidate_ids':[first['id'],second['id']],
                    'overlap_area_pt2':area,'physical_quantity':None,
                    'reason':'Projected outlines overlap; verify roof levels and coverage before summing'})
    use_counts=[sum(label in pitch_labels(m) for m in found) for label in labels]
    return {'measurements':found,'pitch_labels':labels,
        'unresolved_source_outlines':unresolved,
        'multiple_pitch_label_candidates':[{'candidate_id':m['id'],'pitch_labels':pitch_labels(m),
            'physical_quantity':None,'reason':'Agreeing slopes do not establish exclusive roof-face ownership'}
            for m in found if len(pitch_labels(m))>1],
        'unmatched_or_ambiguous_pitch_labels':[label for label,count in zip(labels,use_counts) if count!=1],
        'certified':False,**({'view_bounds_pt':list(view_bounds_pt),'complex_face_candidates':complex_faces,
            'network_alternatives':alternatives,'overlapping_face_candidates':overlaps,
            'cutout_conflicting_outlines':[{
                **{key:m[key] for key in ('id','page','points','pitch_candidate','source_cad_paths')},
                **({'pitch_candidates':m['pitch_candidates']} if 'pitch_candidates' in m else {}),
                'reason':'Another source outline at this pitch label contains interior rings',
                'physical_quantity':None} for m in cutout_conflicts],
            'edge_network_diagnostics':networks} if view_bounds_pt is not None else {})}
