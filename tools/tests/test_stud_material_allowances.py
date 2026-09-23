import copy
import unittest
from stud_material_allowances import apply, COMPONENTS


class StudMaterialAllowances(unittest.TestCase):
    def setUp(self):
        members=[{'id':'field:F1','source_id':'F1','kind':'field','sku':'precut'},
                 {'id':'field:F2','source_id':'F2','kind':'field','sku':'long'},
                 {'id':'king:O1','source_id':'O1','kind':'king_studs','sku':'precut'},
                 {'id':'corner:C1','source_id':'C1','kind':'junction_studs','sku':'long'}]
        self.components=[{'id':identity,'unit':'EA','quantity':sum(m['kind']==kind for m in members),
            'component_ids':[m['source_id'] for m in members if m['kind']==kind]}
            for kind,identity in COMPONENTS.items()]
        self.study={'priced_components':[{'component_id':'roof','pretax_extension':'100.00'}],
            'unpriced_components':[{'component_id':c['id']} for c in self.components]+[{'component_id':'jacks'}],
            'separately_owned_components':[], 'priced_component_subtotal_before_tax_delivery_markup':'100.00',
            'full_framing_total':None,'current_price_certified':False}
        first={'id':'low','members':members,'pending_members':[],'unpriced_stock':[],
            'stock_quantities':{'precut':2,'long':2},
            'boards':[{'id':m['id'],'sku':m['sku'],'cuts':[{'piece_id':m['id']}]} for m in members],
            'priced_stock':[{'sku':sku,'unit':'EA','quantity':2,'unit_price':price,
                'pretax_extension':total,'date':'2026-01-07','sources':[{'invoice':'saved'}]}
                for sku,price,total in [('precut','3.82','7.64'),('long','5.56','11.12')]]}
        second=copy.deepcopy(first);second['id']='high'
        self.review={'status':'unselected_height_scenarios','selected_scenario':None,'config_sha256':'config',
            'measurement_dependencies':[],'source_hashes':{},'source_pdf_hashes':{},'assumptions':[],
            'remaining':['Jacks and other stud scope'],'scenarios':[first,second]}

    def result(self):
        result=copy.deepcopy(self.study);apply(result,self.components,self.review);return result

    def test_selected_scenario_does_not_require_unselected_comparison_to_agree(self):
        self.review['status']='selected_height_scenario';self.review['selected_scenario']='high'
        self.review['scenarios'][0]['unpriced_stock']=['missing comparison product']
        result=self.result()
        self.assertTrue(result['stud_stock_mapping']['applied'])
        self.assertEqual(result['stud_stock_mapping']['scenario_ids'],['high'])
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'118.76')

    def test_selected_scenario_still_requires_its_own_complete_members_and_prices(self):
        self.review['status']='selected_height_scenario';self.review['selected_scenario']='high'
        self.review['scenarios'][1]['pending_members']=[{'id':'unlocated'}]
        self.assertFalse(self.result()['stud_stock_mapping']['applied'])

    def test_missing_duplicate_or_stale_height_selection_is_rejected(self):
        self.review['status']='selected_height_scenario';self.review['selected_scenario']='missing'
        with self.assertRaises(ValueError):self.result()
        self.review['selected_scenario']='high';self.review['scenarios'].append(copy.deepcopy(self.review['scenarios'][1]))
        with self.assertRaises(ValueError):self.result()
        self.review['scenarios'].pop();self.review['status']='withheld_geometry_changed'
        with self.assertRaises(ValueError):self.result()

    def test_agreed_purchases_replace_counts_without_double_charging(self):
        before=copy.deepcopy((self.study,self.components,self.review));result=self.result()
        self.assertIn('wall-height decision remains open',result['stud_stock_mapping']['reason'])
        self.assertIn('no height selected',result['priced_components'][1]['product_match_basis'])
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'118.76')
        self.assertEqual(result['unpriced_components'],[{'component_id':'jacks'}])
        purchases=result['priced_components'][1:]
        self.assertEqual(sum(p['quantity'] for p in purchases),4)
        self.assertEqual(sum(sum(p['member_allocations'].values()) for p in purchases),4)
        self.assertEqual(set(result['stud_stock_mapping']['included_component_ids']),set(COMPONENTS.values()))
        self.assertIsNone(result['stud_stock_mapping']['selected_scenario'])
        self.assertIsNone(result['full_framing_total']);self.assertFalse(result['current_price_certified'])
        self.assertEqual((self.study,self.components,self.review),before)

    def test_same_count_different_locations_or_units_stays_unpriced(self):
        for change in ('location','count','unit','duplicate'):
            with self.subTest(change=change):
                self.setUp()
                if change=='location':self.components[0]['component_ids'][0]='different'
                elif change=='count':self.components[0]['quantity']=3
                elif change=='unit':self.components[0]['unit']='LF'
                else:self.components[0]['component_ids']=['F1','F1']
                result=self.result();self.assertFalse(result['stud_stock_mapping']['applied'])
                self.assertEqual(result['priced_components'],self.study['priced_components'])
                self.assertEqual(len(result['unpriced_components']),4)

    def test_changed_geometry_or_pending_members_and_prices_are_withheld(self):
        for change in ('geometry','members','prices'):
            self.setUp()
            if change=='geometry':self.review.update(status='withheld_geometry_changed',scenarios=[])
            elif change=='members':self.review['scenarios'][0]['pending_members']=[{'id':'missing'}]
            else:self.review['scenarios'][0]['unpriced_stock']=['precut']
            result=self.result();self.assertFalse(result['stud_stock_mapping']['applied'])
            self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'100.00')

    def test_different_scenario_rate_is_not_silently_selected(self):
        rate=self.review['scenarios'][1]['priced_stock'][0]
        rate.update(unit_price='4.00',pretax_extension='8.00')
        result=self.result();self.assertFalse(result['stud_stock_mapping']['applied'])
        self.assertIn('different stock or prices',result['stud_stock_mapping']['reason'])

    def test_duplicate_members_or_missing_board_cuts_are_rejected(self):
        self.review['scenarios'][0]['members'].append(self.review['scenarios'][0]['members'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.result()
        self.setUp();self.review['scenarios'][0]['boards'].pop()
        with self.assertRaisesRegex(ValueError,'exactly once'):self.result()

    def test_board_product_or_purchase_quantity_mismatch_is_rejected(self):
        self.review['scenarios'][0]['boards'][0]['sku']='long'
        with self.assertRaisesRegex(ValueError,'product'):self.result()
        self.setUp();self.review['scenarios'][0]['priced_stock'][0]['quantity']=3
        with self.assertRaisesRegex(ValueError,'counts or units'):self.result()

    def test_existing_cost_ownership_and_invalid_extensions_are_rejected(self):
        self.study['priced_components'].append({'component_id':COMPONENTS['field'],'pretax_extension':'1.00'})
        with self.assertRaisesRegex(ValueError,'cost owner'):self.result()
        self.setUp()
        for scenario in self.review['scenarios']:scenario['priced_stock'][0]['pretax_extension']='1.00'
        with self.assertRaisesRegex(ValueError,'extension'):self.result()

    def test_incompatible_scenario_stock_allocation_stays_separate(self):
        scenario=self.review['scenarios'][1]
        scenario['members'][0]['sku']='long';scenario['members'][1]['sku']='precut'
        scenario['boards'][0]['sku']='long';scenario['boards'][1]['sku']='precut'
        result=self.result();self.assertFalse(result['stud_stock_mapping']['applied'])

    def test_jack_blanks_replace_only_the_matching_component(self):
        self.components.append({'id':'wall-component-jack_studs','unit':'EA','quantity':2,'component_ids':['O1']})
        self.study['unpriced_components'][-1]={'component_id':'wall-component-jack_studs'}
        for scenario in self.review['scenarios']:
            scenario['jack_stock_allowance']=True
            for n in range(2):
                identity=f'jack:O1:{n}'
                scenario['members'].append({'id':identity,'source_id':'O1','kind':'jack_studs','sku':'precut'})
                scenario['boards'].append({'id':identity,'sku':'precut','cuts':[{'piece_id':identity}]})
            scenario['stock_quantities']['precut']=4
            scenario['priced_stock'][0].update(quantity=4,pretax_extension='15.28')
        result=self.result()
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'126.40')
        self.assertEqual(result['unpriced_components'],[])
        self.assertIn('wall-component-jack_studs',result['stud_stock_mapping']['included_component_ids'])
        self.components[-1]['component_ids']=['another-door']
        self.assertFalse(self.result()['stud_stock_mapping']['applied'])

    def test_scenarios_cannot_mix_jack_scope(self):
        self.review['scenarios'][0]['jack_stock_allowance']=True
        result=self.result()
        self.assertFalse(result['stud_stock_mapping']['applied'])
        self.assertEqual(result['priced_components'],self.study['priced_components'])


if __name__=='__main__':unittest.main()
