import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from answer_store import AnswerStore


class HomeownerAnswers(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'answers.sqlite3'
        self.store=AnswerStore(self.path);self.case=self.store.create_case('Synthetic homeowner case')
    def tearDown(self):self.tmp.cleanup()
    def report(self,stage='pre_bid'):
        return self.store.attach_report(self.case,{'meta':{'report_type':stage},'questions':['Who pays permit fees?']})
    def question(self,index=0):return self.store.read_case(self.case)['reports'][index]['questions'][0]
    def test_two_stages_keep_separate_report_evidence(self):
        first=self.report();q=self.question()
        self.store.record_answer(first,q['id'],'Builder says included',['Proposal page 3'])
        second=self.report('bid_gap')
        case=AnswerStore(self.path).read_case(self.case)
        self.assertEqual(len(case['reports']),2)
        self.assertEqual(case['reports'][1]['questions'][0]['status'],'awaiting_answer')
        self.assertEqual(case['reports'][0]['questions'][0]['answers'][0]['evidence_refs'],['Proposal page 3'])
        self.assertFalse(case['permit_compliance_verified'])
    def test_answer_changes_are_append_only_and_not_automatically_approved(self):
        report=self.report();qid=self.question()['id']
        self.store.record_answer(report,qid,'Not sure')
        self.store.record_answer(report,qid,'Written inclusion received',['Addendum 1, section 4'])
        q=self.question();self.assertEqual([a['revision'] for a in q['answers']],[1,2])
        self.assertFalse(q['resolved']);self.assertEqual(q['status'],'answer_received_needs_review')
        self.assertEqual(q['answers'][0]['text'],'Not sure')
    def test_unknown_case_question_and_empty_answer_refused(self):
        report=self.report();qid=self.question()['id']
        for rid,question,text in [(report,'wrong','Yes'),('other',qid,'Yes'),(report,qid,'')]:
            with self.assertRaises(ValueError):self.store.record_answer(rid,question,text)
        with self.assertRaises(ValueError):self.store.read_case('wrong')
    def test_separate_cases_do_not_mix_in_returned_records(self):
        self.report();other=self.store.create_case('Second synthetic case')
        self.assertEqual(self.store.read_case(other)['reports'],[])
    def test_report_tampering_refused(self):
        self.report()
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE reports SET body=?',('{}',))
        with self.assertRaises(ValueError):self.store.read_case(self.case)
    def test_question_text_cannot_drift_from_source_report(self):
        self.report()
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE questions SET text=?',('Different scope',))
        with self.assertRaises(ValueError):self.store.read_case(self.case)
    def test_review_resolves_only_the_latest_answer_and_preserves_history(self):
        report=self.report();qid=self.question()['id']
        answer=self.store.record_answer(report,qid,'Included',['Contract p3'])
        self.store.review_answer(report,answer['answer_id'],'synthetic-reviewer','accepted','Written inclusion matches scope',['Contract p3'])
        self.assertTrue(self.question()['resolved'])
        self.store.record_answer(report,qid,'Builder revised the exclusion',['Addendum 2'])
        self.assertFalse(self.question()['resolved'])
        self.assertEqual(self.question()['status'],'answer_received_needs_review')
        self.assertEqual(len(self.question()['answers'][0]['reviews']),1)
        self.assertFalse(self.store.read_case(self.case)['estimate_released'])
    def test_review_requires_correct_report_identity_and_evidence(self):
        report=self.report();answer=self.store.record_answer(report,self.question()['id'],'Included')
        for rid,reviewer,evidence in [('other','operator',['source']), (report,'',['source']), (report,'operator',[])]:
            with self.assertRaises(ValueError):
                self.store.review_answer(rid,answer['answer_id'],reviewer,'accepted','Reason',evidence)
        self.assertFalse(self.question()['resolved'])
    def test_reviewer_can_reopen_without_erasing_prior_decision(self):
        report=self.report();answer=self.store.record_answer(report,self.question()['id'],'Included')
        for decision in ['accepted','needs_clarification']:
            self.store.review_answer(report,answer['answer_id'],'synthetic-reviewer',decision,'Review rationale',['source'])
        self.assertFalse(self.question()['resolved'])
        self.assertEqual(len(self.question()['answers'][0]['reviews']),2)
    def test_reviewed_answer_tampering_is_refused(self):
        report=self.report();answer=self.store.record_answer(report,self.question()['id'],'Included')
        self.store.review_answer(report,answer['answer_id'],'synthetic-reviewer','accepted','Reviewed source',['source'])
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE answers SET text=?',('Excluded',))
        with self.assertRaises(ValueError):self.store.read_case(self.case)

    def test_followup_uses_current_answer_without_rewriting_original_report(self):
        report=self.report();qid=self.question()['id']
        original=self.store.read_case(self.case)['reports'][0]['source_report']
        answer=self.store.record_answer(report,qid,'Included',['Contract p3'])
        self.store.review_answer(report,answer['answer_id'],'reviewer','accepted','Written scope checked',['Contract p3'])
        accepted=self.store.followup_report(self.case,report)
        self.assertEqual(accepted['resolved_question_count'],1)
        self.assertEqual(accepted['open_question_ids'],[])
        self.store.record_answer(report,qid,'Now excluded',['Addendum 2'])
        reopened=self.store.followup_report(self.case,report)
        self.assertEqual(reopened['open_question_ids'],[qid])
        self.assertIsNone(reopened['questions'][0]['latest_review'])
        self.assertEqual(reopened['questions'][0]['latest_answer']['revision'],2)
        self.assertEqual(self.store.read_case(self.case)['reports'][0]['source_report'],original)
        self.assertFalse(reopened['estimate_released'])
        self.assertEqual(accepted['resolved_question_count'],1)

    def test_followup_cannot_use_report_from_another_case(self):
        report=self.report();other=self.store.create_case('Other case')
        with self.assertRaisesRegex(ValueError,'does not belong'):
            self.store.followup_report(other,report)

if __name__=='__main__':unittest.main()
