"""Circle-and-parallel-bar evidence; electrical meaning still requires legend review."""
import math
import hashlib
import json
import numpy as np


def outlet_shapes(page,ink='red'):
    paths=[];lines=[];circles=[]
    for path in page.get_drawings():
        color=path.get('color')
        if color is None:continue
        if ink=='red':selected=color[0]>color[1]+35/255 and color[0]>color[2]+35/255
        elif ink=='dark':selected=max(color)<200/255
        else:raise ValueError('Choose explicit red or dark symbol ink')
        if not selected:continue
        paths.append(path)
        for item in path['items']:
            if item[0]!='l':continue
            a=np.array(item[1]);b=np.array(item[2]);length=float(np.linalg.norm(b-a))
            if length>=1:lines.append((a,b,length,path['seqno']))
    if not lines:return []
    starts=np.array([v[0] for v in lines]);ends=np.array([v[1] for v in lines]);lengths=np.array([v[2] for v in lines])
    for path in paths:
        curves=[i for i in path['items'] if i[0]=='c'];r=path['rect']
        if len(curves)<4 or len(curves)!=len(path['items']) or min(r.width,r.height)<2:continue
        if abs(r.width/r.height-1)>.06:continue
        diameter=(r.width+r.height)/2;center=np.array([(r.x0+r.x1)/2,(r.y0+r.y1)/2])
        samples=[]
        for curve in curves:
            points=np.array([list(p) for p in curve[1:]])
            for t in (0,.25,.5,.75,1):
                samples.append((1-t)**3*points[0]+3*(1-t)**2*t*points[1]+3*(1-t)*t*t*points[2]+t**3*points[3])
        if max(abs(np.linalg.norm(p-center)/(diameter/2)-1) for p in samples)>.06:continue
        if np.linalg.norm(np.array(curves[0][1])-np.array(curves[-1][-1]))>diameter*.02:continue
        nearby=np.where((lengths>=diameter*.75)&(lengths<=diameter*2.5)&
                        (np.linalg.norm((starts+ends)/2-center,axis=1)<diameter))[0]
        bars=[]
        for index in nearby:
            direction=(ends[index]-starts[index])/lengths[index];normal=np.array([-direction[1],direction[0]])
            projections=[float(np.dot(p-center,direction)) for p in (starts[index],ends[index])]
            distance=float(np.dot(starts[index]-center,normal))
            if min(projections)<0<max(projections) and .05*diameter<abs(distance)<.49*diameter:
                bars.append((index,direction,normal,distance))
        pairs=[]
        for n,(index,direction,normal,distance) in enumerate(bars):
            for other,other_direction,_,_ in bars[n+1:]:
                if abs(float(np.dot(direction,other_direction)))<.998:continue
                other_distance=float(np.dot(starts[other]-center,normal))
                if distance*other_distance>=0 or abs(distance+other_distance)>diameter*.12:continue
                pairs.append({'path_sequence_numbers':sorted({int(lines[index][3]),int(lines[other][3])}),
                              'gap_diameter_ratio':abs(distance-other_distance)/diameter,
                              'length_diameter_ratios':[float(lengths[index]/diameter),float(lengths[other]/diameter)],
                              'angle_degrees':math.degrees(math.atan2(direction[1],direction[0]))%180})
        if not pairs:continue
        center_lines=[]
        for index in nearby:
            direction=(ends[index]-starts[index])/lengths[index];normal=np.array([-direction[1],direction[0]])
            projections=[float(np.dot(p-center,direction)) for p in (starts[index],ends[index])]
            if abs(float(np.dot(starts[index]-center,normal)))>diameter*.05:continue
            if not min(projections)<-diameter*.4<diameter*.4<max(projections):continue
            angle=math.degrees(math.atan2(direction[1],direction[0]))%180
            if any(abs(math.sin(math.radians(angle-p['angle_degrees'])))<.05 for p in pairs):
                center_lines.append(int(lines[index][3]))
        circles.append({'point_pt':center.tolist(),'bbox_pt':list(r),'diameter_pt':diameter,
                        'circle_path_sequence_number':path['seqno'],'bar_pairs':pairs,
                        'center_line_path_sequence_numbers':sorted(set(center_lines)),
                        'status':'shape_candidate_requires_legend_and_scope_review'})
    return circles


def plan_vector_outlets(document,config,plan_sha256):
    from template_symbol_candidates import box
    from text_symbol_candidates import symbol_candidates
    from vector_symbol_frames import rectangle_frames
    if config.get('plan_sha256')!=plan_sha256:raise ValueError('Vector definitions belong to another drawing')
    if not config.get('pages'):raise ValueError('Vector page definitions required')
    seen=set();measurements=[];page_results=[]
    for definition in config['pages']:
        number=definition['page']
        if type(number) is not int or not 1<=number<=len(document) or number in seen:raise ValueError('Unique valid vector page required')
        seen.add(number);page=document[number-1]
        if page.rotation:raise ValueError('Rotated PDF page requires orientation review')
        exclusions=definition.get('exclusions',[])
        for e in exclusions:
            box(e['bbox_pt'],page.rect.width,page.rect.height)
            if not e.get('source'):raise ValueError('Exclusion source required')
        shapes=outlet_shapes(page,definition['ink']);frames=rectangle_frames(page,definition['ink'])
        legends=definition.get('legends',[]);ids=set();references=[]
        for legend in legends:
            if any(not isinstance(legend.get(k),str) or not legend[k].strip() for k in ('id','label','meaning_source')):
                raise ValueError('Vector legend identity, label and source required')
            if legend['id'] in ids:raise ValueError('Duplicate vector legend identity')
            ids.add(legend['id']);bounds=box(legend['bbox_pt'],page.rect.width,page.rect.height)
            contained=[s for s in shapes if bounds[0]<=s['bbox_pt'][0]<s['bbox_pt'][2]<=bounds[2] and bounds[1]<=s['bbox_pt'][1]<s['bbox_pt'][3]<=bounds[3]]
            if len(contained)!=1 or len(contained[0]['bar_pairs'])!=1:raise ValueError('Legend needs one unambiguous circle/bar symbol')
            limits=legend['diameter_scale_range']
            if (not isinstance(limits,list) or len(limits)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in limits)
                    or not 0<limits[0]<=limits[1]):raise ValueError('Positive diameter scale range required')
            references.append((legend,contained[0]))
        if not references:raise ValueError('Vector legends required')
        field=[{**s,'qualifiers':[]} for s in shapes if not any(s['bbox_pt'][0]<=e['bbox_pt'][2] and s['bbox_pt'][2]>=e['bbox_pt'][0] and s['bbox_pt'][1]<=e['bbox_pt'][3] and s['bbox_pt'][3]>=e['bbox_pt'][1] for e in exclusions)]
        unresolved_labels=[];label_definitions=definition.get('qualifying_labels',{})
        label_results=symbol_candidates(page,label_definitions,exclusions) if label_definitions else {'measurements':[]}
        for group in label_results['measurements']:
            for label in group['source_labels']:
                hits=[s for s in field if math.dist(s['point_pt'],label['point_pt'])<=s['diameter_pt']*1.6]
                if len(hits)!=1:
                    unresolved_labels.append({**label,'reason':'No unique nearby circle/bar symbol'})
                    for s in hits:s['qualifiers'].append({'type':'ambiguous_label','label':label})
                else:hits[0]['qualifiers'].append({'type':'label','token':group['symbol_token'],'label':label})
        groups={l['id']:[] for l,_ in references};unassigned=[];qualified=[]
        for s in field:
            x0,y0,x1,y1=s['bbox_pt'];diameter=s['diameter_pt']
            enclosures=[f for f in frames if f['bbox_pt'][0]<=x0<x1<=f['bbox_pt'][2] and f['bbox_pt'][1]<=y0<y1<=f['bbox_pt'][3]
                        and f['bbox_pt'][2]-f['bbox_pt'][0]<2*diameter and f['bbox_pt'][3]-f['bbox_pt'][1]<2*diameter]
            if enclosures:s['qualifiers'].append({'type':'boxed','frames':enclosures})
            if s['qualifiers']:qualified.append(s);continue
            matches=[]
            if len(s['bar_pairs'])==1:
                for legend,ref in references:
                    scale=diameter/ref['diameter_pt'];low,high=legend['diameter_scale_range']
                    same_center=bool(s['center_line_path_sequence_numbers'])==bool(ref['center_line_path_sequence_numbers'])
                    ratio=s['bar_pairs'][0]['gap_diameter_ratio']/ref['bar_pairs'][0]['gap_diameter_ratio']
                    if low<=scale<=high and same_center and abs(ratio-1)<=.1:matches.append(legend['id'])
            if len(matches)==1:groups[matches[0]].append(s)
            else:unassigned.append({**s,'matching_legend_ids':matches})
        for legend,ref in references:
            located=groups[legend['id']]
            if not located:continue
            identity='vector-'+hashlib.sha256(json.dumps([number,legend,located],sort_keys=True).encode()).hexdigest()[:16]
            measurements.append({'id':identity,'label':legend['label'],'kind':'count','page':number,
                'points':[s['point_pt'] for s in located],'width_pt':page.rect.width,'height_pt':page.rect.height,
                'color':legend.get('color','#0f766e'),'dependent_rows':[],'engine_line_ids':[identity],
                'meaning_source':legend['meaning_source'],'source_shapes':located,'reference_shape':ref,
                'scope_status':'Vector symbol candidates; labels, redlines, trade coverage and products require review.'})
        page_results.append({'page':number,'field_shapes':len(field),'qualified_shapes':qualified,
                             'unassigned_shapes':unassigned,'unresolved_labels':unresolved_labels})
    return {'plan_sha256':plan_sha256,'definitions_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'measurements':measurements,'pages':page_results,'scope_review_required':True,'coverage_certified':False,'estimate_released':False}
