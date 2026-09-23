import copy
import hashlib
import json
import threading
import unittest
import urllib.error
import urllib.request
import test_tile_underlayment_review as fields_fixture
import test_floor_sundries as products_fixture
from measurement_review import make_server


class FloorSupplyPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fields_fixture.UnderlaymentTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.folder,self.company,self.store=self.fixture.job()
        self.proof={'plan_sha256':self.store.read()['plan_sha256'],'field_ids':['bath'],
                    'products':products_fixture.FloorSundriesTests().products()}
        self.proof['products']['board']['thickness_inches']=.25
        self.config={'plan_sha256':self.proof['plan_sha256'],'pools':[{'id':'bath-supplies','field_ids':['bath'],
                     'source_file':'products.json'}]}
        self.write()

    def write(self):
        raw=json.dumps(self.proof).encode();(self.folder/'products.json').write_bytes(raw)
        self.config['pools'][0]['source_sha256']=hashlib.sha256(raw).hexdigest()
        (self.folder/'floor_supply_purchase_review.json').write_text(json.dumps(self.config))

    def draft(self):return self.fixture.draft(self.folder,self.company,self.store)

    def test_current_geometry_drives_supply_pool_without_charging_estimate(self):
        draft=self.draft();review=draft['floor_supply_purchase_review'];pool=review['pools'][0]
        self.assertEqual(pool['calculation']['installed_area_sf'],84)
        self.assertTrue(pool['product_thickness_verified'])
        self.assertEqual(review['unassigned_field_ids'],['slab-room'])
        self.assertFalse(review['included_in_estimate_total']);self.assertFalse(review['ready_to_order'])
        self.assertTrue(all(r.get('line_cost') is None for r in draft['rows']))

    def test_wrong_thickness_nonboard_and_duplicate_assignments_rejected(self):
        original=copy.deepcopy(self.proof);config=copy.deepcopy(self.config)
        for kind in ('thickness','slab','duplicate','missing'):
            self.proof=copy.deepcopy(original);self.config=copy.deepcopy(config)
            if kind=='thickness':self.proof['products']['board']['thickness_inches']=.5
            if kind=='slab':self.proof['field_ids']=self.config['pools'][0]['field_ids']=['slab-room']
            if kind=='duplicate':self.config['pools'].append(dict(self.config['pools'][0],id='duplicate'))
            if kind=='missing':self.proof['field_ids']=self.config['pools'][0]['field_ids']=['missing']
            self.write()
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.draft()

    def test_live_boundary_edit_changes_bag_count_and_changed_source_fails(self):
        server=make_server(self.store);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def get():
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/export-snapshot') as response:return json.load(response)
        def count(snapshot):
            c=snapshot['draft']['floor_supply_purchase_review']['pools'][0]['calculation']
            return next(r['quantity'] for r in c['components'] if r['component']=='bedding')
        try:
            before=get();self.assertEqual(count(before),1)
            state=self.store.read()
            self.store.save('wood',[[0,0],[110,0],[110,100],[0,100]],state['version'],state['plan_sha256'],'Synthetic enlargement')
            after=get();self.assertEqual(count(after),2)
            self.assertNotEqual(before['snapshot_sha256'],after['snapshot_sha256'])
            path=self.folder/'products.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(urllib.error.HTTPError) as error:get()
            self.assertEqual(error.exception.code,400)
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
