"""State, arithmetic, revision and HTTP checks for the bounded slab editor."""
import json
import math
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from contextlib import closing

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from slab_review import ReviewStore, Conflict, calculate, digest, historical_formula, make_server, trade_draft, validate_polygon


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        (self.folder/'plan.pdf').write_bytes(b'test-drawing-identity')
        (self.folder/'sheet-4.png').write_bytes(b'test-drawing-render')
        self.config={'width_pt':2000,'height_pt':2000,'page':3,'plan_name':'Test precon',
            'plan_sha256':digest(self.folder/'plan.pdf'),
            'asset_hashes':{'sheet-4.png':digest(self.folder/'sheet-4.png')},
            'scale':{'ppf':10},'waste_percent':10,
            'initial_points':[[100,100],[300,100],[300,200],[100,200]],
            'comparison_outer_points':[[90,90],[310,90],[310,210],[90,210]],
            'assembly':{'lines':[{'estimate_item_id':'concrete','name':'Concrete','unit':'CY','formula':'round({QTY}*0.015)'}]},
            'required_information':['Confirm boundary and specifications']}
        (self.folder/'review_config.json').write_text(json.dumps(self.config))
        self.store=ReviewStore(self.folder)

    def tearDown(self): self.tmp.cleanup()

    def payload(self,points=None,version=1):
        return {'base_version':version,'plan_sha256':self.config['plan_sha256'],
                'points':points or [[100,100],[400,100],[400,200],[100,200]],'note':'Extend slab'}

    def test_independent_rectangle_arithmetic(self):
        r=self.store.read()['results']
        self.assertEqual(r['net_sf'],200)
        self.assertEqual(r['perimeter_lf'],60)
        self.assertAlmostEqual(r['order_sf'],220)
        self.assertEqual(r['historical_assembly_quantity'],220)
        self.assertFalse(r['verification_valid'])
        self.assertIsNone(r['current_total'])
        self.assertIsNone(r['concrete_volume_cy'])

    def test_concave_polygon(self):
        # 20x20 square minus 10x10 notch; an independent area of 300 SF.
        p=[[100,100],[300,100],[300,200],[200,200],[200,300],[100,300]]
        self.assertEqual(calculate(self.config,p)['net_sf'],300)

    def test_reversed_winding(self):
        a=calculate(self.config,self.config['initial_points'])
        b=calculate(self.config,list(reversed(self.config['initial_points'])))
        self.assertEqual(a,b)

    def test_save_reload_and_prior_version(self):
        before=self.store.read()
        saved=self.store.save(self.payload())
        self.assertEqual(saved['version'],2)
        self.assertEqual(saved['results']['net_sf'],300)
        self.assertAlmostEqual(saved['results']['order_sf'],330)
        reopened=ReviewStore(self.folder)
        self.assertEqual(reopened.read(),saved)
        self.assertEqual(reopened.read(1),before)
        self.assertEqual(len(reopened.history()),2)
        text=trade_draft(self.config,saved)
        self.assertIn('300.00 SF',text)
        self.assertIn('Measurement version: 2',text)

    def test_coordinate_precision(self):
        p=[[100.123456789,100],[300.987654321,100],[300.987654321,200],[100.123456789,200]]
        self.store.save(self.payload(p))
        loaded=ReviewStore(self.folder).read()['points']
        self.assertEqual(p,loaded)

    def test_switching_saved_measurements_keeps_each_boundary(self):
        red = self.store.read()
        original_blue = json.loads(json.dumps(self.config['comparison_outer_points']))
        state = self.store.state()
        self.assertEqual(state['measurements']['red'], red)
        self.assertEqual(state['measurements']['blue']['version'], 0)
        blue_points = [[90,90],[320,90],[320,210],[90,210]]
        blue = self.store.save(dict(self.payload(blue_points), outline='blue'))
        red2 = self.store.save(dict(self.payload(version=2), outline='red'))
        reopened = ReviewStore(self.folder).state()
        self.assertEqual(reopened['measurements']['blue'], blue)
        self.assertEqual(reopened['measurements']['red'], red2)
        self.assertEqual(self.store.read(1), red)
        self.assertEqual(self.config['comparison_outer_points'], original_blue)
        self.assertIn('Measurement: blue outline', trade_draft(self.config, blue))
        self.assertFalse(blue['results']['verification_valid'])

    def test_legacy_versions_remain_readable_without_rewriting(self):
        legacy = self.store.read()
        legacy.pop('outline')
        raw = json.dumps(legacy)
        with closing(sqlite3.connect(self.store.database)) as db, db:
            db.execute('UPDATE versions SET snapshot=? WHERE version=1', (raw,))
        self.assertEqual(self.store.state()['measurements']['red']['points'], legacy['points'])
        with closing(sqlite3.connect(self.store.database)) as db:
            self.assertEqual(db.execute('SELECT snapshot FROM versions WHERE version=1').fetchone()[0], raw)

    def test_unknown_measurement_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save(dict(self.payload(), outline='unknown'))
        self.assertEqual(len(self.store.history()), 1)

    def test_restore_creates_version(self):
        original=self.store.read()
        self.store.save(self.payload())
        restored=self.store.save(self.payload(original['points'],2))
        self.assertEqual(restored['version'],3)
        self.assertEqual(restored['points'],original['points'])
        self.assertEqual(self.store.read(2)['results']['net_sf'],300)

    def test_stale_save_rejected(self):
        self.store.save(self.payload())
        with self.assertRaises(Conflict):self.store.save(self.payload())
        self.assertEqual(len(self.store.history()),2)

    def test_concurrent_writers_only_one_wins(self):
        second=ReviewStore(self.folder)
        barrier=threading.Barrier(2); outcomes=[]
        def save(store):
            barrier.wait()
            try:store.save(self.payload());outcomes.append('saved')
            except Conflict:outcomes.append('conflict')
        ts=[threading.Thread(target=save,args=(s,)) for s in [self.store,second]]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertCountEqual(outcomes,['saved','conflict'])

    def test_wrong_drawing_payload_rejected(self):
        p=self.payload();p['plan_sha256']='0'*64
        with self.assertRaises(Conflict):self.store.save(p)

    def test_plan_file_tamper(self):
        (self.folder/'plan.pdf').write_bytes(b'changed-drawing')
        with self.assertRaises(Conflict):self.store.read()

    def test_displayed_image_tamper(self):
        (self.folder/'sheet-4.png').write_bytes(b'changed-render')
        with self.assertRaises(Conflict):self.store.read()

    def test_changed_config_cannot_reuse_saved_measurement(self):
        self.config['scale']['ppf']=20
        (self.folder/'review_config.json').write_text(json.dumps(self.config))
        with self.assertRaises(Conflict):ReviewStore(self.folder)

    def test_corrupt_saved_result_refused(self):
        value=self.store.read();value['results']['net_sf']=999
        with closing(sqlite3.connect(self.store.database)) as db, db:
            db.execute('UPDATE versions SET snapshot=? WHERE version=1',(json.dumps(value),))
        with self.assertRaises(Conflict):self.store.read()

    def test_invalid_boundaries(self):
        cases=[[],[[1,1],[2,2],[3,3]],[[1,1],[5,5],[1,5],[5,1]],
               [[1,1],[5,1],[5,5],[1,1]],[[1,1],[5,1],[math.nan,5]],
               [[-1,1],[5,1],[5,5]],[[1,1],[5,1],[2001,5]],
               [[1,1],[True,4],[5,5]],[[1,1],[5,1],[3,1],[3,4]]]
        for p in cases:
            with self.subTest(p=p), self.assertRaises(ValueError):validate_polygon(p,2000,2000)

    def test_client_cannot_certify_or_supply_amount(self):
        for key in ['results','status','current_total']:
            p=self.payload();p[key]='certified'
            with self.assertRaises(ValueError):self.store.save(p)

    def test_formula_replay_and_code_rejection(self):
        self.assertEqual(historical_formula('round({QTY}*0.015)',1018),16)
        self.assertEqual(historical_formula('round({QTY}/2000)',1018),1)
        self.assertEqual(historical_formula('{QTY}*0.6',1018),__import__('decimal').Decimal('610.8'))
        for f in ['__import__("os").system("echo bad")','quantity.__class__','round(1,2)','quantity**100','1/0']:
            with self.subTest(f=f), self.assertRaises((ValueError,ArithmeticError)):historical_formula(f,10)

    def test_http_save_read_draft_and_origin(self):
        server=make_server(self.store,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        def post(path,payload,origin=url):
            req=urllib.request.Request(url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':origin})
            return urllib.request.urlopen(req)
        try:
            with urllib.request.urlopen(url+'/api/state') as r:self.assertEqual(json.load(r)['measurements']['red']['version'],1)
            with post('/api/save',dict(self.payload(), outline='blue')) as r:self.assertEqual(json.load(r)['version'],2)
            with urllib.request.urlopen(url+'/api/state') as r:
                measurements = json.load(r)['measurements']
                self.assertEqual(measurements['red']['version'],1)
                self.assertEqual(measurements['blue']['version'],2)
            with urllib.request.urlopen(url+'/draft/2.md') as r:self.assertIn(b'300.00 SF',r.read())
            with self.assertRaises(urllib.error.HTTPError) as denied:post('/api/save',self.payload(version=2),'https://example.com')
            self.assertEqual(denied.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):post('/api/preview',{'points':[[0,0]]})
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main(verbosity=2)
