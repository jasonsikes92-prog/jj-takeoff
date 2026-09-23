"""Create live hardware purchase mappings from a job-specific supply review."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from estimate_export_snapshot import verify_snapshot
from kit_purchase_review import import_kit_purchases

FUNCTIONS={'privacy':'Privacy knob sets','passage':'Passage knob sets',
           'pocket-privacy':'Privacy pocket sets','pocket-passage':'Passage pocket sets'}

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

def checked_reference(folder,reference):
    path=(folder/reference['file']).resolve()
    if not path.is_relative_to(folder) or not path.is_file():raise ValueError('Supply evidence must be inside the job')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('Supply evidence changed')
    return path,raw

def prepare(folder,snapshot,review_file):
    """Write quantity-free mappings. The live engine supplies counts and markups."""
    folder=Path(folder).resolve();review_path=Path(review_file).resolve()
    if not review_path.is_relative_to(folder):raise ValueError('Supply review must be inside the job')
    review_raw=review_path.read_bytes();review=json.loads(review_raw)
    draft=verify_snapshot(snapshot)['draft'];hardware=draft.get('hardware_quantity_review')
    if not hardware:raise ValueError('Current hardware quantity review is required')
    if (hashlib.sha256((folder/'plan.pdf').read_bytes()).hexdigest()!=draft['plan_sha256']
            or hashlib.sha256((folder/'template_rows.json').read_bytes()).hexdigest()!=draft.get('template_sha256')):
        raise ValueError('Hardware snapshot belongs to another plan or template')
    if (review.get('plan_sha256')!=draft['plan_sha256']
            or review.get('hardware_review_sha256')!=digest(hardware)):
        raise ValueError('Supply review belongs to different hardware scope')
    if (review.get('applies_to')!='hardware_function_supply'
            or any(not isinstance(review.get(k),str) or not review[k].strip() for k in ('reviewer','basis'))):
        raise ValueError('Explicit function-supply review and basis required')
    dependencies=[{'file':str(review_path.relative_to(folder)),'sha256':hashlib.sha256(review_raw).hexdigest()}]
    evidence=review.get('source_files')
    if not isinstance(evidence,list) or not evidence:raise ValueError('Supply review needs original source evidence')
    dependency_bytes={review_path:review_raw}
    for reference in evidence:
        path,raw=checked_reference(folder,reference);dependency_bytes[path]=raw;dependencies.append(reference)
    target=next(r for r in draft['rows'] if r['row_id']==hardware['target_row_id'])
    parents=[r for r in draft['rows'] if r['name']==target['parent'] and r['cost_type'] in ('GROUP','ASSEMBLY')]
    if len(parents)!=1:raise ValueError('Hardware needs one matching template parent')
    groups={g['id']:g for g in hardware['groups']}
    expected={'opening-hardware-'+key for key in FUNCTIONS}
    if set(groups)!=expected or len(hardware['groups'])!=4:raise ValueError('Hardware function groups are missing or duplicated')
    items=review.get('items',[])
    if (not isinstance(items,list) or any(not isinstance(i,dict) for i in items)
            or len({i.get('input_id') for i in items})!=len(items)
            or any(i.get('input_id') not in groups or i.get('supply_status') not in ('separate','included','unknown') for i in items)):
        raise ValueError('Supply review has duplicate, unknown or invalid function decisions')
    decisions={i['input_id']:i for i in items}
    config_path=(folder/'kit_purchase_review.json').resolve()
    if not config_path.is_relative_to(folder):raise ValueError('Purchase mapping must stay inside the job')
    prior=config_path.read_bytes() if config_path.exists() else None
    config=json.loads(prior) if prior is not None else {'plan_sha256':draft['plan_sha256'],'purchases':[]}
    if config['plan_sha256']!=draft['plan_sha256']:raise ValueError('Existing purchase mapping belongs to another plan')
    assigned=set()
    for reference in config['purchases']:
        _,raw=checked_reference(folder,reference);existing=json.loads(raw)
        if existing.get('replaces_row_id')==target['row_id']:assigned.add(existing.get('assembly_input_id'))
    proposed=[];unresolved=[]
    for function,label in FUNCTIONS.items():
        identity='opening-hardware-'+function;decision=decisions.get(identity,{'supply_status':'unknown'})
        status=decision['supply_status']
        if status!='separate':
            unresolved.append({'input_id':identity,'supply_status':status,
                'reason':'No separate charge; verify the included package owner' if status=='included' else 'Supplier inclusion unresolved; no separate charge assigned'})
            continue
        if identity in assigned or identity in target.get('assembly_input_cost_owners',{}):raise ValueError('Hardware function already has a purchase owner')
        purchase={'plan_sha256':draft['plan_sha256'],'row_id':'JJ-HARDWARE-'+function.upper(),
            'ownership':'assembly_input','replaces_row_id':target['row_id'],'parent_row_id':parents[0]['row_id'],
            'name':label,'unit':'each','assembly_input_id':identity,'product_status':'specification_pending',
            'source':dependencies[0],'evidence_files':dependencies,'supply_status':'separate',
            'basis':'One complete set per live reviewed single-leaf opening. Separate supply by function: '+review['basis'],
            'remaining':['Product, fit, delivered price and installation ownership remain unresolved.',
                'Full-plan coverage and supplier scope remain subject to review. No prior-job quantities or prices are copied.']}
        path=(folder/'scope_evidence'/('automatic_hardware_'+function+'.json')).resolve()
        if not path.is_relative_to(folder):raise ValueError('Purchase evidence must stay inside the job')
        if path.exists():raise FileExistsError('Existing hardware purchase evidence preserved')
        raw=(json.dumps(purchase,indent=2)+'\n').encode()
        reference={'file':str(path.relative_to(folder)),'sha256':hashlib.sha256(raw).hexdigest()}
        config['purchases'].append(reference);proposed.append((path,raw,reference))
    if not proposed:return {'created':[],'unresolved':unresolved,'prices_copied':False}
    # Verify all evidence again before writing, then validate the candidate through the production importer.
    for path,raw in dependency_bytes.items():
        if path.read_bytes()!=raw:raise ValueError('Supply evidence changed during setup')
    written=[]
    try:
        for path,raw,_ in proposed:
            path.parent.mkdir(exist_ok=True)
            with path.open('xb') as stream:stream.write(raw)
            written.append(path)
        import_kit_purchases(draft,{'plan_sha256':draft['plan_sha256'],'purchases':[r for _,_,r in proposed]},folder)
        if (config_path.read_bytes() if config_path.exists() else None)!=prior:raise ValueError('Purchase mapping changed during setup')
        config_path.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    except Exception:
        for path in written:path.unlink()
        raise
    return {'created':[str(p.relative_to(folder)) for p in written],'unresolved':unresolved,
        'counts_source':'Live opening hardware review','prices_copied':False,'restart_review_server':True}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-dir',required=True);parser.add_argument('--snapshot',required=True)
    parser.add_argument('--scope-review',required=True)
    args=parser.parse_args(argv)
    result=prepare(args.job_dir,json.loads(Path(args.snapshot).read_bytes()),args.scope_review)
    print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
