"""Represent a complex roof face using editable gross and deduction outlines.

These are review candidates. Dormer roof surfaces must be measured separately.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from area_cutouts import cutout_issues
from measurement_store import calculate


def component_candidates(face,points_per_foot,width_pt,height_pt):
    holes=face.get('holes')
    if not isinstance(holes,list) or not holes:raise ValueError('Complex roof face needs interior rings')
    rise=face['pitch_candidate']['rise']
    if type(rise) not in (int,float) or not math.isfinite(rise) or not 0<rise<=24:
        raise ValueError('Complex roof face needs a valid pitch candidate')
    source={key:face[key] for key in ('page','points','holes','pitch_candidate','source_cad_paths')}
    if 'pitch_candidates' in face:source['pitch_candidates']=face['pitch_candidates']
    digest=hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()
    parent='roof-gross-'+digest[:16];measurements=[];terms=[]
    for index,points in enumerate([face['points'],*holes]):
        identity=parent if index==0 else 'roof-cutout-'+digest[:16]+'-'+str(index)
        measurement={'id':identity,'label':('Roof outer outline '+face['pitch_candidate']['text'] if index==0
            else 'Roof cutout '+str(index)+' from '+face['pitch_candidate']['text']),
            'page':face['page'],'kind':'area','points':points,'points_per_foot':points_per_foot,
            'width_pt':width_pt,'height_pt':height_pt,'surface_factor':math.hypot(12,rise)/12,
            'color':['#f97316','#db2777','#2563eb'][index%3],'dependent_rows':[],
            'source_method':'complex roof face as gross outline and separate cutout candidates',
            'source_complex_face_sha256':digest,'source_cad_paths':face['source_cad_paths'],
            'engine_line_ids':[identity],'scope_status':'Verify roof exclusions; dormer surfaces and complete coverage remain unresolved'}
        if index==0 and 'pitch_candidates' in face:
            measurement['pitch_candidates']=face['pitch_candidates']
        calculate(measurement);measurements.append(measurement)
        terms.append({'id':identity,'measurement_id':identity,'kind':'area',
            'operation':'add' if index==0 else 'deduct',**({'cutout_of':parent} if index else {})})
    issues=cutout_issues({m['id']:m for m in measurements},terms)
    if issues:raise ValueError('Invalid complex roof geometry: '+issues[0]['reason'])
    return {'measurements':measurements,'surface_components':terms,'source_complex_face_sha256':digest,
        'scope_certified':False,'remaining':['Verify that each ring is excluded from this roof plane.',
            'Measure the dormer roof surfaces separately; do not copy the main roof pitch to them.',
            'Verify complete roof coverage before pricing or ordering.']}
