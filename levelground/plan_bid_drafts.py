"""Retrieve current trade requests for the case reviewer, without publishing them."""
import hashlib
import json
import sys
from pathlib import Path

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path[:0]=[str(TOOLS),str(TOOLS/'viewer')]
from measurement_store import MeasurementStore
from roof_bid_scope import from_folder as roof_scope,render_markdown as render_roof
from company_scope_bids import from_folder as company_scopes,render_markdown as render_company
from opening_bid_scope import from_folder as opening_scope,render_markdown as render_openings
from opening_framing_scope import from_folder as framing_scope,render_markdown as render_framing
from drywall_bid_scope import from_folder as drywall_scope,render_markdown as render_drywall
from bid_comparison import scope_digest


def from_workspace(workspaces,case_id,workspace_id):
    status=workspaces.read(case_id,workspace_id)
    if status['measurement_status']!='candidates_require_review':
        raise ValueError('Current sheet-reviewed measurement candidates are required')
    job=workspaces.root/case_id/workspace_id;folder=job/'draft_takeoff'
    files=[job/name for name in ('case_workspace.json','sheet_review.json','plan_inventory.json',
                                'estimate_intake.json','company_profile_snapshot.json')]
    files+=[folder/name for name in ('summary.json','measurements.json','quantity_rules.json')]
    optional=[folder/name for name in ('roof_partition_inputs.json','roof_coverage_review.json','company_scope_review.json',
        'opening_schedule_review.json','wall_classification_review.json','wall_alignment_breaks.json',
        'opening_quantity_review.json','door_policy_revision.json','door_hardware_policy_revision.json','room_use_review.json',
        'drywall_practice_review.json','ceiling_surface_review.json','roof_edge_review.json','plan.pdf')]
    before={p:p.read_bytes() for p in files}
    before.update({p:p.read_bytes() if p.exists() else None for p in optional})
    manifest=json.loads(before[job/'case_workspace.json'])
    for name in ('estimate_intake.json','company_profile_snapshot.json','plan_inventory.json'):
        if hashlib.sha256(before[job/name]).hexdigest()!=manifest['initial_file_sha256'][name]:
            raise ValueError('Frozen intake changed; resolve its revision before using bid drafts')
    store=MeasurementStore(folder);state=store.read();drafts=[]
    def watch(path):
        path=path.resolve()
        if not path.is_relative_to(job.resolve()):raise ValueError('Opening bid sources must stay inside their job')
        if path not in before:before[path]=path.read_bytes()
        return json.loads(before[path])
    def watch_intake(path):
        intake=watch(path)
        watch(path.parent/intake['company_profile_snapshot'])
    def add(trade,scope,markdown,saved_path,kind):
        if scope['plan_sha256']!=status['plan_sha256'] or scope['measurement_version']!=state['version']:
            raise ValueError('Bid scope and workspace measurements differ; retry')
        if scope_digest(scope)!=scope['scope_sha256'] or scope.get('sent') is not False:
            raise ValueError('Current unsent bid fingerprint required')
        raw=saved_path.read_bytes() if saved_path.exists() else None;before[saved_path]=raw
        saved=json.loads(raw) if raw is not None else None
        if saved is not None and scope_digest(saved)!=saved.get('scope_sha256'):
            raise ValueError('Saved bid snapshot contents have changed')
        drafts.append({'trade':trade,'scope_kind':kind,'scope':scope,'markdown':markdown,
            'saved_scope_sha256':saved['scope_sha256'] if saved is not None else None,
            'saved_snapshot_status':('not_saved' if saved is None else
                'current' if saved['scope_sha256']==scope['scope_sha256'] else 'older_revision'),
            'sent':False})
    if before[folder/'roof_partition_inputs.json'] is not None:
        if before[folder/'roof_edge_review.json'] is not None:
            from roof_edge_scope import linked_folder
            linked=linked_folder(folder,json.loads(before[folder/'roof_edge_review.json']))
            for name in ('measurements.json','measurement_edits.sqlite3','plan.pdf'):
                p=linked/name;before[p]=p.read_bytes()
        scope=roof_scope(folder)
        add('Roofing',scope,render_roof(scope),folder/'roof_bid_scope/roofing.json','roof_face_request')
    if before[folder/'company_scope_review.json'] is not None:
        for scope in company_scopes(folder)['scopes']:
            add(scope['trade'],scope,render_company(scope),
                folder/'company_bid_scopes'/(scope['trade'].lower()+'.json'),'company_scope_additions')
    if before[folder/'opening_schedule_review.json'] is not None:
        watch_intake(job/'estimate_intake.json')
        for name in ('door_policy_revision.json','door_hardware_policy_revision.json'):
            revision=before[folder/name]
            if revision is not None:
                revision=json.loads(revision)
                watch_intake((folder/revision['base_intake_path']).resolve())
                watch(folder/revision['profile_path'])
        mapping=before[folder/'opening_quantity_review.json']
        if mapping is not None:
            policy=json.loads(mapping).get('installation_policy')
            if policy:watch_intake((folder/policy['path']).resolve())
        framing=framing_scope(folder,state)
        add('Framing',framing,render_framing(framing),folder/'opening_bid_scope/framing.json','opening_framing_request')
        scope=opening_scope(folder,state)
        scope['scope_sha256']=scope_digest(scope)
        text=render_openings(scope)+'\nScope fingerprint: `'+scope['scope_sha256']+'`.\n'
        add('Windows and doors',scope,text,folder/'opening_bid_scope/windows_doors.json','opening_assembly_request')
    if before[folder/'drywall_practice_review.json'] is not None:
        watch_intake(job/'estimate_intake.json')
        scope=drywall_scope(folder,state)
        add('Drywall',scope,render_drywall(scope),folder/'drywall_bid_scope/drywall.json','drywall_surface_request')
    if any((p.read_bytes() if p.exists() else None)!=raw for p,raw in before.items()):
        raise ValueError('Bid source files changed during retrieval; retry')
    if store.read()['version']!=state['version'] or workspaces.read(case_id,workspace_id)!=status:
        raise ValueError('Workspace changed during bid retrieval; retry')
    return {'workspace_id':workspace_id,'plan_sha256':status['plan_sha256'],
        'measurement_version':state['version'],'status':'reviewer_drafts','drafts':drafts,
        'sent':False,'homeowner_release_approved':False,'complete_trade_coverage':False,
        'notice':'Current unsent scope drafts only. Company additions are estimating practices, not homeowner-confirmed specifications. '
                 'Reconcile the full plan, selections, inclusions and current prices before requesting a final bid.'}
