import copy
import hashlib
import json
import unittest
from tools.component_material_allowances import calculate, public_allowance_catalog


class ComponentAllowances(unittest.TestCase):
    def test_supplier_net_pieces_are_not_multiplied_by_plies(self):
        component={'id':'BM7','label':'2x12 SPF No.2','unit':'EA','quantity':10,'plies':2,
                   'stock_length_ft':8,'scheduled_lf':80,
                   'source_snapshot':{'supplier_layout_sha256':'a'*64}}
        mapping={'component_id':'BM7','quantity_unit':'stick','rate_unit':'EA','sku':'SPF-8',
                 'stock_length_ft':8,'basis':'One scheduled net piece is one whole stock board.',
                 'scheduled_piece_sha256':hashlib.sha256(json.dumps(component,sort_keys=True).encode()).hexdigest()}
        catalog={'rates':[{'sku':'SPF-8','unit':'EA','status':'dated_allowance_candidate',
                          'unit_price':'13.55','date':'2026-09-21','selected_sources':[]}]}
        result=calculate([component],[mapping],catalog)
        self.assertEqual(result['priced_components'][0]['quantity'],10)
        self.assertEqual(result['priced_components'][0]['quantity_unit'],'stick')
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'135.50')
        self.assertFalse(result['purchase_authorized'])
        for change in ({'quantity':12},{'stock_length_ft':10},{'label':'Different grade'},
                       {'source_snapshot':{'supplier_layout_sha256':'b'*64}}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                calculate([{**component,**change}],[mapping],catalog)
        with self.assertRaises(ValueError):
            calculate([component],[{k:v for k,v in mapping.items() if k!='scheduled_piece_sha256'}],catalog)

    def setUp(self):
        self.components=[{'id':'top','label':'Top plate scenario','quantity':72,'unit':'stick',
            'sku':'TOP-SYP2','stock_length_ft':16,'source_snapshot':{'geometry':'a'}},
            {'id':'bottom','quantity':34,'unit':'stick'}]
        self.mappings=[{'component_id':'top','source_sku':'TOP-SYP2','sku':'2416SYP2',
            'stock_length_ft':16,'quantity_unit':'stick','rate_unit':'EA','basis':'One 16-foot SYP No.2 stick'}]
        self.catalog={'rates':[{'sku':'2416SYP2','unit':'EA','date':'2025-12-22',
            'unit_price':'5.00','status':'dated_allowance_candidate','selected_sources':[{'invoice':'100'}]}]}
    def result(self):return calculate(self.components,self.mappings,self.catalog)
    def test_partial_subtotal_and_unpriced_material_remain_distinct(self):
        r=self.result();self.assertEqual(r['priced_component_subtotal_before_tax_delivery_markup'],'360.00')
        self.assertIsNone(r['full_framing_total']);self.assertFalse(r['current_price_certified'])
        self.assertEqual(r['unpriced_components'][0]['component_id'],'bottom')
        self.assertEqual(r['priced_components'][0]['source_date'],'2025-12-22')

    def public_record(self):
        return {'sku':'HD-PT-16','unit':'EA','observed_on':'2026-09-20','unit_price':'14.58',
            'currency':'USD','price_kind':'public_dated_allowance','price_url':'https://example.com/product',
            'description':'2x4x16 treated stock','location_limit':'Store price and availability unverified',
            'tax_included':False,'delivery_included':False}

    def test_public_price_prices_whole_stock_without_certifying_trade_or_geometry(self):
        original=copy.deepcopy(self.catalog)
        catalog=public_allowance_catalog(self.catalog,[self.public_record()],'2026-09-20')
        self.components[0]['quantity']=8;self.mappings[0]['sku']='HD-PT-16'
        r=calculate(self.components,self.mappings,catalog)
        self.assertEqual(r['priced_component_subtotal_before_tax_delivery_markup'],'116.64')
        self.assertEqual(self.catalog,original)
        self.assertIsNone(r['full_framing_total']);self.assertFalse(r['purchase_authorized'])
        self.assertEqual(r['priced_components'][0]['rate_sources'][0]['price_kind'],'public_dated_allowance')
        self.components[0]['quantity']=9
        self.assertEqual(calculate(self.components,self.mappings,catalog)['priced_component_subtotal_before_tax_delivery_markup'],'131.22')

    def test_public_price_rejects_future_invalid_or_duplicate_sources(self):
        for change in ({'observed_on':'2026-09-21'},{'unit_price':'NaN'},{'unit_price':0},
                       {'tax_included':True},{'unit':'LF'},{'price_url':'file:///secret'},
                       {'currency':'CAD'},{'location_limit':''},{'sku':'2416SYP2'}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                public_allowance_catalog(self.catalog,[{**self.public_record(),**change}],'2026-09-20')
        with self.assertRaises(ValueError):
            public_allowance_catalog(self.catalog,[self.public_record(),self.public_record()],'2026-09-20')
    def test_edit_reprices_and_restore_returns_baseline(self):
        first=self.result();self.components[0]['quantity']=73
        self.assertEqual(self.result()['priced_component_subtotal_before_tax_delivery_markup'],'365.00')
        self.components[0]['quantity']=72;self.assertEqual(self.result(),first)
    def test_wrong_unit_grade_length_fraction_and_duplicate_refused(self):
        original=copy.deepcopy(self.components)
        for changes in [{'unit':'LF'},{'sku':'TOP-SPF3'},{'stock_length_ft':12},{'quantity':72.5},{'quantity':True}]:
            self.components=copy.deepcopy(original);self.components[0].update(changes)
            with self.assertRaises(ValueError):self.result()
        self.components=original;self.mappings*=2
        with self.assertRaises(ValueError):self.result()
    def test_conflicting_or_missing_rates_and_missing_candidates_are_not_zero_prices(self):
        self.catalog['rates'][0].update(status='conflicting_latest_sources',unit_price=None)
        result=self.result();self.assertFalse(result['priced_components']);self.assertEqual(len(result['unpriced_components']),2)
        self.assertIsNone(result['full_framing_total'])
        self.components.pop(0);self.assertIn('not present',self.result()['unpriced_components'][0]['reason'])
    def test_zero_quantity_is_not_unknown_and_decimal_rounding_is_explicit(self):
        self.components[0]['quantity']=0;self.assertEqual(self.result()['priced_components'][0]['pretax_extension'],'0.00')
        self.components[0]['quantity']=3;self.catalog['rates'][0]['unit_price']='1.005'
        self.assertEqual(self.result()['priced_components'][0]['pretax_extension'],'3.02')

    def test_each_and_length_inputs_are_not_silently_omitted_from_partial_review(self):
        additions=[{'id':'studs','quantity':232,'unit':'EA'},
                   {'id':'ceiling','quantity':4,'unit':'EA'},
                   {'id':'kits','quantity':2,'unit':'EA'},
                   {'id':'wall-length','quantity':267.52,'unit':'LF'}]
        self.components.extend(additions);original=copy.deepcopy(self.components)
        result=self.result()
        unpriced={r['component_id']:r for r in result['unpriced_components']}
        self.assertEqual(set(unpriced),{'bottom',*(r['id'] for r in additions)})
        for source in additions:
            item=unpriced[source['id']]
            self.assertEqual((item['quantity'],item['unit']),(source['quantity'],source['unit']))
            self.assertIn('no stock quantity or price assumed',item['reason'])
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'360.00')
        self.assertIsNone(result['full_framing_total'])
        self.assertEqual(self.components,original)

    def test_unmapped_source_changes_and_absence_follow_current_inputs(self):
        self.components.append({'id':'studs','quantity':232,'unit':'EA'})
        initial=self.result()
        self.components[-1]['quantity']=233
        self.assertEqual(self.result()['unpriced_components'][-1]['quantity'],233)
        self.components[-1]['quantity']=0
        self.assertEqual(self.result()['unpriced_components'][-1]['quantity'],0)
        self.components.pop()
        self.assertNotIn('studs',[r['component_id'] for r in self.result()['unpriced_components']])
        self.assertEqual(initial['priced_components'],self.result()['priced_components'])


if __name__=='__main__':unittest.main()
