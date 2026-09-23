"""Recheck frozen permit evidence for a current reviewer report."""
import hashlib
import json
from pathlib import Path
from local_requirements import requirements_context


def from_workspace(job,plan_sha256,as_of):
    job=Path(job)
    inventory_raw=(job/'plan_inventory.json').read_bytes()
    inventory=json.loads(inventory_raw)
    manifest=json.loads((job/'case_workspace.json').read_bytes())
    if hashlib.sha256(inventory_raw).hexdigest()!=manifest['initial_file_sha256']['plan_inventory.json']:
        raise ValueError('Frozen permit inventory changed; resolve the workspace revision')
    if inventory.get('plan_sha256')!=plan_sha256:
        raise ValueError('Permit inventory belongs to another drawing')
    expected=inventory.get('local_requirements_sha256')
    if not expected:
        return {'status':'unbound_legacy_snapshot','as_of':as_of,'candidates':[],'needs_review':[],
            'missing_project_fields':[],'coverage_complete':False,'permit_compliance_verified':False,
            'notice':'This older workspace has no source-bound permit input. Review jurisdiction and official requirements before relying on a permit checklist.'}
    context_path=job/'local_requirements.json';registry_path=job/'official_requirements_snapshot.json'
    if not context_path.is_file() or not registry_path.is_file():
        raise ValueError('Frozen permit evidence is missing')
    context_raw=context_path.read_bytes();registry_raw=registry_path.read_bytes()
    if hashlib.sha256(context_raw).hexdigest()!=expected:
        raise ValueError('Frozen permit project basis changed; resolve its revision')
    saved=json.loads(context_raw)
    if saved.get('plan_sha256')!=plan_sha256:
        raise ValueError('Permit evidence belongs to another drawing')
    digest=hashlib.sha256(registry_raw).hexdigest()
    if saved.get('registry_sha256')!=digest:
        raise ValueError('Frozen official requirement evidence changed')
    if not isinstance(saved.get('project_basis'),dict):
        raise ValueError('Frozen permit evidence lacks its project basis')
    # Re-evaluate age and dates now; a once-current result is not timeless approval.
    result=requirements_context(saved['project_basis'],json.loads(registry_raw),as_of)
    return {**result,'status':'reviewer_source_context','registry_sha256':digest,
        'project_context_sha256':expected,
        'notice':'Dated official-source evidence for review. Confirm applicability and package inclusions; no permit approval or fee estimate is issued.'}
