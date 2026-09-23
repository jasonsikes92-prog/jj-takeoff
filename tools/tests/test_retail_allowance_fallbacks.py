import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from retail_allowance_fallbacks import register_retail_fallbacks
from retail_price_refresh import prepare_refresh
from measurement_estimate import price_draft


class RetailFallbacks(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.observation={'date':'2026-09-17','unit_price':10,'unit':'box','currency':'USD','tax_included':False,
            'source':'https://www.homedepot.com/p/123','product_id':'123','model':'M1','product_name':'Chairs',
            'unit_basis':'50 chairs per box','observation_method':'Synthetic test observation',
            'local_store_price_verified':False,'availability_verified':False,'checkout_price_verified':False,'job_delivery_availability_verified':False}
        tax={'plan_sha256':'plan','percent':8,'effective_from':'2026-07-01','effective_through':'2026-09-30','jurisdiction':'Fixture','source':'Synthetic tax'}
        rate={**self.observation,**self.save('observation.json',self.observation),'row_id':'chairs','evidence_kind':'retail_listing',
            'pricing_basis':'unit_rate','scope_reviewed':True,'validity_policy':'observation_date_only','valid_through':'2026-09-17',
            'purchase_tax':{**self.save('tax.json',tax),**{k:tax[k] for k in ['percent','effective_from','effective_through']}}}
        self.pricing={'plan_sha256':'plan','measurement_version':1,'rates':[rate],
            'allowance_authorization':self.save('owner.json',{'answer':'Use saved rates as dated allowances'})}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[{'row_id':'chairs','unit':'box','cost_type':'MATERIAL','markup_pct':'15',
            'draft_quantity':2,'unit_cost':None,'line_cost':None,'line_price':None}]}

    def save(self,name,data):
        p=self.root/name;p.write_text(json.dumps(data));return {'source_file':name,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

    def price(self,pricing,date):return price_draft(self.draft,pricing,date,self.root)['rows'][0]

    def test_midnight_fallback_retains_date_cost_tax_and_uncertainty(self):
        pricing=register_retail_fallbacks(self.pricing,self.root)
        current=self.price(pricing,'2026-09-17');dated=self.price(pricing,'2026-09-18')
        self.assertEqual((current['line_cost'],dated['line_cost'],dated['line_price']),(21.6,21.6,24.84))
        self.assertNotIn('pricing_basis',current);self.assertEqual(dated['pricing_basis'],'dated_allowance')
        self.assertEqual(dated['price_evidence']['date'],'2026-09-17');self.assertFalse(dated['current_price_certified'])
        self.assertEqual(pricing['rates'],self.pricing['rates']);self.assertNotIn('dated_allowances',self.pricing)

    def test_refreshed_price_wins_then_latest_observation_becomes_fallback(self):
        pricing=register_retail_fallbacks(self.pricing,self.root)
        refreshed,files=prepare_refresh(pricing,[{'row_id':'chairs','record':{**self.observation,'date':'2026-09-18','unit_price':12}}],'2026-09-18')
        for name,raw in files.items():(self.root/name).write_bytes(raw)
        refreshed=register_retail_fallbacks(refreshed,self.root)
        self.assertEqual(self.price(refreshed,'2026-09-18')['line_cost'],25.92)
        self.assertEqual(self.price(refreshed,'2026-09-19')['line_cost'],25.92)
        self.assertEqual(self.price(refreshed,'2026-09-19')['price_evidence']['date'],'2026-09-18')

    def test_registration_is_idempotent_without_duplicate_allowances(self):
        once=register_retail_fallbacks(self.pricing,self.root)
        self.assertEqual(register_retail_fallbacks(once,self.root),once)
        self.assertEqual(len(once['dated_allowances']),1)

    def test_changed_observation_or_missing_authority_is_rejected(self):
        original=copy.deepcopy(self.pricing)
        for key,value in [('unit_price',12),('model','other'),('product_id','other'),('tax_included',True),('scope_reviewed',False)]:
            changed=copy.deepcopy(original);changed['rates'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):register_retail_fallbacks(changed,self.root)
        (self.root/'observation.json').write_text('{}')
        with self.assertRaises(ValueError):register_retail_fallbacks(original,self.root)
        original['allowance_authorization']=self.save('owner.json',{'answer':'No'})
        with self.assertRaisesRegex(ValueError,'authorization'):register_retail_fallbacks(original,self.root)

    def test_unknown_quantity_and_expired_tax_do_not_get_invented_totals(self):
        pricing=register_retail_fallbacks(self.pricing,self.root)
        self.assertIsNone(self.price(pricing,'2026-10-01')['line_cost'])
        self.draft['rows'][0]['draft_quantity']=None
        row=self.price(pricing,'2026-09-18');self.assertEqual(row['unit_cost'],10);self.assertIsNone(row['line_cost'])

    def test_changed_original_document_is_rejected_after_registration(self):
        pricing=register_retail_fallbacks(self.pricing,self.root);(self.root/'observation.json').write_text('{}')
        with self.assertRaises(ValueError):self.price(pricing,'2026-09-18')


if __name__=='__main__':unittest.main()
