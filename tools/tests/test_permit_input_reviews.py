import concurrent.futures
from pathlib import Path
import tempfile
import unittest
from answer_store import AnswerStore
from permit_input_reviews import PermitInputReviews


class PermitInputReviewTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=AnswerStore(Path(temp.name)/'cases.sqlite3')
        self.case=self.store.create_case('Test');self.other=self.store.create_case('Other')
        self.reviews=PermitInputReviews(self.store)
        self.ref=self.store.attach_evidence(self.case,'permit.txt',b'Synthetic county evidence')['reference']
        self.payload={'expected_revision':0,'jurisdiction':{'state':'GA','authority_verified':False},
            'rationale':'Correct the recorded property state','evidence_refs':[self.ref]}

    def save(self,payload=None):
        return self.reviews.save(self.case,'a'*64,'b'*64,'reviewer',payload or self.payload)

    def test_revisions_preserve_history_and_reject_stale_saves(self):
        first=self.save()
        with self.assertRaisesRegex(ValueError,'revision changed'):self.save()
        second=self.save({**self.payload,'expected_revision':1,'jurisdiction':{'state':'SC'}})
        self.assertEqual(second['records'][0],first['records'][0])
        self.assertEqual(second['records'][1]['parent_sha256'],first['revision_sha256'])
        reopened=PermitInputReviews(AnswerStore(self.store.path)).read(self.case,'a'*64,'b'*64)
        self.assertEqual(reopened,second)
        with self.assertRaisesRegex(ValueError,'history changed'):
            self.reviews.read(self.case,'a'*64,'c'*64)

    def test_cross_case_evidence_invalid_inputs_and_tampering_are_rejected(self):
        other=self.store.attach_evidence(self.other,'private.txt',b'private')['reference']
        for update in ({'evidence_refs':[other]},{'evidence_refs':[]},{'rationale':' '},
                       {'expected_revision':True},{'jurisdiction':{'authority_verified':'yes'}},
                       {'jurisdiction':{'code_basis_date':'bad'}},{'reviewer_id':'spoofed'}):
            with self.subTest(update=update),self.assertRaises(ValueError):self.save({**self.payload,**update})
        self.assertEqual(self.reviews.read(self.case,'a'*64,'b'*64)['revision'],0)
        self.save()
        with self.store.connect() as db,db:
            db.execute("UPDATE permit_input_reviews SET body='{}'")
        with self.assertRaisesRegex(ValueError,'history changed'):self.reviews.read(self.case,'a'*64,'b'*64)

    def test_concurrent_reviewers_cannot_silently_overwrite_each_other(self):
        def attempt(_):
            try:return self.save()['revision']
            except ValueError as error:return str(error)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
        self.assertEqual(results.count(1),1)
        self.assertTrue(any(isinstance(r,str) and 'revision changed' in r for r in results))
        self.assertEqual(self.reviews.read(self.case,'a'*64,'b'*64)['revision'],1)


if __name__=='__main__':unittest.main()
