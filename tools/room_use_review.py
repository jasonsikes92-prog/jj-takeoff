"""Keep room-use interpretations tied to the plan and current region geometry."""
import copy
import hashlib
import json
from pathlib import Path


def binding(plan_sha256,region):
    fields=('id','page','points_per_foot','points','holes','printed_labels')
    if region.get('boundary_source_issues'):fields+=('boundary_source_issues',)
    return hashlib.sha256(json.dumps({'plan_sha256':plan_sha256,
        'region':{k:region[k] for k in fields}},sort_keys=True,allow_nan=False).encode()).hexdigest()


def apply(result,review):
    output=copy.deepcopy(result)
    if review is None:return output
    if review.get('plan_sha256')!=result['plan_sha256']:raise ValueError('Room uses belong to another drawing')
    if not isinstance(review.get('reviewer'),str) or not review['reviewer'].strip():raise ValueError('Room-use reviewer required')
    decisions=review.get('decisions')
    if not isinstance(decisions,list):raise ValueError('Room-use decisions required')
    known={r['id']:r for r in output['regions']};seen=set();unresolved=[]
    for decision in decisions:
        identity=decision.get('region_id')
        if not isinstance(identity,str) or not identity or identity in seen:raise ValueError('Room-use decisions require unique region IDs')
        seen.add(identity)
        if any(not isinstance(decision.get(k),str) or not decision[k].strip() for k in ('room_use','name','basis')):
            raise ValueError('Room use, name and source basis required')
        region=known.get(identity)
        if region is None or decision.get('source_sha256')!=binding(result['plan_sha256'],region):
            unresolved.append({'region_id':identity,'reason':'Region geometry or printed labels changed or region is missing'});continue
        region['room_use_confirmed']=True
        region['association_review']='Room use reviewed from source; finish limits and material selections remain unconfirmed'
        region['room_use_review']={'room_use':decision['room_use'],'name':decision['name'],
            'basis':decision['basis'],'reviewer':review['reviewer'],'source_sha256':decision['source_sha256'],
            'status':'current_source_review','owner_approved':False}
    digest=hashlib.sha256(json.dumps(review,sort_keys=True,allow_nan=False).encode()).hexdigest()
    output['room_use_review']={'review_sha256':digest,'unresolved_decisions':unresolved,
        'unreviewed_region_ids':[r['id'] for r in output['regions'] if not r['room_use_confirmed']],
        'finish_coverage_confirmed':False}
    output['source_sha256']=hashlib.sha256(json.dumps([result['source_sha256'],digest]).encode()).hexdigest()
    return output


def read_review(folder):
    path=Path(folder)/'room_use_review.json'
    return json.loads(path.read_bytes()) if path.exists() else None
