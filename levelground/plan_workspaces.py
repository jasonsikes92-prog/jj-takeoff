"""Bind a selected case upload to the existing new-plan intake workflow."""
import hashlib
import json
import sys
import tempfile
import threading
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from new_plan_intake import create_job
from answer_store import now
from document_processing import DocumentProcessing
from plan_sheet_review import read_sheet_review
from permit_input_reviews import PermitInputReviews, validate_jurisdiction
from permit_report_context import from_workspace as frozen_permit_context
from local_requirements import requirements_context


class PlanWorkspaces:
    def __init__(self, store, root):
        self.store = store
        self.root = Path(root).resolve()
        self.lock = threading.Lock()
        self.permit_reviews = PermitInputReviews(store)

    def initialize(self, case_id, reference, reviewer_id, jurisdiction=None):
        """Caller authorizes the reviewer and the selected upload's plan role.

        No measurement, price or report is approved here. Company defaults stay
        internal to the workspace and do not become homeowner project facts.
        """
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise ValueError('Reviewer identity required')
        if jurisdiction is not None:
            validate_jurisdiction(jurisdiction)
        case_key = str(uuid.UUID(case_id))
        evidence = self.store.read_evidence(case_id, reference)
        if not evidence['body'].startswith(b'%PDF-'):
            raise ValueError('A plan PDF is required')
        prepared = DocumentProcessing(self.store).read(case_id, evidence['id'])
        if prepared['status'] != 'text_extracted':
            raise ValueError('Complete document preparation and resolve unreadable pages first')
        if prepared['source_sha256'] != evidence['sha256']:
            raise ValueError('Upload preparation does not match this source')
        job = self.root / case_key / evidence['sha256']
        with self.lock:
            if job.exists():
                if jurisdiction is not None:
                    path=job/'local_requirements.json'
                    saved=json.loads(path.read_bytes()) if path.exists() else {}
                    if saved.get('project_basis')!=jurisdiction:
                        raise ValueError('Existing workspace preserved; jurisdiction changes require a reviewed intake revision')
                return self.read(case_id, evidence['sha256'])
            job.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=job.parent) as scratch:
                plan = Path(scratch) / 'uploaded-plan.pdf'
                plan.write_bytes(evidence['body'])
                create_job(plan, job,inputs={'jurisdiction':jurisdiction or {}})
            manifest = {
                'case_id': case_id, 'workspace_id': evidence['sha256'],
                'source_reference': reference, 'source_filename': evidence['filename'],
                'plan_sha256': evidence['sha256'], 'created_at': now(),
                'selected_by': reviewer_id.strip(),
                'document_role': 'plan_selected_for_intake',
                'initial_file_sha256': {name: hashlib.sha256((job / name).read_bytes()).hexdigest()
                    for name in ('estimate_intake.json', 'plan_inventory.json', 'company_profile_snapshot.json')},
                'independent_validation_status': 'not_established',
            }
            (job / 'case_workspace.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
            return self.read(case_id, evidence['sha256'])

    def prebid_draft(self, case_id, workspace_id):
        """Generate a reviewer preview; do not attach or publish a case report."""
        from plan_report import draft_from_workspace
        return draft_from_workspace(self, case_id, workspace_id)

    def _permit_base(self,case_id,workspace_id,as_of):
        status=self.read(case_id,workspace_id)
        job=self.root/case_id/workspace_id
        return job,frozen_permit_context(job,status['plan_sha256'],as_of)

    def permit_inputs(self,case_id,workspace_id):
        job,base=self._permit_base(case_id,workspace_id,date.today().isoformat())
        if base['status']=='unbound_legacy_snapshot':
            raise ValueError('Legacy permit intake needs source binding before input revisions')
        history=self.permit_reviews.read(case_id,workspace_id,base['project_context_sha256'])
        original=json.loads((job/'local_requirements.json').read_bytes())['project_basis']
        return {**history,'initial_project_basis':original,
            'project_basis':history['records'][-1]['project_basis'] if history['records'] else original}

    def revise_permit_inputs(self,case_id,workspace_id,reviewer_id,payload):
        _,base=self._permit_base(case_id,workspace_id,date.today().isoformat())
        if base['status']=='unbound_legacy_snapshot':
            raise ValueError('Legacy permit intake needs source binding before input revisions')
        return self.permit_reviews.save(case_id,workspace_id,base['project_context_sha256'],reviewer_id,payload)

    def permit_context(self,case_id,workspace_id,as_of):
        job,base=self._permit_base(case_id,workspace_id,as_of)
        if base['status']=='unbound_legacy_snapshot':return base
        history=self.permit_reviews.read(case_id,workspace_id,base['project_context_sha256'])
        if history['records']:
            registry=json.loads((job/'official_requirements_snapshot.json').read_bytes())
            base={**base,**requirements_context(history['records'][-1]['project_basis'],registry,as_of)}
        return {**base,'input_revision':history['revision'],'input_revision_sha256':history['revision_sha256']}

    def trade_bid_drafts(self, case_id, workspace_id):
        from plan_bid_drafts import from_workspace
        return from_workspace(self, case_id, workspace_id)

    def measure(self, case_id, workspace_id, reviewer_id, sheet_review_sha256):
        """Prepare candidates for an explicitly reviewed upload; never overwrite a draft."""
        from new_plan_measure import measure_job
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise ValueError('Reviewer identity required')
        with self.lock:
            status = self.read(case_id, workspace_id)
            review = status['sheet_review']
            if (not review or not review['measurement_allowed'] or
                    review['review_sha256'] != sheet_review_sha256):
                raise ValueError('Current approved sheet scope and its review revision are required')
            job = self.root / str(uuid.UUID(case_id)) / workspace_id
            manifest = json.loads((job / 'case_workspace.json').read_text(encoding='utf-8'))
            expected = manifest['initial_file_sha256']
            def check_intake():
                for name in ('estimate_intake.json', 'plan_inventory.json', 'company_profile_snapshot.json'):
                    if hashlib.sha256((job / name).read_bytes()).hexdigest() != expected[name]:
                        raise ValueError('Frozen intake changed; resolve the workspace revision before measuring')
            check_intake()
            if (job / 'draft_takeoff').exists():
                if status['measurement_status'] == 'candidates_require_review':
                    return status
                raise ValueError('Existing incomplete or stale draft preserved; inspect before creating a new revision')
            measure_job(job)
            check_intake()
            status = self.read(case_id, workspace_id)
            if status['measurement_status'] != 'candidates_require_review':
                raise ValueError('Measurement source changed during preparation; output preserved for review')
            record = {'case_id':case_id, 'workspace_id':workspace_id, 'reviewer_id':reviewer_id.strip(),
                'completed_at':now(), 'sheet_review_sha256':sheet_review_sha256,
                'initial_file_sha256':expected,
                'summary_sha256':hashlib.sha256((job / 'draft_takeoff/summary.json').read_bytes()).hexdigest(),
                'status':'candidates_require_review', 'estimate_released':False}
            with (job / 'measurement_run.json').open('x', encoding='utf-8') as stream:
                stream.write(json.dumps(record, indent=2) + '\n')
            return status

    def read(self, case_id, workspace_id):
        case_key = str(uuid.UUID(case_id))
        if (not isinstance(workspace_id, str) or len(workspace_id) != 64 or
                any(c not in '0123456789abcdef' for c in workspace_id)):
            raise ValueError('Invalid workspace identity')
        job = self.root / case_key / workspace_id
        manifest_path = job / 'case_workspace.json'
        if not manifest_path.is_file():
            raise ValueError('Workspace missing or intake interrupted; existing files preserved')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['case_id'] != case_id or manifest['workspace_id'] != workspace_id:
            raise ValueError('Workspace does not belong to this case')
        evidence = self.store.read_evidence(case_id, manifest['source_reference'])
        digest = hashlib.sha256((job / 'plan.pdf').read_bytes()).hexdigest()
        if digest != evidence['sha256'] or digest != manifest['plan_sha256']:
            raise ValueError('Workspace drawing differs from the selected upload')
        inventory = json.loads((job / 'plan_inventory.json').read_text(encoding='utf-8'))
        if inventory['plan_sha256'] != digest:
            raise ValueError('Sheet inventory belongs to another drawing')
        review = read_sheet_review(job) if (job / 'sheet_review.json').exists() else None
        status = ('sheet_coverage_reviewed_measurement_pending' if review['coverage_passed'] else
                  'partial_scope_reviewed_measurement_pending' if review['measurement_allowed'] else
                  'sheet_review_needs_resolution') if review else 'intake_created_sheet_review_required'
        candidate_status = 'not_measured'
        candidate_counts = None
        summary_path = job / 'draft_takeoff' / 'summary.json'
        if summary_path.parent.exists() and not summary_path.exists():
            candidate_status = 'preparation_incomplete'
            status = 'measurement_preparation_incomplete'
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
            if (not review or summary.get('plan_sha256') != digest or
                    summary.get('sheet_review_sha256') != review['review_sha256']):
                candidate_status = 'source_or_review_changed'
                status = 'measurement_source_or_review_changed'
            else:
                candidate_status = 'candidates_require_review'
                status = ('partial_measurement_candidates_require_review'
                          if review['measurement_scope'] == 'reviewed_subset' else
                          'measurement_candidates_require_review')
                candidate_counts = {key: summary[key] for key in
                                    ('editable_region_candidates', 'editable_count_candidates')}
                candidate_counts.update({key:summary[key] for key in
                    ('editable_length_candidates','editable_measurements') if key in summary})
        # Publish only intake status; private company settings/prices and filesystem
        # paths are not included in the homeowner case response.
        return {'workspace_id': workspace_id, 'source_reference': manifest['source_reference'],
                'source_filename': manifest['source_filename'], 'plan_sha256': digest,
                'status': status,
                'sheet_review': ({key: review[key] for key in ('coverage_passed', 'reviewed_pages',
                                  'page_count', 'unresolved_issues', 'review_sha256',
                                  'unexamined_pages', 'missing_roles', 'measurement_allowed',
                                  'measurement_scope', 'measurement_role_pages')} if review else None),
                'page_count': len(inventory['pages']),
                'measurement_status': candidate_status, 'candidate_counts': candidate_counts,
                'failed_preparation_attempts': sum(1 for _ in job.glob(
                    '.takeoff-attempt-*/preparation_failure.json')),
                'role_candidates': (review or inventory)['role_candidates'],
                'roles_requiring_disambiguation': (review or inventory)['roles_requiring_disambiguation'],
                'estimate_released': False, 'measurements_certified': False,
                'independent_validation_status': manifest['independent_validation_status']}
