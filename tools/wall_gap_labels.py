"""Locate printed opening-tag candidates beside current wall gaps."""
import hashlib
import re
from pathlib import Path
import fitz
from wall_run_candidates import from_state,WALL_METHOD
from wall_short_piece_directions import propose
from wall_gap_obstructions import screen
from wall_alignment_breaks import apply_review as alignment_sections

METHOD='wall_gap_printed_tag_candidates_v3'


def page_labels(page):
    labels=[]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            text=''.join(span['text'] for span in line['spans']).strip()
            if not re.fullmatch(r'\d{4,5}(?:[A-Z]+)?',text):continue
            direction=line['dir']
            axis='horizontal' if abs(direction[0])>.99 else 'vertical' if abs(direction[1])>.99 else None
            bounds=list(line['bbox'])
            identity=f'{page.number+1}:{text}:{bounds}'
            labels.append({'id':'printed-tag-'+hashlib.sha256(identity.encode()).hexdigest()[:16],
                'page':page.number+1,'text':text,'bbox_pt':bounds,'axis':axis,'direction':list(direction)})
    return sorted({label['id']:label for label in labels}.values(),key=lambda label:label['id'])


def match_labels(runs,labels,obstruction_review=None):
    gaps=[];uses={label['id']:[] for label in labels}
    for run in runs['run_candidates']:
        horizontal=run['axis']=='horizontal'
        low,high=run['centerline_coordinate_range_pt']
        tolerance=run['points_per_foot']*3/12
        for index,gap in enumerate(run['gaps']):
            matches=[]
            for label in labels:
                if label['page']!=run['page'] or label['axis']!=run['axis']:continue
                x0,y0,x1,y1=label['bbox_pt']
                along,across=((x0+x1)/2,(y0+y1)/2) if horizontal else ((y0+y1)/2,(x0+x1)/2)
                if low-tolerance<=across<=high+tolerance and gap['from_pt']<along<gap['to_pt']:
                    matches.append(label['id'])
            identity=f"{run['id']}:gap-{index+1}"
            obstructions=obstruction_review['obstructions_by_gap'].get(identity,[]) if obstruction_review else []
            junctions=obstruction_review.get('junctions_by_gap',{}).get(identity,[]) if obstruction_review else []
            if not obstructions and not junctions:
                for label_id in matches:uses[label_id].append(identity)
            gaps.append({'id':identity,'run_id':run['id'],'page':run['page'],'axis':run['axis'],
                'from_pt':gap['from_pt'],'to_pt':gap['to_pt'],'drawn_gap_lf':gap['length_lf'],
                'candidate_label_ids':sorted(matches),'obstructions':obstructions,'junction_contacts':junctions})
    for gap in gaps:
        matches=gap['candidate_label_ids']
        gap['status']=('drawn_piece_obstructs_gap' if gap['obstructions'] else
            'junction_tag_conflict' if gap['junction_contacts'] and matches else
            'wall_junction_candidate' if gap['junction_contacts'] else 'no_aligned_tag' if not matches else 'multiple_tags_require_review' if len(matches)>1
            else 'tag_shared_by_multiple_gaps' if len(uses[matches[0]])>1 else 'unique_tag_location_candidate')
    return {'method':METHOD,'plan_sha256':runs['plan_sha256'],
        'measurement_version':runs['measurement_version'],'measurement_inputs_sha256':runs['measurement_inputs_sha256'],
        'classification_review_sha256':runs.get('classification_review_sha256'),
        'wall_run_method':runs['method'],'maximum_tag_offset_inches':3,'gaps':gaps,'labels':labels,
        'unmatched_label_ids':sorted(key for key,value in uses.items() if not value),
        'shared_label_ids':sorted(key for key,value in uses.items() if len(value)>1),
        'obstruction_review':obstruction_review,
        'certified':False,'purchase_quantity':None,
        'limitations':['Numeric tag syntax and proximity do not prove an opening type or manufacturer rough opening.',
            'Unlabeled gaps may be wall intersections, fireplaces, openings or disconnected wall scope.',
            'Perpendicular wall-end contacts are junction candidates, not approved backing assemblies or added wall length.',
            'Short-piece direction and wall classification remain unresolved; no nominal-size convention is assumed.',
            'Gap IDs are local to this measurement revision; reconcile changed geometry before reusing a review.']}


def from_plan_state(plan,state,classification_review=None,alignment_review=None):
    from wall_gap_continuity import apply_from_plan
    plan=Path(plan)
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:
        raise ValueError('Wall gap labels require the measurement source drawing')
    runs=from_state(state,classification_review)
    from diagonal_wall_analysis import from_state as diagonal_analysis
    from wall_classification_review import STROKE_METHODS
    pages=sorted({m['page'] for m in state['measurements'].values() if m.get('source_method') in (WALL_METHOD,*STROKE_METHODS)}
        | {r['page'] for r in runs['run_candidates']})
    with fitz.open(plan) as doc:
        labels=[label for page in pages for label in page_labels(doc[page-1])]
    if hashlib.sha256(plan.read_bytes()).hexdigest()!=state['plan_sha256']:
        raise ValueError('Source drawing changed during label extraction')
    result=match_labels(runs,labels,screen(runs,state))
    result['alignment_review']=alignment_sections(state,runs,result,alignment_review)
    apply_from_plan(plan,state,runs,result)
    directions,projected=propose(state,labels)
    assisted_runs=from_state(projected,classification_review)
    assisted=match_labels(assisted_runs,labels,screen(assisted_runs,state))
    assisted['alignment_review']=alignment_sections(projected,assisted_runs,assisted,alignment_review)
    apply_from_plan(plan,projected,assisted_runs,assisted)
    assisted['projected_measurement_inputs_sha256']=assisted['measurement_inputs_sha256']
    assisted['measurement_inputs_sha256']=runs['measurement_inputs_sha256']
    assisted['run_candidates']=assisted_runs['run_candidates']
    assisted['direction_method']=directions['method']
    assisted['status']='Direction-assisted candidates; source outlines are unchanged and not certified'
    result['short_piece_directions']=directions
    result['direction_assisted']=assisted
    result['diagonal_analysis']=diagonal_analysis(state,labels,classification_review)
    return result
