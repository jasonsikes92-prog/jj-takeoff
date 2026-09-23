import copy
import unittest

from trade_response_review import review_response, revision_basis


class TradeResponseReview(unittest.TestCase):
    def setUp(self):
        self.scope = {'snapshot_sha256': 'current', 'plan_sha256': 'plan', 'trade': 'test',
            'items': [{'row_id': 'A', 'draft_quantity': 10, 'unit': 'LF', 'issues': ['Field layout unresolved']},
                      {'row_id': 'B', 'draft_quantity': 1, 'unit': 'EA', 'issues': []}]}
        self.meta = {'company': 'Test supplier', 'quote_number': '1', 'quote_date': '2026-09-21',
            'quoted_total': 100, 'delivery_included': 'Yes', 'tax_included': 'Yes'}
        self.rows = [{'scope_id': 'A', 'response': 'Priced separately', 'quoted_quantity': 10,
            'quoted_unit': 'LF', 'unit_price': 10, 'line_amount': 100},
            {'scope_id': 'B', 'response': 'Included in package', 'included_under': 'A'}]

    def review(self):
        return review_response(self.scope, self.meta, self.rows, 'current')

    def test_reconciled_arithmetic_never_approves_pricing_or_source_scope(self):
        originals = copy.deepcopy((self.scope, self.meta, self.rows))
        result = self.review()
        self.assertEqual(result['charged_line_total'], '100')
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['responses'][0]['source_scope_issues'], ['Field layout unresolved'])
        self.assertFalse(result['pricing_approved'])
        self.assertFalse(result['estimate_changed'])
        self.assertEqual(originals, (self.scope, self.meta, self.rows))

    def test_blank_response_is_not_a_zero_quote(self):
        self.rows = [{'scope_id': 'A'}, {'scope_id': 'B'}]
        self.meta = {}
        result = self.review()
        self.assertEqual(result['unanswered_scope_ids'], ['A', 'B'])
        self.assertIsNone(result['charged_line_total'])
        self.assertIsNone(result['total_with_explicit_charges'])
        self.assertTrue(result['issues'])

    def test_missing_duplicate_extra_or_stale_scope_rejected(self):
        for rows in (self.rows[:1], self.rows + self.rows[:1], self.rows + [{'scope_id': 'C'}]):
            with self.assertRaises(ValueError):
                review_response(self.scope, self.meta, rows, 'current')
        with self.assertRaises(ValueError):
            review_response(self.scope, self.meta, self.rows, 'changed')

    def test_included_charge_and_cycles_flagged(self):
        self.rows[1]['line_amount'] = 20
        self.assertTrue(any('duplicate' in i for i in self.review()['responses'][1]['issues']))
        self.rows[0].update(response='Included in package', included_under='B')
        self.assertTrue(all(any('different, separately priced' in i for i in r['issues'])
                            for r in self.review()['responses']))

    def test_established_cost_owner_cannot_be_charged_silently(self):
        self.scope['items'][0]['cost_owner_row_id'] = 'B'
        self.assertTrue(any('another cost owner' in i for i in self.review()['responses'][0]['issues']))

    def test_quantity_rate_unit_and_billing_basis_review(self):
        self.rows[0].update(quoted_quantity=11, quoted_unit='SF', line_amount=100)
        issues = self.review()['responses'][0]['issues']
        for text in ('times rate', 'Quoted unit differs', 'Quoted quantity differs'):
            self.assertTrue(any(text in i for i in issues))
        self.rows[0].update(quoted_quantity=None, unit_price=None)
        self.assertTrue(any('no lump sum inferred' in i for i in self.review()['responses'][0]['issues']))

    def test_invalid_numbers_and_explicit_zero(self):
        for value in (True, -1, 'NaN', 'Infinity', 'bad'):
            self.rows[0]['line_amount'] = value
            self.assertIsNone(self.review()['charged_line_total'])
        self.rows[0].update(line_amount=0, unit_price=0)
        self.meta['quoted_total'] = 0
        self.assertEqual(self.review()['charged_line_total'], '0')
        self.assertEqual(self.review()['issues'], [])

    def test_delivery_tax_and_narrative_are_not_silently_zeroed(self):
        self.meta.update(delivery_included='No', delivery_charge=79, quoted_total=179)
        self.assertEqual(self.review()['total_with_explicit_charges'], '179')
        self.meta['delivery_included'] = 'Yes'
        self.assertIsNone(self.review()['total_with_explicit_charges'])
        self.meta.update(delivery_included='No', other_charges_exclusions='Additional lift rental')
        self.assertIsNone(self.review()['total_with_explicit_charges'])
        self.meta.update(other_charges_exclusions=None, delivery_charge=None)
        self.assertIsNone(self.review()['total_with_explicit_charges'])

    def test_reference_only_cannot_dispose_of_active_work(self):
        self.rows[1] = {'scope_id': 'B', 'response': 'Reference only'}
        self.assertTrue(self.review()['responses'][1]['issues'])
        self.scope['items'][1]['quote_action'] = 'Reference heading only; no separate charge'
        self.assertEqual(self.review()['responses'][1]['issues'], [])

    def test_unchanged_trade_can_use_an_older_response_with_original_source(self):
        self.scope['measurement_version'] = 2
        issued = {**copy.deepcopy(self.scope), 'snapshot_sha256': 'old', 'measurement_version': 1}
        result = revision_basis(self.scope, issued, ['plan','old',1], 'current')
        self.assertTrue(result['trade_content_unchanged'])
        self.assertEqual(result['issued_snapshot_sha256'], 'old')
        for identity in (['plan','forged',1], ['other plan','old',1], ['plan','old',2]):
            with self.assertRaises(ValueError):
                revision_basis(self.scope, issued, identity, 'current')
        with self.assertRaises(ValueError):
            revision_basis(self.scope, issued, ['plan','old',1], 'stale current')

    def test_quantity_ownership_notes_exclusions_and_plan_changes_require_review(self):
        self.scope.update(measurement_version=1, excluded_items=[], additional_scope=[])
        issued = {**copy.deepcopy(self.scope), 'snapshot_sha256':'old'}
        for change in (
            {'items':[{**self.scope['items'][0], 'draft_quantity':11}, self.scope['items'][1]]},
            {'items':[{**self.scope['items'][0], 'covered_by_package':'B'}, self.scope['items'][1]]},
            {'items':[{**self.scope['items'][0], 'issues':['New unresolved detail']}, self.scope['items'][1]]},
            {'excluded_items':[{'row_id':'C'}]}, {'additional_scope':[{'id':'new work'}]},
            {'plan_sha256':'another drawing'},
        ):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError,'Trade scope changed'):
                revision_basis({**self.scope,**change}, issued, ['plan','old',1], 'current')


if __name__ == '__main__':
    unittest.main()
