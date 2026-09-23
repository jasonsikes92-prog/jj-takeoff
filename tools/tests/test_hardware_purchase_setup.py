import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from hardware_purchase_setup import prepare,digest
from kit_purchase_review import import_kit_purchases
from measurement_store import encode
import test_hardware_quantity_review as fixtures

class HardwareSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.fixture=fixtures.HardwareQuantityTests();self.fixture.setUp()
        self.fixture.draft['rows'].append({'row_id':'parent','name':self.fixture.target['parent'],'cost_type':'GROUP'})
        (self.root/'plan.pdf').write_bytes(b'Synthetic plan source')
        plan=hashlib.sha256((self.root/'plan.pdf').read_bytes()).hexdigest()
        self.fixture.draft['plan_sha256']=self.fixture.schedule['plan_sha256']=plan
        template=self.save('template_rows.json',{'rows':self.fixture.draft['rows']})
        self.draft=self.fixture.run_review();self.draft['template_sha256']=template['sha256']
        self.refresh()
        source=self.save('supplier.txt',{'scope':'Synthetic separate supply exclusion for all four functions'})
        self.review={'plan_sha256':plan,'hardware_review_sha256':digest(self.draft['hardware_quantity_review']),
            'reviewer':'Test fixture','basis':'Synthetic fixture; no real supplier decision',
            'applies_to':'hardware_function_supply','source_files':[source],
            'items':[{'input_id':g['id'],'supply_status':'separate'} for g in self.draft['hardware_quantity_review']['groups']]}
        self.review_path=self.root/'scope.json';self.save_review()

    def save(self,name,value):
        path=self.root/name;path.write_text(json.dumps(value))
        return {'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def refresh(self):
        body={'draft':self.draft,'readiness':{}}
        self.snapshot={**body,'snapshot_sha256':hashlib.sha256(encode(body).encode()).hexdigest()}

    def save_review(self):self.save('scope.json',self.review)
    def run_setup(self):return prepare(self.root,self.snapshot,self.review_path)
    def imported(self,draft=None):
        return import_kit_purchases(draft or self.draft,json.loads((self.root/'kit_purchase_review.json').read_bytes()),self.root)

    def test_generates_four_mappings_without_frozen_counts_products_or_prices(self):
        result=self.run_setup();self.assertEqual(len(result['created']),4)
        for file in result['created']:
            purchase=json.loads((self.root/file).read_bytes())
            self.assertNotIn('quantity',purchase);self.assertNotIn('unit_price',purchase);self.assertNotIn('product_id',purchase)
        rows=self.imported()['additional_cost_rows']
        self.assertEqual([r['draft_quantity'] for r in rows],[1,1,None,None])
        self.assertTrue(all(r['markup_pct']=='8' and r['line_cost'] is None for r in rows))
        self.assertNotIn('supplier package inclusion unresolved',' '.join(rows[0]['quantity_sources'][0]['remaining']))
        changed=copy.deepcopy(self.draft);changed['rows'][-2]['assembly_inputs'][0]['quantity']=4
        self.assertEqual(self.imported(changed)['additional_cost_rows'][0]['draft_quantity'],4)

    def test_unknown_and_included_do_not_create_separate_costs(self):
        self.review['items'][0]['supply_status']='included';self.review['items'][1]['supply_status']='unknown'
        self.save_review();result=self.run_setup()
        self.assertEqual(len(result['created']),2);self.assertEqual(len(result['unresolved']),2)
        self.assertEqual(len(self.imported()['additional_cost_rows']),2)

    def test_all_unknown_preserves_job_without_new_mapping(self):
        self.review['items']=[];self.save_review()
        self.assertEqual(self.run_setup()['created'],[])
        self.assertFalse((self.root/'kit_purchase_review.json').exists())

    def test_original_source_change_invalidates_generated_purchase(self):
        self.run_setup();path=self.root/'supplier.txt';raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'source evidence'):self.imported()
        path.write_bytes(raw);self.assertEqual(self.imported()['additional_cost_rows'][0]['draft_quantity'],1)
        self.review_path.write_bytes(self.review_path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'source evidence'):self.imported()

    def test_rerun_preserves_saved_files(self):
        self.run_setup();prior=(self.root/'kit_purchase_review.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already has'):self.run_setup()
        self.assertEqual((self.root/'kit_purchase_review.json').read_bytes(),prior)

    def test_bad_review_scope_decisions_and_source_rejected(self):
        original=copy.deepcopy(self.review)
        for change in ({'plan_sha256':'wrong'},{'hardware_review_sha256':'wrong'},{'applies_to':'all_jobs'},
                       {'reviewer':''},{'source_files':[]},{'items':[{'input_id':'unknown','supply_status':'separate'}]},
                       {'items':original['items']+[original['items'][0]]}):
            self.review={**original,**change};self.save_review()
            with self.subTest(change=change),self.assertRaises(ValueError):self.run_setup()
        self.review=original;self.save_review();(self.root/'supplier.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.run_setup()

    def test_changed_job_plan_and_template_rejected(self):
        for name in ('plan.pdf','template_rows.json'):
            path=self.root/name;raw=path.read_bytes();path.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'another plan or template'):self.run_setup()
            path.write_bytes(raw)

    def test_existing_cost_owner_rejects_setup_and_rolls_back_new_files(self):
        self.draft['rows'][-2]['assembly_input_cost_owners']={'opening-hardware-privacy':'existing'};self.refresh()
        with self.assertRaisesRegex(ValueError,'already has'):self.run_setup()
        self.draft['rows'][-2].pop('assembly_input_cost_owners');self.draft['rows'][-2]['unit_cost']=10;self.refresh()
        with self.assertRaisesRegex(ValueError,'already assigned'):self.run_setup()
        self.assertFalse((self.root/'kit_purchase_review.json').exists())
        self.assertEqual(list((self.root/'scope_evidence').glob('*.json')),[])

if __name__=='__main__':unittest.main()
