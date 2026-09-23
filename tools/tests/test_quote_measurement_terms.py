import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from quote_measurement_terms import extract_terms
from quote_intake import intake_quote


class MeasurementTerms(unittest.TestCase):
    def terms(self,text):return extract_terms([{'page':1,'text':text}])

    def test_explicit_values_have_page_line_sources_without_price_assignment(self):
        result=self.terms('Scope\nNo deductions for windows or doors.\nBilling waste: 0%\nMaterial waste: 10%')
        self.assertEqual([(c['field'],c['value']) for c in result['candidates']],
            [('deduct_window_door_openings',False),('billing_waste_percent','0'),('material_purchase_waste_percent','10')])
        self.assertEqual([c['line'] for c in result['candidates']],[2,3,4])
        self.assertTrue(all(not c['reviewed'] and not c['pricing_line_ids'] and not c['scope_ids'] for c in result['candidates']))
        self.assertEqual(result['automatic_pricing_assertions'],0)

    def test_supported_positive_negative_and_decimal_wording(self):
        cases={'No opening deductions.':False,'Do not deduct openings.':False,'Windows and doors are not deducted.':False,
            'Opening deductions: none':False,'Deduct window and door openings.':True,
            'Opening deductions: yes':True,'Windows and doors are deducted.':True}
        for text,value in cases.items():
            with self.subTest(text=text):self.assertIs(self.terms(text)['candidates'][0]['value'],value)
        self.assertEqual(self.terms('No added billing waste')['candidates'][0]['value'],'0')
        self.assertEqual(self.terms('2.50% billing waste')['candidates'][0]['value'],'2.5')

    def test_conditions_thresholds_questions_and_unspecified_waste_stay_uninterpreted(self):
        for text in ['No deductions for windows or doors unless larger than 32 SF.',
                'Openings over 32 SF are deducted.','No deductions for windows or doors?',
                'Billing waste: 10% if measured by floor area','Includes 10% waste',
                'Waste allowance: 10%','Billing waste: -5%','Billing waste: 5-10%']:
            with self.subTest(text=text):
                candidates=self.terms(text)['candidates'];self.assertEqual(len(candidates),1)
                self.assertIsNone(candidates[0]['field']);self.assertIsNone(candidates[0]['value'])
        self.assertEqual(self.terms('Waste disposal included.\n4 window openings.')['candidates'],[])

    def test_wrapped_and_blank_pages_do_not_invent_a_value(self):
        result=extract_terms([{'page':1,'text':'Billing waste:\n10%'},{'page':2,'text':''}])
        self.assertEqual(len(result['candidates']),1)
        self.assertIsNone(result['candidates'][0]['value'])
        self.assertFalse(result['complete_document_review'])

    def test_differing_values_are_retained_without_selecting_a_winner(self):
        result=extract_terms([{'page':1,'text':'Billing waste: 0%\nMaterial waste: 10%'},
            {'page':2,'text':'Billing waste: 10.0%\nBilling waste: 10%'}])
        self.assertEqual([c['value'] for c in result['candidates']],['0','10','10','10'])
        self.assertEqual(len(result['fields_with_multiple_values']),1)
        self.assertEqual(result['fields_with_multiple_values'][0]['field'],'billing_waste_percent')
        self.assertEqual(len(result['fields_with_multiple_values'][0]['candidate_ids']),3)
        self.assertEqual(len({c['id'] for c in result['candidates']}),4)

    def test_quote_intake_saves_source_bound_candidates_without_filling_reviewed_quote(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'quote.txt';raw=b'No deductions for windows or doors.\nBilling waste: 0%'
            source.write_bytes(raw);folder=root/'intake'
            scope={'plan_sha256':'drawing','measurement_version':1,'items':[{'id':'work','label':'Drywall'}]}
            summary=intake_quote(source,folder,scope,'test')
            candidates=json.loads((folder/'measurement_term_candidates.json').read_text())
            self.assertEqual(summary['measurement_term_candidate_count'],2)
            self.assertEqual(candidates['source_sha256'],hashlib.sha256(raw).hexdigest())
            quote=json.loads((folder/'quotes.json').read_text())[0]
            self.assertFalse(quote['reviewed']);self.assertNotIn('pricing_lines',quote)
            self.assertIsNone(quote['total']);self.assertEqual(quote['scope_items'][0]['status'],'unknown')
