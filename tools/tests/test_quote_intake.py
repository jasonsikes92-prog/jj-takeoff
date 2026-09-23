import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quote_intake import intake_quote,total_candidates
from bid_comparison import compare_quotes


class QuoteIntake(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.scope={'plan_sha256':'drawing','measurement_version':1,
                    'items':[{'id':'install','label':'Installation'},{'id':'tax','label':'Tax'}]}
        self.source=self.root/'received.pdf';self.out=self.root/'intake'
        with fitz.open() as doc:
            p=doc.new_page();p.insert_text((30,30),'Installation included. Tax excluded. Total $1,000.')
            doc.new_page();doc.save(self.source)

    def test_original_pages_and_unknowns_survive_comparison(self):
        result=intake_quote(self.source,self.out,self.scope,'Q1')
        self.assertEqual((self.out/'source.pdf').read_bytes(),self.source.read_bytes())
        self.assertEqual(result['pages_needing_visual_or_ocr_review'],[2])
        pages=json.loads((self.out/'source_pages.json').read_text())
        self.assertIn('Tax excluded',pages['pages'][0]['text'])
        quotes=json.loads((self.out/'quotes.json').read_text())
        compared=compare_quotes(self.scope,quotes,'2026-09-16',self.out)['quotes'][0]
        self.assertIsNone(compared['quoted_total'])
        self.assertFalse(compared['same_scope_current_quote'])
        self.assertEqual([i['status'] for i in compared['scope_matrix']],['unknown','unknown'])
        self.assertIn('Quote issue date is unconfirmed',compared['comparison_issues'])
        self.assertIn('Supplier identity is unconfirmed',compared['comparison_issues'])
        with self.assertRaises(FileExistsError):intake_quote(self.source,self.out,self.scope,'Q1')

    def test_changed_source_is_rejected_after_intake(self):
        intake_quote(self.source,self.out,self.scope,'Q1','Example supplier')
        quotes=json.loads((self.out/'quotes.json').read_text())
        (self.out/'source.pdf').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'evidence changed'):
            compare_quotes(self.scope,quotes,'2026-09-16',self.out)

    def test_invalid_document_and_scope_do_not_create_intake(self):
        self.source.write_bytes(b'not a pdf')
        with self.assertRaises(Exception):intake_quote(self.source,self.out,self.scope,'Q1')
        self.assertFalse(self.out.exists())
        self.source=self.root/'quote.txt';self.source.write_text('Fixture quote',encoding='utf-8')
        self.scope['items'].append(self.scope['items'][0])
        with self.assertRaises(ValueError):intake_quote(self.source,self.out,self.scope,'Q1')
        self.assertFalse(self.out.exists())

    def test_utf8_text_with_bom_is_preserved(self):
        source=self.root/'quote.txt';raw=b'\xef\xbb\xbfUnreviewed exclusions';source.write_bytes(raw)
        intake_quote(source,self.out,self.scope,'Q1')
        self.assertEqual((self.out/'source.txt').read_bytes(),raw)
        pages=json.loads((self.out/'source_pages.json').read_text())
        self.assertEqual(pages['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(pages['pages'][0]['text'],'Unreviewed exclusions')

    def test_total_candidates_keep_conflicts_and_exclude_subtotals(self):
        pages=[{'page':1,'text':'Subtotal: $900.00\nTotal Price: $1,000.00\nDeposit: $500.00'},
               {'page':2,'text':'Grand Total\n$1,100.00\nTotal: $12,34.00'}]
        found=total_candidates(pages)
        self.assertEqual([v['value'] for v in found],['1000.00','1100.00'])
        self.assertEqual([v['page'] for v in found],[1,2])
        self.assertEqual(found[0]['line'],2)
        self.assertTrue(all(not v['reviewed'] and not v['currency_confirmed'] for v in found))

if __name__=='__main__':unittest.main()
