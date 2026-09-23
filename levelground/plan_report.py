"""Build a reviewer-only pre-bid draft from current shared measurement rules."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS / 'viewer'))
from measurement_store import MeasurementStore, encode
from measurement_scope_reviews import ScopeReviews
from measurement_quantities import rollup
from jnj_takeoff import report_from_takeoff
from opening_schedule import from_folder as opening_schedule
from opening_references import references as opening_references


def draft_from_workspace(workspaces, case_id, workspace_id):
    status = workspaces.read(case_id, workspace_id)
    if status['measurement_status'] != 'candidates_require_review':
        raise ValueError('A current, sheet-reviewed measurement workspace is required')
    job = workspaces.root / case_id / workspace_id
    folder = job / 'draft_takeoff'
    files = [job / name for name in ('case_workspace.json', 'sheet_review.json', 'plan_inventory.json')]
    files += [folder / name for name in ('summary.json', 'measurements.json', 'quantity_rules.json')]
    before = {path:hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    opening_files=[folder/name for name in ('opening_schedule_review.json','wall_classification_review.json','wall_alignment_breaks.json')]
    opening_before={path:hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None for path in opening_files}
    permit_files=[job/name for name in ('local_requirements.json','official_requirements_snapshot.json')]
    permit_before={path:hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None for path in permit_files}
    as_of=date.today().isoformat()
    permits=workspaces.permit_context(case_id,workspace_id,as_of)
    rules = json.loads((folder / 'quantity_rules.json').read_text())
    store = MeasurementStore(folder)
    state = store.read()
    reviews = ScopeReviews(store, rules)
    effective = reviews.effective_rules()
    quantities = rollup(state, effective)
    openings=(opening_references(opening_schedule(folder,state,include_company_policy=False))
        if opening_before[folder/'opening_schedule_review.json'] is not None else None)
    source = {'plan_sha256':status['plan_sha256'],
              'sheet_review_sha256':status['sheet_review']['review_sha256'],
              'measurement_version':state['version'],
              'measurement_state_sha256':hashlib.sha256(encode(state).encode()).hexdigest(),
              'quantity_rules_sha256':reviews.rules_sha256,
              'effective_rules_sha256':hashlib.sha256(encode(effective).encode()).hexdigest(),
              'summary_sha256':before[folder / 'summary.json'],
              'workspace_id':workspace_id, 'source_reference':status['source_reference']}
    if openings is not None:source['opening_references_sha256']=openings['source_sha256']
    source['permit_context_sha256']=hashlib.sha256(encode(permits).encode()).hexdigest()
    report = report_from_takeoff({'lines':[], 'not_measured':[]},
        {key:None for key in ('heated_sf', 'stories', 'foundation', 'garage', 'finish_level')}, {},
        property_label='Plan review: ' + status['source_filename'],
        report_id='LG-DRAFT-' + hashlib.sha256(encode(source).encode()).hexdigest()[:16],
        date=as_of)
    report['meta']['verdict_note'] = ('Reviewer draft from the selected plan workspace. Quantities below are partial '
        'draft references, not certified takeoff or purchase quantities. Full scope and a current budget remain unresolved.')
    report.update(report_status='reviewer_draft', source_workspace=source,
                  sheet_coverage_passed=status['sheet_review']['coverage_passed'],
                  complete_home_review=False, homeowner_release_approved=False,
                  measurements_certified=False, permit_compliance_verified=False, estimate_released=False)
    report['permit_review']=permits
    if permits['status']=='unbound_legacy_snapshot':
        report['unknowns'].append(permits['notice'])
    for key in permits['missing_project_fields']:
        report['unknowns'].append('Permit review needs '+key.replace('_',' ')+'.')
    for item in permits['candidates']+permits['needs_review']:
        detail=item['summary']
        if item['review_issues']:detail+=' Review needed: '+'; '.join(item['review_issues'])+'.'
        basis=item['authority']+'; checked '+item['checked_on']
        if item.get('source_page'):basis+='; source page '+str(item['source_page'])
        basis+='; '+item['source_url']
        report['findings'].append({'category':'scope_confirmation','title':'Permit review: '+item['topic'],
            'detail':detail,'confidence':'needs_confirmation','basis':basis,
            'bid_amount':None,'realistic_low':None,'realistic_high':None})
        report['unknowns'].extend(item['topic']+': '+reason for reason in item['review_issues'])
    report['questions'].append('Which permit requirements apply to this property, and who includes each required document, inspection, test and fee in the written scope?')
    mapped = set()
    if openings is not None:
        report['opening_references']={k:openings[k] for k in ('source_enumeration_current','details','open_passage_count','coverage_certified','purchase_released')}
        report['quantities'].extend(openings['quantities'])
        report['unknowns'].extend(openings['unknowns'])
        report['questions'].append('Will the written scope list each window and door assembly, its product specifications, hardware and installation inclusions?')
    for quantity in quantities['quantities']:
        ids = quantity['measurement_ids']
        mapped.update(ids)
        pages = sorted({state['measurements'][identity]['page'] for identity in ids})
        report['quantities'].append({'item':'Draft reference: ' + quantity['label'],
            'qty':round(quantity['measured_quantity'], 4), 'unit':quantity['unit'],
            'source':'Selected plan, page(s) ' + ', '.join(map(str, pages)),
            'confidence':'needs_confirmation', 'measurement_ids':ids,
            'quantity_rule_id':quantity['id'], 'measurement_version':state['version'],
            'certified':False, 'purchase_quantity':None})
        report['unknowns'].extend(quantity['label'] + ': ' + item for item in quantity['remaining'])
    for pending in quantities['pending_quantities']:
        mapped.update(pending['measurement_ids'])
        report['unknowns'].append(pending['label'] + ': ' + pending['reason'] + '; quantity withheld.')
    for identity, measurement in state['measurements'].items():
        if identity not in mapped:
            report['unknowns'].append(measurement.get('label', identity) + ': scope has not been mapped or reviewed for this report.')
    sheet = status['sheet_review']
    if not sheet['coverage_passed']:
        detail = 'The supplied drawing set has unresolved coverage; this is not a complete plan review.'
        missing = sheet['missing_roles']
        if missing:
            detail += ' Missing sheet roles: ' + ', '.join(missing) + '.'
        if sheet['unresolved_issues']:
            detail += ' ' + ' '.join(sheet['unresolved_issues'])
        report['findings'].insert(0, {'category':'scope_confirmation', 'title':'Resolve the drawing set',
            'detail':detail, 'confidence':'needs_confirmation', 'basis':'Reviewed sheet inventory for the selected uploaded plan',
            'bid_amount':None, 'realistic_low':None, 'realistic_high':None})
        report['questions'].insert(0, 'Please provide the complete current drawing set and resolve the noted missing sheets or revision conflicts.')
        report['unknowns'].insert(0, detail)
    report['unknowns'].extend([
        'The full home takeoff is incomplete. Trades without a draft reference above are not measured by this report.',
        'Property jurisdiction, site conditions and applicable permit requirements are not established by these measurements.',
        'Current budget, contractor scope, material purchasing quantities and independent accuracy validation remain unresolved.'])
    report['unknowns'] = list(dict.fromkeys(report['unknowns']))
    # A draft is one source snapshot, never a mix of revisions observed mid-read.
    if (any(hashlib.sha256(path.read_bytes()).hexdigest() != digest for path, digest in before.items())
            or any((hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)!=digest for path,digest in opening_before.items())
            or any((hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)!=digest for path,digest in permit_before.items())
            or workspaces.permit_context(case_id,workspace_id,as_of)!=permits
            or store.read() != state or reviews.effective_rules() != effective
            or workspaces.read(case_id, workspace_id) != status):
        raise ValueError('Workspace changed while preparing the report; generate a fresh draft')
    return report
