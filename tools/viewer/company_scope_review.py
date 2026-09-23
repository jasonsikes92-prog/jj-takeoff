"""Carry frozen company scope into new-job assembly inputs without pricing it."""
import copy
import hashlib
import json
from pathlib import Path
from company_profile import resolve,scope_allowances
from company_scope_bids import TILE_RULES,FOUNDATION_RULES

TARGETS={
    'exterior-hose-bibbs':('Count Each Water Opening','Plumbing','SUBCONTRACTOR'),
    'attic-hvac-walkway-platform':('Framing Lumber','Framing','MATERIAL'),
}

def read_decisions(folder,config,plan_sha256):
    folder=Path(folder).resolve()
    path=(folder/config['intake_path']).resolve()
    if path!=folder.parent/'estimate_intake.json':
        raise ValueError('Company scope must use its own parent job intake')
    raw=path.read_bytes();intake=json.loads(raw)
    if hashlib.sha256(raw).hexdigest()!=config['intake_sha256']:
        raise ValueError('Company scope intake changed; review its mapping')
    if intake['plan_sha256']!=plan_sha256 or config['plan_sha256']!=plan_sha256:
        raise ValueError('Company scope belongs to another drawing')
    profile_path=(path.parent/intake['company_profile_snapshot']).resolve()
    if not profile_path.is_relative_to(path.parent):raise ValueError('Company profile must stay inside its job')
    profile_raw=profile_path.read_bytes();profile=json.loads(profile_raw)
    if hashlib.sha256(profile_raw).hexdigest()!=intake['company_profile_sha256']:
        raise ValueError('Frozen company profile changed')
    if (profile['profile_id'],profile['version'])!=(intake['company_profile_id'],intake['company_profile_version']):
        raise ValueError('Company profile identity differs from intake')
    replay=resolve(profile,intake['project_facts'],intake['project_overrides'])
    if any(replay[k]!=intake[k] for k in ('settings','provenance','resolved_conflicts')):
        raise ValueError('Company scope settings differ from frozen decisions')
    return replay

def read_scope(folder,config,plan_sha256):
    replay=read_decisions(folder,config,plan_sha256)
    return scope_allowances(replay['settings'],replay['provenance'])

def default_mapping(folder,template,plan_sha256):
    path=Path(folder).parent/'estimate_intake.json'
    if not path.exists():return None
    config={'plan_sha256':plan_sha256,'intake_path':'../estimate_intake.json',
        'intake_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mappings':[]}
    for allowance in read_scope(folder,config,plan_sha256):
        signature=TARGETS[allowance['id']]
        matches=[r for r in template['rows'] if tuple(r[k].strip() for k in ('name','parent','cost_type'))==signature]
        if len(matches)!=1:raise ValueError('Company scope template owner missing or ambiguous: '+allowance['id'])
        config['mappings'].append({'scope_id':allowance['id'],'row_id':matches[0]['row_id']})
    return config

def import_scope(draft,folder,config,state=None):
    if 'company_scope_review' in draft:raise ValueError('Company scope already imported')
    decisions=read_decisions(folder,config,draft['plan_sha256'])
    allowances={a['id']:a for a in scope_allowances(decisions['settings'],decisions['provenance'])}
    mappings=config['mappings']
    if len(mappings)!=len(allowances) or {m['scope_id'] for m in mappings}!=set(allowances):
        raise ValueError('Every company scope needs exactly one template owner')
    result=copy.deepcopy(draft)
    for mapping in mappings:
        identity=mapping['scope_id'];a=allowances[identity]
        matches=[r for r in result['rows'] if r['row_id']==mapping['row_id']]
        if len(matches)!=1:raise ValueError('Company scope target missing or ambiguous')
        row=matches[0]
        if tuple(row[k].strip() for k in ('name','parent','cost_type'))!=TARGETS[identity]:
            raise ValueError('Company scope template identity changed')
        if (row['completion_status'].startswith('not_applicable') or row.get('covered_by_package')
                or row.get('cost_owner_row_id') or any(row.get(k) is not None for k in ('draft_quantity','line_cost'))):
            raise ValueError('Company scope target is already assigned or excluded')
        if (any(q['id']==identity for r in result['rows'] for q in r.get('assembly_inputs',[]))
                or any(q['id']==identity for q in result.get('pending_quantities',[]))):
            raise ValueError('Company scope input already assigned')
        item={**copy.deepcopy(a),'use':'assembly_input','template_rows':[row['excel_row']],
            'certified':False,'remaining':[a['remaining']],
            'source_snapshot':{'intake_sha256':config['intake_sha256'],'source_rule':a['source_rule']}}
        if a['quantity'] is None:
            item['reason']=a['remaining']
            result.setdefault('pending_quantities',[]).append(item)
        else:row.setdefault('assembly_inputs',[]).append(item)
        row['certified']=False
    result['company_scope_review']={'intake_sha256':config['intake_sha256'],
        'scope_ids':list(allowances),'measured_from_plan':False,'prices_applied':False,
        'specifications':[{'source_rule':key,'value':copy.deepcopy(decisions['settings'][key]),
            'provenance':copy.deepcopy(decisions['provenance'][key]),'intake_sha256':config['intake_sha256']}
            for key in list(TILE_RULES)+list(FOUNDATION_RULES) if key in decisions['settings']],
        'unresolved_conditions':[key for key in ('attic_HVAC',) if key in decisions['facts_to_extract_from_plan']]}
    if (Path(folder)/'tile_underlayment_review.json').exists():
        from tile_underlayment_review import import_underlayment
        result=import_underlayment(result,state,folder)
    if (Path(folder)/'floor_supply_purchase_review.json').exists():
        from floor_supply_purchase_review import import_purchases
        result=import_purchases(result,folder)
    return result
