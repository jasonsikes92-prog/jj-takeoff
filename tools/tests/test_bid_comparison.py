import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bid_comparison import compare_quotes,scope_digest


class BidComparison(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'quote.txt').write_bytes(b'Synthetic fixture')
        self.scope={'plan_sha256':'plan','measurement_version':3,'items':[
            {'id':'floor','label':'Flooring'},{'id':'delivery','label':'Delivery'}]}
        self.quote={'id':'A','supplier':'Synthetic supplier','source_file':'quote.txt',
            'source_sha256':hashlib.sha256(b'Synthetic fixture').hexdigest(),'date':'2026-09-01',
            'valid_through':'2026-09-30','currency':'USD','total':'1234.56','reviewed':True,
            'reviewed_scope_sha256':scope_digest(self.scope),'evidence_kind':'current_supplier_quote',
            'scope_items':[{'scope_id':i,'status':'included','source_ref':'page 1'} for i in ('floor','delivery')]}

    def run_quote(self,q=None,scope=None):
        return compare_quotes(scope or self.scope,[q or self.quote],'2026-09-16',self.root)['quotes'][0]

    def test_current_complete_package_preserves_total_without_automatic_purchase(self):
        r=self.run_quote();self.assertTrue(r['same_scope_current_quote'])
        self.assertEqual(r['quoted_total'],'1234.56');self.assertIsNone(r['adjusted_total'])
        self.assertFalse(r['purchase_authorized'])

    def test_missing_excluded_allowance_and_unknown_scope_are_not_priced(self):
        for status in ('missing','excluded','allowance','unknown'):
            q=copy.deepcopy(self.quote)
            if status=='missing':q['scope_items'].pop()
            else:q['scope_items'][1]['status']=status
            r=self.run_quote(q);self.assertFalse(r['same_scope_current_quote'])
            self.assertIsNone(r['adjusted_total']);self.assertEqual(r['quoted_total'],'1234.56')

    def test_supplier_inclusion_cannot_resolve_unknown_drawing_openings(self):
        self.scope['unresolved_opening_ids']=['unlocated-opening']
        self.quote['reviewed_scope_sha256']=scope_digest(self.scope)
        for kind in ('current_supplier_quote','dated_supplier_allowance'):
            self.quote['evidence_kind']=kind
            result=self.run_quote()
            self.assertFalse(result['same_scope_current_quote'])
            self.assertFalse(result['same_scope_dated_allowance'])
            self.assertIn('source scope',result['comparison_issues'][0])
            self.assertEqual(result['quoted_total'],'1234.56')
            self.assertIsNone(result['adjusted_total'])

    def test_revision_change_invalidates_review_even_when_plan_same(self):
        scope=copy.deepcopy(self.scope);scope['measurement_version']=4
        self.assertFalse(self.run_quote(scope=scope)['same_scope_current_quote'])
        scope=copy.deepcopy(self.scope);scope['items'][0]['label']='Flooring with changed finish'
        self.assertFalse(self.run_quote(scope=scope)['same_scope_current_quote'])

    def test_stale_historical_unreviewed_unknown_total_do_not_pass(self):
        for field,value in [('valid_through',None),('valid_through','2026-09-02'),('evidence_kind','historical_invoice'),('reviewed',False),('total',None)]:
            q=copy.deepcopy(self.quote);q[field]=value
            self.assertFalse(self.run_quote(q)['same_scope_current_quote'])

    def test_passed_validity_date_retains_quote_without_inventing_increase(self):
        q=copy.deepcopy(self.quote);q['valid_through']='2026-09-02'
        r=self.run_quote(q)
        self.assertEqual(r['quoted_total'],'1234.56')
        self.assertIsNone(r['adjusted_total'])
        self.assertEqual(r['comparison_issues'],[
            'Printed validity date has passed; follow up on whether the supplier still honors the quoted price'])
        self.assertFalse(r['same_scope_current_quote'])
        self.assertFalse(r['purchase_authorized'])

    def test_cheaper_excluded_scope_quote_is_not_equivalent_or_a_winner(self):
        cheaper=copy.deepcopy(self.quote);cheaper['id']='B';cheaper['total']='1000'
        cheaper['scope_items'][1]['status']='excluded'
        r=compare_quotes(self.scope,[cheaper,self.quote],'2026-09-16',self.root)
        self.assertFalse(r['quotes'][0]['same_scope_current_quote'])
        self.assertTrue(r['quotes'][1]['same_scope_current_quote'])
        self.assertIsNone(r['winner'])
        self.assertEqual(r['quotes'][0]['quoted_total'],'1000')

    def test_bad_sources_duplicates_and_invalid_totals_rejected(self):
        for field,value in [('source_file','../outside.txt'),('total','NaN'),('total',True),('total',-1)]:
            q=copy.deepcopy(self.quote);q[field]=value
            with self.assertRaises(ValueError):self.run_quote(q)
        q=copy.deepcopy(self.quote);q['scope_items'].append(q['scope_items'][0])
        with self.assertRaises(ValueError):self.run_quote(q)
        q=copy.deepcopy(self.quote);q['scope_items'][0]['source_ref']=''
        with self.assertRaises(ValueError):self.run_quote(q)
        (self.root/'quote.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.run_quote()

    def test_changed_scope_ids_preserve_old_quote_without_applying_old_pricing(self):
        scope=copy.deepcopy(self.scope);scope['items'][0]['id']='new-floor'
        scope['requires_pricing_basis_review']=True
        result=self.run_quote(scope=scope)
        self.assertFalse(result['same_scope_current_quote'])
        self.assertEqual(result['previous_scope_items_not_in_current_revision'][0]['scope_id'],'floor')
        self.assertEqual(result['scope_matrix'][0]['status'],'unknown')
        self.assertIsNone(result['pricing_review']['charged_line_total'])
        self.assertEqual(result['quoted_total'],'1234.56')

    def test_asserted_scope_requires_text_source_reference(self):
        for status in ('included','excluded','allowance'):
            for source in (None,True,False,12,[],{},'',' \t\n'):
                quote=copy.deepcopy(self.quote)
                quote['scope_items'][0].update(status=status,source_ref=source)
                with self.subTest(status=status,source=source),self.assertRaisesRegex(ValueError,'source location'):
                    self.run_quote(quote)

    def test_unknown_scope_may_keep_null_source_without_claiming_completeness(self):
        quote=copy.deepcopy(self.quote)
        quote['scope_items'][0].update(status='unknown',source_ref=None)
        result=self.run_quote(quote)
        self.assertFalse(result['same_scope_current_quote'])
        self.assertEqual(result['scope_matrix'][0]['status'],'unknown')
        self.assertEqual(result['quoted_total'],'1234.56')


if __name__=='__main__':unittest.main()
