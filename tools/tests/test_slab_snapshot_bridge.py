import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from slab_snapshot_bridge import import_slab_snapshot,profile_hash


class SlabBridge(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'snapshot.json'
        item={'template_row_id':'concrete','quantity':16,'unit':'CY','markup_percent':15,
              'quantity_status':'Rounded after waste','cost':3040,'sell_amount':3496}
        self.snapshot={'plan_sha256':'plan','version':33,'construction':{'profile':{},
            'profile_sha256':profile_hash({}),'outputs':{'estimate_rows':[item,{**item,'template_row_id':'extra'}]}}}
        self.path.write_text(json.dumps(self.snapshot))
        self.draft={'plan_sha256':'plan','rows':[{'row_id':'concrete','unit':'YD3','markup_pct':'15',
             'cost_type':'MATERIAL','completion_status':'evidence_in_progress','draft_quantity':None,'line_cost':None}]}
        self.mapping={'concrete':{'source_unit':'CY','template_unit':'YD3','basis':'Cubic yards in both sources'}}

    def test_quantity_and_supplemental_budget_survive_without_current_price(self):
        result=import_slab_snapshot(self.draft,self.path,self.mapping)
        self.assertEqual(result['rows'][0]['draft_quantity'],16)
        self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertEqual(result['rows'][0]['saved_trade_budget']['cost'],3040)
        self.assertEqual(len(result['slab_snapshot']['supplemental_rows']),1)
        self.assertIsNone(self.draft['rows'][0]['draft_quantity'])
        with self.assertRaises(ValueError):import_slab_snapshot(result,self.path,self.mapping)

    def test_wrong_units_markup_plan_and_profile_rejected(self):
        for field,value in [('unit','each'),('markup_pct','7')]:
            draft=copy.deepcopy(self.draft);draft['rows'][0][field]=value
            with self.assertRaises(ValueError):import_slab_snapshot(draft,self.path,self.mapping)
        draft=copy.deepcopy(self.draft);draft['plan_sha256']='other'
        with self.assertRaises(ValueError):import_slab_snapshot(draft,self.path,self.mapping)
        self.snapshot['construction']['profile']['changed']=True;self.path.write_text(json.dumps(self.snapshot))
        with self.assertRaises(ValueError):import_slab_snapshot(self.draft,self.path,self.mapping)

    def test_explicit_supplemental_ownership_preserves_original_rows_and_withholds_old_prices(self):
        self.draft['rows'].append({'row_id':'slab','name':'Slab','cost_type':'ASSEMBLY','line_cost':None})
        self.snapshot['construction']['outputs']['estimate_rows'][1]['name']='Additional steel'
        self.path.write_text(json.dumps(self.snapshot))
        mapping={'extra':{'parent_row_id':'slab','unit':'CY','markup_pct':15,'cost_type':'MATERIAL','basis':'Synthetic assembly test'}}
        result=import_slab_snapshot(self.draft,self.path,self.mapping,mapping)
        extra=result['additional_cost_rows'][0]
        self.assertEqual(len(result['rows']),2)
        self.assertEqual((extra['row_id'],extra['parent_row_id'],extra['draft_quantity']),('extra','slab',16))
        self.assertIsNone(extra['unit_cost']);self.assertIsNone(extra['line_cost'])
        self.assertEqual(extra['saved_trade_budget']['cost'],3040)
        for change in ('parent','unit','markup','duplicate','bundled'):
            candidate=copy.deepcopy(self.draft);assignment=copy.deepcopy(mapping)
            if change=='parent':assignment['extra']['parent_row_id']='missing'
            if change=='unit':assignment['extra']['unit']='box'
            if change=='markup':assignment['extra']['markup_pct']=7
            if change=='duplicate':candidate['additional_cost_rows']=[copy.deepcopy(extra)]
            if change=='bundled':candidate['rows'][-1]['covered_by_package']='package'
            with self.assertRaises(ValueError):import_slab_snapshot(candidate,self.path,self.mapping,assignment)

if __name__=='__main__':unittest.main()
