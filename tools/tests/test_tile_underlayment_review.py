import copy
import hashlib
import json
import threading
import unittest
import urllib.error
import urllib.request

import test_company_scope_review as fixtures
from company_scope_review import import_scope
from company_scope_bids import build_scopes
from measurement_store import MeasurementStore
from measurement_estimate import template_draft
from measurement_review import make_server


class UnderlaymentTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.CompanyScopeTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def job(self,overrides=None):
        folder,company,_=self.fixture.job(overrides=overrides)
        raw=json.loads((folder/'measurements.json').read_bytes());base=raw['measurements'][0]
        shapes={'wood':[[0,0],[100,0],[100,100],[0,100]],
                'shower':[[0,0],[40,0],[40,40],[0,40]],
                'slab':[[120,0],[200,0],[200,100],[120,100]]}
        raw['measurements']=[dict(base,id=i,kind='area',points=p) for i,p in shapes.items()]
        (folder/'measurements.json').write_text(json.dumps(raw))
        # Replace only this disposable test fixture's original line-measurement database.
        (folder/'measurement_edits.sqlite3').unlink()
        config={'plan_sha256':raw['plan_sha256'],'groups':[
            {'id':'bath','measurement_ids':['wood'],'deduction_ids':['shower'],
             'substrate':'wood_floor','basis':'Synthetic tile field less shower'},
            {'id':'slab-room','measurement_ids':['slab'],'substrate':'concrete_slab',
             'basis':'Synthetic slab tile field'}]}
        self.write_config(folder,config)
        return folder,company,MeasurementStore(folder)

    def write_config(self,folder,config):
        proof=json.dumps({k:config[k] for k in ('plan_sha256','groups')}).encode()
        (folder/'tile-assignment.json').write_bytes(proof)
        config.update(source_file='tile-assignment.json',source_sha256=hashlib.sha256(proof).hexdigest())
        (folder/'tile_underlayment_review.json').write_text(json.dumps(config))

    def draft(self,folder,company,store):
        state=store.read()
        draft=template_draft(state,self.fixture.rules,self.fixture.template)
        return import_scope(draft,folder,company,state)

    def test_substrate_defaults_net_area_and_no_prices(self):
        folder,company,store=self.job();draft=self.draft(folder,company,store)
        fields=draft['tile_underlayment_review']['fields']
        self.assertEqual([(f['net_sf'],f['underlayment']) for f in fields],
                         [(84,'cement_board'),(80,'none_direct_to_slab')])
        self.assertEqual(fields[0]['board_thickness_inches'],.25)
        self.assertIsNone(fields[1]['board_thickness_inches'])
        self.assertTrue(all(f['purchase_quantity'] is None for f in fields))
        tile=next(s for s in build_scopes(draft)['scopes'] if s['trade']=='Tile')
        item=next(i for i in tile['items'] if i['id']=='tile-floor-underlayment')
        self.assertIn('84.00 SF',item['label']);self.assertIn('80.00 SF',item['label'])
        self.assertFalse(tile['ready_to_order']);self.assertIsNone(draft['whole_house_total'])

    def test_override_does_not_inherit_board_thickness(self):
        folder,company,store=self.job({'tile.floor_underlayment_by_substrate':{
            'wood_floor':'specified_membrane','concrete_slab':'none_direct_to_slab'}})
        field=self.draft(folder,company,store)['tile_underlayment_review']['fields'][0]
        self.assertEqual(field['underlayment'],'specified_membrane')
        self.assertIsNone(field['board_thickness_inches'])

    def test_explicit_partial_deduction_clips_at_floor_boundary(self):
        folder,company,store=self.job()
        config=json.loads((folder/'tile_underlayment_review.json').read_bytes())
        config['groups'][0]['clip_deductions_to_field']=True
        self.write_config(folder,config)
        state=store.read()
        store.save('shower',[[0,0],[110,0],[110,40],[0,40]],state['version'],state['plan_sha256'],'Synthetic overhang')
        field=self.draft(folder,company,store)['tile_underlayment_review']['fields'][0]
        self.assertEqual((field['net_sf'],field['deducted_sf'],field['deduction_outside_field_sf']),(60,40,4))

    def test_bad_geometry_and_unknown_substrate_fail(self):
        folder,company,store=self.job()
        config=json.loads((folder/'tile_underlayment_review.json').read_bytes())
        for kind in ('duplicate','overlap','outside','substrate','whole-deduction'):
            changed=copy.deepcopy(config);group=changed['groups'][0]
            if kind=='duplicate':group['measurement_ids']*=2
            if kind=='overlap':changed['groups'][1]['measurement_ids']=['wood']
            if kind=='outside':group['deduction_ids']=['slab']
            if kind=='substrate':group['substrate']='unknown'
            if kind=='whole-deduction':group['deduction_ids']=['wood']
            self.write_config(folder,changed)
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.draft(folder,company,store)

    def test_assignment_tampering_and_stale_bid_revision_fail(self):
        folder,company,store=self.job();draft=self.draft(folder,company,store)
        draft['measurement_version']+=1
        with self.assertRaises(ValueError):build_scopes(draft)
        path=folder/'tile_underlayment_review.json';config=json.loads(path.read_bytes())
        config['groups'][0]['substrate']='concrete_slab';path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):self.draft(folder,company,store)

    def test_live_export_and_bid_recalculate_after_edit_and_reject_changed_evidence(self):
        folder,company,store=self.job()
        server=make_server(store);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def get(route):
            with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}'+route) as response:return json.load(response)
        try:
            first=get('/api/company-scope-bids')
            exported=get('/api/export-snapshot')
            self.assertEqual(exported['draft']['tile_underlayment_review']['fields'][0]['net_sf'],84)
            state=store.read()
            store.save('wood',[[0,0],[110,0],[110,100],[0,100]],state['version'],state['plan_sha256'],'Synthetic resize')
            second=get('/api/company-scope-bids')
            tile1=next(s for s in first['scopes'] if s['trade']=='Tile')
            tile2=next(s for s in second['scopes'] if s['trade']=='Tile')
            self.assertNotEqual(tile1['scope_sha256'],tile2['scope_sha256'])
            self.assertEqual(get('/api/export-snapshot')['draft']['tile_underlayment_review']['fields'][0]['net_sf'],94)
            path=folder/'tile-assignment.json';path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(urllib.error.HTTPError) as error:get('/api/company-scope-bids')
            self.assertEqual(error.exception.code,400)
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
