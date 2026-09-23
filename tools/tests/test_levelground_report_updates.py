import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from answer_store import AnswerStore,encode


class UpdatedReports(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=AnswerStore(Path(self.tmp.name)/'answers.sqlite3');self.case=self.store.create_case('Synthetic case')
        self.original={'meta':{'report_type':'bid_gap','bid_total':100000},
            'findings':[{'title':'Permit fee scope','detail':'Confirm who pays fees','basis':'Bid unclear',
                         'bid_amount':None,'realistic_low':None}],
            'quantities':[{'item':'Floor','qty':1000}],'questions':['Who pays permit fees?','Who handles site work?'],
            'unknowns':['Site conditions not verified']}
        self.report=self.store.attach_report(self.case,self.original)
        q=self.store.read_case(self.case)['reports'][0]['questions'][0];self.qid=q['id']
        answer=self.store.record_answer(self.report,q['id'],'Builder includes fees',['Addendum p2'])
        review=self.store.review_answer(self.report,answer['answer_id'],'test-reviewer','accepted','Written fee inclusion',['Addendum p2'])
        self.update={'finding_index':0,'finding_sha256':hashlib.sha256(encode(self.original['findings'][0]).encode()).hexdigest(),
            'question_id':q['id'],'answer_id':answer['answer_id'],'review_id':review['review_id'],
            'replacement':{'detail':'Written addendum includes permit fees; permit approval remains unverified.',
                           'basis':'Reviewed addendum p2'}}

    def test_full_report_updates_reviewed_narrative_and_retains_financial_evidence(self):
        revised=self.store.updated_report(self.case,self.report,[self.update])
        self.assertEqual(revised['questions'],['Who handles site work?'])
        self.assertEqual(revised['findings'][0]['detail'],self.update['replacement']['detail'])
        self.assertEqual(revised['quantities'],self.original['quantities'])
        self.assertEqual(revised['meta']['bid_total'],100000)
        self.assertEqual(revised['unknowns'],self.original['unknowns'])
        self.assertIsNone(revised['findings'][0]['realistic_low'])
        self.assertEqual(self.store.read_case(self.case)['reports'][0]['source_report'],self.original)

    def test_new_answer_invalidates_old_finding_update_and_reopens_question(self):
        self.store.record_answer(self.report,self.qid,'Fees now excluded',['New addendum'])
        with self.assertRaisesRegex(ValueError,'latest accepted'):self.store.updated_report(self.case,self.report,[self.update])
        revised=self.store.updated_report(self.case,self.report)
        self.assertEqual(revised['questions'],self.original['questions'])
        self.assertEqual(revised['findings'],self.original['findings'])

    def test_wrong_case_finding_hash_and_financial_replacement_rejected(self):
        other=self.store.create_case('Other')
        with self.assertRaises(ValueError):self.store.updated_report(other,self.report,[self.update])
        for change in ('hash','money','duplicate','review'):
            u=copy.deepcopy(self.update)
            if change=='hash':u['finding_sha256']='wrong'
            if change=='money':u['replacement']['bid_amount']=0
            if change=='review':u['review_id']+=1
            updates=[u,u] if change=='duplicate' else [u]
            with self.subTest(change=change),self.assertRaises(ValueError):self.store.updated_report(self.case,self.report,updates)

    def test_later_reviewer_reversal_invalidates_prior_update(self):
        self.store.review_answer(self.report,self.update['answer_id'],'reviewer','needs_clarification','Evidence scope unclear',['Addendum p2'])
        with self.assertRaises(ValueError):self.store.updated_report(self.case,self.report,[self.update])

if __name__=='__main__':unittest.main()
