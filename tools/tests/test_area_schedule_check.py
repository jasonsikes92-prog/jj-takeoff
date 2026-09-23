import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from area_schedule_check import compare


class AreaScheduleCheck(unittest.TestCase):
    def setUp(self):
        self.references = [{'page': 2, 'rows': [{'label': 'HEATED AREA', 'sqft': 100}]}]
        self.measurements = [{'id': 'floor', 'kind': 'area', 'source_area_label': 'Heated Area',
            'page': 2, 'points': [[0, 0], [10, 0], [10, 10], [0, 10]],
            'points_per_foot': 1, 'width_pt': 100, 'height_pt': 100}]

    def test_agreement_is_not_approval_and_does_not_mutate_inputs(self):
        before = copy.deepcopy(self.measurements)
        result = compare(self.references, self.measurements)
        self.assertEqual(result['status'], 'within_tolerance')
        self.assertFalse(result['certified'])
        self.assertFalse(result['estimate_released'])
        self.assertEqual(self.measurements, before)

    def test_edit_flags_discrepancy_and_changes_fingerprint(self):
        before = compare(self.references, self.measurements)
        self.measurements[0]['points'][1][0] = 12
        self.measurements[0]['points'][2][0] = 12
        after = compare(self.references, self.measurements)
        self.assertEqual(after['rows'][0]['status'], 'discrepancy')
        self.assertAlmostEqual(after['rows'][0]['difference_percent'], 20)
        self.assertNotEqual(before['input_sha256'], after['input_sha256'])

    def test_duplicate_labels_are_not_summed_or_silently_matched(self):
        self.references[0]['rows'] *= 2
        self.assertEqual(compare(self.references, self.measurements)['rows'][0]['status'], 'ambiguous_scope')

    def test_missing_geometry_and_wrong_page_remain_open(self):
        self.measurements[0]['page'] = 3
        result = compare(self.references, self.measurements)
        self.assertEqual({r['status'] for r in result['rows']}, {'measurement_missing', 'printed_reference_missing'})

    def test_projected_area_not_slope_factor(self):
        self.measurements[0]['surface_factor'] = 1.5
        self.assertEqual(compare(self.references, self.measurements)['rows'][0]['measured_sf'], 100)

    def test_empty_or_zero_reference_never_passes(self):
        self.assertEqual(compare([], [])['status'], 'no_comparable_scope')
        self.references[0]['rows'][0]['sqft'] = 0
        self.assertEqual(compare(self.references, self.measurements)['status'], 'review_required')


if __name__ == '__main__':
    unittest.main()
