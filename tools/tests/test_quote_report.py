import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from quote_report import report_from_quote,scope_digest
from answer_store import AnswerStore


class QuoteReport(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.raw=b'Synthetic reviewed quote';(self.root/'quote.txt').write_bytes(self.raw)
        self.scope={'plan_sha256':'drawing','measurement_version':1,'items':[
            {'id':x,'label':x.title()} for x in ('work','delivery','fixtures','tax')]}
        self.quote={'id':'Q1','supplier':'Test supplier','source_file':'quote.txt',
            'source_sha256':hashlib.sha256(self.raw).hexdigest(),'date':'2026-09-01',
            'valid_through':'2026-09-30','currency':'USD','total':'1000.00','reviewed':True,
            'reviewed_scope_sha256':scope_digest(self.scope),'evidence_kind':'current_supplier_quote',
            'scope_items':[{'scope_id':key,'status':status,'source_ref':'page 1'} for key,status in
                           [('work','included'),('delivery','excluded'),('fixtures','allowance')]]}

    def report(self):
        return report_from_quote(self.scope,[self.quote],'Q1','2026-09-16',self.root,
                                 {'report_id':'TEST','is_sample':True})

    def test_exclusions_allowances_and_unknowns_keep_distinct_meaning(self):
        report=self.report();findings=report['findings']
        self.assertEqual(len(findings),3)
        self.assertEqual(findings[0]['category'],'excluded_scope')
        self.assertEqual(findings[0]['confidence'],'fact')
        self.assertNotIn('low_allowance',[f['category'] for f in findings])
        self.assertIn('does not prove',findings[2]['detail'])
        self.assertTrue(all(f['realistic_low'] is None and f['bid_amount'] is None for f in findings))
        self.assertIsNone(report['meta']['bid_total'])
        self.assertEqual(report['meta']['trade_quote_total'],'1000.00')
        self.assertFalse(report['complete_home_bid_review'])

    def test_unreviewed_or_stale_scope_never_asserts_exclusion_as_fact(self):
        for change in ('unreviewed','stale'):
            if change=='unreviewed':self.quote['reviewed']=False
            else:self.quote['reviewed']=True;self.scope['measurement_version']=2
            r=self.report()
            self.assertEqual(len(r['findings']),4)
            self.assertTrue(all(f['confidence']=='needs_confirmation' for f in r['findings']))

    def test_changed_document_is_rejected(self):
        (self.root/'quote.txt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.report()

    def test_unsourced_exclusion_is_not_reported_as_a_homeowner_fact(self):
        self.quote['scope_items'][1]['source_ref']=None
        with self.assertRaisesRegex(ValueError,'source location'):
            self.report()

    def test_missing_installation_prompts_explicit_builder_question_without_invented_cost(self):
        self.scope['items']=[{'id':'wall','label':'Bedroom walls'}]
        self.scope['required_work']='complete'
        self.quote['reviewed_scope_sha256']=scope_digest(self.scope)
        self.quote['scope_items']=[{'scope_id':'wall','status':'included','source_ref':'page 1'}]
        self.quote['pricing_lines']=[{'id':'supply','scope_ids':['wall'],'work':'materials',
            'basis':'lump_sum','amount':'1000','source_ref':'page 1 material price'}]
        report=self.report()
        self.assertFalse(report['quote_comparison']['same_scope_current_quote'])
        self.assertTrue(any('required labor is missing' in f['detail'] for f in report['findings']))
        self.assertTrue(any('material supply and installation labor' in q for q in report['questions']))
        self.assertTrue(all(f['bid_amount'] is None and f['realistic_low'] is None and
                            f['realistic_high'] is None for f in report['findings']))
        self.quote['pricing_lines'][0]['work']='complete'
        self.assertEqual(self.report()['findings'],[])
        self.assertEqual(self.report()['questions'],[])

    def test_pricing_findings_reach_homeowner_even_when_all_scope_is_included(self):
        self.scope['requires_pricing_basis_review']=True
        self.quote['reviewed_scope_sha256']=scope_digest(self.scope)
        self.quote['scope_items']=[{'scope_id':i['id'],'status':'included','source_ref':'p1'} for i in self.scope['items']]
        report=self.report()
        self.assertEqual(len(report['findings']),1)
        self.assertEqual(report['findings'][0]['category'],'pricing_confirmation')
        self.assertIn('billing units',report['questions'][0])
        self.assertFalse(report['quote_comparison']['same_scope_current_quote'])
        self.assertIsNone(report['findings'][0]['realistic_high'])

    def test_report_questions_enter_return_visit_without_auto_resolution(self):
        store=AnswerStore(self.root/'cases.sqlite3');case=store.create_case('Test case')
        pre=store.attach_report(case,{'meta':{'report_type':'pre_bid'},'questions':['What scope is planned?']})
        report=store.attach_report(case,self.report())
        evidence=store.attach_evidence(case,'quote.txt',self.raw)
        follow=store.followup_report(case,report)
        qid=follow['questions'][0]['id']
        store.record_answer(report,qid,'Builder says delivery is now included',[evidence['reference']])
        updated=store.followup_report(case,report)
        self.assertFalse(updated['questions'][0]['resolved'])
        self.assertEqual(len(store.read_case(case)['reports']),2)
        self.assertFalse(updated['estimate_released'])

if __name__=='__main__':unittest.main()
