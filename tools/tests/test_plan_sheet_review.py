import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plan_sheet_review import read_sheet_review
from new_plan_measure import measure_job


class SheetReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.job = Path(self.tmp.name)
        roles = ['cover', 'foundation', 'floor_plan', 'roof_plan', 'elevation']
        titles = ['Cover', 'Foundation Plan', 'Main Floor Plan', 'Roof Plan', 'Elevations']
        pages = []
        with fitz.open() as doc:
            for n, (role, title) in enumerate(zip(roles, titles), 1):
                page = doc.new_page()
                page.insert_text((30, 30), title)
                view = self.job / f'page_{n}.png'
                page.get_pixmap().save(view)
                pages.append({'page': n, 'role': role, 'title': title, 'view': view.name,
                              'view_sha256': hashlib.sha256(view.read_bytes()).hexdigest()})
            doc.save(self.job / 'plan.pdf')
        self.sha = hashlib.sha256((self.job / 'plan.pdf').read_bytes()).hexdigest()
        self.review = {'plan_sha256': self.sha, 'reviewer': 'synthetic-test-reviewer',
                       'cover_index': [[i, title] for i, title in enumerate(titles, 1)],
                       'pages': pages, 'unresolved_issues': []}
        # Deliberately wrong parser candidate. Reviewed routing must win.
        (self.job / 'plan_inventory.json').write_text(json.dumps({
            'plan_sha256': self.sha, 'unique_role_pages': {'foundation': 1},
            'roles_requiring_disambiguation': {}}))
        self.save()

    def save(self):
        (self.job / 'sheet_review.json').write_text(json.dumps(self.review))

    def assert_engine_blocked(self):
        with patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaises(ValueError):
                measure_job(self.job)
            engine.assert_not_called()
        self.assertFalse((self.job / 'draft_takeoff').exists())

    def test_reviewed_roles_route_engine_without_pricing_or_certification(self):
        review = read_sheet_review(self.job)
        self.assertTrue(review['coverage_passed'])
        self.assertEqual(review['reviewed_pages'], 5)
        result = {'status': 'more_information_required', 'pages': {}, 'lines': []}
        with patch('jnj_takeoff.run_takeoff', return_value=result) as engine:
            summary = measure_job(self.job)
        self.assertEqual(engine.call_args.args[1], {'foundation': 1, 'floor_area': 2, 'roof': 3})
        self.assertEqual(summary['sheet_review_sha256'], review['review_sha256'])
        self.assertFalse(summary['estimate_released'])
        self.assertIsNone(summary['whole_house_total'])

    def test_missing_review_blocks_before_any_output(self):
        (self.job / 'sheet_review.json').unlink()
        self.assert_engine_blocked()

    def partial_scope(self):
        self.review['cover_index'].append([6, 'Site Plan'])
        self.review['unresolved_issues'] = ['Confirm drawing revision before final estimate']
        self.review['partial_measurement_review'] = {
            'role_pages': {'foundation': 2},
            'basis': 'Extract foundation candidates only; site and revision remain unresolved.',
            'missing_roles': ['site'],
            'unresolved_issues': self.review['unresolved_issues'].copy()}
        self.save()

    def test_partial_scope_routes_only_selected_pages_and_retains_coverage_failure(self):
        self.partial_scope()
        review = read_sheet_review(self.job)
        self.assertFalse(review['coverage_passed'])
        self.assertTrue(review['measurement_allowed'])
        self.assertEqual(review['measurement_scope'], 'reviewed_subset')
        result = {'status': 'more_information_required', 'pages': {1: {'ppf': 10}},
                  'lines': [{'id': 'foundation-area', 'page': 1, 'method': 'synthetic',
                    'geometry': {'kind': 'polygon', 'points': [[20,20],[120,20],[120,120],[20,120]]}}]}
        scale = {'controls': [], 'usable_candidate': True, 'points_per_foot': 10,
                 'method': 'synthetic calibration for page-routing isolation'}
        with patch('jnj_takeoff.run_takeoff', return_value=result) as engine, \
             patch('dimension_scale.split_dimension_scale', return_value=scale):
            summary = measure_job(self.job)
        self.assertEqual(engine.call_args.args[1], {'foundation': 1})
        self.assertEqual(summary['editable_measurements'], 1)
        self.assertFalse(summary['sheet_coverage_passed'])
        self.assertEqual(summary['missing_sheet_roles'], ['site'])
        self.assertEqual(summary['unresolved_sheet_issues'], self.review['unresolved_issues'])
        self.assertFalse(summary['estimate_released'])
        self.assertIsNone(summary['whole_house_total'])
        self.assertEqual(summary['current_prices'], {})
        self.assertEqual(summary['template_rows'], 711)

    def test_partial_scope_cannot_bypass_unexamined_or_changed_coverage(self):
        self.partial_scope()
        original = copy.deepcopy(self.review)
        for change in ('unexamined', 'issue', 'missing', 'ambiguous'):
            with self.subTest(change=change):
                self.review = copy.deepcopy(original)
                if change == 'unexamined': self.review['pages'].pop()
                if change == 'issue': self.review['unresolved_issues'].append('New revision conflict')
                if change == 'missing': self.review['cover_index'].append([7, 'Mechanical Plan'])
                if change == 'ambiguous': self.review['pages'][0]['role'] = 'foundation'
                self.save()
                self.assert_engine_blocked()

    def test_partial_scope_requires_matching_reviewed_pages_and_basis(self):
        self.partial_scope()
        original = copy.deepcopy(self.review)
        for change in ({'role_pages': {}}, {'role_pages': {'foundation': 1}},
                       {'role_pages': {'unknown': 2}}, {'role_pages': {'foundation': True}},
                       {'basis': ' '}, {'missing_roles': []}):
            with self.subTest(change=change):
                self.review = copy.deepcopy(original)
                self.review['partial_measurement_review'].update(change)
                self.save()
                self.assert_engine_blocked()

    def test_partial_scope_refuses_electrical_extraction_outside_selected_pages(self):
        self.partial_scope()
        (self.job / 'electrical_template_definitions.json').write_text(json.dumps(
            {'plan_sha256': self.sha, 'pages': [{'page': 3}]}))
        self.assert_engine_blocked()

    def test_unexamined_page_or_missing_indexed_site_blocks(self):
        original = copy.deepcopy(self.review)
        self.review['pages'].pop()
        self.save()
        self.assertFalse(read_sheet_review(self.job)['coverage_passed'])
        self.assert_engine_blocked()
        self.review = original
        self.review['cover_index'].append([6, 'Site Plan'])
        self.review['coverage_passed'] = True  # A stored assertion cannot bypass recalculation.
        self.save()
        self.assertFalse(read_sheet_review(self.job)['coverage_passed'])
        self.assert_engine_blocked()

    def test_source_or_view_changes_reject_stale_review(self):
        self.review['plan_sha256'] = 'wrong'
        self.save()
        self.assert_engine_blocked()
        self.review['plan_sha256'] = self.sha
        self.save()
        (self.job / 'page_2.png').write_bytes(b'changed')
        self.assert_engine_blocked()

    def test_review_changed_during_extraction_prevents_editor_output(self):
        self.partial_scope()
        def change_review(*args, **kwargs):
            self.review['partial_measurement_review']['basis'] += ' Revised scope.'
            self.save()
            return {'status': 'more_information_required', 'pages': {}, 'lines': []}
        with patch('jnj_takeoff.run_takeoff', side_effect=change_review):
            with self.assertRaisesRegex(ValueError, 'review changed'):
                measure_job(self.job)
        self.assertFalse((self.job / 'draft_takeoff/summary.json').exists())
        self.assertFalse((self.job / 'draft_takeoff/measurements.json').exists())

    def test_duplicate_out_of_range_and_external_views_rejected(self):
        original = copy.deepcopy(self.review)
        for change in ({'page': 0}, {'page': 6}, {'page': 2}, {'view': '../outside.png'}):
            with self.subTest(change=change):
                self.review = copy.deepcopy(original)
                self.review['pages'][0].update(change)
                self.save()
                self.assert_engine_blocked()

    def test_explicit_sheet_issue_blocks_even_with_all_core_roles(self):
        self.review['unresolved_issues'] = ['Cover and title block revision conflict']
        self.save()
        self.assertFalse(read_sheet_review(self.job)['coverage_passed'])
        self.assert_engine_blocked()

    def test_no_index_requires_explanation_and_never_skips_core_roles(self):
        self.review['cover_index'] = []
        self.save()
        self.assert_engine_blocked()
        self.review['no_index_reason'] = 'All five synthetic pages examined; no index printed'
        self.save()
        self.assertTrue(read_sheet_review(self.job)['coverage_passed'])
        self.review['pages'][3]['role'] = 'other'
        self.save()
        self.assertFalse(read_sheet_review(self.job)['coverage_passed'])


if __name__ == '__main__':
    unittest.main()
