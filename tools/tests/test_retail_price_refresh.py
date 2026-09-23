import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from retail_price_refresh import prepare_refresh


class RetailRefresh(unittest.TestCase):
    def setUp(self):
        self.rate={'row_id':'retail','evidence_kind':'retail_listing','date':'2026-09-16',
                   'product_id':'123','unit':'box','currency':'USD','unit_basis':'50 per box',
                   'tax_included':False,'source':'https://www.homedepot.com/p/123',
                   'unit_price':10,'displayed_store_stock':99,'purchase_tax':{'percent':8},'basis':'Existing scope'}
        self.pricing={'plan_sha256':'plan','measurement_version':3,'rates':[self.rate,{'row_id':'owner','evidence_kind':'jason_approved_rate','unit_price':190}]}
        self.record={k:self.rate[k] for k in ('product_id','unit','currency','unit_basis','tax_included','source')}
        self.record.update(date='2026-09-17',product_name='Chair box',unit_price=12,
                           observation_method='Rendered product listing',local_store_price_verified=False,
                           availability_verified=False,checkout_price_verified=False,job_delivery_availability_verified=False)

    def run_refresh(self,record=None,identity='retail'):
        return prepare_refresh(self.pricing,[{'row_id':identity,'record':record or self.record}],'2026-09-17')

    def test_refresh_retains_scope_tax_owner_and_input_without_stale_stock(self):
        original=copy.deepcopy(self.pricing)
        updated,files=self.run_refresh(); rate=updated['rates'][0]
        self.assertEqual(self.pricing,original)
        self.assertEqual(updated['rates'][1],original['rates'][1])
        self.assertEqual(rate['purchase_tax'],self.rate['purchase_tax'])
        self.assertEqual(rate['basis'],self.rate['basis'])
        self.assertNotIn('displayed_store_stock',rate)
        self.assertEqual(rate['valid_through'],'2026-09-17')
        raw=files[rate['source_file']]
        self.assertEqual(hashlib.sha256(raw).hexdigest(),rate['source_sha256'])
        self.assertEqual(json.loads(raw),self.record)

    def test_date_product_unit_currency_and_tax_changes_rejected(self):
        for key,value in [('date','2026-09-18'),('product_id','456'),('unit','each'),('currency','EUR'),('unit_basis','40 per box'),('tax_included',True),('source','https://example.com/p/123')]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.run_refresh({**self.record,key:value})

    def test_unknown_duplicate_and_owner_replacement_rejected(self):
        for identity in ('unknown','owner'):
            with self.assertRaises(ValueError):self.run_refresh(identity=identity)
        observation={'row_id':'retail','record':self.record}
        with self.assertRaises(ValueError):prepare_refresh(self.pricing,[observation,observation],'2026-09-17')

    def test_missing_limits_and_invalid_prices_rejected(self):
        for key,value in [('unit_price',float('nan')),('unit_price',-1),('unit_price',True),('availability_verified',None),('observation_method','')]:
            with self.subTest(key=key,value=value):
                with self.assertRaises(ValueError):self.run_refresh({**self.record,key:value})

    def test_observation_cannot_replace_scope_tax_or_another_product_url(self):
        for key,value in [('purchase_tax',{'percent':0}),('basis','Changed scope'),('source','https://www.homedepot.com/p/456')]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.run_refresh({**self.record,key:value})

    def test_identical_observation_is_idempotent_and_revised_price_gets_new_evidence(self):
        first,files=self.run_refresh()
        second,files2=prepare_refresh(first,[{'row_id':'retail','record':self.record}],'2026-09-17')
        self.assertEqual(first,second);self.assertEqual(files,files2)
        _,changed=self.run_refresh({**self.record,'unit_price':13})
        self.assertTrue(set(changed).isdisjoint(files))


if __name__=='__main__':unittest.main()
