import copy
import hashlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen
import fitz
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from scope_applicability import apply_applicability
from estimate_readiness import readiness
from measurement_estimate import price_draft
from measurement_review import make_server
from measurement_store import MeasurementStore


class ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'review.json'
        self.source.write_text('{"review": "No eight-foot doors in the reviewed schedule"}')
        row = {'row_id': 'row8', 'excel_row': '8', 'name': '8-foot door', 'parent': 'Doors',
               'cost_type': 'MATERIAL', 'markup_pct': '15', 'unit': 'each',
               'completion_status': 'not_yet_reconciled', 'draft_quantity': None,
               'line_cost': None, 'line_price': None, 'unit_cost': None,
               'assembly_inputs': [], 'quantity_sources': []}
        self.draft = {'plan_sha256': 'plan', 'measurement_version': 1, 'rows': [row],
                      'whole_house_total': None, 'estimate_released': False}
        self.config = {'plan_sha256': 'plan', 'measurement_version': 1, 'reviewer': 'test',
                       'exclusions': [{'row_id': 'row8', 'reason': 'Reviewed doors are 6 feet 8 inches',
                                       'sources': [{'file': self.source.name,
                                                    'sha256': hashlib.sha256(self.source.read_bytes()).hexdigest()}]}]}

    def apply(self, draft=None, config=None):
        return apply_applicability(draft or self.draft, config or self.config, self.root)

    def test_exclusion_preserves_row_fields_and_never_turns_unknowns_into_zero(self):
        original = copy.deepcopy(self.draft)
        result = self.apply()
        self.assertEqual(self.draft, original)
        self.assertEqual(len(result['rows']), 1)
        for key in ('row_id', 'excel_row', 'name', 'parent', 'unit', 'markup_pct', 'cost_type'):
            self.assertEqual(result['rows'][0][key], original['rows'][0][key])
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertIsNone(result['rows'][0]['line_price'])
        report = readiness(result, {'rows': original['rows']})
        self.assertEqual(report['rows_with_open_issues'], 0)
        self.assertIsNone(report['whole_house_total'])
        self.assertFalse(report['estimate_released'])

    def test_changed_plan_or_measurement_reopens_exclusion(self):
        for change in ({'plan_sha256': 'new-plan'}, {'measurement_version': 2}):
            with self.subTest(change=change):
                draft = self.apply()
                draft.update(change)
                result = self.apply(draft)
                self.assertEqual(result['rows'][0]['completion_status'], 'applicability_review_required')
                issues = readiness(result, {'rows': self.draft['rows']})['rows'][0]['issues']
                self.assertIn('Scope applicability needs renewed review', issues)
                self.assertIn('Quantity unresolved', issues)

    def test_selected_cost_rows_follow_scope_not_unrelated_geometry(self):
        selected = {**self.draft['rows'][0], 'row_id': 'selected', 'name': 'Lap siding',
                    'draft_quantity': 1500, 'cost_type': 'SUBCONTRACTOR', 'parent': 'Siding', 'unit': 'SF'}
        self.draft['rows'].append(selected)
        self.config['exclusions'][0]['requires_mapped_cost_rows'] = [
            {k: selected[k] for k in ('row_id', 'name', 'parent', 'unit', 'cost_type')}]
        self.draft['unrelated_link_hash'] = 'changed bathroom geometry'
        self.assertEqual(self.apply()['rows'][0]['completion_status'], 'not_applicable_source_reviewed')
        selected['draft_quantity'] = 1600
        self.assertEqual(self.apply()['rows'][0]['completion_status'], 'not_applicable_source_reviewed')
        for key, value in [('draft_quantity', None), ('unit', 'EA'), ('name', 'Other scope'),
                           ('completion_status', 'not_applicable_source_reviewed')]:
            original = selected[key]; selected[key] = value
            self.assertEqual(self.apply()['rows'][0]['applicability_review']['status'],
                             'source_or_revision_changed_review_required')
            selected[key] = original
        self.config['exclusions'].append({**self.config['exclusions'][0], 'row_id': 'selected'})
        with self.assertRaisesRegex(ValueError, 'also configured as excluded'):
            self.apply()

    def test_changed_or_missing_source_reopens_row(self):
        approved = self.apply()
        self.source.write_text('Changed schedule')
        self.assertEqual(self.apply(approved)['rows'][0]['completion_status'], 'applicability_review_required')
        self.source.unlink()
        self.assertEqual(self.apply(approved)['rows'][0]['completion_status'], 'applicability_review_required')

    def test_job_selection_dependency_reopens_exclusion_when_changed(self):
        evidence=self.root/'evidence';evidence.mkdir()
        (evidence/self.source.name).write_bytes(self.source.read_bytes())
        selection=self.root/'prices.json';selection.write_text('{"model":"faucet-with-drain"}')
        config=copy.deepcopy(self.config)
        config['exclusions'][0]['job_sources']=[{'file':'prices.json','sha256':hashlib.sha256(selection.read_bytes()).hexdigest()}]
        result=apply_applicability(self.draft,config,evidence)
        self.assertEqual(result['rows'][0]['completion_status'],'not_applicable_source_reviewed')
        selection.write_text('{"model":"different-faucet"}')
        reopened=apply_applicability(result,config,evidence)
        self.assertEqual(reopened['rows'][0]['completion_status'],'applicability_review_required')
        self.assertIn('Scope applicability needs renewed review',readiness(reopened,{'rows':self.draft['rows']})['rows'][0]['issues'])
        config['exclusions'][0]['job_sources'][0]['file']='../outside.json'
        with self.assertRaisesRegex(ValueError,'inside the job'):
            apply_applicability(self.draft,config,evidence)

    def test_expired_review_reopens_fresh_baseline_exclusions(self):
        baseline=copy.deepcopy(self.draft)
        baseline['rows'][0]['completion_status']='not_applicable_plan_baseline'
        for change in ({'measurement_version':2},{'plan_sha256':'new-plan'}):
            result=self.apply({**baseline,**change})
            self.assertEqual(result['rows'][0]['completion_status'],'applicability_review_required')
            report=readiness(result,{'rows':baseline['rows']})
            self.assertEqual(report['rows'][0]['role'],'cost_line')
            self.assertIn('Quantity unresolved',report['rows'][0]['issues'])
        self.source.write_text('Changed evidence')
        self.assertEqual(self.apply(baseline)['rows'][0]['completion_status'],'applicability_review_required')
        self.source.unlink()
        self.assertEqual(self.apply(baseline)['rows'][0]['completion_status'],'applicability_review_required')

    def test_exclusion_cannot_hide_a_quantity_package_or_price(self):
        for change in ({'draft_quantity': 0}, {'draft_quantity': 2}, {'assembly_inputs': [{'id': 'scope'}]},
                       {'covered_by_package': 'package'}, {'cost_owner_row_id': 'extra'}, {'line_cost': 100}):
            with self.subTest(change=change):
                draft = copy.deepcopy(self.draft)
                draft['rows'][0].update(change)
                with self.assertRaisesRegex(ValueError, 'conflicts'):
                    self.apply(draft)

    def test_invalid_owner_source_and_group_exclusions_refused(self):
        for change in ({'row_id': 'unknown'}, {'sources': []}, {'reason': ''},
                       {'sources': [{'file': '../outside.json', 'sha256': 'x'}]}):
            with self.subTest(change=change):
                config = copy.deepcopy(self.config)
                config['exclusions'][0].update(change)
                with self.assertRaises(ValueError): self.apply(config=config)
        self.config['exclusions'] *= 2
        with self.assertRaises(ValueError): self.apply()
        self.config['exclusions'] = self.config['exclusions'][:1]
        self.draft['rows'][0]['cost_type'] = 'GROUP'
        with self.assertRaises(ValueError): self.apply()

    def test_unit_pricing_cannot_charge_an_excluded_option(self):
        pricing = {'plan_sha256': 'plan', 'measurement_version': 1,
                   'rates': [{'row_id': 'row8', 'validity_policy': 'owner_rate_until_changed'}]}
        with self.assertRaisesRegex(ValueError, 'Excluded template'):
            price_draft(self.apply(), pricing, '2026-09-16', self.root)

    def zero_area_fixture(self):
        self.draft['rows'][0].update(name='SF SECOND FLOOR', parent='INPUTS',
                                    unit='ft2', pricing_role='input_only')
        self.config['zero_area_inputs'] = self.config.pop('exclusions')
        self.config['exclusions'] = []
        self.config['zero_area_inputs'][0]['reason'] = 'Reviewed plan has only one floor'

    def test_reviewed_absent_floor_is_zero_and_remains_nonbillable(self):
        self.zero_area_fixture()
        result = self.apply()
        self.assertEqual(result['rows'][0]['draft_quantity'], 0)
        self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertEqual(readiness(result, {'rows': self.draft['rows']})['rows'][0]['issues'], [])
        self.assertEqual(self.apply(result), result)
        self.assertIsNone(self.draft['rows'][0]['draft_quantity'])
        self.assertFalse(result['estimate_released'])

    def test_changed_source_or_revision_withdraws_reviewed_zero(self):
        self.zero_area_fixture()
        result = self.apply()
        for change in ({'plan_sha256': 'different'}, {'measurement_version': 2}):
            reopened = self.apply({**result, **change})
            self.assertIsNone(reopened['rows'][0]['draft_quantity'])
            self.assertIn('Input value unresolved', readiness(reopened, {'rows': self.draft['rows']})['rows'][0]['issues'])
        self.source.write_text('New plan has a second floor')
        self.assertIsNone(self.apply(result)['rows'][0]['draft_quantity'])

    def test_reviewed_zero_cannot_hide_existing_area_or_nonarea_cost(self):
        self.zero_area_fixture()
        for change in ({'draft_quantity': 400}, {'line_cost': 100}, {'unit': 'month'},
                       {'parent': 'Flooring'}, {'cost_type': 'ASSEMBLY'}):
            draft = copy.deepcopy(self.draft)
            draft['rows'][0].update(change)
            with self.assertRaises(ValueError):
                self.apply(draft)
        self.config['zero_area_inputs'] *= 2
        with self.assertRaises(ValueError):
            self.apply()

    def test_http_estimate_and_readiness_apply_and_reopen_the_same_exclusion(self):
        self.draft['rows'][0]['completion_status']='not_applicable_plan_baseline'
        job = self.root / 'job'
        job.mkdir()
        with fitz.open() as pdf:
            pdf.new_page(width=500, height=500)
            pdf.save(job / 'plan.pdf')
        digest = hashlib.sha256((job / 'plan.pdf').read_bytes()).hexdigest()
        (job / 'measurements.json').write_text(json.dumps({'plan_sha256': digest, 'measurements': [
            {'id': 'm', 'label': 'Synthetic measurement', 'kind': 'length', 'page': 1,
             'width_pt': 500, 'height_pt': 500, 'points_per_foot': 10,
             'points': [[0, 0], [100, 0]], 'color': '#123456', 'dependent_rows': []}]}))
        (job / 'quantity_rules.json').write_text(json.dumps({'plan_sha256': digest, 'rules': []}))
        (job / 'template_rows.json').write_text(json.dumps({'rows': self.draft['rows']}))
        evidence = job / 'scope_evidence'
        evidence.mkdir()
        (evidence / self.source.name).write_bytes(self.source.read_bytes())
        self.config['plan_sha256'] = digest
        (job / 'scope_applicability.json').write_text(json.dumps(self.config))
        store = MeasurementStore(job)
        server = make_server(store)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}'
            with urlopen(url + '/api/estimate-draft') as response: before = json.load(response)
            self.assertEqual(before['rows'][0]['completion_status'], 'not_applicable_source_reviewed')
            store.save('m', [[0, 0], [200, 0]], 1, digest, 'Synthetic edit')
            with urlopen(url + '/api/readiness') as response: after = json.load(response)
            self.assertIn('Scope applicability needs renewed review', after['rows'][0]['issues'])
            self.assertEqual(after['rows'][0]['role'], 'cost_line')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
