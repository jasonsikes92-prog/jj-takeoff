import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_estimate import price_draft
from estimating_price_review import accepted_estimating_price


class DatedAllowances(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.draft={'plan_sha256':'plan','measurement_version':2,'rows':[{
            'row_id':'lap','unit':'ft2','cost_type':'SUBCONTRACTOR','markup_pct':'7',
            'draft_quantity':150,'unit_cost':None,'line_cost':None,'line_price':None,
            'certified':False,'assembly_inputs':[]}], 'whole_house_total':None,'estimate_released':False}
        original=self.save('original.txt',{'synthetic':'$240 per square'})
        self.record={'plan_sha256':'plan','original_document':original,'rate':{
            'row_id':'lap','unit':'ft2','unit_price':2.4,'source_unit_price':240,
            'units_per_source_unit':100,'source_unit':'square','date':'2025-10-10',
            'source':'Fixture supplier','scope_reviewed':True,'scope_match':'Installed lap siding',
            'tax_delivery_basis':'Saved installed rate; no separate charges documented',
            'currency':'USD','pricing_basis':'unit_rate','evidence_kind':'dated_supplier_allowance'}}
        self.pricing={'plan_sha256':'plan','measurement_version':1,'rates':[],
            'allowance_authorization':self.save('owner.json',{'answer':'Use saved rates as dated allowances'}),
            'dated_allowances':[self.save('rate.json',self.record)]}

    def save(self,name,record):
        path=self.root/name;path.write_text(json.dumps(record))
        return {'source_file':name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def run_price(self):
        return price_draft(self.draft,self.pricing,'2026-09-17',self.root)

    def test_allowance_keeps_date_and_markup_without_certifying(self):
        result=self.run_price();row=result['rows'][0]
        self.assertEqual((row['unit_cost'],row['line_cost'],row['line_price']),(2.4,360,385.2))
        self.assertIn('2025-10-10',row['price_status']);self.assertIn('allowance',row['price_status'])
        self.assertFalse(row['current_price_certified']);self.assertFalse(row['certified'])
        self.assertTrue(accepted_estimating_price(row))
        self.assertIsNone(result['whole_house_total']);self.assertFalse(result['estimate_released'])
        self.assertIsNone(self.draft['rows'][0]['unit_cost'])

    def test_partial_reference_gets_rate_but_no_total(self):
        self.draft['rows'][0].update(draft_quantity=None,assembly_inputs=[{'quantity':150}])
        row=self.run_price()['rows'][0]
        self.assertEqual(row['unit_cost'],2.4);self.assertIsNone(row['line_cost']);self.assertIsNone(row['line_price'])
        self.assertFalse(accepted_estimating_price(row))

    def test_company_template_allowance_is_not_labeled_supplier_evidence(self):
        self.record['rate'].update(evidence_kind='dated_company_template_allowance',source='Owner template')
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        row=self.run_price()['rows'][0]
        self.assertEqual(row['line_cost'],360)
        self.assertIn('Company-template estimating allowance',row['price_status'])
        self.assertFalse(row['current_price_certified'])
        (self.root/'original.txt').write_text('changed template')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_price()

    def test_withheld_trade_allowance_does_not_break_unrelated_edits(self):
        self.draft['rows']=[]
        for flags in ({},{'saved_trade_review_required':'Geometry changed'}, {'withheld_supplemental_cost_ids':['lap']}):
            trial={**self.draft,**flags}
            with self.assertRaisesRegex(ValueError,'Unknown dated allowance'):
                price_draft(trial,self.pricing,'2026-09-17',self.root)
        self.draft.update(saved_trade_review_required='Geometry changed',withheld_supplemental_cost_ids=['lap'])
        result=self.run_price()
        self.assertEqual(result['unapplied_prices'][0]['row_id'],'lap')
        self.assertEqual(result['rows'],[])
        self.assertNotIn('unapplied_prices',self.draft)
        (self.root/'original.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_price()

    def test_kit_allowance_requires_matching_product_and_model(self):
        self.draft['rows'][0]['quantity_sources']=[{'kind':'reviewed_kit_purchase','product_id':'selected','model':'25045'}]
        with self.assertRaisesRegex(ValueError,'product'):self.run_price()
        self.record['rate'].update(product_id='selected',model='25045')
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        self.assertEqual(self.run_price()['rows'][0]['line_cost'],360)
        self.record['rate']['model']='other'
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        with self.assertRaisesRegex(ValueError,'product'):self.run_price()

    def test_identified_item_allowance_rejects_product_or_model_substitution(self):
        self.material_allowance()
        self.draft['rows'][0]['quantity_sources']=[{'kind':'reviewed_item_purchase','product_id':'knob','model':'privacy'}]
        for product,model in (('wrong','privacy'),('knob','passage'),(None,None),('knob','privacy')):
            self.record['rate'].update(product_id=product,model=model)
            self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
            if (product,model)==('knob','privacy'):
                self.assertEqual(self.run_price()['rows'][0]['line_cost'],516.24)
            else:
                with self.assertRaisesRegex(ValueError,'product'):self.run_price()

    def test_invoice_ratio_preserves_precision_and_reprices_changed_area(self):
        from decimal import Decimal
        rate=str(Decimal('20583')/Decimal('3416.22'))
        self.record['rate'].update(unit_price=rate,source_unit_price=20583,
            units_per_source_unit=3416.22,source_unit='historical job')
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        self.draft['rows'][0]['draft_quantity']=3416.22
        result=self.run_price();row=result['rows'][0]
        self.assertIsInstance(row['unit_cost'],float)
        self.assertEqual(row['price_evidence']['unit_price'],rate)
        self.assertEqual(row['line_cost'],20583)
        self.draft=result;self.draft['rows'][0]['draft_quantity']=3423.2402359751427
        changed=self.run_price()['rows'][0]
        self.assertEqual((changed['line_cost'],changed['line_price']),(20625.3,22069.07))

    def test_latest_compatible_source_wins_independent_of_order(self):
        newer=copy.deepcopy(self.record);newer['rate'].update(date='2026-01-02',unit_price=3,source_unit_price=300)
        self.pricing['dated_allowances'].insert(0,self.save('newer.json',newer))
        self.assertEqual(self.run_price()['rows'][0]['unit_cost'],3)

    def test_current_rate_precedes_allowance_and_expired_rate_falls_back(self):
        self.pricing['measurement_version']=2
        ref=self.save('current.json',{'fixture':'$4 per SF'})
        rate={**self.record['rate'],**ref,'unit_price':4,'date':'2026-09-17',
            'valid_through':'2026-09-20','evidence_kind':'current_supplier_quote'}
        self.pricing['rates']=[rate]
        self.assertEqual(self.run_price()['rows'][0]['unit_cost'],4)
        rate.update(date='2026-09-01',valid_through='2026-09-02')
        self.assertEqual(self.run_price()['rows'][0]['unit_cost'],2.4)

    def test_evidence_and_authorization_changes_are_rejected(self):
        for name in ('owner.json','original.txt','rate.json'):
            path=self.root/name;before=path.read_bytes();path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'hash'):self.run_price()
            path.write_bytes(before)

    def test_invalid_scope_unit_conversion_date_and_source_are_rejected(self):
        for key,value in [('unit','each'),('scope_reviewed',False),('scope_match',''),
                          ('unit_price',3),('unit_price',True),('date','2027-01-01'),
                          ('units_per_source_unit',0),('pricing_basis','package')]:
            record=copy.deepcopy(self.record);record['rate'][key]=value
            self.pricing['dated_allowances']=[self.save('rate.json',record)]
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_price()

    def test_package_excluded_and_input_ownership_rejected(self):
        original=copy.deepcopy(self.draft['rows'][0])
        for key,value in [('covered_by_package','package'),('cost_owner_row_id','extra'),
                          ('completion_status','not_applicable_source_reviewed'),
                          ('cost_type','ASSEMBLY'),('parent','INPUTS')]:
            self.draft['rows'][0]={**original,key:value}
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_price()

    def test_same_date_competing_rates_require_selection(self):
        self.pricing['dated_allowances'].append(self.save('duplicate.json',self.record))
        with self.assertRaisesRegex(ValueError,'Same-date'):self.run_price()

    def test_existing_dated_allowance_recalculates_without_compounding(self):
        self.draft=self.run_price();self.draft['rows'][0]['draft_quantity']=200
        row=self.run_price()['rows'][0]
        self.assertEqual((row['line_cost'],row['line_price']),(480,513.6))

    def material_allowance(self):
        self.draft['rows'][0].update(cost_type='MATERIAL',unit='each',draft_quantity=2,markup_pct='8')
        tax={'plan_sha256':'plan','percent':8,'effective_from':'2026-07-01','effective_through':'2026-09-30',
            'jurisdiction':'Fixture jurisdiction','source':'Fixture tax schedule'}
        reference=self.save('tax.json',tax)
        self.record['rate'].update(unit='each',unit_price=239,source_unit_price=239,units_per_source_unit=1,
            tax_included=False,purchase_tax={**reference,**{k:tax[k] for k in ('percent','effective_from','effective_through')}})
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]

    def test_material_tax_before_markup_and_no_compounding(self):
        self.material_allowance();result=self.run_price();row=result['rows'][0]
        self.assertEqual((row['supplier_cost'],row['purchase_tax'],row['line_cost'],row['line_price']),(478,38.24,516.24,557.54))
        self.assertEqual(row['unit_cost'],239);self.assertEqual(row['purchase_tax_percent'],8)
        self.draft=result;self.assertEqual(self.run_price()['rows'][0]['line_cost'],516.24)
        self.draft['rows'][0]['draft_quantity']=None
        row=self.run_price()['rows'][0];self.assertIsNone(row['line_cost']);self.assertIsNone(row['purchase_tax'])
        self.draft['rows'][0]['draft_quantity']=0
        self.assertEqual(self.run_price()['rows'][0]['line_cost'],0)

    def test_expired_tax_withholds_material_allowance(self):
        self.material_allowance()
        row=price_draft(self.draft,self.pricing,'2026-10-01',self.root)['rows'][0]
        self.assertIsNone(row['unit_cost']);self.assertIsNone(row['line_cost']);self.assertIn('tax evidence',row['price_status'])

    def test_material_requires_explicit_tax_treatment(self):
        self.material_allowance();self.record['rate'].pop('purchase_tax')
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        with self.assertRaisesRegex(ValueError,'tax treatment'):self.run_price()
        self.record['rate']['tax_included']=True
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        self.assertEqual(self.run_price()['rows'][0]['line_cost'],478)

    def test_tax_hash_mismatch_and_double_tax_rejected(self):
        self.material_allowance();(self.root/'tax.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_price()
        self.material_allowance();self.record['rate']['tax_included']=True
        self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
        with self.assertRaisesRegex(ValueError,'pretax'):self.run_price()

    def test_tax_project_percent_and_effective_window_validation(self):
        for key,value in [('plan_sha256','other'),('percent',True),('percent',101),('percent','NaN'),('effective_through','2026-06-30')]:
            self.material_allowance();tax=json.loads((self.root/'tax.json').read_text());tax[key]=value
            ref=self.save('tax.json',tax)
            self.record['rate']['purchase_tax']={**ref,**{k:tax[k] for k in ('percent','effective_from','effective_through')}}
            self.pricing['dated_allowances']=[self.save('rate.json',self.record)]
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.run_price()

if __name__=='__main__':unittest.main()
