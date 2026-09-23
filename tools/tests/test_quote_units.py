import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from quote_intake import extract_document_pages
from quote_table_candidates import extract_tables,explicit_unit
from bid_pricing_findings import pricing_findings
from test_bfs_invoice import fixture


def unit_pdf(unit,ruled=False):
    with fitz.open() as doc:
        page=doc.new_page()
        if ruled:
            for x in (20,250,320,390,470,585):page.draw_line((x,60),(x,140))
            for y in (60,95,140):page.draw_line((20,y),(585,y))
        for x,text in zip((30,270,335,400,500),('Description','Qty','U/M','Rate','Amount')):page.insert_text((x,80),text)
        for x,text in zip((30,270,335,400,500),('Materials','2',unit,'$10.00','$20.00')):
            if text:page.insert_text((x,115),text)
        return doc.tobytes()


class QuoteUnits(unittest.TestCase):
    def test_unit_columns_in_ruled_and_unruled_tables_preserve_source(self):
        for ruled in (False,True):
            for unit,canonical in [('EA','each'),('LF','linear_ft'),('SF','sq_ft')]:
                with self.subTest(unit=unit,ruled=ruled):
                    extraction=extract_tables(extract_document_pages(unit_pdf(unit,ruled),'.pdf'))
                    self.assertEqual(len(extraction['pricing_candidates']),1)
                    row=extraction['pricing_candidates'][0]
                    self.assertEqual(row['quantity_unit'],canonical);self.assertEqual(row['quantity_unit_as_printed'],unit)
                    self.assertEqual(row['cell_sources']['quantity_unit']['text'],unit)
                    self.assertTrue(row['arithmetic_matches']);self.assertFalse(row['reviewed'])
                    questions=pricing_findings(extraction,'evidence:test','fixture.pdf')
                    self.assertEqual(len(questions),1 if unit=='SF' else 0)
                    if unit=='SF':self.assertIsNone(row['billing_basis'])

    def test_unknown_or_blank_units_are_not_guessed(self):
        for unit in ('SQ','BOM',''):
            extraction=extract_tables(extract_document_pages(unit_pdf(unit),'.pdf'))
            row=extraction['pricing_candidates'][0]
            self.assertIsNone(row['quantity_unit']);self.assertIsNone(row['billing_basis'])
            self.assertEqual(len(pricing_findings(extraction,'evidence:test','fixture.pdf')),1)
        self.assertEqual(explicit_unit('Square Feet')['quantity_unit'],'sq_ft')
        self.assertIsNone(explicit_unit('Square Feet')['billing_basis'])

    def test_bfs_shipped_quantity_is_distinct_from_order_and_sku(self):
        extraction=extract_tables([{'page':1,'width':612,'words':fixture(ordered='25',shipped='12',unit='EA',price='2.00',extension='24.00')}])
        row=extraction['pricing_candidates'][0]
        self.assertEqual(row['quantity'],'12');self.assertEqual(row['ordered_quantity'],25)
        self.assertEqual(row['quantity_role'],'shipped');self.assertEqual(row['sku'],'1460340000')
        self.assertEqual(row['quantity_unit'],'each');self.assertEqual(row['amount'],'24.00')
        self.assertEqual(row['cell_sources']['quantity']['text'],'12')
        self.assertEqual(row['cell_sources']['sku']['text'],'1460340000')
        self.assertEqual(row['scope_ids'],[]);self.assertFalse(row['reviewed'])

    def test_zero_shipment_and_package_component_unit_remain_explicit(self):
        extraction=extract_tables([{'page':1,'width':612,'words':fixture(ordered='12',shipped='0')}])
        row=extraction['pricing_candidates'][0]
        self.assertEqual(row['quantity'],'0');self.assertEqual(row['ordered_quantity'],12)
        self.assertEqual(row['quantity_unit_as_printed'],'BOM');self.assertIsNone(row['quantity_unit'])
        self.assertNotIn('included_in',row)

    def test_unsupported_bfs_form_or_mismatch_is_visible_and_not_partially_priced(self):
        for width,words in [(700,fixture()),(612,fixture(price='2.00',extension='22.00')),
                            (612,fixture(shipped=''))]:
            result=extract_tables([{'page':1,'width':width,'words':words}])
            self.assertEqual(result['pricing_candidates'],[])
            self.assertEqual(len(result['unparsed_table_rows']),1)
            self.assertEqual(pricing_findings(result,'evidence:test','bfs.pdf')[0]['category'],'pricing_extraction_incomplete')


if __name__=='__main__':unittest.main()
