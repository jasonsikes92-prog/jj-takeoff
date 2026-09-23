import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from framing_snapshot_bridge import import_framing_snapshot


class FramingSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.path=self.folder/'framing.json'
        (self.folder/'layout.pdf').write_bytes(b'Synthetic source layout')
        self.saved={'version':1,'floor_footprint':{'plan_sha256':'plan'},
            'profile':{'subfloor_specification':{'source':{'sha256':hashlib.sha256(b'Synthetic source layout').hexdigest()}}},
            'pending_external_inputs':['Connection schedule and current quote'],
            'supplier_schedule':[{'scope':'first_floor','plot_id':'F1','product_as_extracted':'Engineered member',
                'net_qty_as_printed':3,'plies':3,'length_ft':20,'page':1},
                {'scope':'ceiling','plot_id':'B1','product_as_extracted':'Structural ceiling member',
                'net_qty_as_printed':2,'plies':2,'length_ft':10,'page':2}]}
        self.mapping={'supplier_layout_file':'layout.pdf','scope_rows':{'first_floor':'101','ceiling':'100'}}
        self.draft={'plan_sha256':'plan','rows':[{'row_id':str(r),'cost_type':'MATERIAL',
            'completion_status':'not_yet_reconciled','draft_quantity':2145 if r==101 else None,
            'line_cost':None,'line_price':None,'assembly_inputs':[],'markup_pct':'15'} for r in (100,101)]}

    def run_import(self):
        self.path.write_text(json.dumps(self.saved))
        return import_framing_snapshot(self.draft,self.path,self.mapping)

    def test_pieces_not_multiplied_by_plies_and_floor_ceiling_not_double_owned(self):
        original=copy.deepcopy(self.draft);value=self.run_import()
        self.assertEqual(value['framing_snapshot']['scope_totals'],{
            'first_floor':{'scheduled_pieces':3,'scheduled_lf':60},'ceiling':{'scheduled_pieces':2,'scheduled_lf':20}})
        ceiling,floor=value['rows']
        self.assertEqual(floor['draft_quantity'],2145)
        self.assertIsNone(ceiling['draft_quantity'])
        self.assertEqual(floor['assembly_inputs'][0]['quantity'],3)
        self.assertEqual(ceiling['assembly_inputs'][0]['quantity'],2)
        self.assertTrue(all(r['line_cost'] is None and r['markup_pct']=='15' for r in value['rows']))
        self.assertEqual(self.draft,original)

    def test_changed_layout_wrong_plan_and_duplicate_component_refused(self):
        self.saved['floor_footprint']['plan_sha256']='different'
        with self.assertRaisesRegex(ValueError,'another drawing'):self.run_import()
        self.saved['floor_footprint']['plan_sha256']='plan'
        self.saved['supplier_schedule'].append(copy.deepcopy(self.saved['supplier_schedule'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):self.run_import()
        self.saved['supplier_schedule'].pop()
        (self.folder/'layout.pdf').write_bytes(b'Changed')
        with self.assertRaisesRegex(ValueError,'source changed'):self.run_import()

    def test_double_import_and_incompatible_owner_refused(self):
        self.draft=self.run_import()
        with self.assertRaisesRegex(ValueError,'already imported'):self.run_import()
        self.draft.pop('framing_snapshot')
        self.draft['rows'][0]['covered_by_package']='package'
        with self.assertRaisesRegex(ValueError,'already priced'):self.run_import()

    def test_invalid_quantities_refused(self):
        for key,value in [('net_qty_as_printed',-1),('net_qty_as_printed',True),('plies',0),('length_ft',float('nan'))]:
            original=self.saved['supplier_schedule'][0][key]
            self.saved['supplier_schedule'][0][key]=value
            with self.assertRaisesRegex(ValueError,'Invalid supplier'):self.run_import()
            self.saved['supplier_schedule'][0][key]=original


if __name__=='__main__':unittest.main()
