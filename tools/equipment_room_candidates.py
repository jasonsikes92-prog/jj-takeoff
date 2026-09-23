"""Use labelled equipment geometry as an explicit, limited room-use inference."""
import copy
import hashlib
import json
import math
import cv2
import fitz
import numpy as np
from shapely.geometry import Polygon,box,Point
from room_use_review import binding


def water_heater_labels(page):
    result=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=''.join(s['text'] for s in line['spans']).strip()
            if text.upper() not in ('WH','W.H.'):continue
            result.append({'text':text,'page':page.number+1,'bounds_pt':list(line['bbox'])})
    return result


def circular_body(page,region,label):
    """Corroborate WH text with a closed circular outline, not a text-only guess."""
    shape=Polygon(region['points'],region['holes']);scale=region['points_per_foot']
    clip=fitz.Rect(shape.bounds);zoom=4
    pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),clip=clip,alpha=False,colorspace=fitz.csRGB)
    pixels=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    mask=(pixels.max(axis=2)<180).astype(np.uint8)*255
    contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    found=[]
    for contour in contours:
        area=cv2.contourArea(contour);perimeter=cv2.arcLength(contour,True)
        if perimeter<=0 or 4*math.pi*area/perimeter**2<.85:continue
        (x,y),radius=cv2.minEnclosingCircle(contour)
        center=[(pix.x+x)/zoom,(pix.y+y)/zoom];radius/=zoom
        diameter_inches=2*radius/scale*12
        if not 12<=diameter_inches<=48:continue
        body=Point(center).buffer(radius,quad_segs=64)
        if not shape.covers(body) or not body.covers(box(*label['bounds_pt'])):continue
        # Text must be centrally located, and the symbol materially occupies this small enclosure.
        label_center=[(label['bounds_pt'][i]+label['bounds_pt'][i+2])/2 for i in (0,1)]
        if math.dist(center,label_center)>radius*.3 or body.area/shape.area<.1:continue
        if any(math.dist(center,c['center_pt'])<scale*.1 and abs(radius-c['radius_pt'])<scale*.1 for c in found):continue
        found.append({'center_pt':center,'radius_pt':radius,'symbol_diameter_at_plan_scale_inches':diameter_inches,
            'circularity':4*math.pi*area/perimeter**2,'render_zoom':zoom,
            'contour_sha256':hashlib.sha256(contour.tobytes()).hexdigest()})
    return found[0] if len(found)==1 else None


def apply(rooms,document):
    result=copy.deepcopy(rooms);evidence=[]
    labels={page:water_heater_labels(document[page-1]) for page in {r['page'] for r in result['regions']}}
    stale={d['region_id'] for d in result.get('room_use_review',{}).get('unresolved_decisions',[])}
    for region in result['regions']:
        old=region.get('room_use_inference',{})
        if region.get('room_use_confirmed') or region['id'] in stale or region.get('boundary_source_issues') or region['printed_labels'] or old.get('room_use'):continue
        shape=Polygon(region['points'],region['holes']);scale=region['points_per_foot']
        if not 0<shape.area/scale**2<=60 or max(shape.bounds[2]-shape.bounds[0],shape.bounds[3]-shape.bounds[1])/scale>10:continue
        contained=[l for l in labels[region['page']] if shape.covers(box(*l['bounds_pt']))]
        if len(contained)!=1:continue
        links=[c for c in result['opening_connections'] if any(s.get('region_id')==region['id'] for s in c['sides'])]
        if len(links)!=1 or links[0]['status']!='two_region_boundaries':continue
        body=circular_body(document[region['page']-1],region,contained[0])
        if body is None:continue
        source={'region_source_sha256':binding(result['plan_sha256'],region),'label':contained[0],
            'body':body,'connection':links[0],'plan_sha256':result['plan_sha256']}
        source['source_sha256']=hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()
        candidate={'region_id':region['id'],'room_use':'utility','status':'equipment_symbol_inference',
            'source_sha256':binding(result['plan_sha256'],region),'equipment_evidence':source,
            'basis':'WH-labelled circular tank symbol in a small otherwise unnamed enclosure with one interior connection; utility use is an estimating assumption, not confirmation of exclusive room use.',
            'requires_review':True,'certified':False,'owner_approved':False}
        region['room_use_inference']=candidate;evidence.append(candidate)
    if evidence:
        replacements={c['region_id']:c for c in evidence}
        if 'room_use_candidates' in result:
            result['room_use_candidates']['candidates']=[replacements.get(c['region_id'],c) for c in result['room_use_candidates']['candidates']]
            result['room_use_candidates']['automatic_candidate_count']=sum(c.get('room_use') is not None for c in result['room_use_candidates']['candidates'])
        result['equipment_room_candidates']={'candidates':evidence,'equipment_quantity_released':False,'complete_room_interpretation':False}
        result['source_sha256']=hashlib.sha256(json.dumps([rooms['source_sha256'],evidence],sort_keys=True,allow_nan=False).encode()).hexdigest()
    return result
