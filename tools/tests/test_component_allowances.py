import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from component_allowances import quantity_binding
from measurement_estimate import price_draft
from estimating_price_review import accepted_estimating_price


class ComponentAllowanceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.row={'row_id':'roof','unit':'ft2','cost_type':'SUBCONTRACTOR','draft_quantity':5559,
            'markup_pct':7,'quantity_sources':[{'id':'roof','purchase_pack':{'quantity':167}}],
            'assembly_inputs':[],'unit_cost':None,'line_cost':None,'line_price':None}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[self.row]}
        self.record={'plan_sha256':'plan','row_id':'roof','unit':'ft2','source':'Test roofer',
            'date':'2026-01-28','currency':'USD','scope_reviewed':True,'tax_delivery_basis':'Installed package',
            'original_document':self.save('invoice.json',{'source':'fixture invoice'}),
            'scope_confirmation':self.save('scope.json',{'answer':'Included'}),
            'reviewed_quantity_binding':quantity_binding(self.row),'components':[
                {'id':'shingles','quantity_numerator':167,'quantity_denominator':3,'unit':'square',
                 'unit_price':175,'source_ref':'Invoice line 1','quantity_basis':'Whole bundles'},
                {'id':'drip','quantity_numerator':320,'quantity_denominator':1,'unit':'LF',
                 'unit_price':1.85,'source_ref':'Invoice line 5','quantity_basis':'Fixture purchase allowance'},
                {'id':'boots','quantity_numerator':1,'quantity_denominator':1,'unit':'house',
                 'unit_price':50,'source_ref':'Invoice line 6','quantity_basis':'One house'}]}
        self.pricing={'plan_sha256':'plan','measurement_version':1,'rates':[],
            'allowance_authorization':self.save('authority.json',{'answer':'Use saved rates as dated allowances'})}

    def save(self,name,value):
        p=self.root/name;p.write_text(json.dumps(value))
        return {'source_file':name,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

    def price(self):
        self.pricing['dated_component_allowances']=[self.save('components.json',self.record)]
        return price_draft(self.draft,self.pricing,'2026-09-17',self.root)['rows'][0]

    def test_three_components_one_cost_owner_and_original_markup(self):
        before=copy.deepcopy(self.draft);r=self.price()
        self.assertEqual(r['line_cost'],10383.67);self.assertEqual(r['line_price'],11110.53)
        self.assertEqual(r['draft_quantity'],5559);self.assertEqual(r['unit'],'ft2')
        self.assertEqual([c['cost'] for c in r['price_evidence']['components']],[9741.67,592,50])
        self.assertFalse(r['current_price_certified']);self.assertEqual(self.draft,before)
        self.assertTrue(accepted_estimating_price(r))

    def test_quantity_or_source_edits_withhold_price(self):
        for field,value in [('draft_quantity',5558),('quantity_sources',[{'id':'changed'}]),('assembly_inputs',[{'id':'new'}])]:
            old=self.row[field];self.row[field]=value
            r=self.price();self.assertIsNone(r['line_cost']);self.assertIn('withheld',r['price_status'])
            self.assertFalse(accepted_estimating_price(r))
            self.row[field]=old

    def test_changed_evidence_fails(self):
        (self.root/'scope.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash'):self.price()

    def test_invalid_amounts_and_duplicate_components_fail(self):
        original=copy.deepcopy(self.record['components'])
        for key,value in [('quantity_numerator',-1),('quantity_denominator',0),('unit_price',True),('unit_price','NaN')]:
            self.record['components']=copy.deepcopy(original);self.record['components'][0][key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaises(ValueError):self.price()
        self.record['components']=original+[original[0]]
        with self.assertRaisesRegex(ValueError,'unique'):self.price()

    def test_wrong_scope_unit_plan_future_date_or_owner_fail(self):
        for key,value in [('plan_sha256','wrong'),('unit','EA'),('scope_reviewed',False),('date','2027-01-01')]:
            old=self.record[key];self.record[key]=value
            with self.assertRaises(ValueError):self.price()
            self.record[key]=old
        self.pricing['allowance_authorization']=self.save('authority.json',{'answer':'No'})
        with self.assertRaisesRegex(ValueError,'authorization'):self.price()

    def test_existing_price_wins_without_extra_charge(self):
        self.row.update(unit_cost=2,line_cost=11118,line_price=11896.26)
        self.assertEqual(self.price()['line_cost'],11118)

    def test_package_owned_excluded_and_duplicate_targets_fail(self):
        for field,value in [('covered_by_package','other'),('cost_owner_row_id','other'),('completion_status','not_applicable_source_reviewed')]:
            self.row[field]=value
            with self.assertRaises(ValueError):self.price()
            self.row.pop(field)
        ref=self.save('components.json',self.record);self.pricing['dated_component_allowances']=[ref,ref]
        with self.assertRaisesRegex(ValueError,'Unique'):price_draft(self.draft,self.pricing,'2026-09-17',self.root)

    def test_component_material_tax_and_expiry(self):
        self.row['markup_pct']=8
        self.record['components']=[{'id':'windows','quantity_numerator':1,'quantity_denominator':1,
            'unit':'set','unit_price':11462.63,'source_ref':'Fixture windows','quantity_basis':'Complete schedule'}]
        tax={'plan_sha256':'plan','percent':8,'effective_from':'2026-07-01','effective_through':'2026-09-30',
            'jurisdiction':'Fixture county','source':'Fixture tax table'}
        ref=self.save('tax.json',tax);self.record.update(tax_included=False,
            purchase_tax={**ref,**{k:tax[k] for k in ('percent','effective_from','effective_through')}})
        result=self.price()
        self.assertEqual((result['supplier_cost'],result['purchase_tax'],result['line_cost'],result['line_price']),
            (11462.63,917.01,12379.64,13370.01))
        expired=price_draft(self.draft,self.pricing,'2026-10-01',self.root)['rows'][0]
        self.assertIsNone(expired['line_cost']);self.assertIsNone(expired['unit_cost'])
        self.assertIn('tax evidence',expired['price_status'])
        (self.root/'tax.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'hash'):self.price()

    def test_repricing_prior_component_draft_rechecks_source(self):
        result=self.price();self.draft['rows']=[result]
        result['quantity_sources']=[{'id':'edited-source-same-whole-quantity'}]
        changed=self.price()
        self.assertIsNone(changed['line_cost']);self.assertIsNone(changed['unit_cost'])
        self.assertNotIn('price_evidence',changed);self.assertIn('withheld',changed['price_status'])

    def test_material_package_keeps_total_and_withholds_changed_schedule(self):
        self.row.update(cost_type='MATERIAL',draft_quantity=2145,markup_pct=15,
            assembly_inputs=[{'id':'floor-joists','quantity':49}])
        self.record['reviewed_quantity_binding']=quantity_binding(self.row)
        self.record['components']=[{'id':'floor package','quantity_numerator':1,'quantity_denominator':1,
            'unit':'package','unit_price':9483.45,'source_ref':'Supplier floor quote',
            'quantity_basis':'Reviewed floor schedule, not a transferable square-foot rate'}]
        tax={'plan_sha256':'plan','percent':8,'effective_from':'2026-07-01','effective_through':'2026-09-30',
            'jurisdiction':'Fixture county','source':'Fixture tax table'}
        ref=self.save('tax.json',tax)
        self.record.update(tax_included=False,purchase_tax={**ref,
            **{k:tax[k] for k in ('percent','effective_from','effective_through')}})
        result=self.price()
        self.assertEqual((result['supplier_cost'],result['purchase_tax'],result['line_cost'],result['line_price']),
                         (9483.45,758.68,10242.13,11778.45))
        self.assertFalse(result['current_price_certified'])
        self.draft['rows']=[result]
        result['assembly_inputs'][0]['quantity']=50
        changed=self.price()
        self.assertIsNone(changed['line_cost']);self.assertIsNone(changed['unit_cost'])
        self.assertIn('withheld',changed['price_status'])

    def supplemental(self):
        self.row.update(cost_type='ALLOWANCE',unit='each',draft_quantity=6,markup_pct=8,
            source_row_id='reference',source_assembly_input_id='fans',
            quantity_sources=[{'id':'fans','items':[{'model':'A','quantity':6}]}])
        self.draft['rows']=[{'row_id':'reference','pricing_role':'input_only',
            'assembly_input_cost_owners':{'fans':'roof'}}]
        self.draft['additional_cost_rows']=[self.row]
        self.record.update(unit='each',reviewed_quantity_binding=quantity_binding(self.row))
        self.record['components']=[{'id':'fans','quantity_numerator':6,'quantity_denominator':1,
            'unit':'each','unit_price':100,'source_ref':'Invoice fans','quantity_basis':'Reviewed assortment'}]
        self.pricing['dated_component_allowances']=[self.save('components.json',self.record)]

    def test_supplemental_components_price_only_explicit_input_owner(self):
        self.supplemental()
        result=price_draft(self.draft,self.pricing,'2026-09-17',self.root)
        row=result['additional_cost_rows'][0]
        self.assertEqual((row['draft_quantity'],row['line_cost'],row['line_price']),(6,600,648))
        self.assertIsNone(result['rows'][0].get('line_cost'))
        self.assertFalse(row['current_price_certified'])
        self.assertTrue(accepted_estimating_price(row))

    def test_supplemental_missing_owner_and_duplicate_identity_rejected(self):
        self.supplemental();good=copy.deepcopy(self.draft)
        for change in ('missing','wrong','role','duplicate'):
            self.draft=copy.deepcopy(good)
            source=self.draft['rows'][0]
            if change=='missing':source['assembly_input_cost_owners']={}
            if change=='wrong':source['assembly_input_cost_owners']['fans']='other'
            if change=='role':source['pricing_role']='cost_line'
            if change=='duplicate':self.draft['rows'].append(copy.deepcopy(self.row))
            with self.subTest(change=change),self.assertRaises(ValueError):
                price_draft(self.draft,self.pricing,'2026-09-17',self.root)

    def test_supplemental_pending_count_or_changed_assortment_withholds_price(self):
        self.supplemental()
        for field,value in [('draft_quantity',None),('quantity_sources',[{'id':'fans','items':[{'model':'B','quantity':6}]}])]:
            old=self.row[field];self.row[field]=value
            row=price_draft(self.draft,self.pricing,'2026-09-17',self.root)['additional_cost_rows'][0]
            self.assertIsNone(row.get('line_cost'));self.assertIn('withheld',row['price_status'])
            self.row[field]=old

    def test_component_material_support_does_not_enable_unreviewed_cost_types(self):
        self.row['cost_type']='LABOR'
        with self.assertRaisesRegex(ValueError,'cost ownership'):self.price()

    def allocated(self):
        self.record['components']=[{'id':'fixtures','quantity_numerator':1,'quantity_denominator':1,
            'unit':'each','unit_price':100,'source_ref':'Line 1','quantity_basis':'Reviewed invoice component'}]
        invoice={'id':'invoice',**self.record['original_document'],'total':'200.00',
            'allocations':[{'id':'first','amount':'100.00'},{'id':'second','amount':'100.00'}]}
        self.record['invoice_allocations']={**self.save('ledger.json',{'invoices':[invoice]}),
            'claims':[{'invoice_id':'invoice','allocation_id':'first'}]}
        other=copy.deepcopy(self.row);other['row_id']='other';self.draft['rows'].append(other)
        second=copy.deepcopy(self.record);second['row_id']='other'
        second['invoice_allocations']['claims'][0]['allocation_id']='second'
        return second

    def test_separate_component_allocations_price_once_and_reject_overclaim(self):
        second=self.allocated()
        def run():
            self.pricing['dated_component_allowances']=[self.save('first.json',self.record),self.save('second.json',second)]
            return price_draft(self.draft,self.pricing,'2026-09-17',self.root)
        self.assertEqual([r['line_cost'] for r in run()['rows']],[100,100])
        second['invoice_allocations']['claims'][0]['allocation_id']='first'
        with self.assertRaisesRegex(ValueError,'already charged'):run()
        second['invoice_allocations']['claims'][0]['allocation_id']='second'
        second['components'][0]['unit_price']=101
        with self.assertRaisesRegex(ValueError,'claims must equal'):run()

    def test_component_partition_rejects_unallocated_claim_or_whole_package(self):
        second=self.allocated();second.pop('invoice_allocations')
        self.pricing['dated_component_allowances']=[self.save('first.json',self.record),self.save('second.json',second)]
        with self.assertRaisesRegex(ValueError,'explicit allocation'):
            price_draft(self.draft,self.pricing,'2026-09-17',self.root)
        self.pricing['dated_component_allowances']=[self.save('first.json',self.record)]
        self.draft['rows'][1].update(line_cost=200,price_evidence={'quote':{'source_sha256':self.record['original_document']['source_sha256']}})
        with self.assertRaisesRegex(ValueError,'already charged by a package'):
            price_draft(self.draft,self.pricing,'2026-09-17',self.root)

if __name__=='__main__':unittest.main()
