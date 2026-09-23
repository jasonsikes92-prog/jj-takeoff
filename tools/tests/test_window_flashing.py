import copy
import hashlib
import json
import unittest
from window_flashing import flashing_takeoff
import test_window_snapshot_bridge as fixtures


class WindowFlashingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WindowSnapshotTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        for a, w, h in zip(f.saved['material_schedule']['assemblies'], (108, 72), (72, 60)):
            a.update(rough_opening_width_in=w, rough_opening_height_in=h)
        f.draft['rows'].append({'row_id':'113', 'excel_row':'113', 'unit':'roll',
                               'cost_type':'MATERIAL', 'draft_quantity':None, 'line_cost':None})
        self.rule = {'roll_length_ft':50, 'tape_width_in':6, 'sill_upturn_in':2,
                     'jamb_extension_in':2, 'head_extension_in':6, 'corner_piece_in':12}
        self.basis = {'plan_sha256':'plan', 'status':'estimating_allowance',
                      'basis':'Test allowance', 'assumptions':['Site-cut corners'],
                      'remaining':['Installation method not approved'], 'product':'Test roll',
                      'documents':[{'file':'spec.pdf', 'sha256':hashlib.sha256((f.root/'spec.pdf').read_bytes()).hexdigest()}],
                      'cut_rule':self.rule}
        self.save_basis()

    def save_basis(self):
        f = self.fixture
        path = f.root/'flashing.json'; path.write_text(json.dumps(self.basis))
        f.mapping['flashing'] = {'row_id':'113', 'file':path.name,
                                 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_opening_groups_not_individual_panes_and_no_certification(self):
        f = self.fixture; before = copy.deepcopy(f.draft)
        result = f.run_import(); row = result['rows'][-1]; q = row['quantity_sources'][0]
        # Two physical opening perimeters total 52 ft, plus 4 ft of cuts per opening.
        self.assertEqual(q['rough_opening_perimeter_ft'], 52)
        self.assertEqual(q['cut_length_ft'], 60)
        self.assertEqual(len(q['cuts']), 12)
        self.assertEqual(row['draft_quantity'], 2)
        self.assertAlmostEqual(q['packing']['unused_length_ft'], 40)
        self.assertFalse(row['certified']); self.assertFalse(q['order_released'])
        self.assertFalse(result['estimate_released']); self.assertEqual(f.draft, before)

    def test_changed_opening_changes_quantity_and_instances_remain_unique(self):
        assemblies = copy.deepcopy(self.fixture.saved['material_schedule']['assemblies'])
        assemblies[0]['assembly_quantity'] = 4
        result = flashing_takeoff(assemblies, self.rule)
        self.assertEqual(result['cut_length_ft'], 162)
        self.assertEqual(result['quantity'], 4)
        self.assertEqual(len({c['run_id'] for c in result['cuts']}), 30)
        packed = [c for s in result['packing']['stocks'] for c in s['cuts']]
        self.assertCountEqual(packed, result['cuts'])

    def test_changed_evidence_and_plan_are_rejected(self):
        (self.fixture.root/'flashing.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence'):self.fixture.run_import()
        self.basis['plan_sha256'] = 'other'; self.save_basis()
        with self.assertRaisesRegex(ValueError, 'matching plan'):self.fixture.run_import()
        self.basis['plan_sha256'] = 'plan'
        self.basis['documents'][0]['sha256'] = '0'*64; self.save_basis()
        with self.assertRaisesRegex(ValueError, 'evidence'):self.fixture.run_import()

    def test_missing_schedule_and_existing_purchase_owner_are_rejected(self):
        self.fixture.mapping.pop('material_row_id')
        with self.assertRaisesRegex(ValueError, 'verified material'):self.fixture.run_import()
        self.fixture.mapping['material_row_id'] = '112'
        self.fixture.draft['rows'][-1]['covered_by_package'] = 'framing'
        with self.assertRaisesRegex(ValueError, 'already assigned'):self.fixture.run_import()

    def test_invalid_dimensions_and_oversized_strip_are_not_silently_priced(self):
        for value in (None, True, 0, -1, float('nan')):
            rule = dict(self.rule, roll_length_ft=value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                flashing_takeoff(self.fixture.saved['material_schedule']['assemblies'], rule)
        assemblies = copy.deepcopy(self.fixture.saved['material_schedule']['assemblies'])
        assemblies[0]['rough_opening_width_in'] = 600
        with self.assertRaisesRegex(ValueError, 'fit stock'):flashing_takeoff(assemblies, self.rule)
        assemblies[0] = copy.deepcopy(assemblies[1])
        with self.assertRaisesRegex(ValueError, 'Unique'):flashing_takeoff(assemblies, self.rule)


if __name__ == '__main__':unittest.main()
