import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from flooring_selection_review import read_selections
from flooring_bid_scope import build_scope,render_markdown
from room_use_review import binding
from export_opening_bid import source_files


class FlooringSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.region={'id':'bath','page':1,'points_per_foot':10,'points':[[0,0],[100,0],[100,100],[0,100]],
                     'holes':[],'printed_labels':[{'text':'BATH'}]}
        self.rooms={'plan_sha256':'plan','measurement_version':1,'source_sha256':'source','regions':[self.region]}
        self.document={'projectId':2,'capturedAt':'2026-09-09','response':{'data':{'selections':{'data':[
            {'id':3,'projectId':2,'name':'Flooring tile','optionSetting':'SINGLE','items':[
                {'id':4,'name':'Selected tile','status':'SELECTED','quantity':900,'costValue':999,'sku':'TILE'},
                {'id':5,'name':'Unselected tile','status':'PENDING','quantity':900,'costValue':1}]}]}}}}
        self.config={'plan_sha256':'plan','project_id':2,'decisions':[{'region_id':'bath',
            'region_sha256':binding('plan',self.region),'source_file':'evidence/selection.json','selection_id':3,'item_id':4}]}
        (self.root/'evidence').mkdir();self.write()

    def write(self):
        raw=json.dumps(self.document).encode();(self.root/'evidence/selection.json').write_bytes(raw)
        self.config['decisions'][0]['source_sha256']=hashlib.sha256(raw).hexdigest()
        (self.root/'flooring_selection_review.json').write_text(json.dumps(self.config))

    def test_selected_product_reaches_bid_without_historical_price_or_quantity(self):
        review=read_selections(self.root,self.rooms);scope=build_scope(self.rooms,selection_review=review)
        item=scope['items'][0]
        self.assertEqual(item['finish_selection']['product'],'Selected tile')
        self.assertEqual(item['reference_quantity'],100);self.assertIsNone(item['unit_price'])
        self.assertIsNone(item['purchase_quantity']);self.assertEqual(scope['unresolved_finish_region_ids'],[])
        self.assertNotIn('costValue',json.dumps(scope));self.assertNotIn('900',json.dumps(scope))
        self.assertIn('Selected tile (saved selection 2026-09-09)',render_markdown(scope))
        self.assertFalse(item['finish_scope_confirmed']);self.assertFalse(scope['ready_to_order'])

    def test_pending_and_multiple_single_options_remain_unresolved(self):
        for kind in ('pending','multiple'):
            records=self.document['response']['data']['selections']['data'][0]['items']
            records[0]['status']='PENDING' if kind=='pending' else 'SELECTED'
            records[1]['status']='SELECTED' if kind=='multiple' else 'PENDING';self.write()
            review=read_selections(self.root,self.rooms)
            self.assertEqual(review['selections'],{});self.assertEqual(len(review['unresolved']),1)

    def test_geometry_changes_withhold_selection_and_change_bid(self):
        first=build_scope(self.rooms,selection_review=read_selections(self.root,self.rooms))
        self.region['points'][1][0]=110
        review=read_selections(self.root,self.rooms)
        self.assertEqual(review['selections'],{})
        second=build_scope(self.rooms,selection_review=review)
        self.assertNotEqual(first['scope_sha256'],second['scope_sha256'])
        self.assertEqual(second['unresolved_finish_region_ids'],['bath'])

    def test_cross_project_hash_tampering_and_duplicate_links_rejected(self):
        original=copy.deepcopy(self.config)
        for kind in ('project','hash','duplicate','path'):
            self.config=copy.deepcopy(original)
            if kind=='project':self.config['project_id']=9
            if kind=='hash':self.config['decisions'][0]['source_sha256']='wrong'
            if kind=='duplicate':self.config['decisions']*=2
            if kind=='path':self.config['decisions'][0]['source_file']='../outside.json'
            (self.root/'flooring_selection_review.json').write_text(json.dumps(self.config))
            with self.subTest(kind=kind),self.assertRaises(ValueError):read_selections(self.root,self.rooms)

    def test_export_tracks_nested_selection_evidence(self):
        before=source_files(self.root)
        path=self.root/'evidence/selection.json';self.assertIn(str(path),before)
        path.write_bytes(path.read_bytes()+b' ')
        self.assertNotEqual(before,source_files(self.root))


if __name__=='__main__':unittest.main()
