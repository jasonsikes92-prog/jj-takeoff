"""Run reviewed floor levels separately and retain one shared-building scope."""
import argparse
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from plan_sheet_review import read_sheet_review
from new_plan_measure import measure_job

BASE_FILES=('plan.pdf','estimate_intake.json','company_profile_snapshot.json','plan_inventory.json',
            'official_requirements_snapshot.json','local_requirements.json',
            'door_core_specifications.json','door_hardware_specifications.json')


def project_allowances(scopes):
    """Deduplicate explicit project allowances; never add their per-floor copies."""
    unique={};origins={};unresolved=[]
    for scope in scopes:
        for item in scope['summary'].get('unlocated_scope_allowances',[]):
            if item.get('quantity_scope')!='project':
                unresolved.append({'source_scope':scope['id'],'allowance':copy.deepcopy(item)})
                continue
            identity=item['id']
            if identity in unique and unique[identity]!=item:
                raise ValueError('Conflicting project allowance across levels: '+identity)
            unique[identity]=copy.deepcopy(item)
            origins.setdefault(identity,[]).append(scope['id'])
    return {'items':[{**item,'source_scopes':origins[key]} for key,item in unique.items()],
            'unresolved_scope_items':unresolved,'included_in_estimate_total':False}


def run(job):
    job=Path(job).resolve();target=job/'level_takeoffs'
    if target.exists():raise FileExistsError('Existing level takeoffs preserved; create a new revision')
    routing=read_sheet_review(job);raw=(job/'multilevel_review.json').read_bytes();config=json.loads(raw)
    if (config['plan_sha256']!=routing['plan_sha256'] or config['sheet_review_sha256']!=routing['review_sha256']
            or routing['unexamined_pages'] or not routing['coverage_passed']):
        raise ValueError('Multi-level routing requires its current complete sheet review')
    levels=config['levels'];ids=[level['id'] for level in levels];pages=[level['page'] for level in levels]
    expected=routing['role_candidates'].get('floor',[])
    if (len(levels)<2 or len(ids)!=len(set(ids)) or len(pages)!=len(set(pages))
            or sorted(pages)!=sorted(expected) or any(type(p) is not int for p in pages)
            or any(not isinstance(i,str) or not re.fullmatch('[a-z][a-z0-9_-]{0,47}',i) or i=='shared' for i in ids)):
        raise ValueError('Assign every reviewed floor-plan page to one distinct safe level ID')
    parent_review=json.loads((job/'sheet_review.json').read_bytes())
    sources={str(job/name):hashlib.sha256((job/name).read_bytes()).hexdigest() for name in BASE_FILES if (job/name).is_file()}
    sources[str(job/'sheet_review.json')]=routing['review_sha256']
    sources[str(job/'multilevel_review.json')]=hashlib.sha256(raw).hexdigest()
    for page in parent_review['pages']:
        sources[str((job/page['view']).resolve())]=page['view_sha256']
    shared={k:v for k,v in routing['unique_role_pages'].items() if k!='floor'}
    scopes=[(level['id'],{'floor':level['page']},level) for level in levels]
    if shared:scopes.append(('shared',shared,None))
    scope_files=config.get('scope_files',{})
    permitted={'floor_wall_view_review.json':'floor','roof_view_review.json':'roof',
               'roof_dormer_pitch_review.json':'roof','roof_coverage_review.json':'roof'}
    scoped_sources={}
    roles_by_scope={identity:roles for identity,roles,_ in scopes}
    for identity,files in scope_files.items():
        if identity not in roles_by_scope:raise ValueError('Unknown scope for reviewed input')
        scoped_sources[identity]={}
        for name,evidence in files.items():
            if name not in permitted or permitted[name] not in roles_by_scope[identity]:
                raise ValueError('Reviewed input does not belong to this scope')
            source=(job/evidence['file']).resolve()
            if not source.is_relative_to(job):raise ValueError('Reviewed input must stay within this job')
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            if digest!=evidence['sha256']:raise ValueError('Reviewed scope input changed')
            sources[str(source)]=digest;scoped_sources[identity][name]=source
    # Keep stable child paths. Each child publishes atomically; the combined
    # manifest is written only after every child and parent-source check passes.
    attempt=target;attempt.mkdir()
    summaries=[];combined=[]
    for identity,roles,level in scopes:
        child=attempt/identity;child.mkdir()
        for name in BASE_FILES:
            if (job/name).is_file():shutil.copyfile(job/name,child/name)
        for name,source in scoped_sources.get(identity,{}).items():
            shutil.copyfile(source,child/name)
        review=copy.deepcopy(parent_review)
        for page in review['pages']:
            source=(job/page['view']).resolve()
            page['view']=f"sheet_views/page-{page['page']:02d}.png"
            destination=child/page['view'];destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
        subset={'role_pages':roles,'basis':'Explicit multi-level partition; other scopes are retained in sibling jobs.',
                'missing_roles':routing['missing_roles'],'unresolved_issues':review['unresolved_issues']}
        if level is not None:
            subset['floor_level']={'id':identity,'page':level['page'],'other_floor_pages':[p for p in expected if p!=level['page']]}
        review['partial_measurement_review']=subset
        (child/'sheet_review.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
        summary=measure_job(child)
        measurement_path=child/'draft_takeoff/measurements.json'
        if measurement_path.exists():
            for measurement in json.loads(measurement_path.read_bytes())['measurements']:
                if measurement['page'] not in roles.values():raise ValueError('Child measurement escaped its assigned pages')
                combined.append({**measurement,'id':identity+':'+measurement['id'],
                    'source_scope':identity,'source_measurement_id':measurement['id']})
        summaries.append({'id':identity,'role_pages':roles,'summary':summary,
                          'job_relative_path':identity,'estimate_rows_are_not_additive':True})
    for path,digest in sources.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Parent sources changed during multi-level extraction')
    report={'plan_sha256':routing['plan_sha256'],'source_files':sources,'scopes':summaries,
        'project_allowances':project_allowances(summaries),
        'floor_pages_assigned_once':pages,'shared_scope_count':int(bool(shared)),
        'candidate_measurement_count':len(combined),'whole_house_total':None,'estimate_released':False,
        'limitations':['Do not sum child estimate rows or company allowances; they repeat the template.',
            'Combined measurements are unclassified candidates; scale, scope and quantities still require review.',
            'Multi-view pages and repeated alternative floor drawings need explicit view routing, not invented level quantities.']}
    (attempt/'combined_measurements.json').write_text(json.dumps({'plan_sha256':routing['plan_sha256'],
        'measurements':combined,'certified':False},indent=2)+'\n',encoding='utf-8')
    (attempt/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',required=True)
    report=run(parser.parse_args().job)
    print(json.dumps({'scopes':[s['id'] for s in report['scopes']],
        'candidate_measurements':report['candidate_measurement_count'],'estimate_released':False}))
