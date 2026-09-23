import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from package_pricing import price_packages,scope_digest
from measurement_estimate import price_draft
from estimate_readiness import readiness
from package_quantity_review import current_package_quantity_review


class Packages(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        raw=b'Synthetic complete quote';(self.root/'quote.txt').write_bytes(raw)
        self.draft={'plan_sha256':'plan','measurement_version':3,'rows':[
            {'row_id':i,'unit':'each','cost_type':'SUBCONTRACTOR','parent':'Electrical','markup_pct':'7',
             'completion_status':'evidence_in_progress','draft_quantity':None,'line_cost':None,'line_price':None}
            for i in ('package','alternate')]}
        scope={'plan_sha256':'plan','measurement_version':3,'items':[{'id':'all','label':'Complete electrical scope'}]}
        quote={'id':'quote','supplier':'Test supplier','source_file':'quote.txt',
            'source_sha256':hashlib.sha256(raw).hexdigest(),'date':'2026-09-01','valid_through':'2026-09-30',
            'currency':'USD','total':'1000.01','reviewed':True,'reviewed_scope_sha256':scope_digest(scope),
            'evidence_kind':'current_subcontractor_quote','scope_items':[{'scope_id':'all','status':'included','source_ref':'page 1'}]}
        self.package={'scope':scope,'quotes':[quote],'quote_id':'quote','row_id':'package',
            'covered_row_ids':['package','alternate'],'scope_mapping_reviewed':True,
            'reviewed_draft_sha256':scope_digest(self.draft)}

    def run_package(self):return price_packages(self.draft,[self.package],'2026-09-16',self.root)

    def test_each_package_retains_scope_limits_without_changing_price(self):
        self.package['scope_note']='One installation only; future service and permits are separate.'
        row=self.run_package()['rows'][0]
        self.assertEqual(row['price_evidence']['scope_note'],self.package['scope_note'])
        self.assertEqual(row['draft_quantity'],1)
        self.assertEqual(row['line_cost'],1000.01)

    def install_count_review(self):
        self.package['billing_basis']='fixed_package'
        source=self.root/'count.json'
        source.write_text(json.dumps({'plan_sha256':'plan','row_id':'package','quantity':1,
            'unit':'each','basis':'One electrical contract, rough and trim installments',
            'quote_source_sha256':self.package['quotes'][0]['source_sha256']}))
        self.package['package_count_review']={'source_file':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        return source

    def test_documented_package_count_preserves_unmeasured_child_scope(self):
        self.install_count_review()
        for n,row in enumerate(self.draft['rows']):row.update(excel_row=str(n+2),name=row['row_id'])
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package();row=result['rows'][0]
        self.assertEqual(row['draft_quantity'],1)
        self.assertIsNone(row['unit_cost'])
        self.assertEqual(row['line_cost'],1000.01)
        self.assertEqual(row['line_price'],1070.01)
        self.assertEqual(row['price_evidence']['billing_basis'],'fixed_package')
        self.assertTrue(current_package_quantity_review(row,'plan',3))
        self.assertIsNot(row.get('certified'),True)
        report=readiness(result,{'rows':self.draft['rows']})
        self.assertNotIn('Quantity and assembly certification outstanding',report['rows'][0]['issues'])
        self.assertTrue(any('Billing package count verified' in w for w in report['rows'][0]['warnings']))
        child=readiness(result,{'rows':self.draft['rows']})['rows'][1]
        self.assertIn('Quantity unresolved',child['issues'])
        self.assertIn('Quantity and assembly certification outstanding',child['issues'])
        self.assertIsNone(self.draft['rows'][0]['draft_quantity'])

    def test_billing_count_reopens_when_quantity_scope_or_source_changes(self):
        self.install_count_review();row=self.run_package()['rows'][0]
        for change in ({'draft_quantity':2},{'draft_quantity':True},{'unit':'sq ft'},
                       {'unit_cost':1000.01},{'covered_by_package':'other'},
                       {'quantity_sources':[]},{'line_cost':999},{'completion_status':'not_applicable'}):
            changed=copy.deepcopy(row);changed.update(change)
            with self.subTest(change=change):
                self.assertFalse(current_package_quantity_review(changed,'plan',3))
        changed=copy.deepcopy(row);changed['price_evidence']['scope_note']='Changed coverage'
        self.assertFalse(current_package_quantity_review(changed,'plan',3))
        changed=copy.deepcopy(row);changed['price_evidence']['package_count_review']['source_sha256']='other'
        self.assertFalse(current_package_quantity_review(changed,'plan',3))
        self.assertFalse(current_package_quantity_review(row,'other',3))
        self.assertFalse(current_package_quantity_review(row,'plan',4))

    def test_package_price_alone_does_not_verify_billing_count(self):
        self.package['billing_basis']='fixed_package'
        row=self.run_package()['rows'][0]
        self.assertNotIn('package_quantity_review',row)
        self.assertFalse(current_package_quantity_review(row,'plan',3))

    def test_supplemental_billing_count_retains_unpriced_and_unmeasured_scope(self):
        self.supplemental()
        source=self.install_count_review()
        record=json.loads(source.read_bytes());record['row_id']='extra'
        source.write_text(json.dumps(record))
        self.package['package_count_review']['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        self.package['unpriced_scope']=['Excavation']
        result=self.run_package();row=result['additional_cost_rows'][0]
        self.assertTrue(current_package_quantity_review(row,'plan',3))
        result['pending_quantities']=[{'label':'Service trench route','row_ids':['extra'],'template_rows':[]}]
        report=readiness(result,{'rows':self.draft['rows']})['additional_cost_rows'][0]
        self.assertNotIn('Quantity and assembly certification outstanding',report['issues'])
        self.assertIn('Unpriced package scope: Excavation',report['issues'])
        self.assertIn('Measurement scope review outstanding: Service trench route',report['issues'])
        self.assertIs(row['certified'],False)

    def test_verified_billing_count_does_not_hide_missing_scope(self):
        self.install_count_review()
        for n,row in enumerate(self.draft['rows']):row.update(excel_row=str(n+2),name=row['row_id'])
        self.package['unpriced_scope']=['Permit fees']
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package()
        result['pending_quantities']=[{'label':'Unmeasured route','template_rows':['2']}]
        report=readiness(result,{'rows':self.draft['rows']})
        self.assertIn('Unpriced package scope: Permit fees',report['rows'][0]['issues'])
        self.assertIn('Measurement scope review outstanding: Unmeasured route',report['rows'][0]['issues'])
        self.assertIn('Quantity unresolved',report['rows'][1]['issues'])
        self.assertFalse(report['estimate_released'])

    def test_package_count_requires_unchanged_evidence_and_one_each(self):
        source=self.install_count_review()
        original=source.read_bytes()
        source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'count review evidence changed'):self.run_package()
        source.write_bytes(original)
        for value in (0,2,True):
            self.draft['rows'][0]['draft_quantity']=value
            self.package['reviewed_draft_sha256']=scope_digest(self.draft)
            with self.assertRaisesRegex(ValueError,'conflicts'):self.run_package()
        self.draft['rows'][0].update(draft_quantity=None,unit='sq ft')
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'matching each row'):self.run_package()

    def test_total_markup_and_exclusive_ownership_preserved(self):
        result=self.run_package();row=result['rows'][0]
        self.assertEqual(row['line_cost'],1000.01);self.assertEqual(row['line_price'],1070.01)
        self.assertEqual(row['draft_quantity'],1)
        self.assertIsNone(result['rows'][1]['line_cost'])
        self.assertEqual(result['rows'][1]['covered_by_package'],'package')
        self.assertIsNone(self.draft['rows'][0]['line_cost'])
        self.assertIsNone(result['whole_house_total']);self.assertFalse(result['estimate_released'])
        with self.assertRaisesRegex(ValueError,'covered by a package'):
            price_draft(result,{'plan_sha256':'plan','measurement_version':3,'rates':[{'row_id':'alternate'}]},'2026-09-16',self.root)

    def test_scope_gaps_and_expired_or_historical_quote_block_price(self):
        original=copy.deepcopy(self.package)
        for field,value in [('valid_through','2026-09-01'),('evidence_kind','historical_proposal'),('reviewed',False)]:
            self.package=copy.deepcopy(original);self.package['quotes'][0][field]=value
            with self.assertRaises(ValueError):self.run_package()
        self.package=copy.deepcopy(original);self.package['quotes'][0]['scope_items'][0]['status']='allowance'
        with self.assertRaises(ValueError):self.run_package()

    def test_draft_or_source_change_invalidates_package(self):
        self.draft['rows'][0]['markup_pct']='15'
        with self.assertRaisesRegex(ValueError,'different estimate'):self.run_package()
        self.draft['rows'][0]['markup_pct']='7';(self.root/'quote.txt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.run_package()

    def test_viewer_withholds_stale_package_but_preserves_other_rows(self):
        other={'row_id':'unrelated','line_cost':27,'line_price':30}
        self.draft['rows'].append(other)
        result=price_packages(self.draft,[self.package],'2026-09-16',self.root,withhold_stale=True)
        self.assertEqual(result['rows'][-1],other)
        self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertNotIn('covered_by_package',result['rows'][1])
        self.assertEqual(result['pending_packages'][0]['row_id'],'package')
        self.assertFalse(result['estimate_released'])

    def test_owner_scope_confirmation_is_bound_to_original_evidence(self):
        source=self.root/'confirmation.json';source.write_text('{"answer":"included"}')
        self.package['quotes'][0]['scope_confirmation']={'source_file':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
        self.assertEqual(self.run_package()['rows'][0]['line_cost'],1000.01)
        source.write_text('{"answer":"excluded"}')
        with self.assertRaisesRegex(ValueError,'scope confirmation evidence changed'):self.run_package()

    def test_overlap_or_bad_target_cannot_double_charge(self):
        with self.assertRaises(ValueError):price_packages(self.draft,[self.package,self.package],'2026-09-16',self.root)
        self.draft['rows'][0]['unit']='sq ft';self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'subcontractor each'):self.run_package()

    def test_package_and_unit_rates_cannot_double_charge_replaced_row(self):
        self.draft['rows'][1]['cost_owner_row_id']='purchase'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'supplemental purchase'):
            self.run_package()

        with self.assertRaisesRegex(ValueError,'assigned to another purchase row'):
            price_draft(self.draft,{'plan_sha256':'plan','measurement_version':3,
                'rates':[{'row_id':'alternate'}]},'2026-09-16',self.root)
        self.draft['rows'][1].pop('cost_owner_row_id')
        self.draft['additional_cost_rows']=[{'row_id':'purchase','parent_row_id':'package'}]
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'supplemental purchase'):
            self.run_package()

    def test_fixed_equipment_rental_preserves_type_units_and_quantity(self):
        self.draft['rows'][0].update(cost_type='EQUIPMENT',unit='each',draft_quantity=None)
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaises(ValueError):self.run_package()
        self.package.update(billing_basis='fixed_package',scope_note='One rental contract with multiple billed periods and delivery')
        result=self.run_package();row=result['rows'][0]
        self.assertEqual((row['cost_type'],row['unit'],row['markup_pct']),('EQUIPMENT','each','7'))
        self.assertEqual((row['line_cost'],row['line_price']),(1000.01,1070.01))
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        self.assertFalse(result['estimate_released'])
        self.draft['rows'][0]['draft_quantity']=2
        with self.assertRaisesRegex(ValueError,'different estimate'):self.run_package()
        self.draft['rows'][0]['draft_quantity']=None
        (self.root/'quote.txt').write_bytes(b'Changed rental terms')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.run_package()

    def allow_dated(self):
        self.package['quotes'][0].update(evidence_kind='dated_supplier_allowance',valid_through=None)
        source=self.root/'owner.json'
        source.write_text(json.dumps({'answer':'Use saved rates as dated allowances'}))
        self.package['allowance_authorization']={'source_file':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}

    def material_tax_package(self):
        self.allow_dated()
        self.draft['rows'][0].update(cost_type='MATERIAL',markup_pct='15')
        self.package.update(billing_basis='fixed_package',covered_row_ids=['package'],tax_included=False)
        self.package['quotes'][0]['total']='150.99'
        record={'plan_sha256':'plan','percent':8,'effective_from':'2026-07-01',
                'effective_through':'2026-09-30','jurisdiction':'Test county','source':'Synthetic tax fixture'}
        path=self.root/'tax.json';path.write_text(json.dumps(record))
        self.package['purchase_tax']={k:record[k] for k in ('percent','effective_from','effective_through')}
        self.package['purchase_tax'].update(source_file=path.name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)

    def test_material_package_adds_tax_once_before_markup_without_inventing_quantity(self):
        self.material_tax_package()
        row=self.run_package()['rows'][0]
        self.assertEqual((row['supplier_cost'],row['purchase_tax'],row['line_cost'],row['line_price']),
                         (150.99,12.08,163.07,187.53))
        self.assertIsNone(row['draft_quantity'])
        self.assertIsNone(row['unit_cost'])
        self.assertEqual(row['price_evidence']['quote']['quoted_total'],'150.99')
        self.assertFalse(row['current_price_certified'])

    def test_material_package_withholds_expired_tax(self):
        self.material_tax_package()
        row=price_packages(self.draft,[self.package],'2026-10-01',self.root)['rows'][0]
        self.assertIsNone(row['line_cost'])
        self.assertIsNone(row['line_price'])
        self.assertNotIn('estimating_price_review',row)
        self.assertIn('not effective',row['price_status'])

    def test_material_package_rejects_changed_tax_and_tax_included_conflict(self):
        self.material_tax_package()
        self.package['tax_included']=True
        with self.assertRaisesRegex(ValueError,'explicitly pretax'):self.run_package()
        self.package['tax_included']=False
        (self.root/'tax.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_package()

    def test_package_tax_cannot_be_added_to_subcontractor_price(self):
        self.material_tax_package()
        self.draft['rows'][0]['cost_type']='SUBCONTRACTOR'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'fixed dated material'):self.run_package()

    def test_fixed_fee_allowance_keeps_unpriced_scope_open(self):
        self.allow_dated()
        for n, row in enumerate(self.draft['rows']):
            row.update(excel_row=str(n+2), name=row['row_id'])
        self.draft['rows'][0].update(cost_type='FEE', markup_pct='15')
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaises(ValueError):self.run_package()
        self.package.update(billing_basis='fixed_package', covered_row_ids=['package'],
            scope_note='Documented temporary-water service only; not all project utilities.',
            unpriced_scope=['Temporary electric service and additional tank deliveries'])
        result=self.run_package();row=result['rows'][0]
        self.assertEqual((row['cost_type'],row['markup_pct']),('FEE','15'))
        self.assertEqual((row['line_cost'],row['line_price']),(1000.01,1150.01))
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        check=readiness(result,{'rows':self.draft['rows']})['rows'][0]
        self.assertTrue(check['estimating_price_accepted'])
        self.assertIn('Unpriced package scope: Temporary electric service and additional tank deliveries',check['issues'])
        self.assertIn('Quantity unresolved',check['issues'])
        self.assertFalse(row['current_price_certified']);self.assertFalse(result['estimate_released'])
        with self.assertRaisesRegex(ValueError,'overlapping'):
            price_packages(self.draft,[self.package,self.package],'2026-09-16',self.root)
        for invalid in ('Unpriced power', [''], [None]):
            self.package['unpriced_scope']=invalid
            with self.assertRaisesRegex(ValueError,'Unpriced package scope'):self.run_package()

    def test_authorized_dated_package_keeps_one_cost_and_explicit_status(self):
        self.allow_dated();result=self.run_package();row=result['rows'][0]
        self.assertEqual((row['line_cost'],row['line_price']),(1000.01,1070.01))
        self.assertEqual(row['pricing_basis'],'dated_package_allowance')
        self.assertFalse(row['current_price_certified'])
        self.assertIn('2026-09-01',row['price_status'])
        self.assertFalse(row['price_evidence']['quote']['same_scope_current_quote'])
        self.assertEqual(result['rows'][1]['covered_by_package'],'package')
        self.assertIsNone(result['rows'][1]['line_cost'])
        self.assertFalse(result['estimate_released'])

    def test_dated_package_requires_unchanged_explicit_authorization(self):
        self.allow_dated();authority=self.package.pop('allowance_authorization')
        with self.assertRaisesRegex(ValueError,'authorization'):self.run_package()
        self.package['allowance_authorization']=authority
        (self.root/'owner.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'authorization'):self.run_package()
        authority['source_sha256']=hashlib.sha256(b'{}').hexdigest()
        with self.assertRaisesRegex(ValueError,'authorization'):self.run_package()

    def test_allowance_template_owner_preserves_markup_and_readiness_gaps(self):
        self.allow_dated()
        self.draft['rows'][0].update(cost_type='ALLOWANCE',markup_pct='8')
        for i,row in enumerate(self.draft['rows']):
            row.update(excel_row=str(i+1),name=row['row_id'])
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package()
        self.assertEqual(result['rows'][0]['line_price'],1080.01)
        audit=readiness(result,self.draft)
        self.assertNotIn('Current price certification outstanding',audit['rows'][0]['issues'])
        self.assertTrue(audit['rows'][0]['estimating_price_accepted'])
        self.assertIn('Accepted estimating allowance; current supplier price unverified',audit['rows'][0]['warnings'])
        self.assertEqual(audit['rows'][1]['role'],'covered_by_package')
        self.assertEqual(audit['rows'][1]['issues'],[])
        self.assertFalse(audit['estimate_released'])

    def test_dated_package_still_rejects_incomplete_scope_and_invalid_date(self):
        self.allow_dated();original=copy.deepcopy(self.package)
        for field,value in [('date',None),('date','2027-01-01'),('reviewed',False),('currency','EUR')]:
            self.package=copy.deepcopy(original);self.package['quotes'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_package()
        for status in ('unknown','excluded','allowance'):
            self.package=copy.deepcopy(original);self.package['quotes'][0]['scope_items'][0]['status']=status
            with self.subTest(status=status),self.assertRaises(ValueError):self.run_package()

    def test_dated_package_rejects_revision_change_and_duplicate_charge(self):
        self.allow_dated()
        with self.assertRaises(ValueError):price_packages(self.draft,[self.package,self.package],'2026-09-16',self.root)
        self.draft['measurement_version']=4
        with self.assertRaisesRegex(ValueError,'different estimate'):self.run_package()

    def test_fixed_package_preserves_area_and_unresolved_measurements(self):
        self.allow_dated()
        for i,row in enumerate(self.draft['rows']):
            row.update(unit='ft2',cost_type='ALLOWANCE',markup_pct='8',
                       excel_row=str(i+1),name=row['row_id'],unit_cost=None)
        self.draft['rows'][1]['assembly_inputs']=[{'id':'ceiling','quantity':2000}]
        self.package['billing_basis']='fixed_package'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package()
        owner=result['rows'][0]
        self.assertEqual((owner['line_cost'],owner['line_price']),(1000.01,1080.01))
        self.assertEqual(owner['unit'],'ft2')
        self.assertIsNone(owner['draft_quantity'])
        self.assertIsNone(owner['unit_cost'])
        self.assertEqual(result['rows'][1]['assembly_inputs'],self.draft['rows'][1]['assembly_inputs'])
        audit=readiness(result,self.draft)
        self.assertIn('Quantity unresolved',audit['rows'][0]['issues'])
        self.assertIn('Quantity and assembly certification outstanding',audit['rows'][1]['issues'])
        self.draft['rows'][1]['assembly_inputs'][0]['quantity']=2100
        held=price_packages(self.draft,[self.package],'2026-09-16',self.root,withhold_stale=True)
        self.assertIsNone(held['rows'][0]['line_cost'])
        self.assertNotIn('covered_by_package',held['rows'][1])

    def test_fixed_package_preserves_existing_quantity_without_inventing_rate(self):
        self.draft['rows'][0].update(unit='ft2',draft_quantity=2000,unit_cost=None)
        self.package['billing_basis']='fixed_package'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        row=self.run_package()['rows'][0]
        self.assertEqual(row['draft_quantity'],2000)
        self.assertIsNone(row['unit_cost'])
        self.assertEqual(row['line_cost'],1000.01)

    def supplemental(self):
        for i,row in enumerate(self.draft['rows']):row.update(excel_row=str(i+1),name=row['row_id'])
        self.draft['rows'].append({'row_id':'trade','excel_row':'3','name':'Electrical','parent':'Utilities',
            'cost_type':'GROUP','unit':'','markup_pct':'0','completion_status':'rollup_only','line_cost':None})
        self.package.update(row_id='extra',covered_row_ids=['extra'],billing_basis='fixed_package',
            scope_note='Separate installed service; route length and trenching unresolved.',
            supplemental_cost={'parent_row_id':'trade','markup_source_row_id':'package',
                'name':'Separate service','scope_id':'service'},reviewed_draft_sha256=scope_digest(self.draft))

    def test_fixed_labor_package_preserves_unit_markup_and_unknown_area(self):
        self.allow_dated()
        self.draft['rows'][0].update(cost_type='LABOR',unit='sq ft',unit_cost=None)
        self.package['billing_basis']='fixed_package'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        row=self.run_package()['rows'][0]
        self.assertEqual((row['line_cost'],row['line_price']),(1000.01,1070.01))
        self.assertEqual((row['cost_type'],row['unit'],row['markup_pct']),('LABOR','sq ft','7'))
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        self.draft['rows'][0]['draft_quantity']=500
        held=price_packages(self.draft,[self.package],'2026-09-16',self.root,withhold_stale=True)
        self.assertIsNone(held['rows'][0]['line_cost'])

    def test_material_package_covers_existing_purchase_once(self):
        self.draft['rows'][0].update(cost_type='MATERIAL',unit='LF',markup_pct='15')
        extra=copy.deepcopy(self.draft['rows'][1])
        extra.update(row_id='leaf',parent_row_id='trade',draft_quantity=1,unit_cost=None)
        self.draft['additional_cost_rows']=[extra]
        self.package.update(billing_basis='fixed_package',covered_row_ids=['package','alternate','leaf'],
                            reviewed_draft_sha256=scope_digest(self.draft))
        result=self.run_package()
        self.assertEqual(result['rows'][0]['line_price'],1150.01)
        self.assertEqual(result['additional_cost_rows'][0]['covered_by_package'],'package')
        self.assertIsNone(result['additional_cost_rows'][0]['line_cost'])
        self.assertEqual(result['additional_cost_rows'][0]['draft_quantity'],1)
        with self.assertRaisesRegex(ValueError,'covered by a package'):
            price_draft(result,{'plan_sha256':'plan','measurement_version':3,'rates':[{'row_id':'leaf'}]},'2026-09-16',self.root)
        self.draft['additional_cost_rows'][0]['line_cost']=50
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'already has a price'):self.run_package()

    def test_material_package_requires_fixed_billing_and_unique_purchase_ids(self):
        self.draft['rows'][0]['cost_type']='MATERIAL'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'subcontractor each'):self.run_package()
        self.draft['additional_cost_rows']=[copy.deepcopy(self.draft['rows'][0])]
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'Duplicate template or supplemental'):self.run_package()

    def test_labor_package_requires_explicit_fixed_billing_basis(self):
        self.draft['rows'][0]['cost_type']='LABOR'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'subcontractor each'):self.run_package()

    def test_supplemental_service_has_one_cost_without_inventing_a_length(self):
        self.supplemental();self.allow_dated();result=self.run_package()
        self.assertEqual(result['rows'],self.draft['rows'])
        row=result['additional_cost_rows'][0]
        self.assertEqual((row['line_cost'],row['line_price'],row['markup_pct']),(1000.01,1070.01,'7'))
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        audit=readiness(result,self.draft)
        issues=audit['additional_cost_rows'][0]['issues']
        self.assertIn('Quantity unresolved',issues)
        self.assertNotIn('Current price certification outstanding',issues)
        self.assertTrue(audit['additional_cost_rows'][0]['estimating_price_accepted'])
        self.assertNotIn('Supplemental parent ownership is unresolved or already priced',issues)
        with self.assertRaisesRegex(ValueError,'covered by a package'):
            price_draft(result,{'plan_sha256':'plan','measurement_version':3,'rates':[{'row_id':'extra'}]},'2026-09-16',self.root)

    def test_changed_supplemental_scope_stays_visible_but_unpriced(self):
        self.supplemental();self.draft['measurement_version']=4
        result=price_packages(self.draft,[self.package],'2026-09-16',self.root,withhold_stale=True)
        self.assertIsNone(result['additional_cost_rows'][0]['line_cost'])
        self.assertEqual(result['pending_packages'][0]['row_id'],'extra')

    def test_supplemental_labor_inherits_assembly_labor_markup(self):
        self.supplemental();self.allow_dated()
        self.draft['rows'][0]['cost_type']='LABOR'
        self.draft['rows'][-1]['cost_type']='ASSEMBLY'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package();extra=result['additional_cost_rows'][0]
        self.assertEqual((extra['cost_type'],extra['markup_pct'],extra['line_price']),('LABOR','7',1070.01))
        issues=readiness(result,self.draft)['additional_cost_rows'][0]['issues']
        self.assertNotIn('Supplemental package ownership is not supported by a priced package',issues)
        for cost_type in ('ALLOWANCE','GROUP'):
            self.draft['rows'][0]['cost_type']=cost_type
            self.package['reviewed_draft_sha256']=scope_digest(self.draft)
            with self.assertRaisesRegex(ValueError,'matching markup source'):self.run_package()

    def test_supplemental_duplicate_scope_parent_and_markup_errors_are_rejected(self):
        self.supplemental();original=copy.deepcopy(self.package)
        for field,value in [('parent_row_id','missing'),('parent_row_id','package'),('markup_source_row_id','trade')]:
            self.package=copy.deepcopy(original);self.package['supplemental_cost'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.run_package()
        self.package=original
        for duplicate_id,scope_id in [('extra','service'),('another','service'),('another','another-service')]:
            duplicate=copy.deepcopy(original);duplicate['row_id']=duplicate_id;duplicate['covered_row_ids']=[duplicate_id]
            duplicate['supplemental_cost']['scope_id']=scope_id
            with self.subTest(duplicate_id=duplicate_id,scope_id=scope_id),self.assertRaises(ValueError):
                price_packages(self.draft,[original,duplicate],'2026-09-16',self.root)

    def test_supplemental_material_preserves_markup_without_inventing_stock(self):
        self.supplemental();self.allow_dated()
        self.draft['rows'][0].update(cost_type='MATERIAL',unit='LF',markup_pct='15')
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        result=self.run_package();row=result['additional_cost_rows'][0]
        self.assertEqual(result['rows'],self.draft['rows'])
        self.assertEqual((row['cost_type'],row['markup_pct'],row['line_cost'],row['line_price']),
                         ('MATERIAL','15',1000.01,1150.01))
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        self.assertEqual(readiness(result,self.draft)['additional_cost_rows'][0]['issues'],
                         ['Quantity unresolved','Quantity and assembly certification outstanding'])
        self.draft['rows'][0]['parent']='Other trade'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'matching markup source'):self.run_package()

    def test_partial_trim_reference_does_not_become_package_quantity(self):
        from test_floor_trim_reference import sample
        self.supplemental();self.allow_dated()
        reference=sample();reference.pop('plan_sha256');reference.pop('measurement_version')
        reference['floor_finish_review']['plan_sha256']='plan'
        self.draft.update(reference)
        self.package['supplemental_cost']['quantity_reference']='floating_floor_wall_runs'
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        row=self.run_package()['additional_cost_rows'][0]
        self.assertEqual(row['assembly_inputs'][0]['quantity'],30)
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['unit_cost'])
        self.assertEqual(row['line_cost'],1000.01)
        self.draft['baseboard_review']['rooms'][0].update(finish_perimeter_lf=34,remaining_wall_run_lf=29,segments=[{'length_lf':29}])
        held=price_packages(self.draft,[self.package],'2026-09-16',self.root,withhold_stale=True)
        self.assertEqual(held['additional_cost_rows'][0]['assembly_inputs'][0]['quantity'],29)
        self.assertIsNone(held['additional_cost_rows'][0]['line_cost'])
        self.package['supplemental_cost']['quantity_reference']='invented'
        with self.assertRaisesRegex(ValueError,'Unknown supplemental quantity reference'):self.run_package()

    def test_installed_allowance_addition_preserves_base_and_template_markup(self):
        self.supplemental();self.allow_dated()
        self.draft['rows'][0].update(cost_type='ALLOWANCE',unit='ft2',markup_pct='8')
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)
        with self.assertRaisesRegex(ValueError,'matching markup source'):self.run_package()
        self.package['supplemental_cost']['installed_scope']='Separate garage and sound-wall installed addition'
        result=self.run_package();extra=result['additional_cost_rows'][0]
        self.assertEqual(result['rows'],self.draft['rows'])
        self.assertEqual((extra['cost_type'],extra['markup_pct'],extra['line_price']),('ALLOWANCE','8',1080.01))
        self.assertIsNone(extra['draft_quantity']);self.assertIsNone(extra['unit_cost'])
        issues=readiness(result,self.draft)['additional_cost_rows'][0]['issues']
        self.assertEqual(issues,['Quantity unresolved','Quantity and assembly certification outstanding'])
        extra.pop('installed_scope')
        self.assertIn('Supplemental package ownership is not supported by a priced package',readiness(result,self.draft)['additional_cost_rows'][0]['issues'])

    def test_supplemental_readiness_detects_broken_ownership(self):
        self.supplemental();result=self.run_package();result['additional_cost_rows'][0]['covered_by_package']='wrong'
        issues=readiness(result,self.draft)['additional_cost_rows'][0]['issues']
        self.assertIn('Supplemental package ownership is not supported by a priced package',issues)

    def component_then_package(self, part='second', allocated=True):
        document={k:self.package['quotes'][0][k] for k in ('source_file','source_sha256')}
        path=self.root/'ledger.json'
        path.write_text(json.dumps({'invoices':[{'id':'invoice',**document,'total':'2000.02',
            'allocations':[{'id':p,'amount':'1000.01'} for p in ('first','second')]}]}))
        binding={'source_file':path.name,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'claims':[{'invoice_id':'invoice','allocation_id':'first'}]}
        evidence={'original_document':document,'components':[{'cost':1000.01}]}
        if allocated:evidence['invoice_allocations']=binding
        self.draft['rows'].append({'row_id':'component','line_cost':1080.01,
            'pricing_basis':'dated_component_allowance','price_evidence':evidence})
        self.package['billing_basis']='fixed_package'
        self.package['quotes'][0]['invoice_allocations']={**binding,
            'claims':[{'invoice_id':'invoice','allocation_id':part}]}
        self.package['reviewed_draft_sha256']=scope_digest(self.draft)

    def test_package_rejects_component_allocation_already_charged(self):
        self.component_then_package('first')
        with self.assertRaisesRegex(ValueError,'already charged'):self.run_package()

    def test_package_accepts_disjoint_component_allocation(self):
        self.component_then_package()
        result=self.run_package()
        self.assertEqual(result['rows'][0]['line_cost'],1000.01)
        self.assertEqual(result['rows'][2]['line_cost'],1080.01)

    def test_package_rejects_whole_component_invoice(self):
        self.component_then_package(allocated=False)
        with self.assertRaisesRegex(ValueError,'already charged'):self.run_package()

    def test_package_rejects_changed_component_ledger(self):
        self.component_then_package()
        (self.root/'ledger.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'missing or changed'):self.run_package()

if __name__=='__main__':unittest.main()
