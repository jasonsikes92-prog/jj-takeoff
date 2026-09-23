import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces


class PlanWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = AnswerStore(self.root / 'case.sqlite3')
        self.case = self.store.create_case('New home')
        self.other = self.store.create_case('Other homeowner')
        self.processing = DocumentProcessing(self.store)
        self.workspaces = PlanWorkspaces(self.store, self.root / 'workspaces')

    def upload(self):
        with fitz.open() as pdf:
            pdf.new_page().insert_text((30, 30), 'INDEX OF DRAWINGS\nMAIN FLOOR PLAN\nROOF PLAN')
            pdf.new_page().insert_text((30, 30), 'MAIN FLOOR PLAN')
            pdf.new_page().insert_text((30, 30), 'ROOF PLAN')
            raw = pdf.tobytes()
        return self.store.attach_evidence(self.case, 'new-plan.pdf', raw), raw

    def test_upload_creates_source_bound_intake_without_old_quantities_or_prices(self):
        evidence, raw = self.upload()
        self.processing.process_next()
        result = self.workspaces.initialize(self.case, evidence['reference'], 'operator')
        self.assertEqual(result['page_count'], 3)
        self.assertEqual(result['role_candidates'], {'floor': [2], 'roof': [3]})
        job = self.root / 'workspaces' / self.case / result['workspace_id']
        self.assertEqual((job / 'plan.pdf').read_bytes(), raw)
        intake = json.loads((job / 'estimate_intake.json').read_text())
        self.assertEqual(intake['settings']['framing.outside_corner_studs'], 3)
        self.assertEqual(intake['current_prices'], {})
        self.assertEqual(intake['quantity_measurements'], {})
        self.assertEqual(intake['project_overrides'], {})
        self.assertFalse(result['estimate_released'])
        self.assertFalse(result['measurements_certified'])
        self.assertNotIn('settings', result)
        self.assertNotIn('current_prices', result)
        self.assertNotIn(str(self.root), json.dumps(result))
        before = {p.name: p.read_bytes() for p in job.iterdir()}
        self.assertEqual(self.workspaces.initialize(self.case, evidence['reference'], 'operator'), result)
        self.assertEqual({p.name: p.read_bytes() for p in job.iterdir()}, before)
        self.assertEqual(self.store.read_case(self.case)['reports'], [])

    def test_wrong_case_unprepared_or_non_pdf_sources_refused(self):
        evidence, _ = self.upload()
        with self.assertRaises(ValueError):
            self.workspaces.initialize(self.case, evidence['reference'], 'operator')
        self.processing.process_next()
        with self.assertRaises(ValueError):
            self.workspaces.initialize(self.other, evidence['reference'], 'operator')
        text = self.store.attach_evidence(self.case, 'bid.txt', b'Total: $100.00')
        self.processing.process_next()
        with self.assertRaisesRegex(ValueError, 'PDF'):
            self.workspaces.initialize(self.case, text['reference'], 'operator')
        self.assertFalse((self.root / 'workspaces').exists())

    def test_source_change_and_cross_case_workspace_read_refused(self):
        evidence, _ = self.upload()
        self.processing.process_next()
        result = self.workspaces.initialize(self.case, evidence['reference'], 'operator')
        with self.assertRaises(ValueError):
            self.workspaces.read(self.other, result['workspace_id'])
        job = self.root / 'workspaces' / self.case / result['workspace_id']
        (job / 'plan.pdf').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.workspaces.read(self.case, result['workspace_id'])
        with self.assertRaises(ValueError):
            self.workspaces.read(self.case, '../../escape')

    def test_partial_intake_and_existing_owner_edits_are_preserved(self):
        evidence, raw = self.upload()
        self.processing.process_next()
        digest = hashlib.sha256(raw).hexdigest()
        partial = self.root / 'workspaces' / self.case / digest
        partial.mkdir(parents=True)
        marker = partial / 'operator-notes.txt'
        marker.write_text('Preserve my investigation')
        with self.assertRaisesRegex(ValueError, 'interrupted'):
            self.workspaces.initialize(self.case, evidence['reference'], 'operator')
        self.assertEqual(marker.read_text(), 'Preserve my investigation')

    def test_reviewed_sheet_status_is_visible_without_internal_paths_or_defaults(self):
        evidence, _ = self.upload()
        self.processing.process_next()
        result = self.workspaces.initialize(self.case, evidence['reference'], 'operator')
        job = self.root / 'workspaces' / self.case / result['workspace_id']
        pages = []
        with fitz.open(job / 'plan.pdf') as doc:
            for i, role in enumerate(('cover', 'floor_plan', 'roof_plan')):
                view = job / f'page_{i}.png'
                doc[i].get_pixmap().save(view)
                pages.append({'page': i + 1, 'role': role, 'view': view.name,
                    'view_sha256': hashlib.sha256(view.read_bytes()).hexdigest()})
        (job / 'sheet_review.json').write_text(json.dumps({
            'plan_sha256': result['workspace_id'], 'reviewer': 'private-operator-id',
            'cover_index': [[1, 'Main Floor Plan'], [2, 'Roof Plan'], [3, 'Site Plan']],
            'pages': pages, 'unresolved_issues': []}))
        status = self.workspaces.read(self.case, result['workspace_id'])
        self.assertEqual(status['status'], 'sheet_review_needs_resolution')
        self.assertEqual(status['sheet_review']['reviewed_pages'], 3)
        self.assertIn('site', status['sheet_review']['missing_roles'])
        self.assertEqual(status['sheet_review']['unexamined_pages'], [])
        self.assertFalse(status['measurements_certified'])
        self.assertNotIn(str(self.root), json.dumps(status))
        self.assertNotIn('private-operator-id', json.dumps(status))
        self.assertNotIn('settings', status)
        path = job / 'sheet_review.json'
        review = json.loads(path.read_text())
        review['partial_measurement_review'] = {
            'role_pages': {'floor': 2}, 'basis': 'Private reviewer rationale',
            'missing_roles': status['sheet_review']['missing_roles'], 'unresolved_issues': []}
        path.write_text(json.dumps(review))
        partial = self.workspaces.read(self.case, result['workspace_id'])
        self.assertEqual(partial['status'], 'partial_scope_reviewed_measurement_pending')
        self.assertFalse(partial['sheet_review']['coverage_passed'])
        self.assertEqual(partial['sheet_review']['measurement_role_pages'], {'floor': 2})
        self.assertFalse(partial['estimate_released'])
        self.assertNotIn('Private reviewer rationale', json.dumps(partial))
        self.assertNotIn(str(self.root), json.dumps(partial))
        draft = job / 'draft_takeoff'
        draft.mkdir()
        summary = {'plan_sha256': result['workspace_id'],
                   'sheet_review_sha256': partial['sheet_review']['review_sha256'],
                   'editable_region_candidates': 2, 'editable_count_candidates': 0,
                   'private_unit_price': 999, 'private_path': str(job)}
        (draft / 'summary.json').write_text(json.dumps(summary))
        measured = self.workspaces.read(self.case, result['workspace_id'])
        self.assertEqual(measured['status'], 'partial_measurement_candidates_require_review')
        self.assertEqual(measured['candidate_counts']['editable_region_candidates'], 2)
        self.assertFalse(measured['sheet_review']['coverage_passed'])
        self.assertNotIn('private_unit_price', json.dumps(measured))
        self.assertNotIn(str(self.root), json.dumps(measured))
        review['partial_measurement_review']['basis'] += ' Changed.'
        path.write_text(json.dumps(review))
        stale = self.workspaces.read(self.case, result['workspace_id'])
        self.assertEqual(stale['measurement_status'], 'source_or_review_changed')
        self.assertIsNone(stale['candidate_counts'])
        (job / 'page_0.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'image has changed'):
            self.workspaces.read(self.case, result['workspace_id'])


    def test_jurisdiction_is_frozen_and_changed_retries_do_not_overwrite(self):
        evidence,_=self.upload();self.processing.process_next()
        jurisdiction={'state':'GA','authority_id':'GA-JASPER-COUNTY','authority_verified':False}
        result=self.workspaces.initialize(self.case,evidence['reference'],'operator',jurisdiction)
        job=self.workspaces.root/self.case/result['workspace_id']
        context=json.loads((job/'local_requirements.json').read_bytes())
        self.assertEqual(context['project_basis'],jurisdiction)
        before={p:p.read_bytes() for p in job.iterdir() if p.is_file()}
        self.assertEqual(self.workspaces.initialize(self.case,evidence['reference'],'operator',jurisdiction),result)
        with self.assertRaisesRegex(ValueError,'Existing workspace preserved'):
            self.workspaces.initialize(self.case,evidence['reference'],'operator',{**jurisdiction,'authority_verified':True})
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        with self.assertRaisesRegex(ValueError,'must be an object'):
            self.workspaces.initialize(self.case,evidence['reference'],'operator','Jasper')

    def test_permit_corrections_preserve_initial_files_and_require_matching_case(self):
        evidence,_=self.upload();self.processing.process_next()
        result=self.workspaces.initialize(self.case,evidence['reference'],'operator',{'state':'GA'})
        identity=result['workspace_id'];job=self.workspaces.root/self.case/identity
        before={p:p.read_bytes() for p in job.iterdir() if p.is_file()}
        ref=self.store.attach_evidence(self.case,'correction.txt',b'Synthetic location correction')['reference']
        payload={'expected_revision':0,'jurisdiction':{'state':'SC'},'rationale':'Correct property state','evidence_refs':[ref]}
        self.workspaces.revise_permit_inputs(self.case,identity,'operator',payload)
        read=self.workspaces.permit_inputs(self.case,identity)
        self.assertEqual(read['initial_project_basis'],{'state':'GA'})
        self.assertEqual(read['project_basis'],{'state':'SC'})
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(self.workspaces.read(self.case,identity),result)
        with self.assertRaises(ValueError):self.workspaces.revise_permit_inputs(self.other,identity,'operator',payload)
        path=job/'local_requirements.json';path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'project basis changed'):
            self.workspaces.revise_permit_inputs(self.case,identity,'operator',{**payload,'expected_revision':1})

    def test_invalid_jurisdiction_does_not_leave_a_partial_workspace(self):
        evidence,_=self.upload();self.processing.process_next()
        for jurisdiction in ({'code_basis_date':'not-a-date'},{'code_basis_date':2026},
                             {'conditions':[]},{'authority_verified':'yes'},{'state':[]},{'authority_id':1}):
            with self.subTest(jurisdiction=jurisdiction),self.assertRaises(ValueError):
                self.workspaces.initialize(self.case,evidence['reference'],'operator',jurisdiction)
            self.assertFalse(self.workspaces.root.exists())

if __name__ == '__main__':
    unittest.main()
