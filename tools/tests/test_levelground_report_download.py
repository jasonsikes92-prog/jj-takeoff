import base64
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'levelground'))
from report_download import render_download


class ReportDownloadTests(unittest.TestCase):
    def render(self, report):
        raw = render_download(report).decode()
        script = re.findall(r'<script>(.*?)</script>', raw, re.S)[0]
        runner = r'''
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),elements={};
const document={getElementById(id){return elements[id]??=(id==='report-data'
  ?{textContent:JSON.stringify(input.report)}
  :{style:{},classList:{remove(){},toggle(){}},innerHTML:'',textContent:''});},querySelectorAll(){return [];}};
vm.runInNewContext(input.script,{document});
process.stdout.write(JSON.stringify(elements));
'''
        result = subprocess.run(['node', '-e', runner], input=json.dumps({'report':report, 'script':script}),
                                capture_output=True, text=True, encoding='utf-8', check=True)
        return raw, json.loads(result.stdout)

    def test_sparse_report_stays_unknown_and_works_offline(self):
        for stage in ('pre_bid', 'bid_gap'):
            with self.subTest(stage=stage):
                raw, elements = self.render({'meta':{'report_type':stage},
                    'quantities':[{'item':'Unknown area', 'qty':None}, {'item':'Explicit zero', 'qty':0}]})
                self.assertIn('Area not established', elements['rMeta']['innerHTML'])
                self.assertIn('Not measured', elements['qty']['innerHTML'])
                self.assertIn('>0 ', elements['qty']['innerHTML'])
                self.assertIn('Not verified', elements['qty']['innerHTML'])
                self.assertNotIn('<link', raw)
                self.assertNotRegex(raw, r'<(?:script|img|iframe)[^>]+src=')
                script = re.findall(r'<script>(.*?)</script>', raw, re.S)[0]
                digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
                self.assertIn("script-src 'sha256-" + digest + "'", raw)
                self.assertIn("default-src 'none'", raw)

    def test_saved_answers_and_review_evidence_are_escaped_without_mutating_source(self):
        payload = '</script><img src=x onerror="alert(1)"> & builder'
        report = {'meta':{'report_type':'bid_gap'}, 'questions':[payload], 'unknowns':[payload],
                  'return_visit':{'generated_at':'2026-09-17', 'source_report_id':'source-id',
                    'source_report_sha256':'a'*64, 'questions':[{'text':payload, 'status':'review_accepted',
                    'answer':{'text':payload, 'revision':2, 'created_at':'2026-09-17', 'evidence_refs':[payload],
                              'reviews':[{'rationale':payload, 'evidence_refs':[payload]}]}}]}}
        original = copy.deepcopy(report)
        raw, elements = self.render(report)
        self.assertEqual(original, report)
        embedded = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', raw, re.S).group(1)
        self.assertNotIn('<', embedded)
        self.assertEqual(json.loads(embedded), report)
        answers = elements['returnVisitAnswers']['innerHTML']
        self.assertFalse(elements['returnVisit']['hidden'])
        self.assertNotIn('<img', answers)
        self.assertIn(payload, html.unescape(answers))
        self.assertIn('Reviewed · resolved', answers)
        self.assertIn('Answer revision 2', answers)
        self.assertIn('Source SHA-256: ' + 'a'*64, elements['returnVisitMeta']['textContent'])


    def test_reviewer_warning_stays_in_header_when_unpriced_verdict_is_hidden(self):
        report={'meta':{'report_type':'pre_bid','our_range':None,'verdict_note':'Partial references; no complete estimate.'},
            'report_status':'reviewer_draft','homeowner_release_approved':False}
        raw,elements=self.render(report)
        self.assertEqual(elements['verdictSection']['style']['display'],'none')
        self.assertEqual(elements['rType']['textContent'],'Reviewer draft · not approved for release')
        self.assertIn('Partial references',elements['rSummary']['textContent'])
        self.assertEqual(elements['quantityTitle']['textContent'],'Draft measurement references')
        self.assertEqual(elements['quantityLabel']['textContent'],'partial quantities · confirmation required')
        self.assertLess(raw.index('id="rSummary"'),raw.index('id="verdictSection"'))
        for identity in ('rSummary','quantityTitle','quantityLabel'):
            self.assertEqual(len(re.findall('id="'+identity+'"',raw)),1)

    def test_draft_notice_fallback_and_text_are_safe_in_both_report_modes(self):
        for stage in ('pre_bid','bid_gap'):
            report={'meta':{'report_type':stage},'report_status':'reviewer_draft'}
            _,elements=self.render(report)
            self.assertIn('unconfirmed',elements['rSummary']['textContent'])
            payload='</script><img src=x onerror="alert(1)">'
            report['meta']['verdict_note']=payload
            raw,elements=self.render(report)
            self.assertEqual(elements['rSummary']['textContent'],'For review only. '+payload)
            self.assertEqual(elements['rSummary']['innerHTML'],'')
            self.assertNotIn(payload,raw)

    def test_standard_reports_keep_their_existing_headings(self):
        for stage,label in [('pre_bid','Pre-Bid Report'),('bid_gap','Bid Risk &amp; Gap Report')]:
            _,elements=self.render({'meta':{'report_type':stage}})
            self.assertEqual(elements['rType']['innerHTML'],label)
            self.assertNotIn('quantityTitle',elements)
            self.assertNotIn('rSummary',elements)

if __name__ == '__main__':
    unittest.main()
