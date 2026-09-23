import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from bid_clause_candidates import clause_candidates, clause_findings


def source(text, page=1):
    return [{'page':page,'line':n,'source_text':line,'source_ref':f'evidence:test, page {page}, line {n}'}
            for n,line in enumerate(text.splitlines(),1) if line.strip()]


class BidClauseCandidateTests(unittest.TestCase):
    def test_explicit_terms_and_money_keep_source_without_dollar_inference(self):
        lines = source('Cabinet allowance $8,000, installation by others.\nRock excavation charged separately.\nOwner to supply refrigerator.\nMaterial escalation applies.\nSee attached Exhibit B.')
        before = copy.deepcopy(lines)
        found = clause_candidates(lines)
        self.assertEqual({c['kind'] for c in found}, {'allowance','exclusion','extra_charge','owner_supply','price_change','attachment'})
        self.assertEqual(lines,before)
        self.assertEqual(next(c for c in found if c['kind']=='allowance')['money_text'], ['$8,000'])
        for c in found:
            self.assertIsNone(c['dollar_exposure'])
            self.assertEqual(c['scope_status'],'unclear')
            for m in c['matched_wording']:
                self.assertEqual(c['source_text'][m['start']:m['end']],m['text'])

    def test_heading_context_preserves_heading_and_item_and_resets(self):
        found = clause_candidates(source('EXCLUSIONS:\nGutters and downspouts\nLandscaping\nINCLUDED\nFraming\nALLOWANCES\nCabinets $8,000\nPAYMENT TERMS\nDeposit $10,000'))
        self.assertEqual([(c['kind'],c['line']) for c in found], [('exclusion',2),('exclusion',3),('allowance',7)])
        self.assertEqual([e['desc'] for e in found[0]['evidence_lines']], ['EXCLUSIONS:','Gutters and downspouts'])
        self.assertEqual(found[0]['section_context']['line'],1)

    def test_context_does_not_cross_pages_gaps_or_unrecognized_headings(self):
        lines=source('EXCLUSIONS\nGutters')+source('Framing',page=2)
        self.assertEqual(len(clause_candidates(lines)),1)
        self.assertEqual(clause_candidates(source('EXCLUSIONS\n\nGutters')),[])
        self.assertEqual(clause_candidates(source('EXCLUSIONS\nSpecial instructions:\nFraming')),[])

    def test_negative_and_plain_inclusion_wording_not_positive_risk_cues(self):
        for text in ['No additional cost.', 'Gutters are not excluded.', 'No material escalation.',
                     'No allowance.', 'Includes framing and windows.', 'Total: $300,000',
                     'No exclusions.', 'Installation without extra charges.']:
            self.assertEqual(clause_candidates(source(text)),[],text)

    def test_mixed_and_conditional_wording_stays_unverified(self):
        found=clause_candidates(source('Windows included, gutters excluded unless added by change order.'))
        self.assertEqual(len(found),1)
        self.assertIn('unless',found[0]['source_text'])
        self.assertEqual(found[0]['scope_status'],'unclear')
        self.assertIsNone(found[0]['dollar_exposure'])

    def test_none_under_heading_does_not_create_an_excluded_item(self):
        for value in ('None', 'N/A', 'No exclusions.'):
            self.assertEqual(clause_candidates(source('EXCLUSIONS\n' + value)), [])

    def test_unit_price_and_zero_not_converted_to_allowance_totals(self):
        found=clause_candidates(source('Tile allowance $2.50/SF.\nFixture allowance $0.'))
        self.assertEqual([c['money_text']for c in found],[['$2.50'],['$0']])
        self.assertTrue(all(c['dollar_exposure']is None for c in found))

    def test_stable_ids_change_when_evidence_changes_and_findings_group_sources(self):
        lines=source('EXCLUSIONS\nGutters\nLandscaping\nALLOWANCES\nTile $2.50/SF')
        first=clause_candidates(lines)
        self.assertEqual(first,clause_candidates(lines))
        revised=copy.deepcopy(lines);revised[1]['source_text']='Gutters and drainage'
        self.assertNotEqual(first[0]['id'],clause_candidates(revised)[0]['id'])
        findings=clause_findings(first)
        self.assertEqual(len(findings),2)
        excluded=next(f for f in findings if f['title']=='Review exclusion wording')
        self.assertEqual(len(excluded['evidence_lines']),3)
        self.assertTrue(all(f['realistic_low']is None and f['bid_amount']is None for f in findings))

    def test_supplier_price_validity_and_tariff_exception_preserve_exact_wording(self):
        lines = source('All quoted prices will be honored for a period of 15 days from the date of this aggreement.\nThe exception is government imposed tariffs which will be passed on at the time the tariffs become effective.', page=2)
        found = clause_candidates(lines)
        self.assertEqual([(c['kind'], c['page'], c['line']) for c in found],
                         [('quote_validity', 2, 1), ('price_change', 2, 2)])
        self.assertEqual([c['source_text'] for c in found], [line['source_text'] for line in lines])
        self.assertTrue(all(c['dollar_exposure'] is None and c['scope_status'] == 'unclear' for c in found))
        self.assertTrue(all('expires_at' not in c for c in found))

    def test_validity_variants_and_tariff_references_without_charge_wording(self):
        for wording in ('Quote valid until September 30.', 'Proposal expires in 30 days.',
                        'Prices are held for ten days.', 'Pricing is guaranteed through closing.'):
            self.assertEqual([c['kind'] for c in clause_candidates(source(wording))], ['quote_validity'], wording)
        for wording in ('No tariffs will be passed on.', 'Tariff information is attached.',
                        'This quote is not valid for construction.'):
            self.assertEqual(clause_candidates(source(wording)), [], wording)


if __name__ == '__main__':
    unittest.main()
