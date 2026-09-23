import copy
import json
import threading
import unittest
from unittest.mock import Mock,patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from test_levelground_bid_documents import BidDocumentTests
from case_trade_quote import prepare_trade_quote
from case_service import make_server
from bid_comparison import scope_digest


class CaseTradeQuoteTests(unittest.TestCase):
    def setUp(self):
        BidDocumentTests.setUp(self)
        self.payload['document_kind']='trade_quote'
        self.record=self.reviews.save(self.case,'operator',self.payload)
        self.scope={'plan_sha256':'fixture-plan','measurement_version':1,'required_work':'complete',
            'items':[{'id':'gutters','label':'Gutters and downspouts'}],'sent':False}
        self.scope['scope_sha256']=scope_digest(self.scope)
        self.workspace=Mock()
        def drafts(case,identity):
            if case!=self.case or identity!='workspace':raise ValueError('Wrong case workspace')
            return {'drafts':[{'scope':copy.deepcopy(self.scope)}]}
        self.workspace.trade_bid_drafts.side_effect=drafts
        ref=f'evidence:{self.evidence}, page 1'
        self.request={'document_review_id':self.record['id'],'workspace_id':'workspace',
            'scope_sha256':self.scope['scope_sha256'],'rationale':'Synthetic source-reviewed pricing fixture',
            'quote':{'supplier':'Synthetic supplier','date':'2026-09-01','valid_through':'2026-12-01',
                'evidence_kind':'current_subcontractor_quote',
                'scope_items':[{'scope_id':'gutters','status':'included','source_ref':ref}],
                'pricing_lines':[{'id':'materials','scope_ids':['gutters'],'work':'materials',
                    'basis':'lump_sum','amount':123456,'source_ref':ref}]}}

    def draft(self):return prepare_trade_quote(self.reviews,self.workspace,self.case,'operator',self.request)

    def test_retained_quote_reaches_report_without_publication_or_invented_cost(self):
        result=self.draft()
        self.assertTrue(any('required labor is missing' in f['detail'] for f in result['findings']))
        self.assertTrue(any('installation labor' in q for q in result['questions']))
        self.assertIsNone(result['meta']['bid_total'])
        self.assertEqual(result['meta']['trade_quote_total'],'123456.0')
        self.assertFalse(result['homeowner_release_approved'])
        self.assertEqual(self.store.read_case(self.case)['reports'],[])
        self.assertEqual(result['quote_comparison']['source_file'],'synthetic-bid.txt')

    def test_other_case_and_old_scope_are_rejected(self):
        with self.assertRaises(ValueError):
            prepare_trade_quote(self.reviews,self.workspace,self.other,'operator',self.request)
        self.scope['measurement_version']=2;self.scope['scope_sha256']=scope_digest(self.scope)
        with self.assertRaisesRegex(ValueError,'current case trade scope'):self.draft()

    def test_newer_document_review_and_uncited_price_are_rejected(self):
        self.request['quote']['pricing_lines'][0]['source_ref']='a different document'
        with self.assertRaisesRegex(ValueError,'reviewed document page'):self.draft()
        self.request['quote']['pricing_lines'][0]['source_ref']=f'evidence:{self.evidence}, page 1'
        self.reviews.save(self.case,'operator',{**self.payload,'base_review_id':self.record['id']})
        with self.assertRaisesRegex(ValueError,'latest complete'):self.draft()

    def test_client_cannot_replace_retained_document_total(self):
        self.request['quote']['total']=1
        with self.assertRaisesRegex(ValueError,'source-transcribed'):self.draft()

    def test_http_review_publish_and_changed_scope_guard(self):
        server=make_server(self.store.path,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,payload,token):
            req=Request(f'http://127.0.0.1:{server.server_port}'+path,data=None if payload is None else json.dumps(payload).encode(),
                headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            try:
                with urlopen(req,timeout=10) as r:return r.status,json.load(r)
            except HTTPError as e:return e.code,json.load(e)
        try:
            home=server.access.issue(self.case,'homeowner')
            reviewer=server.access.issue(self.case,'operator','reviewer')
            with patch.object(server.workspaces,'trade_bid_drafts',side_effect=self.workspace.trade_bid_drafts.side_effect):
                self.assertEqual(request('/api/trade-quote-draft',self.request,home)[0],403)
                status,report=request('/api/trade-quote-draft',self.request,reviewer)
                self.assertEqual(status,200)
                changed=copy.deepcopy(report);changed['findings']=[]
                self.assertEqual(request('/api/reports',{'report':changed},reviewer)[0],400)
                status,published=request('/api/reports',{'report':report},reviewer)
                self.assertEqual(status,201)
                status,visible=request('/api/reports/'+published['report_id'],None,home)
                self.assertEqual(status,200)
                self.assertTrue(any('installation labor' in q for q in visible['questions']))
                self.assertTrue(visible['trade_quote_sources_current'])
                case=request('/api/case',None,home)[1]
                q=next(q for q in case['reports'][0]['questions'] if 'installation labor' in q['text'])
                self.assertEqual(request('/api/answers',{'report_id':published['report_id'],
                    'question_id':q['id'],'text':'Builder says labor is separate; awaiting written price.',
                    'evidence_refs':[]},home)[0],201)
                self.scope['measurement_version']=2;self.scope['scope_sha256']=scope_digest(self.scope)
                self.assertEqual(request('/api/reports',{'report':report},reviewer)[0],400)
                stale=request('/api/reports/'+published['report_id'],None,home)[1]
                self.assertFalse(stale['trade_quote_sources_current'])
                self.assertEqual(stale['findings'][0]['category'],'source_revision')
                displayed=request('/api/case',None,home)[1]['reports'][0]
                self.assertEqual(displayed['current_report_view']['findings'][0]['category'],'source_revision')
                self.assertFalse(any(f['category']=='source_revision' for f in displayed['source_report']['findings']))
                self.assertEqual(len(self.store.read_case(self.case)['reports'][0]['questions'][-1]['answers']),1)
                queue=request('/api/reviewer-queue',None,reviewer)[1]
                self.assertTrue(any(i['kind']=='trade_quote_revision_review' for i in queue['items']))
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
