import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from hardware_quantity_review import apply_hardware_quantities
from measurement_estimate import price_draft
from kit_purchase_review import import_kit_purchases
import test_opening_quantity_review as fixtures


class HardwareQuantityTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.OpeningQuantities()
        fixture.setUp()
        self.draft, self.schedule = fixture.draft, fixture.schedule
        self.target = {'row_id': 'hardware', 'name': 'Door knobs', 'parent': 'Attic doors and Knobs'}
        self.row = {**self.target, 'excel_row': '156', 'cost_type': 'ALLOWANCE', 'unit': 'each',
            'markup_pct': '8', 'draft_quantity': None, 'assembly_inputs': [], 'quantity_sources': [],
            'completion_status': 'not_yet_reconciled'}
        self.draft['rows'].append(self.row)
        for opening in self.schedule['openings']:
            if opening['role'] == 'interior_door': opening['drawn_panel_count'] = 1
        self.schedule['door_hardware_review'] = {'openings': [
            {'opening_id': 'd1', 'hardware_function': 'privacy'},
            {'opening_id': 'd2', 'hardware_function': 'passage'}]}

    def run_review(self): return apply_hardware_quantities(self.draft, self.schedule, self.target)

    def counts(self, result): return [r['quantity'] for r in result['hardware_quantity_review']['groups']]

    def test_counts_sets_once_and_keeps_package_ownership_unresolved(self):
        before = copy.deepcopy(self.draft)
        result = self.run_review()
        self.assertEqual(self.counts(result), [1, 1, None, None])
        row = result['rows'][-1]
        self.assertEqual(row['pricing_role'], 'input_only')
        self.assertIsNone(row['draft_quantity'])
        self.assertEqual(row['markup_pct'], '8')
        self.assertEqual(len(row['assembly_inputs']), 2)
        self.assertFalse(result['estimate_released'])
        self.assertEqual(self.draft, before)
        rate = {'row_id': 'hardware'}
        with self.assertRaisesRegex(ValueError, 'not billable'):
            price_draft(result, {'plan_sha256': 'plan', 'measurement_version': 1, 'rates': [rate]}, '2026-09-19', '.')

    def test_known_zero_is_different_from_no_group_or_unknown_function(self):
        self.schedule['door_hardware_review']['openings'][0]['hardware_function'] = 'passage'
        self.assertEqual(self.counts(self.run_review()), [0, 2, None, None])
        self.schedule['door_hardware_review']['openings'][0]['hardware_function'] = None
        self.assertEqual(self.counts(self.run_review()), [None]*4)
        self.schedule.pop('door_hardware_review')
        self.assertEqual(self.counts(self.run_review()), [None]*4)

    def test_pocket_sets_require_known_function_and_single_leaf(self):
        pocket = next(o for o in self.schedule['openings'] if o['opening_id'] == 's')
        pocket.update(door_configuration='pocket', drawn_panel_count=1)
        self.schedule['door_hardware_review']['openings'].append({'opening_id': 's', 'hardware_function': 'privacy latch'})
        self.assertEqual(self.counts(self.run_review()), [1, 1, 1, 0])
        pocket['drawn_panel_count'] = 2
        self.assertEqual(self.counts(self.run_review()), [1, 1, None, None])

    def test_stale_missing_or_conflicting_sources_withhold_counts(self):
        for key, value in [('unresolved_opening_ids', ['d1']), ('stale_or_missing_label_ids', ['lost'])]:
            original = self.schedule[key]
            self.schedule[key] = value
            self.assertEqual(self.counts(self.run_review()), [None]*4)
            self.schedule[key] = original
        self.schedule['openings'][1]['drawn_panel_count'] = 2
        self.assertEqual(self.counts(self.run_review()), [None]*4)

    def test_duplicate_owner_prices_exclusions_and_wrong_units_are_rejected(self):
        for key, value in [('unit', 'LF'), ('cost_type', 'LABOR'), ('covered_by_package', 'quote'),
                ('cost_owner_row_id', 'supplier'), ('draft_quantity', 0), ('unit_cost', 0),
                ('assembly_inputs', [{}]), ('completion_status', 'not_applicable')]:
            draft = copy.deepcopy(self.draft)
            draft['rows'][-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                apply_hardware_quantities(draft, self.schedule, self.target)
        result = self.run_review()
        with self.assertRaises(ValueError): apply_hardware_quantities(result, self.schedule, self.target)

    def test_plan_and_revision_identity_are_required(self):
        for key, value in [('plan_sha256', 'other'), ('measurement_version', 999)]:
            schedule = {**self.schedule, key: value}
            with self.assertRaises(ValueError): apply_hardware_quantities(self.draft, schedule, self.target)

    def test_explicit_purchase_owner_uses_one_count_and_inherits_markup(self):
        self.draft['rows'].append({'row_id': 'parent', 'name': self.target['parent'], 'cost_type': 'GROUP'})
        purchase = {'plan_sha256': 'plan', 'row_id': 'privacy-purchase', 'ownership': 'assembly_input',
            'replaces_row_id': 'hardware', 'parent_row_id': 'parent', 'name': 'Privacy set', 'unit': 'each',
            'assembly_input_id': 'opening-hardware-privacy', 'product_status': 'specification_pending',
            'basis': 'Synthetic separate supply review', 'source': 'Synthetic fixture, no actual supplier inclusion claim'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'purchase.json'
            path.write_text(json.dumps(purchase))
            config = {'plan_sha256': 'plan', 'purchases': [{'file': path.name,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]}
            result = import_kit_purchases(self.run_review(), config, root)
            extra = result['additional_cost_rows'][0]
            self.assertEqual((extra['draft_quantity'], extra['markup_pct']), (1, '8'))
            self.assertIsNone(extra['line_cost'])
            with self.assertRaises(ValueError): import_kit_purchases(result, config, root)
            self.schedule['unresolved_opening_ids'] = ['d1']
            self.assertIsNone(import_kit_purchases(self.run_review(), config, root)['additional_cost_rows'][0]['draft_quantity'])


if __name__ == '__main__': unittest.main()
