import hashlib
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from answer_store import AnswerStore


class CaseEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'cases.sqlite3';self.store=AnswerStore(self.path)
        self.case=self.store.create_case('One');self.other=self.store.create_case('Two')
        self.report=self.store.attach_report(self.case,{'meta':{'report_type':'bid_gap'},'questions':['Included?']})
        self.question=self.store.read_case(self.case)['reports'][0]['questions'][0]['id']

    def test_file_bytes_survive_reload_and_link_to_answer_review(self):
        content=b'Synthetic addendum: permit fees included.'
        file=self.store.attach_evidence(self.case,'addendum.txt',content)
        self.assertEqual(AnswerStore(self.path).read_evidence(self.case,file['reference'])['body'],content)
        answer=self.store.record_answer(self.report,self.question,'Included',[file['reference']])
        self.store.review_answer(self.report,answer['answer_id'],'reviewer','accepted','Read addendum',[file['reference']])
        question=self.store.updated_report(self.case,self.report)['return_visit']['questions'][0]
        self.assertTrue(question['resolved'])
        self.assertEqual(question['answer']['linked_evidence'][0]['sha256'],hashlib.sha256(content).hexdigest())
        self.assertTrue(question['answer']['reviews'][0]['linked_evidence'][0]['content_integrity_verified'])

    def test_other_case_file_cannot_be_read_or_used_as_evidence(self):
        file=self.store.attach_evidence(self.other,'private.txt',b'private')
        with self.assertRaises(ValueError):self.store.read_evidence(self.case,file['reference'])
        with self.assertRaises(ValueError):self.store.record_answer(self.report,self.question,'Included',[file['reference']])
        answer=self.store.record_answer(self.report,self.question,'Included')
        with self.assertRaises(ValueError):self.store.review_answer(self.report,answer['answer_id'],'reviewer','accepted','Other source',[file['reference']])

    def test_altered_bytes_block_report_regeneration(self):
        file=self.store.attach_evidence(self.case,'source.txt',b'original')
        self.store.record_answer(self.report,self.question,'Included',[file['reference']])
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('UPDATE evidence_objects SET body=?',(b'altered',))
        with self.assertRaisesRegex(ValueError,'content changed'):self.store.updated_report(self.case,self.report)

    def test_invalid_uploads_and_missing_references_refused(self):
        for name,content in [('',b'a'),('empty',b''),('not bytes','abc')]:
            with self.assertRaises(ValueError):self.store.attach_evidence(self.case,name,content)
        with self.assertRaises(ValueError):self.store.attach_evidence('wrong','file',b'a')
        with self.assertRaises(ValueError):self.store.record_answer(self.report,self.question,'Yes',['evidence:missing'])

if __name__=='__main__':unittest.main()
