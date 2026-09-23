import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from text_symbol_candidates import symbol_candidates, plan_symbol_candidates


class Symbols(unittest.TestCase):
    def page(self):
        doc=fitz.open();self.addCleanup(doc.close);page=doc.new_page()
        for x,y,t in [(30,30,'R'),(60,60,'R'),(300,300,'R'),(100,100,'ROOM'),(30,30,'R')]:
            page.insert_text((x,y),t)
        return page

    def test_exact_labels_and_duplicate_layer_excluded_from_count(self):
        r=symbol_candidates(self.page(),{'R':{'label':'Recessed light','meaning_source':'Fixture legend'}},
            [{'bbox_pt':[280,280,350,330],'source':'Schedule symbol sample'}])
        self.assertEqual(len(r['measurements'][0]['points']),2)
        self.assertEqual(len(r['excluded_labels']['R']),1)
        self.assertTrue(r['measurements'][0]['engine_line_ids']);self.assertFalse(r['certified'])

    def test_missing_labels_do_not_invent_zero_scope(self):
        r=symbol_candidates(self.page(),{'WP':{'label':'Weatherproof outlet','meaning_source':'Legend'}},[])
        self.assertEqual(r['measurements'],[]);self.assertEqual(r['missing_symbol_tokens'],['WP'])

    def test_symbol_meanings_and_exclusion_provenance_required(self):
        with self.assertRaises(ValueError):symbol_candidates(self.page(),{'R':{'label':'light'}},[])
        with self.assertRaises(ValueError):symbol_candidates(self.page(),{'R':{'label':'light','meaning_source':'legend'}},[{'bbox_pt':[1,1,0,0],'source':'legend'}])

    def test_plan_extraction_rejects_missing_duplicate_and_outside_pages(self):
        page=self.page();doc=page.parent
        definition={'page':1,'symbols':{'R':{'label':'light','meaning_source':'legend'}},'exclusions':[]}
        for pages in ([],[definition,definition],[{**definition,'page':2}],[{**definition,'page':True}]):
            with self.assertRaises(ValueError):
                plan_symbol_candidates(doc,{'plan_sha256':'drawing','pages':pages},'drawing')


if __name__=='__main__':unittest.main()
