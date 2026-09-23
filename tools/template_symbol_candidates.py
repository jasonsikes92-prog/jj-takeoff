"""Source-bound raster symbol candidates; matching never approves scope or counts."""
import hashlib
import json
import math
import cv2
import fitz
import numpy as np

MAX_CANDIDATES=1000


def box(value,width,height):
    if (not isinstance(value,list) or len(value)!=4 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in value) or
            not 0<=value[0]<value[2]<=width or not 0<=value[1]<value[3]<=height):
        raise ValueError('Symbol bounds must be finite and inside the page')
    return [math.floor(value[0]),math.floor(value[1]),math.ceil(value[2]),math.ceil(value[3])]


def ink_mask(rgb,ink):
    values=rgb.astype(np.float32)
    if ink=='red':mask=(values[:,:,0]>values[:,:,1]+35)&(values[:,:,0]>values[:,:,2]+35)
    elif ink=='dark':mask=np.max(values,axis=2)<200
    else:raise ValueError('Choose explicit red or dark symbol ink')
    return mask.astype(np.uint8)*255


def matches(mask,reference,scales,threshold,exclusions,rotations=None,stroke_dilations=None):
    if (not isinstance(scales,list) or not 1<=len(scales)<=100 or
            any(type(s) not in (int,float) or not math.isfinite(s) or s<=0 for s in scales) or
            len(scales)!=len(set(scales))):
        raise ValueError('Symbol search needs unique positive finite scales')
    rotations=[0] if rotations is None else rotations
    if (not isinstance(rotations,list) or not rotations or
            any(type(r) is not int or r not in (0,90,180,270) for r in rotations) or
            len(rotations)!=len(set(rotations))):
        raise ValueError('Symbol rotations must be unique quarter turns: 0, 90, 180, 270')
    stroke_dilations=[0] if stroke_dilations is None else stroke_dilations
    if (not isinstance(stroke_dilations,list) or not stroke_dilations or
            any(type(r) is not int or r not in (0,1,2,3) for r in stroke_dilations) or
            len(stroke_dilations)!=len(set(stroke_dilations))):
        raise ValueError('Symbol stroke dilations must be unique pixel radii from 0 through 3')
    if type(threshold) not in (int,float) or not math.isfinite(threshold) or not .5<=threshold<=1:
        raise ValueError('Symbol candidate threshold must be between 0.5 and 1')
    x0,y0,x1,y1=reference;template=mask[y0:y1,x0:x1]
    if np.count_nonzero(template)<8 or np.count_nonzero(template)==template.size:
        raise ValueError('Symbol reference needs visible ink and background')
    field=mask.copy()
    for a,b,c,d in exclusions+[reference]:field[b:d,a:c]=0
    field=cv2.GaussianBlur(field,(3,3),0).astype(np.float32)
    found=[];searched=0
    for scale,rotation,dilation in ((s,r,d) for s in scales for r in rotations for d in stroke_dilations):
        oriented=np.rot90(template,rotation//90)
        width=round(oriented.shape[1]*scale);height=round(oriented.shape[0]*scale)
        if width<3 or height<3 or width>field.shape[1] or height>field.shape[0]:
            raise ValueError('Symbol scale produces an unusable reference size')
        sample=cv2.resize(oriented,(width,height),interpolation=cv2.INTER_LINEAR)
        if dilation:sample=cv2.dilate(sample,np.ones((2*dilation+1,2*dilation+1),np.uint8))
        sample=cv2.GaussianBlur(sample,(3,3),0).astype(np.float32)
        if not np.any(sample):raise ValueError('Scaled symbol reference lost its ink')
        scores=cv2.matchTemplate(field,sample,cv2.TM_CCORR_NORMED);searched+=1
        peaks=(scores>=threshold)&(scores==cv2.dilate(scores,np.ones((3,3),np.uint8)))
        ys,xs=np.where(peaks)
        if len(xs)>MAX_CANDIDATES:
            raise ValueError('Too many symbol candidates; narrow the reference or search settings')
        for x,y in zip(xs,ys):
            bounds=[int(x),int(y),int(x)+width,int(y)+height]
            if any(bounds[0]<c and bounds[2]>a and bounds[1]<d and bounds[3]>b
                   for a,b,c,d in exclusions+[reference]):continue
            found.append({'point_pt':[float(x+width/2),float(y+height/2)],
                          'bbox_pt':bounds,'score':float(scores[y,x]),'scale':scale,
                          'rotation_degrees':rotation,'stroke_dilation_pixels':dilation})
    kept=[]
    for candidate in sorted(found,key=lambda c:(-c['score'],c['point_pt'],c['scale'])):
        width=candidate['bbox_pt'][2]-candidate['bbox_pt'][0]
        if any(math.dist(candidate['point_pt'],old['point_pt'])<
               .5*max(width,old['bbox_pt'][2]-old['bbox_pt'][0]) for old in kept):continue
        kept.append(candidate)
        if len(kept)>MAX_CANDIDATES:raise ValueError('Too many distinct symbol candidates; review required')
    return sorted(kept,key=lambda c:(c['point_pt'][1],c['point_pt'][0])),searched


def plan_template_candidates(document,config,plan_sha256):
    if config.get('plan_sha256')!=plan_sha256:raise ValueError('Symbol templates belong to another drawing')
    resolution=config.get('raster_pixels_per_point',1)
    if type(resolution) is not int or resolution not in (1,2,3):
        raise ValueError('Symbol raster resolution must be 1, 2 or 3 pixels per point')
    pages=config.get('pages',[])
    if not pages:raise ValueError('Symbol template pages required')
    seen=set();measurements=[];searches=[]
    for definition in pages:
        page_number=definition['page']
        if type(page_number) is not int or not 1<=page_number<=len(document) or page_number in seen:
            raise ValueError('Symbol page must be unique and inside this drawing')
        seen.add(page_number);page=document[page_number-1]
        if page.rotation:raise ValueError('Rotated pages require an explicit orientation review')
        exclusions=[]
        for exclusion in definition.get('exclusions',[]):
            if not isinstance(exclusion.get('source'),str) or not exclusion['source'].strip():
                raise ValueError('Symbol exclusion source required')
            bounds=box(exclusion['bbox_pt'],page.rect.width,page.rect.height)
            exclusions.append([v*resolution for v in bounds])
        pix=page.get_pixmap(matrix=fitz.Matrix(resolution,resolution),alpha=False,colorspace=fitz.csRGB)
        rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        templates=definition.get('templates',[]);ids=set()
        if not templates:raise ValueError('Symbol reference definitions required')
        masks={};frames={}
        for template in templates:
            if any(not isinstance(template.get(k),str) or not template[k].strip() for k in ('id','label','meaning_source')):
                raise ValueError('Symbol identity, label and meaning source required')
            if template['id'] in ids:raise ValueError('Duplicate symbol reference identity')
            ids.add(template['id'])
            reference=[v*resolution for v in box(template['bbox_pt'],page.rect.width,page.rect.height)]
            ink=template['ink']
            if ink not in masks:masks[ink]=ink_mask(rgb,ink)
            rotations=template.get('rotations_degrees',[0])
            dilations=template.get('stroke_dilations_pixels',[0])
            found,searched=matches(masks[ink],reference,template['scales'],template['minimum_score'],exclusions,rotations,dilations)
            for candidate in found:
                candidate['point_pt']=[v/resolution for v in candidate['point_pt']]
                candidate['bbox_pt']=[v/resolution for v in candidate['bbox_pt']]
            require_frame=template.get('require_vector_frame',False)
            if type(require_frame) is not bool:raise ValueError('Vector frame requirement must be true or false')
            rejected=[];reference_frame=None
            if require_frame:
                from vector_symbol_frames import rectangle_frames,corroborate_frames
                if ink not in frames:frames[ink]=rectangle_frames(page,ink)
                found,rejected,reference_frame=corroborate_frames(found,frames[ink],template['bbox_pt'])
            searches.append({'page':page_number,'template_id':template['id'],'candidates':found,
                             'scales_searched':len(template['scales']),'variants_searched':searched,
                             'rotation_search_degrees':rotations,
                             'stroke_dilations_pixels':dilations,
                             'vector_reference_frame':reference_frame,'uncorroborated_candidates':rejected,
                             'status':'candidates_require_review' if found else 'no_match_scope_unresolved'})
            if not found:continue
            identity='template-'+hashlib.sha256(json.dumps([page_number,template,found],sort_keys=True).encode()).hexdigest()[:16]
            measurements.append({'id':identity,'label':template['label'],'kind':'count','page':page_number,
                'points':[c['point_pt'] for c in found],'width_pt':page.rect.width,'height_pt':page.rect.height,
                'color':template.get('color','#a21caf'),'dependent_rows':[],'engine_line_ids':[identity],
                'template_id':template['id'],'meaning_source':template['meaning_source'],
                'source_matches':found,'scope_status':'Pattern matches require physical-symbol and coverage review; scores are not accuracy probabilities.'})
    return {'plan_sha256':plan_sha256,'definitions_sha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
            'measurements':measurements,'searches':searches,'scope_review_required':True,
            'coverage_certified':False,'estimate_released':False,'raster_pixels_per_point':resolution,
            'method':'Configured-ink normalized template correlation across explicit scales and quarter turns; no rotation inference'}
