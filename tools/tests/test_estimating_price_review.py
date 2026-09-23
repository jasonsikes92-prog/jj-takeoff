import copy
import unittest
from estimating_price_review import accept_estimating_price, accepted_estimating_price
from estimate_readiness import readiness


class EstimatingPriceReview(unittest.TestCase):
    def setUp(self):
        self.row = {'row_id': '1', 'excel_row': '1', 'name': 'Fixture', 'parent': 'Bath',
            'cost_type': 'MATERIAL', 'unit': 'each', 'markup_pct': 8,
            'draft_quantity': 2, 'unit_cost': 10, 'line_cost': 20, 'line_price': 21.6,
            'price_evidence': {'source': 'validated fixture source'},
            'pricing_basis': 'dated_allowance', 'certified': False,
            'current_price_certified': False}

    def report(self, row):
        return readiness({'plan_sha256': 'plan', 'measurement_version': 1, 'rows': [row]},
                         {'rows': [self.row]})

    def test_acceptance_keeps_quantity_check_and_supplier_warning(self):
        row = copy.deepcopy(self.row)
        accept_estimating_price(row, '2026-09-20', 'authorized_dated_allowance')
        report = self.report(row); detail = report['rows'][0]
        self.assertEqual(detail['issues'], ['Quantity and assembly certification outstanding'])
        self.assertEqual(len(detail['warnings']), 1)
        self.assertEqual(report['accepted_estimating_price_rows'], 1)
        self.assertFalse(row['current_price_certified'])
        self.assertFalse(report['estimate_released']); self.assertIsNone(report['whole_house_total'])

    def test_changes_reopen_acceptance_including_same_total_different_mix(self):
        row = copy.deepcopy(self.row)
        accept_estimating_price(row, '2026-09-20', 'authorized_dated_allowance')
        for key, value in [('draft_quantity', 3), ('unit', 'box'), ('line_cost', 21),
                           ('line_price', 0), ('unit_cost', 11), ('markup_pct', 15),
                           ('price_evidence', {'source': 'changed'}),
                           ('quantity_sources', [{'kind': 'different mix', 'quantity': 2}]),
                           ('covered_by_package', 'other')]:
            changed = copy.deepcopy(row); changed[key] = value
            self.assertFalse(accepted_estimating_price(changed), key)
        changed = copy.deepcopy(row); changed['line_cost'] = None
        self.assertIn('Current line pricing unresolved', self.report(changed)['rows'][0]['issues'])

    def test_missing_or_invalid_amounts_never_receive_acceptance(self):
        for amount in (None, True, -1, float('nan'), float('inf')):
            row = copy.deepcopy(self.row); row['line_cost'] = amount
            accept_estimating_price(row, '2026-09-20', 'owner_estimating_rate')
            self.assertFalse(accepted_estimating_price(row))
        self.assertFalse(accepted_estimating_price(self.row))
        self.assertIn('Current price certification outstanding', self.report(self.row)['rows'][0]['issues'])

    def test_supplemental_keeps_acceptance_warning_without_certifying_quantity(self):
        parent = {**self.row, 'cost_type': 'ASSEMBLY', 'name': 'Bath',
                  'line_cost': None, 'line_price': None}
        extra = {**self.row, 'row_id': 'extra', 'parent_row_id': '1'}
        accept_estimating_price(extra, '2026-09-20', 'owner_estimating_rate')
        report = readiness({'plan_sha256': 'plan', 'measurement_version': 1,
            'rows': [parent], 'additional_cost_rows': [extra]}, {'rows': [parent]})
        detail = report['additional_cost_rows'][0]
        self.assertTrue(detail['estimating_price_accepted']); self.assertEqual(len(detail['warnings']), 1)
        self.assertEqual(detail['issues'], ['Quantity and assembly certification outstanding'])


if __name__ == '__main__':
    unittest.main()
