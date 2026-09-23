import json
import tempfile
import unittest
from pathlib import Path
import fitz
from quote_intake import intake_quote,extract_document_pages
from quote_table_candidates import extract_tables,numeric
from bid_comparison import compare_quotes


def pdf(rows,headers=('Description','Rate','Qty','Line Total')):
    with fitz.open() as doc:
        page=doc.new_page()
        for x,text in zip((30,280,370,460),headers):page.insert_text((x,80),text)
        for index,row in enumerate(rows):
            for x,text in zip((30,280,370,460),row):
                if text:page.insert_text((x,110+index*25),text)
        page.insert_text((370,220),'Subtotal');page.insert_text((460,220),'$100.00')
        page.insert_text((370,245),'Amount Paid');page.insert_text((460,245),'$50.00')
        page.insert_text((370,270),'Total');page.insert_text((460,270),'100.00')
        return doc.tobytes()


def ruled_pdf(extra_column_text=''):
    with fitz.open() as doc:
        page=doc.new_page()
        for x in (30,380,430,560):page.draw_line((x,50),(x,280))
        for y in (50,100,170,240,280):page.draw_line((30,y),(560,y))
        page.insert_text((35,70),'Description');page.insert_text((435,90),'Total')
        page.insert_text((35,120),'Install windows\nJob A');page.insert_text((435,120),'$1,500.00')
        page.insert_text((35,190),'Repair drywall\nStain countertop\nJob B');page.insert_text((435,190),'$1,500.00')
        if extra_column_text:page.insert_text((385,120),extra_column_text)
        page.insert_text((35,260),'Total');page.insert_text((435,260),'$3,000.00')
        return doc.tobytes()


class QuoteTableCandidates(unittest.TestCase):
    def extract(self,raw):return extract_tables(extract_document_pages(raw,'.pdf'))

    def test_native_columns_provide_numbers_and_source_boxes_without_units(self):
        result=self.extract(pdf([('Drywall work','$1.28','11065.72','$14,164.12')]))
        row=result['pricing_candidates'][0]
        self.assertEqual((row['quantity'],row['unit_rate'],row['amount']),('11065.72','1.28','14164.12'))
        self.assertTrue(row['arithmetic_matches']);self.assertIsNone(row['quantity_unit'])
        self.assertIsNone(row['billing_basis']);self.assertEqual(row['scope_ids'],[])
        self.assertFalse(row['reviewed']);self.assertFalse(result['complete_document_pricing'])
        self.assertEqual(row['cell_sources']['unit_rate']['text'],'$1.28')
        self.assertEqual(len(row['cell_sources']['quantity']['bbox']),4)
        self.assertEqual([v['label'] for v in result['labeled_amount_candidates']],['subtotal','amount paid','total'])
        self.assertFalse(result['labeled_amount_candidates'][-1]['currency_confirmed'])

    def test_ruled_cells_preserve_wrapped_job_descriptions_without_invented_rates(self):
        result=self.extract(ruled_pdf())
        self.assertEqual(len(result['pricing_candidates']),2)
        first,second=result['pricing_candidates']
        self.assertIn('Job A',first['description']);self.assertIn('Job B',second['description'])
        self.assertIn('Stain countertop',second['description'])
        for row in (first,second):
            self.assertEqual(row['amount'],'1500.00');self.assertIsNone(row['quantity'])
            self.assertIsNone(row['unit_rate']);self.assertIsNone(row['arithmetic_matches'])
            self.assertEqual(row['extraction_method'],'ruled_pdf_cells')
            self.assertFalse(row['reviewed']);self.assertEqual(row['scope_ids'],[])
        self.assertEqual(len(result['labeled_amount_candidates']),1)
        self.assertEqual(result['labeled_amount_candidates'][0]['value'],'3000.00')
        self.assertEqual(result['unparsed_table_rows'],[])

    def test_unheaded_column_content_prevents_silently_omitting_scope(self):
        result=self.extract(ruled_pdf('Extra'))
        self.assertEqual(len(result['pricing_candidates']),1)
        self.assertEqual(len(result['unparsed_table_rows']),1)
        self.assertIn('Nonempty table column',result['unparsed_table_rows'][0]['reason'])

    def test_ruled_quantity_table_is_not_reinterpreted_as_lump_sum_when_incomplete(self):
        with fitz.open(stream=pdf([('Work','$10.00','','$100.00')]),filetype='pdf') as doc:
            page=doc[0]
            for x in (20,240,340,430,580):page.draw_line((x,60),(x,150))
            for y in (60,95,150):page.draw_line((20,y),(580,y))
            raw=doc.tobytes()
        result=self.extract(raw)
        self.assertEqual(result['pricing_candidates'],[])
        self.assertEqual(len(result['unparsed_table_rows']),1)

    def test_reordered_headers_and_signed_credit_remain_explicit(self):
        result=self.extract(pdf([('Returned material','2','$5.00','($10.00)')],
            headers=('Item','Quantity','Unit Price','Amount')))
        row=result['pricing_candidates'][0]
        self.assertEqual(row['quantity'],'2');self.assertEqual(row['unit_rate'],'5.00')
        self.assertEqual(row['amount'],'-10.00');self.assertFalse(row['arithmetic_matches'])

    def test_missing_or_malformed_cells_are_visible_not_inferred(self):
        result=self.extract(pdf([('Work','$10.00','','$100.00'),('Other','$2.00','1,00','$200.00')]))
        self.assertEqual(result['pricing_candidates'],[])
        self.assertEqual(len(result['unparsed_table_rows']),2)
        result=self.extract(pdf([('Other','$2.00','10','$21.00')]))
        self.assertFalse(result['pricing_candidates'][0]['arithmetic_matches'])

    def test_unknown_headers_and_non_pdf_text_do_not_guess_tables(self):
        result=self.extract(pdf([('Work','$10.00','10','$100.00')],headers=('Description','Cost','Count','Value')))
        self.assertEqual(result['table_headers'],[]);self.assertEqual(result['pricing_candidates'],[])
        self.assertEqual(extract_tables([{'page':1,'text':'Qty Rate Amount 10 2 20'}])['pricing_candidates'],[])
        for text in ('1,00','NaN','Infinity','1/2','12 SF','--1','$1$0','(-10)'):
            self.assertIsNone(numeric(text))

    def test_multiple_pages_and_repeated_headers_keep_provenance(self):
        raw=pdf([('Work','$10.00','10','$100.00')])
        with fitz.open(stream=raw,filetype='pdf') as source,fitz.open() as doc:
            doc.insert_pdf(source);doc.insert_pdf(source);raw=doc.tobytes()
        result=self.extract(raw)
        self.assertEqual([v['page'] for v in result['pricing_candidates']],[1,2])
        self.assertEqual(len(result['table_headers']),2)

    def test_intake_keeps_candidates_out_of_approved_pricing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'invoice.pdf';source.write_bytes(pdf([('Work','$10.00','10','$100.00')]))
            scope={'plan_sha256':'plan','measurement_version':1,'items':[{'id':'work','label':'Work'}]}
            out=root/'intake';summary=intake_quote(source,out,scope,'fixture')
            self.assertEqual(summary['pricing_candidate_count'],1)
            candidates=json.loads((out/'pricing_candidates.json').read_text())
            self.assertEqual(candidates['source_sha256'],summary['source_sha256'])
            quotes=json.loads((out/'quotes.json').read_text())
            self.assertNotIn('pricing_lines',quotes[0]);self.assertIsNone(quotes[0]['total'])
            result=compare_quotes(scope,quotes,'2026-09-19',out)['quotes'][0]
            self.assertFalse(result['same_scope_current_quote']);self.assertFalse(result['purchase_authorized'])
            self.assertEqual(result['scope_matrix'][0]['status'],'unknown')


if __name__=='__main__':unittest.main()
