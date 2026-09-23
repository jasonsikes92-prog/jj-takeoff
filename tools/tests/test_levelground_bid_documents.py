import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'levelground'))
from answer_store import AnswerStore
from bid_document_reviews import BidDocumentReviews
from case_service import make_server
from document_processing import DocumentProcessing
from plan_workspaces import PlanWorkspaces
from reviewer_queue import case_review_queue


class BidDocumentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = AnswerStore(self.root/'cases.sqlite3')
        self.case = self.store.create_case('Synthetic owner')
        self.other = self.store.create_case('Other owner')
        self.processing = DocumentProcessing(self.store)
        self.reviews = BidDocumentReviews(self.store,self.processing)
        self.text = 'Gutters and downspouts included.\nLandscaping excluded.\nTotal: $123,456.00\n'
        evidence = self.store.attach_evidence(self.case,'synthetic-bid.txt',self.text.encode())
        self.evidence = evidence['reference'].split(':')[1]
        self.processing.process_next()
        self.prepared = self.processing.read(self.case,self.evidence)
        self.payload = {'evidence_id':self.evidence,'source_sha256':self.prepared['source_sha256'],
            'extraction_sha256':self.prepared['result_sha256'],'document_kind':'builder_bid',
            'reviewed_pages':[1],'document_review_complete':True,'rationale':'Read the supplied one-page bid; no referenced plan was supplied.',
            'base_review_id':None,'currency':'USD','total_candidate_index':0,
            'lines':[{'page':1,'source_text':'Gutters and downspouts included.','scope_status':'included',
                      'confirmed_scopes':['Gutters & downspouts']},
                     {'page':1,'source_text':'Landscaping excluded.','scope_status':'excluded',
                      'confirmed_scopes':['Landscaping, sod & irrigation']}]}

    def test_source_review_generates_existing_engine_draft_without_publication(self):
        before = self.store.read_case(self.case)
        review = self.reviews.save(self.case,'operator',self.payload)
        report = self.reviews.draft(self.case,review['id'])
        self.assertEqual(report['meta']['bid_total'],123456)
        self.assertIsNone(report['meta']['our_range'])
        self.assertIsNone(report['meta']['home']['heated_sf'])
        self.assertIsNone(report['meta']['home']['stories'])
        self.assertFalse(any(f['title']=='Gutters & downspouts' for f in report['findings']))
        landscape = next(f for f in report['findings'] if f['title']=='Landscaping, sod & irrigation')
        self.assertEqual(landscape['category'],'excluded_scope')
        self.assertIn(self.evidence,landscape['evidence_lines'][0]['source_ref'])
        self.assertTrue(all(f['realistic_high'] is None for f in report['findings']))
        self.assertFalse(report['complete_home_bid_review'])
        self.assertFalse(report['homeowner_release_approved'])
        self.assertEqual(report['quantities'],[])
        self.assertEqual(self.store.read_case(self.case),before)

    def test_trade_quote_or_addendum_never_sets_whole_home_bid_total(self):
        for kind in ('trade_quote','scope_addendum'):
            prior = self.reviews.latest(self.case,self.evidence)
            payload = {**self.payload,'document_kind':kind,'base_review_id':None if prior is None else prior['id']}
            review = self.reviews.save(self.case,'operator',payload)
            report = self.reviews.draft(self.case,review['id'])
            self.assertIsNone(report['meta']['bid_total'])
            self.assertEqual(report['meta']['document_total'],123456)

    def test_total_selection_is_explicit_and_unknown_is_not_zero(self):
        payload = {**self.payload,'total_candidate_index':None}
        review = self.reviews.save(self.case,'operator',payload)
        self.assertIsNone(self.reviews.draft(self.case,review['id'])['meta']['bid_total'])
        for change in ({'total_candidate_index':1},{'currency':'CAD'},{'total_candidate_index':True}):
            with self.assertRaises(ValueError):
                self.reviews.save(self.case,'operator',{**self.payload,'base_review_id':review['id'],**change})

    def test_fabricated_text_pages_scope_and_stale_sources_rejected(self):
        variants = [{'source_sha256':'0'*64},{'extraction_sha256':'0'*64},
                    {'reviewed_pages':[1,1]},{'reviewed_pages':[2]},
                    {'lines':[{'page':1,'source_text':'Invented inclusion'}]},
                    {'lines':[{'page':1,'source_text':'Landscaping excluded.','confirmed_scopes':['invented scope']}]},
                    {'lines':[{'page':True,'source_text':'Landscaping excluded.'}]}]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.reviews.save(self.case,'operator',{**self.payload,**change})
        self.assertIsNone(self.reviews.latest(self.case,self.evidence))
        with self.assertRaises(ValueError): self.reviews.save(self.other,'other',self.payload)

    def test_partial_review_cannot_confirm_scope_or_select_a_total(self):
        payload = {**self.payload,'document_review_complete':False,'total_candidate_index':None}
        with self.assertRaises(ValueError): self.reviews.save(self.case,'operator',payload)
        payload['lines'] = [{'page':1,'source_text':'Landscaping excluded.'}]
        review = self.reviews.save(self.case,'operator',payload)
        report = self.reviews.draft(self.case,review['id'])
        self.assertFalse(any(f['category']=='excluded_scope' for f in report['findings']))
        self.assertIn('partial',' '.join(report['unknowns']))
        with fitz.open() as pdf:
            pdf.new_page().insert_text((20,20),'Bid scope')
            pdf.new_page()
            evidence = self.store.attach_evidence(self.case,'partly-scanned.pdf',pdf.tobytes())
        self.processing.process_next()
        prepared = self.processing.read(self.case,evidence['reference'].split(':')[1])
        with self.assertRaises(ValueError):
            self.reviews.save(self.case,'operator',{**payload,'evidence_id':prepared['evidence_id'],
                'source_sha256':prepared['source_sha256'],'extraction_sha256':prepared['result_sha256'],
                'reviewed_pages':[1,2],'document_review_complete':True,'lines':[{'page':1,'source_text':'Bid scope'}]})

    def test_revision_reopens_queue_and_stale_draft_is_rejected(self):
        workspace = PlanWorkspaces(self.store,self.root/'workspaces')
        queue = lambda:case_review_queue(self.store,self.processing,workspace,self.case)
        review = self.reviews.save(self.case,'operator',self.payload)
        self.assertIn('bid_report_review',[i['kind'] for i in queue()['items']])
        self.store.attach_report(self.case,self.reviews.draft(self.case,review['id']))
        self.assertNotIn('bid_report_review',[i['kind'] for i in queue()['items']])
        with self.assertRaises(ValueError): self.reviews.save(self.case,'operator',self.payload)
        revised = self.reviews.save(self.case,'operator',{**self.payload,'base_review_id':review['id'],'total_candidate_index':None})
        self.assertIn('bid_report_review',[i['kind'] for i in queue()['items']])
        self.assertEqual(self.reviews.read(self.case,review['id'])['bid']['total'],123456)
        with self.assertRaises(ValueError): self.reviews.draft(self.case,review['id'])
        self.assertIsNone(self.reviews.draft(self.case,revised['id'])['meta']['bid_total'])

    def test_earlier_checklist_report_reopens_document_task(self):
        review=self.reviews.save(self.case,'operator',self.payload)
        draft=self.reviews.draft(self.case,review['id'])
        old={**draft,'scope_checklist_version':'earlier-eight-topic-checklist'}
        self.store.attach_report(self.case,old)
        workspaces=PlanWorkspaces(self.store,self.root/'workspaces')
        queue=case_review_queue(self.store,self.processing,workspaces,self.case)
        self.assertTrue(any(i['kind']=='bid_report_review' for i in queue['items']))
        self.store.attach_report(self.case,draft)
        queue=case_review_queue(self.store,self.processing,workspaces,self.case)
        self.assertFalse(any(i['kind']=='bid_report_review' for i in queue['items']))

    def test_altered_review_and_extraction_fail_closed(self):
        review = self.reviews.save(self.case,'operator',self.payload)
        with self.store.connect() as db, db:
            db.execute('UPDATE bid_document_reviews SET body=? WHERE id=?',('{}',review['id']))
        with self.assertRaises(ValueError): self.reviews.read(self.case,review['id'])
        with self.store.connect() as db, db:
            body = {k:v for k,v in review.items() if k!='review_sha256'}
            from answer_store import encode
            db.execute('UPDATE bid_document_reviews SET body=? WHERE id=?',(encode(body),review['id']))
            db.execute('UPDATE document_processing SET result=? WHERE evidence_id=?',('{}',self.evidence))
        with self.assertRaises(ValueError): self.reviews.draft(self.case,review['id'])

    def test_http_review_draft_and_existing_return_visit_flow(self):
        server=make_server(self.store.path,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            operator=server.access.issue(self.case,'assigned-operator','reviewer')
            homeowner=server.access.issue(self.case,'homeowner')
            other=server.access.issue(self.other,'other-operator','reviewer')
            def request(path,payload=None,token=operator):
                headers={'Authorization':'Bearer '+token}
                if payload is not None:headers['Content-Type']='application/json'
                req=Request(f'http://127.0.0.1:{server.server_port}'+path,
                            data=None if payload is None else json.dumps(payload).encode(),headers=headers)
                try:response=urlopen(req,timeout=5)
                except HTTPError as error:response=error
                with response:return response.status,json.load(response)
            endpoint='/api/bid-document-reviews'
            self.assertEqual(request(endpoint,self.payload,homeowner)[0],403)
            self.assertEqual(request(endpoint,self.payload,other)[0],400)
            status,review=request(endpoint,{**self.payload,'reviewer_id':'spoofed'})
            self.assertEqual(status,201);self.assertEqual(review['reviewer_id'],'assigned-operator')
            path=endpoint+'/'+review['id']+'/draft'
            self.assertEqual(request(path,token=homeowner)[0],403)
            self.assertEqual(request(path,token=other)[0],400)
            status,draft=request(path)
            self.assertEqual(status,200)
            status,attached=request('/api/reports',{'report':draft})
            self.assertEqual(status,201)
            case=self.store.read_case(self.case)
            report=case['reports'][0]
            question=report['questions'][0]['id']
            status,_=request('/api/answers',{'report_id':attached['report_id'],'question_id':question,
                'text':'Builder will provide clarification'},homeowner)
            self.assertEqual(status,201)
            status,updated=request('/api/reports/'+attached['report_id'],token=homeowner)
            self.assertEqual(status,200)
            self.assertEqual(updated['return_visit']['questions'][0]['status'],'answer_received_needs_review')
            self.assertEqual(updated['meta']['bid_total'],123456)
            self.assertFalse(updated['return_visit']['prices_recalculated'])
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
