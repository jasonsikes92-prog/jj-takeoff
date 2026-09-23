"""Locate an explicit polyline legend using its longest stroke as an anchor.

Matching supports translated, scaled and rotated strokes, including clustered
symbols. A match is source evidence, not approval of the symbol's trade meaning.
"""
import hashlib
import json
import math
import numpy as np

from template_symbol_candidates import box
from text_symbol_candidates import symbol_candidates


def stroke_matches(page,definition):
    bounds=box(definition['bbox_pt'],page.rect.width,page.rect.height)
    limits=definition['scale_range'];error=definition['maximum_error_ratio']
    if (not isinstance(limits,list) or len(limits)!=2 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in limits) or not 0<limits[0]<=limits[1]):
        raise ValueError('Positive finite stroke scale range required')
    if type(error) not in (int,float) or not math.isfinite(error) or not 0<error<=.05:
        raise ValueError('Stroke error ratio must be positive and at most 0.05')
    ink=definition['ink']
    if ink not in ('red','dark'):raise ValueError('Choose explicit red or dark symbol ink')
    lines=[]
    for path in page.get_drawings():
        color=path.get('color')
        if color is None:continue
        selected=(color[0]>color[1]+35/255 and color[0]>color[2]+35/255) if ink=='red' else max(color)<200/255
        if selected:
            lines.extend((list(i[1]),list(i[2]),path['seqno']) for i in path['items'] if i[0]=='l' and i[1]!=i[2])
    if not lines:raise ValueError('No supported vector line strokes; raster review required')
    starts=np.array([v[0] for v in lines]);ends=np.array([v[1] for v in lines]);mid=(starts+ends)/2
    lengths=np.linalg.norm(ends-starts,axis=1);low=np.minimum(starts,ends);high=np.maximum(starts,ends)
    refs=np.where(np.all(low>=bounds[:2],axis=1)&np.all(high<=bounds[2:],axis=1))[0]
    if len(refs)<3:raise ValueError('Legend requires a distinct anchor and supporting strokes')
    anchor=refs[np.argmax(lengths[refs])];size=lengths[anchor]
    if sum(lengths[refs]>=size*.99)!=1:raise ValueError('Legend needs one distinct longest anchor stroke')
    axis=(ends[anchor]-starts[anchor])/size;basis=np.array([axis,[-axis[1],axis[0]]]).T
    samples=np.vstack([np.linspace(starts[i],ends[i],max(3,math.ceil(lengths[i]/(size*.02))+1)) for i in refs])
    normalized=(samples-mid[anchor])@basis/size
    if np.ptp(normalized[:,1])<.1:raise ValueError('Legend supporting strokes must extend away from the anchor')
    exclusions=[bounds]
    for exclusion in definition.get('exclusions',[]):
        if not isinstance(exclusion.get('source'),str) or not exclusion['source'].strip():raise ValueError('Exclusion source required')
        exclusions.append(box(exclusion['bbox_pt'],page.rect.width,page.rect.height))
    found=[]
    for i in np.where((lengths>=size*limits[0])&(lengths<=size*limits[1]))[0]:
        direction=(ends[i]-starts[i])/lengths[i];rotation=np.array([direction,[-direction[1],direction[0]]]).T
        # Segment direction can be reversed independently of the drawn shape.
        variants=[]
        for sign in (1,-1):
            targets=normalized@(sign*rotation).T*lengths[i]+mid[i]
            aabb=[*targets.min(axis=0),*targets.max(axis=0)]
            if any(aabb[0]<=e[2] and aabb[2]>=e[0] and aabb[1]<=e[3] and aabb[3]>=e[1] for e in exclusions):continue
            tolerance=error*lengths[i]
            local=np.where(np.all(high>=np.array(aabb[:2])-tolerance,axis=1)&np.all(low<=np.array(aabb[2:])+tolerance,axis=1))[0]
            vectors=ends[local]-starts[local];delta=targets[:,None,:]-starts[local][None,:,:]
            t=np.clip(np.sum(delta*vectors[None,:,:],axis=2)/np.sum(vectors*vectors,axis=1)[None,:],0,1)
            distances=np.linalg.norm(delta-t[:,:,None]*vectors[None,:,:],axis=2)
            nearest=distances.argmin(axis=1);maximum=float(distances[np.arange(len(targets)),nearest].max()/lengths[i])
            if maximum<=error:
                variants.append({'point_pt':mid[i].tolist(),'bbox_pt':aabb,'anchor_path_sequence_number':lines[i][2],
                    'support_path_sequence_numbers':sorted({lines[local[n]][2] for n in nearest}),
                    'anchor_length_pt':float(lengths[i]),'scale':float(lengths[i]/size),
                    'maximum_error_ratio':maximum,'qualifiers':[]})
        if variants:
            candidate=min(variants,key=lambda v:v['maximum_error_ratio'])
            if not any(math.dist(candidate['point_pt'],old['point_pt'])<size*limits[0]*.02 for old in found):found.append(candidate)
    return found,{'bbox_pt':bounds,'anchor_path_sequence_number':lines[anchor][2],
                  'anchor_length_pt':float(size),'path_sequence_numbers':sorted({lines[i][2] for i in refs})}


def plan_stroke_candidates(document,config,plan_sha256):
    if config.get('plan_sha256')!=plan_sha256:raise ValueError('Stroke definitions belong to another drawing')
    if not config.get('pages'):raise ValueError('Explicit stroke pages required')
    seen=set();measurements=[];results=[]
    for definition in config['pages']:
        number=definition['page']
        if type(number) is not int or not 1<=number<=len(document) or number in seen:raise ValueError('Unique valid stroke page required')
        seen.add(number);page=document[number-1]
        if page.rotation:raise ValueError('Rotated PDF page requires orientation review')
        if any(not isinstance(definition.get(k),str) or not definition[k].strip() for k in ('id','label','meaning_source')):
            raise ValueError('Stroke identity, label and source required')
        found,reference=stroke_matches(page,definition)
        labels=definition.get('qualifying_labels',{});unresolved=[];claims={}
        if labels:
            labeled=symbol_candidates(page,labels,definition.get('exclusions',[])+[{'bbox_pt':reference['bbox_pt'],'source':'Stroke legend'}])
            for group in labeled['measurements']:
                for label in group['source_labels']:
                    nearby=sorted((math.dist(s['point_pt'],label['point_pt']),i) for i,s in enumerate(found)
                                  if math.dist(s['point_pt'],label['point_pt'])<=s['anchor_length_pt'])
                    if not nearby or (len(nearby)>1 and nearby[1][0]-nearby[0][0]<=found[nearby[0][1]]['anchor_length_pt']*.05):
                        unresolved.append({**label,'reason':'No unique nearest stroke symbol'})
                        for _,i in nearby:found[i]['qualifiers'].append({'type':'ambiguous_label','label':label})
                    else:
                        i=nearby[0][1];claims.setdefault(i,[]).append(label)
                        found[i]['qualifiers'].append({'type':'label','token':group['symbol_token'],'label':label,'distance_pt':nearby[0][0]})
            for i,claimed in claims.items():
                if len(claimed)>1:unresolved.append({'point_pt':found[i]['point_pt'],'labels':claimed,'reason':'Multiple labels claim one symbol'})
        located=[s for s in found if not s['qualifiers']]
        if located:
            identity='stroke-'+hashlib.sha256(json.dumps([number,definition,located],sort_keys=True).encode()).hexdigest()[:16]
            measurements.append({'id':identity,'label':definition['label'],'kind':'count','page':number,
                'points':[s['point_pt'] for s in located],'width_pt':page.rect.width,'height_pt':page.rect.height,
                'color':definition.get('color','#a16207'),'dependent_rows':[],'engine_line_ids':[identity],
                'meaning_source':definition['meaning_source'],'source_shapes':located,'reference_shape':reference,
                'scope_status':'Stroke candidates require visual symbol, qualifier, redline and complete trade-scope review.'})
        results.append({'page':number,'matched_shapes':len(found),'qualified_shapes':[s for s in found if s['qualifiers']],
                        'unresolved_labels':unresolved,'reference_shape':reference})
    return {'plan_sha256':plan_sha256,'definitions_sha256':hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest(),
            'measurements':measurements,'pages':results,'scope_review_required':True,'coverage_certified':False,'estimate_released':False}
