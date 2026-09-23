import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from case_service import make_server


class WorkspaceMeasurement(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.server=make_server(self.root/'cases.sqlite3',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}';self.store=self.server.store
        self.case=self.store.create_case('Synthetic measurement case');other=self.store.create_case('Other case')
        self.reviewer=self.server.access.issue(self.case,'private-reviewer','reviewer')
        self.owner=self.server.access.issue(self.case,'homeowner')
        self.other=self.server.access.issue(other,'other-reviewer','reviewer')
        with fitz.open() as pdf:
            for title in ('COVER','MAIN FLOOR PLAN','ROOF PLAN'):pdf.new_page().insert_text((30,30),title)
            raw=pdf.tobytes()
        evidence=self.store.attach_evidence(self.case,'synthetic.pdf',raw);self.server.processing.process_next()
        status=self.server.workspaces.initialize(self.case,evidence['reference'],'private-reviewer')
        self.sha=status['workspace_id'];self.job=self.server.workspaces.root/self.case/self.sha
        pages=[]
        with fitz.open(self.job/'plan.pdf') as pdf:
            for i,role in enumerate(('cover','floor_plan','roof_plan')):
                view=self.job/f'page{i}.png';pdf[i].get_pixmap().save(view)
                pages.append({'page':i+1,'role':role,'view':view.name,'view_sha256':hashlib.sha256(view.read_bytes()).hexdigest()})
        review={'plan_sha256':self.sha,'reviewer':'private-reviewer','cover_index':[[1,'Main Floor Plan'],[2,'Roof Plan'],[3,'Site Plan']],
            'pages':pages,'unresolved_issues':[]}
        self.review_path=self.job/'sheet_review.json';self.review_path.write_text(json.dumps(review))
        status=self.server.workspaces.read(self.case,self.sha)
        review['partial_measurement_review']={'role_pages':{'floor':2,'roof':3},'basis':'Synthetic partial review',
            'missing_roles':status['sheet_review']['missing_roles'],'unresolved_issues':[]}
        self.review_path.write_text(json.dumps(review));status=self.server.workspaces.read(self.case,self.sha)
        self.review_sha=status['sheet_review']['review_sha256'];self.endpoint='/api/plan-workspaces/'+self.sha+'/measure'

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,path=None,body=None,token=None,post=True):
        request=Request(self.base+(path or self.endpoint),data=json.dumps(body if body is not None else {'sheet_review_sha256':self.review_sha}).encode() if post else None,
            headers={'Authorization':'Bearer '+(token or self.reviewer),'Content-Type':'application/json','Origin':self.base})
        try:
            with urlopen(request) as response:return response.status,json.load(response)
        except HTTPError as error:return error.code,json.load(error)

    def prepare(self,job):
        time.sleep(.03)
        folder=Path(job)/'draft_takeoff';folder.mkdir()
        (folder/'summary.json').write_text(json.dumps({'plan_sha256':self.sha,'sheet_review_sha256':self.review_sha,
            'editable_region_candidates':2,'editable_count_candidates':0,'editable_length_candidates':3,'editable_measurements':5,
            'private_path':str(self.job),'private_price':999}))

    def test_authenticated_current_request_runs_once_and_keeps_reports_private(self):
        with patch('new_plan_measure.measure_job',side_effect=self.prepare) as engine:
            code,result=self.request();self.assertEqual(code,200)
            before={p.name:p.read_bytes() for p in self.job.iterdir() if p.is_file()}
            self.assertEqual(self.request(),(200,result));engine.assert_called_once()
        self.assertEqual(result['candidate_counts']['editable_measurements'],5)
        self.assertEqual(result['measurement_status'],'candidates_require_review')
        self.assertFalse(result['measurements_certified']);self.assertFalse(result['estimate_released'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.job.iterdir() if p.is_file()})
        for private in ('private_price','private-reviewer',str(self.root),'settings','markup_pct'):
            self.assertNotIn(private,json.dumps(result))
        record=json.loads((self.job/'measurement_run.json').read_bytes())
        self.assertEqual(record['reviewer_id'],'private-reviewer');self.assertEqual(record['sheet_review_sha256'],self.review_sha)
        self.assertEqual(self.store.read_case(self.case)['reports'],[])
        code,queue=self.request('/api/reviewer-queue',post=False)
        row=next(i for i in queue['items'] if i['kind']=='measurement_scope_review')
        self.assertEqual(row['trade_bid_drafts_request'],{'method':'GET',
            'url':'/api/plan-workspaces/'+self.sha+'/trade-bid-drafts'})

    def test_trade_bid_drafts_require_the_case_reviewer_and_preserve_private_errors(self):
        endpoint='/api/plan-workspaces/'+self.sha+'/trade-bid-drafts'
        self.assertEqual(self.request(endpoint,token=self.owner,post=False)[0],403)
        self.assertEqual(self.request(endpoint,token=self.other,post=False)[0],400)
        self.assertEqual(self.request(endpoint,post=False)[0],400)
        expected={'status':'reviewer_drafts','drafts':[],'sent':False}
        with patch.object(self.server.workspaces,'trade_bid_drafts',return_value=expected) as action:
            self.assertEqual(self.request(endpoint,post=False),(200,expected))
            action.assert_called_once_with(self.case,self.sha)
        with patch.object(self.server.workspaces,'trade_bid_drafts',side_effect=OSError('Private '+str(self.root))):
            code,response=self.request(endpoint,post=False)
            self.assertEqual(code,409);self.assertNotIn(str(self.root),json.dumps(response))
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_homeowner_other_case_old_review_and_extra_input_are_refused(self):
        with patch('new_plan_measure.measure_job') as engine:
            self.assertEqual(self.request(token=self.owner)[0],403)
            self.assertEqual(self.request(token=self.other)[0],400)
            self.assertEqual(self.request(body={'sheet_review_sha256':'old'})[0],400)
            self.assertEqual(self.request(body={'sheet_review_sha256':self.review_sha,'force':True})[0],400)
            self.review_path.rename(self.job/'saved_review.json')
            self.assertEqual(self.request()[0],400);engine.assert_not_called()
        self.assertFalse((self.job/'draft_takeoff').exists())

    def test_frozen_intake_changes_are_rejected_before_engine(self):
        path=self.job/'estimate_intake.json';path.write_bytes(path.read_bytes()+b' ')
        with patch('new_plan_measure.measure_job') as engine:
            self.assertEqual(self.request()[0],400);engine.assert_not_called()

    def test_overlapping_requests_do_not_run_two_measurements(self):
        with patch('new_plan_measure.measure_job',side_effect=self.prepare) as engine:
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.request(),range(2)))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0][0],200);engine.assert_called_once()

    def test_partial_output_is_preserved_and_queue_does_not_offer_a_retry(self):
        def fail(job):
            folder=Path(job)/'draft_takeoff';folder.mkdir();(folder/'keep.txt').write_text('Retain partial evidence')
            raise OSError('Synthetic disk error with private path '+str(job))
        with patch('new_plan_measure.measure_job',side_effect=fail) as engine:
            code,response=self.request();self.assertEqual(code,409);self.assertNotIn(str(self.root),json.dumps(response))
            self.assertEqual(self.request()[0],400);engine.assert_called_once()
        self.assertEqual((self.job/'draft_takeoff/keep.txt').read_text(),'Retain partial evidence')
        status=self.server.workspaces.read(self.case,self.sha);self.assertEqual(status['measurement_status'],'preparation_incomplete')
        code,queue=self.request('/api/reviewer-queue',post=False)
        row=next(i for i in queue['items'] if i['kind']=='measurement_preparation_incomplete')
        self.assertNotIn('measurement_request',row)

    def test_staged_failure_retains_evidence_and_api_retry_uses_current_review(self):
        result={'status':'more_information_required','pages':{1:{'ppf':10}},'lines':[
            {'id':'synthetic','page':1,'method':'synthetic','geometry':{
                'kind':'polygon','points':[[10,10],[110,10],[110,110],[10,110]]}}]}
        with patch('jnj_takeoff.run_takeoff',return_value=result), patch(
                'opening_quantity_review.default_mapping',side_effect=OSError('Private '+str(self.root))):
            code,error=self.request()
        self.assertEqual(code,409);self.assertNotIn(str(self.root),json.dumps(error))
        self.assertFalse((self.job/'draft_takeoff').exists())
        failed,=list(self.job.glob('.takeoff-attempt-*'))
        before={p.name:p.read_bytes() for p in failed.iterdir() if p.is_file()}
        self.assertIn('measurements.json',before)
        status=self.server.workspaces.read(self.case,self.sha)
        self.assertEqual(status['failed_preparation_attempts'],1)
        code,queue=self.request('/api/reviewer-queue',post=False)
        row=next(i for i in queue['items'] if i['kind']=='measurement_preparation_retry')
        self.assertEqual(row['measurement_request']['body']['sheet_review_sha256'],self.review_sha)
        with patch('jnj_takeoff.run_takeoff',return_value=result) as engine:
            self.assertEqual(self.request(body={'sheet_review_sha256':'old'})[0],400)
            self.assertEqual(self.request(token=self.owner)[0],403)
            engine.assert_not_called()
            code,status=self.request()
        self.assertEqual(code,200)
        self.assertEqual(status['measurement_status'],'candidates_require_review')
        self.assertFalse(status['estimate_released'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in failed.iterdir() if p.is_file()})
        self.assertEqual(self.request(),(200,status))
        self.assertEqual(self.store.read_case(self.case)['reports'],[])

    def test_review_queue_offers_current_action_and_stale_completed_output_is_not_overwritten(self):
        code,queue=self.request('/api/reviewer-queue',post=False)
        row=next(i for i in queue['items'] if i['kind']=='measurement_not_prepared')
        self.assertEqual(row['measurement_request'],{'method':'POST','url':self.endpoint,'body':{'sheet_review_sha256':self.review_sha}})
        with patch('new_plan_measure.measure_job',side_effect=self.prepare):self.assertEqual(self.request()[0],200)
        original=(self.job/'draft_takeoff/summary.json').read_bytes()
        review=json.loads(self.review_path.read_bytes());review['partial_measurement_review']['basis']+=' revised'
        self.review_path.write_text(json.dumps(review));status=self.server.workspaces.read(self.case,self.sha)
        with patch('new_plan_measure.measure_job') as engine:
            self.assertEqual(self.request(body={'sheet_review_sha256':status['sheet_review']['review_sha256']})[0],400)
            engine.assert_not_called()
        self.assertEqual((self.job/'draft_takeoff/summary.json').read_bytes(),original)


if __name__=='__main__':unittest.main()
