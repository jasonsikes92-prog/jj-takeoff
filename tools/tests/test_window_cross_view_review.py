import hashlib
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
import fitz
from window_cross_view_review import sources_from_sheet_review,from_plan,from_folder


class WindowCrossViewReview(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name);self.plan=self.folder/'plan.pdf'
        with fitz.open() as doc:
            doc.new_page().insert_text((50,50),'3062SH')
            doc.new_page().insert_text((50,50),'3050FX')
            doc.save(self.plan)
        self.review={'measurement_allowed':True,'measurement_scope':'reviewed_set',
            'plan_sha256':hashlib.sha256(self.plan.read_bytes()).hexdigest(),
            'review_sha256':'synthetic-test-review','role_candidates':{'floor':[1],'elevations':[2]}}

    def test_full_review_yields_unpriced_candidate(self):
        sources=sources_from_sheet_review(self.review)
        (self.folder/'window_cross_view_sources.json').write_text(json.dumps(sources))
        result=from_folder(self.folder)
        self.assertEqual([r['tag'] for r in result['unrepresented_elevation_tags']],['3050FX'])
        self.assertFalse(result['certified']);self.assertIsNone(result['whole_building_count'])

    def test_subset_never_implicitly_adds_elevations(self):
        self.review.update(measurement_scope='reviewed_subset',measurement_role_pages={'floor':1})
        self.assertIsNone(sources_from_sheet_review(self.review))
        self.review['measurement_role_pages']['elevations']=2
        self.assertEqual(sources_from_sheet_review(self.review)['elevation_pages'],[2])

    def test_blocked_review_and_missing_config_produce_no_candidates(self):
        self.review['measurement_allowed']=False
        self.assertIsNone(sources_from_sheet_review(self.review))
        self.assertIsNone(from_folder(self.folder))

    def test_changed_plan_and_invalid_pages_are_rejected(self):
        sources=sources_from_sheet_review(self.review)
        for pages in ([1],[3],[True],[{}],[]):
            with self.subTest(pages=pages),self.assertRaises(ValueError):
                from_plan(self.plan,{**sources,'elevation_pages':pages})
        with self.assertRaisesRegex(ValueError,'another drawing'):
            from_plan(self.plan,{**sources,'plan_sha256':'wrong'})

    def test_http_returns_candidates_and_rejects_changed_source_config(self):
        from measurement_store import MeasurementStore
        from measurement_review import make_server
        sources=sources_from_sheet_review(self.review)
        path=self.folder/'window_cross_view_sources.json'
        path.write_text(json.dumps(sources))
        measurement={'id':'wall','page':1,'kind':'length','width_pt':595,'height_pt':842,
            'points_per_foot':10,'points':[[0,0],[100,0]],'dependent_rows':[],
            'color':'#d97706','label':'Synthetic wall'}
        (self.folder/'measurements.json').write_text(json.dumps({
            'plan_sha256':sources['plan_sha256'],'measurements':[measurement]}))
        server=make_server(MeasurementStore(self.folder))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/api/window-cross-view'
        try:
            with urllib.request.urlopen(url) as response:result=json.load(response)
            self.assertEqual(result['unrepresented_elevation_tags'][0]['tag'],'3050FX')
            self.assertFalse(result['certified'])
            path.write_text(json.dumps({**sources,'plan_sha256':'changed'}))
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
            self.assertEqual(error.exception.code,400)
            path.unlink()
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
            self.assertEqual(error.exception.code,404)
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
