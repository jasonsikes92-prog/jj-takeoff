import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from template_unit_reviews import reviewed_template


class TemplateUnitReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.template = {'rows': [{'row_id': 'vanity', 'name': 'Vanity Cabinets',
                                  'cost_type': 'ALLOWANCE', 'unit': 'ft2', 'markup_pct': '8',
                                  'completion_status': 'evidence_in_progress'}]}
        (self.root/'template_rows.json').write_text(json.dumps(self.template))
        (self.root/'answer.json').write_text(json.dumps({'answers': [{'answer': 'LF'}]}))
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.config = {'plan_sha256': 'plan', 'reviewed': True,
                       'template_rows_sha256': sha(self.root/'template_rows.json'),
                       'corrections': [{'row_id': 'vanity', 'name': 'Vanity Cabinets',
                                        'cost_type': 'ALLOWANCE', 'original_unit': 'ft2', 'unit': 'LF',
                                        'basis': 'Owner confirms vanity LF; no price or quantity conversion.',
                                        'source': {'file': 'answer.json', 'sha256': sha(self.root/'answer.json'),
                                                   'json_pointer': '/answers/0/answer'}}]}

    def run_review(self):
        return reviewed_template(self.template, self.config, self.root, 'plan')

    def test_corrected_copy_preserves_original_and_markup(self):
        original = copy.deepcopy(self.template)
        raw = (self.root/'template_rows.json').read_bytes()
        row = self.run_review()['rows'][0]
        self.assertEqual(row['unit'], 'LF')
        self.assertEqual(row['unit_review']['original_unit'], 'ft2')
        self.assertEqual(row['markup_pct'], '8')
        self.assertNotIn('draft_quantity', row)
        self.assertNotIn('unit_cost', row)
        self.assertEqual(self.template, original)
        self.assertEqual((self.root/'template_rows.json').read_bytes(), raw)

    def test_changed_answer_rejected_even_with_refreshed_hash(self):
        p = self.root/'answer.json';p.write_text('{"answers":[{"answer":"EA"}]}')
        self.config['corrections'][0]['source']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'saved answer'): self.run_review()

    def test_missing_or_changed_source_rejected(self):
        (self.root/'answer.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'source missing or changed'): self.run_review()
        (self.root/'answer.json').unlink()
        with self.assertRaisesRegex(ValueError, 'source missing or changed'): self.run_review()

    def test_other_plan_or_template_rejected(self):
        with self.assertRaisesRegex(ValueError, 'matching plan'):
            reviewed_template(self.template, self.config, self.root, 'other')
        (self.root/'template_rows.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'original template'): self.run_review()

    def test_wrong_row_identity_unit_or_excluded_scope_rejected(self):
        for key, value in [('name', 'Countertop'), ('cost_type', 'LABOR'), ('unit', 'each'),
                           ('completion_status', 'not_applicable')]:
            with self.subTest(key=key):
                row=self.template['rows'][0];previous=row.get(key);row[key]=value
                with self.assertRaises(ValueError): self.run_review()
                row[key]=previous

    def test_duplicate_correction_rejected(self):
        self.config['corrections'].append(copy.deepcopy(self.config['corrections'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicated'): self.run_review()

    def test_invalid_source_pointer_rejected(self):
        for pointer in ('answer', '/answers/2/answer', '/answers/-1/answer', '/answers/00/answer'):
            with self.subTest(pointer=pointer):
                self.config['corrections'][0]['source']['json_pointer']=pointer
                with self.assertRaises(ValueError): self.run_review()

    def test_source_outside_job_rejected(self):
        self.config['corrections'][0]['source']['file']='../answer.json'
        with self.assertRaisesRegex(ValueError, 'source missing or changed'): self.run_review()


if __name__ == '__main__':
    unittest.main()
