import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from floor_finish_review import import_finish


class FloorFinishTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'owner.json').write_text('{"answer":"carpet"}')
        m=lambda identity,x:{'id':identity,'page':1,'kind':'area','points':[[x,0],[x+20,0],[x+20,20],[x,20]],'points_per_foot':2,'width_pt':100,'height_pt':100}
        self.state={'plan_sha256':'plan','version':3,'measurements':{'bed':m('bed',0),'hall':m('hall',30)}}
        self.draft={'plan_sha256':'plan','measurement_version':3,'rows':[
            {'row_id':'parent','name':'Flooring','cost_type':'ASSEMBLY'},
            {'row_id':'material','name':'LVP','parent':'Flooring','cost_type':'ALLOWANCE','markup_pct':'8',
             'assembly_inputs':[{'id':'lvp','measurement_ids':['hall'],'quantity':100}]},
            {'row_id':'labor','parent':'Flooring','cost_type':'LABOR','markup_pct':'7'}]}
        self.config={'plan_sha256':'plan','source_file':'owner.json','source_sha256':hashlib.sha256((self.root/'owner.json').read_bytes()).hexdigest(),
            'id':'carpet','label':'Bedroom carpet contour','basis':'Owner selection; verified room label','measurement_ids':['bed'],
            'displaced_row_id':'material','displaced_assembly_id':'lvp','parent_row_id':'parent','remaining':['Finish faces and roll layout'],
            'cost_rows':[{'row_id':'carpet-material','name':'Carpet and pad','unit':'sq yd','markup_source_row_id':'material'},
                         {'row_id':'carpet-labor','name':'Carpet installation','unit':'sq yd','markup_source_row_id':'labor'}]}

    def run_review(self):return import_finish(self.draft,self.state,self.config,self.root)

    def test_separate_area_and_inherited_markups_without_price(self):
        original=copy.deepcopy(self.draft);r=self.run_review()
        self.assertEqual(self.draft,original)
        self.assertEqual(r['floor_finish_review']['finish_area_sf'],100)
        self.assertEqual([x['markup_pct'] for x in r['additional_cost_rows']],['8','7'])
        for x in r['additional_cost_rows']:
            self.assertIsNone(x['draft_quantity']);self.assertIsNone(x['line_cost'])

    def test_edit_updates_carpet_only(self):
        self.state['measurements']['bed']['points']=[[0,0],[22,0],[22,20],[0,20]]
        r=self.run_review()['floor_finish_review']
        self.assertEqual(r['finish_area_sf'],110);self.assertEqual(r['remaining_finish_area_sf'],100)

    def test_duplicate_or_overlapping_room_rejected(self):
        self.config['measurement_ids']=['bed','bed']
        with self.assertRaises(ValueError):self.run_review()
        self.config['measurement_ids']=['hall']
        with self.assertRaises(ValueError):self.run_review()
        self.config['measurement_ids']=['bed'];self.state['measurements']['hall']['points']=[[10,0],[30,0],[30,20],[10,20]]
        with self.assertRaises(ValueError):self.run_review()

    def test_source_plan_and_revision_rejected(self):
        original=copy.deepcopy(self.config);self.config['plan_sha256']='other'
        with self.assertRaises(ValueError):self.run_review()
        self.config=original;self.state['version']=4
        with self.assertRaises(ValueError):self.run_review()
        self.state['version']=3;(self.root/'owner.json').write_text('changed')
        with self.assertRaises(ValueError):self.run_review()

    def test_invalid_shape_and_sloped_floor_rejected(self):
        self.state['measurements']['bed']['surface_factor']=1.2
        with self.assertRaises(ValueError):self.run_review()
        self.state['measurements']['bed']['surface_factor']=1
        self.state['measurements']['bed']['points']=[[0,0],[20,20],[0,20],[20,0]]
        with self.assertRaises(ValueError):self.run_review()

    def test_duplicate_cost_owner_or_priced_parent_rejected(self):
        self.config['cost_rows'][1]['row_id']='carpet-material'
        with self.assertRaises(ValueError):self.run_review()
        self.config['cost_rows'][1]['row_id']='carpet-labor';self.draft['rows'][0]['line_cost']=100
        with self.assertRaises(ValueError):self.run_review()


if __name__=='__main__':unittest.main()
