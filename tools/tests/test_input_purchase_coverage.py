import copy
import unittest
from component_allowances import quantity_binding
from estimating_price_review import accept_estimating_price
from estimate_readiness import readiness
from input_purchase_coverage import purchase_coverage


class InputPurchaseCoverage(unittest.TestCase):
    def setUp(self):
        self.source = {'file': 'owner.json', 'sha256': 'a' * 64, 'field': 'garage'}
        self.measured = {'id': 'floods', 'quantity': 4, 'unit': 'EA', 'measurement_ids': ['floods'],
                         'template_rows': ['633'], 'linked_review': {'geometry_sha256': 'geometry',
                         'measurement_version': 1, 'job': 'electrical', 'config_sha256': 'config'}}
        mapped = copy.deepcopy(self.measured)
        mapped.update(template_rows=['214'], source_template_rows=['633'])
        mapped['linked_review']['template_row_mapping'] = {'633': '214'}
        self.confirmed = {'id': 'garage', 'quantity': 2, 'unit': 'EA', 'source_kind': 'owner_confirmation',
                          'source': self.source, 'measurement_ids': []}
        self.row = {'row_id': 'exterior', 'draft_quantity': 6, 'unit': 'each',
                    'pricing_basis': 'dated_component_allowance', 'line_cost': 60, 'line_price': 65,
                    'quantity_sources': [{'source_kind': 'owner_and_measured_count', 'unit': 'EA',
                        'owner_confirmed_count': 2, 'source': self.source,
                        'included_assembly_inputs': [mapped], 'quantity': 6}], 'assembly_inputs': [mapped]}
        self.bind(self.row)

    def bind(self, row):
        row['price_evidence'] = {'reviewed_quantity_binding': quantity_binding(row)}
        accept_estimating_price(row, '2026-09-21', 'authorized_dated_allowance')

    def test_mapped_measurement_and_owner_count_share_existing_cost(self):
        for q in (self.measured, self.confirmed):
            self.assertEqual(purchase_coverage(q, [self.row]),
                             {'status': 'covered', 'owner_row_ids': ['exterior']})

    def test_changed_measurement_or_owner_evidence_does_not_hide_gap(self):
        changes = [('quantity', 5), ('unit', 'SF'), ('measurement_ids', ['different'])]
        for key, value in changes:
            q = copy.deepcopy(self.measured); q[key] = value
            self.assertIsNone(purchase_coverage(q, [self.row]))
        for key in ('geometry_sha256', 'measurement_version', 'job', 'config_sha256'):
            q = copy.deepcopy(self.measured); q['linked_review'][key] = 'changed'
            self.assertIsNone(purchase_coverage(q, [self.row]))
        for key in ('file', 'sha256', 'field'):
            q = copy.deepcopy(self.confirmed); q['source'][key] = 'changed'
            self.assertIsNone(purchase_coverage(q, [self.row]))

    def test_stale_price_or_count_and_wrong_owner_do_not_cover(self):
        for key, value in [('line_cost', None), ('line_price', 999), ('draft_quantity', 7),
                           ('pricing_role', 'input_only'), ('covered_by_package', 'other'),
                           ('cost_owner_row_id', 'other')]:
            r = copy.deepcopy(self.row); r[key] = value
            self.assertIsNone(purchase_coverage(self.measured, [r]))
        r = copy.deepcopy(self.row); r['price_evidence']['reviewed_quantity_binding'] = 'stale'
        accept_estimating_price(r, '2026-09-21', 'authorized_dated_allowance')
        self.assertIsNone(purchase_coverage(self.measured, [r]))

    def test_combined_quantity_must_reconcile_even_after_price_review(self):
        for value in (5, -1, True, None):
            r = copy.deepcopy(self.row); r['quantity_sources'][0]['owner_confirmed_count'] = value
            self.bind(r)
            self.assertIsNone(purchase_coverage(self.measured, [r]))
        r = copy.deepcopy(self.row); r['quantity_sources'][0]['included_assembly_inputs'][0]['quantity'] = 4.5
        self.bind(r)
        self.assertIsNone(purchase_coverage(self.measured, [r]))

    def test_zero_requires_explicit_owner_source(self):
        q = copy.deepcopy(self.confirmed); q['quantity'] = 0
        self.assertEqual(purchase_coverage(q, [])['status'], 'owner_excluded')
        for key in ('source_kind', 'source'):
            bad = copy.deepcopy(q); bad.pop(key)
            self.assertIsNone(purchase_coverage(bad, []))
        for value in (False, None, -1):
            bad = copy.deepcopy(q); bad['quantity'] = value
            self.assertIsNone(purchase_coverage(bad, []))

    def test_duplicate_template_and_supplemental_owners_remain_errors(self):
        r = copy.deepcopy(self.row); r['row_id'] = 'duplicate'; self.bind(r)
        self.assertEqual(purchase_coverage(self.measured, [self.row, r])['status'], 'duplicate')
        source = {'row_id': 'lighting', 'excel_row': '633', 'name': 'Lights', 'parent': 'Lighting',
                  'cost_type': 'ALLOWANCE', 'unit': 'ft2', 'markup_pct': '8',
                  'pricing_role': 'input_only', 'assembly_inputs': [self.measured],
                  'assembly_input_cost_owners': {'floods': 'supplemental'}}
        priced = {**self.row, 'excel_row': '214', 'name': 'Exterior', 'parent': 'Electrical',
                  'cost_type': 'ALLOWANCE', 'markup_pct': '8'}
        self.bind(priced)
        draft = {'plan_sha256': 'plan', 'measurement_version': 1, 'rows': [source, priced]}
        report = readiness(draft, {'rows': draft['rows']})
        self.assertIn('Assembly input has multiple purchase owners: floods', report['rows'][0]['issues'])
        self.assertFalse(report['estimate_released'])


if __name__ == '__main__':
    unittest.main()
