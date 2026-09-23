"""Persist company practice defaults into each new job without copying job actuals."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

DEFAULT_PROFILE = Path(__file__).resolve().parents[1] / 'company/jnj_profile.json'

def scope_allowances(settings, provenance):
    allowances=[]
    key = 'plumbing.exterior_hose_bibbs'
    if key in settings:
        count = settings[key]
        if type(count) is not int or count < 0:
            raise ValueError('Exterior hose-bibb allowance must be a nonnegative whole count')
        allowances.append({'id':'exterior-hose-bibbs','label':'Exterior hose bibbs',
             'quantity':count,'unit':'EA','quantity_scope':'project','source_rule':key,'provenance':provenance.get(key),
             'basis':'Company estimating allowance or explicit project override; not a count of plan symbols',
             'locations':[],'locations_reviewed':False,'measured_from_plan':False,
             'current_price':None,'remaining':'Confirm locations and reconcile any project-specific count; include in plumbing scope once'})
    key='framing.attic_HVAC_walkway_and_platform'
    if settings.get(key)=='include_in_framing_scope':
        allowances.append({'id':'attic-hvac-walkway-platform','label':'Attic HVAC walkway and equipment platform',
            'quantity':None,'unit':'SF','quantity_scope':'project','source_rule':key,'provenance':provenance.get(key),
            'basis':'Saved company scope practice for attic HVAC; no walkway or platform dimensions assumed',
            'locations':[],'locations_reviewed':False,'measured_from_plan':False,'current_price':None,
            'remaining':'Locate attic access and HVAC equipment; measure walkway and platform separately, determine supports/materials, and include installation in framing once'})
    return allowances


def resolve(profile, facts=None, project_overrides=None):
    facts = facts or {}
    project_overrides = project_overrides or {}
    boolean_facts={key for rule in profile['rules'] for key,value in rule.get('when',{}).items()
                   if type(value) is bool}
    for key in sorted(boolean_facts):
        if facts.get(key) is not None and type(facts[key]) is not bool:
            raise ValueError(f'Plan fact {key} must be true, false or null (unresolved); do not infer it from text or numbers')
    if facts.get('concrete_slab') is False:
        for key in ('backfilled_slab','thickened_slab_edge','interior_slab'):
            if facts.get(key) is True:
                raise ValueError(f'Plan facts conflict: {key}=true requires a concrete slab; resolve concrete_slab=false')
    settings, provenance, conflicts, missing_facts = {}, {}, [], set()
    for rule in profile['rules']:
        key = rule['key']
        if key in project_overrides:
            continue
        conditions = rule.get('when', {})
        if any(facts.get(k) is not None and facts[k] != v for k, v in conditions.items()):
            continue
        missing = {k for k in conditions if facts.get(k) is None}
        if missing:
            missing_facts.update(missing)
            continue
        settings[key] = copy.deepcopy(rule['value'])
        provenance[key] = {'basis': 'company_default', 'profile_version': profile['version'], 'source': rule['source']}
    for key, value in project_overrides.items():
        default = next((r for r in profile['rules'] if r['key'] == key), None)
        if default and default['value'] != value:
            conflicts.append({'key': key, 'company_default': copy.deepcopy(default['value']), 'project_value': copy.deepcopy(value), 'resolution': 'Project specification takes precedence'})
        settings[key] = copy.deepcopy(value)
        provenance[key] = {'basis': 'project_override'}
    return {'settings': settings, 'provenance': provenance, 'resolved_conflicts': conflicts,
            'unlocated_scope_allowances':scope_allowances(settings, provenance),
            'facts_to_extract_from_plan': sorted(missing_facts), 'current_prices': {},
            'quantity_measurements': {}, 'structural_approval': False,
            'status': 'Defaults initialized; plan extraction, measurements and pricing not yet complete'}

def initialize(plan, job_dir, profile_path=DEFAULT_PROFILE, facts=None, project_overrides=None):
    plan, job_dir, profile_path = Path(plan), Path(job_dir), Path(profile_path)
    plan_bytes = plan.read_bytes()
    if not plan_bytes.startswith(b'%PDF-'):
        raise ValueError('Plan must be a PDF')
    target = job_dir / 'estimate_intake.json'
    snapshot = job_dir / 'company_profile_snapshot.json'
    if target.exists() or snapshot.exists():
        raise FileExistsError('Existing intake preserved; do not overwrite job decisions')
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    result = resolve(profile, facts, project_overrides)
    result.update(plan_file=str(plan.resolve()), plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
                  company_profile_id=profile['profile_id'], company_profile_version=profile['version'],
                  company_profile_sha256=hashlib.sha256(profile_bytes).hexdigest(),
                  company_profile_snapshot=snapshot.name,
                  project_facts=facts or {}, project_overrides=project_overrides or {})
    job_dir.mkdir(parents=True, exist_ok=True)
    with snapshot.open('xb') as saved:
        saved.write(profile_bytes)
    with target.open('x',encoding='utf-8') as saved:
        saved.write(json.dumps(result, indent=2)+'\n')
    return target

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--job-dir', required=True)
    parser.add_argument('--profile', default=str(DEFAULT_PROFILE))
    parser.add_argument('--project-inputs', help='JSON containing facts and project_overrides')
    args = parser.parse_args(argv)
    inputs = json.loads(Path(args.project_inputs).read_text(encoding='utf-8')) if args.project_inputs else {}
    path = initialize(args.plan, args.job_dir, args.profile, inputs.get('facts'), inputs.get('project_overrides'))
    print(json.dumps({'intake': str(path), 'profile_loaded': True, 'estimate_complete': False}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
