import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jnj_takeoff import ingest_bid, ingest_bid_xlsx, findings_from_bid, report_from_takeoff

SCOPE={'title':'Gutters & downspouts','question':'Are gutters and downspouts included?',
       'detect':'dollar','scope_keys':['gutter','downspout'],'expected':(3000,5000)}

class BidScopeTests(unittest.TestCase):
    def review(self,lines):
        return findings_from_bid(ingest_bid(lines),{},[SCOPE])

    def test_keyword_absence_is_not_an_omission_or_price(self):
        result=self.review([{'desc':'Complete exterior package','amount':25000}])[0]
        self.assertEqual(result['category'],'scope_confirmation')
        self.assertIsNone(result['bid_amount'])
        self.assertIsNone(result['realistic_low'])
        self.assertIn('does not prove',result['basis'])

    def test_zero_bundled_line_with_specific_source_is_included(self):
        self.assertEqual(self.review([{'desc':'Gutters included in roofing','amount':0,
            'scope_status':'included','source_ref':'proposal p2 item6',
            'confirmed_scopes':[SCOPE['title']]}]),[])

    def test_partial_or_unsourced_confirmation_does_not_close_scope(self):
        for extra in ({'source_ref':'p2'},{'confirmed_scopes':[SCOPE['title']]}):
            self.assertEqual(len(self.review([{'desc':'Gutters','amount':0,'scope_status':'included',**extra}])),1)

    def test_exclusion_and_conflicting_evidence_remain_unpriced(self):
        line={'desc':'Gutters excluded','amount':None,'scope_status':'excluded',
              'source_ref':'p2','confirmed_scopes':[SCOPE['title']]}
        self.assertEqual(self.review([line])[0]['category'],'excluded_scope')
        included={**line,'desc':'Gutters included','scope_status':'included','source_ref':'p3'}
        result=self.review([line,included])[0]
        self.assertEqual(result['category'],'scope_confirmation')
        self.assertEqual(len(result['evidence_lines']),2)
        self.assertIsNone(result['realistic_high'])

    def test_unknown_amount_is_not_zero_total(self):
        bid=ingest_bid([{'desc':'Gutters','amount':None}])
        self.assertIsNone(bid['total']);self.assertIsNone(bid['lines'][0]['amount'])
        report=report_from_takeoff({'lines':[]},{},{},bid=bid)
        self.assertEqual(report['meta']['report_type'],'bid_gap')
        self.assertIsNone(report['meta']['bid_total'])

    def test_optional_technology_is_not_assumed(self):
        bid=ingest_bid([],total=500000)
        unknown=next(r for r in findings_from_bid(bid,{}) if 'Home technology' in r['title'])
        self.assertEqual(unknown['scope_status'],'selection_unconfirmed')
        self.assertIn('no cost or requirement is assumed',unknown['basis'])
        self.assertFalse(any('Home technology' in r['title'] for r in findings_from_bid(bid,{'home_technology':False})))
        enabled=findings_from_bid(bid,{'home_technology':True})
        self.assertTrue(any('Home technology' in r['title'] for r in enabled))
        self.assertTrue(all(r['realistic_low'] is None for r in enabled))

    def test_blank_and_zero_xlsx_lines_are_preserved(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'bid.xlsx';wb=openpyxl.Workbook();ws=wb.active
            ws.append(['Scope','Amount']);ws.append(['Gutters bundled',0]);ws.append(['Drainage TBD',None])
            wb.save(path);bid=ingest_bid_xlsx(path)
        self.assertEqual(len(bid['lines']),2);self.assertIsNone(bid['total'])
        self.assertEqual(bid['lines'][0]['amount'],0)

    def test_empty_checklist_is_respected(self):
        self.assertEqual(findings_from_bid(ingest_bid([],total=100),{},[]),[])

if __name__=='__main__':unittest.main()
