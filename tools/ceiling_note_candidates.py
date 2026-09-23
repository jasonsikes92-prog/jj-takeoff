"""Locate explicit ceiling notes without inferring unshown surface extents."""
import copy
import hashlib
import json
import re
from shapely.geometry import Polygon,box

HEIGHT=re.compile(r'''(\d+)'\s*-\s*(\d+(?:\.\d+)?)"\s*CLG\.?''')
PITCH=re.compile(r'(\d+(?:\.\d+)?)\s*/\s*12\s+VAULT')


def page_notes(page):
    notes=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            raw=''.join(s['text'] for s in line['spans']).strip();normalized=' '.join(raw.upper().split())
            height=HEIGHT.fullmatch(normalized);pitch=PITCH.fullmatch(normalized);data=None
            if height:
                feet,inches=map(float,height.groups())
                if inches<12 and feet*12+inches>0:data={'kind':'ceiling_height','height_inches':feet*12+inches}
            elif pitch and float(pitch[1])>0:data={'kind':'vault_pitch','rise_inches':float(pitch[1]),'run_inches':12}
            elif normalized=='VAULTED':data={'kind':'vaulted'}
            if data is None:continue
            bounds=list(line['bbox']);identity=hashlib.sha256(json.dumps([page.number+1,raw,bounds]).encode()).hexdigest()[:16]
            notes.append({'id':'ceiling-note-'+identity,'page':page.number+1,'text':raw,'bounds_pt':bounds,**data})
    return notes


def attach(result,notes):
    output=copy.deepcopy(result);regions=output['regions'];unresolved=[]
    for region in regions:region['ceiling_notes']=[]
    shapes={r['id']:Polygon(r['points'],r['holes']) for r in regions}
    for note in notes:
        matched=[r for r in regions if r['page']==note['page'] and shapes[r['id']].covers(box(*note['bounds_pt']))]
        if len(matched)==1:matched[0]['ceiling_notes'].append(copy.deepcopy(note))
        else:unresolved.append({**note,'candidate_region_ids':[r['id'] for r in matched],
            'reason':'Ceiling note has no unique containing region; no nearest-room assignment'})
    for region in regions:
        found=region['ceiling_notes'];heights={n['height_inches'] for n in found if n['kind']=='ceiling_height'}
        pitches={(n['rise_inches'],n['run_inches']) for n in found if n['kind']=='vault_pitch'}
        vaulted=any(n['kind'] in ('vaulted','vault_pitch') for n in found)
        conflict=len(heights)>1 or len(pitches)>1
        region['ceiling_reference']={'status':'conflicting_notes' if conflict else 'vault_extent_review_required' if vaulted
            else 'height_note_only' if heights else 'no_explicit_ceiling_note',
            'noted_height_inches':next(iter(heights)) if len(heights)==1 else None,
            'noted_pitch':dict(zip(('rise_inches','run_inches'),next(iter(pitches)))) if len(pitches)==1 else None,
            'surface_area_sf':None,'purchase_quantity':None,
            'basis':'Located printed notes only; height may be a spring/eave height, and a vault note does not establish its full footprint'}
    output['ceiling_note_review']={'unresolved_notes':unresolved,'whole_ceiling_surface_sf':None,
        'coverage_confirmed':False}
    output['source_sha256']=hashlib.sha256(json.dumps([result['source_sha256'],notes],sort_keys=True,allow_nan=False).encode()).hexdigest()
    return output
