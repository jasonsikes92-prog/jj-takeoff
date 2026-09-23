import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from foundation_snapshot_bridge import import_foundation_snapshot


class FoundationBridge(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'source.json'
        outputs={k:{} for k in ('footing_reinforcement','crawlspace_access_door','footing_pump','pier_masonry','pier_caps','pad_reinforcement')}
        outputs.update(blocks=1282,bags=None)
        self.path.write_text(json.dumps({'plan_sha256':'plan','version':32,'outputs':outputs}))
        self.draft={'plan_sha256':'plan','rows':[{'row_id':'block','cost_type':'MATERIAL','completion_status':'evidence_in_progress','unit':'ft2','draft_quantity':None}]}
        self.mapping=[{'row_id':'block','quantity_path':'outputs.blocks','source_unit':'block','use':'assembly_input','basis':'Unit mismatch retained','remaining':['Resolve template unit']}]

    def test_block_count_never_becomes_square_feet(self):
        result=import_foundation_snapshot(self.draft,self.path,self.mapping)
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(result['rows'][0]['assembly_inputs'][0]['quantity'],1282)
        self.assertEqual(result['rows'][0]['unit'],'ft2')
        with self.assertRaises(ValueError):import_foundation_snapshot(result,self.path,self.mapping)

    def test_unknowns_stay_null_and_bad_units_or_plan_rejected(self):
        self.mapping[0]['quantity_path']='outputs.bags'
        result=import_foundation_snapshot(self.draft,self.path,self.mapping)
        self.assertIsNone(result['rows'][0]['assembly_inputs'][0]['quantity'])
        self.mapping[0].update(use='template_quantity',template_unit='each')
        with self.assertRaises(ValueError):import_foundation_snapshot(self.draft,self.path,self.mapping)
        self.draft['plan_sha256']='other'
        with self.assertRaises(ValueError):import_foundation_snapshot(self.draft,self.path,self.mapping)

    def test_purchased_sticks_convert_to_stock_lf_without_changing_the_source(self):
        saved=json.loads(self.path.read_text())
        saved['outputs'].update(sticks=48,stock_ft=20)
        self.path.write_text(json.dumps(saved))
        self.draft['rows'][0]['unit']='LF'
        mapping={'row_id':'block','quantity_path':'outputs.sticks','source_unit':'stick',
                 'use':'template_quantity','template_unit':'LF','stock_length_path':'outputs.stock_ft',
                 'basis':'Purchased stock LF, not net reinforcement length','remaining':['Field steps']}
        result=import_foundation_snapshot(self.draft,self.path,[mapping])
        row=result['rows'][0]
        self.assertEqual(row['draft_quantity'],960)
        evidence=row['quantity_sources'][0]
        self.assertEqual((evidence['source_quantity'],evidence['stock_length_ft'],evidence['unit']),(48,20,'LF'))
        self.assertFalse(row['certified'])
        self.assertIsNone(self.draft['rows'][0]['draft_quantity'])
        for key,value in [('sticks',48.5),('sticks',None),('sticks',True),('stock_ft',0),('stock_ft',-20),('stock_ft',float('inf'))]:
            changed=copy.deepcopy(saved);changed['outputs'][key]=value
            self.path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):import_foundation_snapshot(self.draft,self.path,[mapping])
        self.path.write_text(json.dumps(saved))
        mapping['source_unit']='LF'
        with self.assertRaises(ValueError):import_foundation_snapshot(self.draft,self.path,[mapping])

    def supplemental(self):
        self.draft['rows'][0]['markup_pct']='15'
        self.draft['rows'].append({'row_id':'assembly','name':'Foundation','cost_type':'ASSEMBLY'})
        return {'pier-blocks':{'parent_row_id':'assembly','markup_source_row_id':'block',
            'quantity_path':'outputs.blocks','name':'Separate pier block stock','unit':'block',
            'basis':'Separate physical scope, purchased in blocks'}}

    def test_supplemental_preserves_units_markup_and_missing_price(self):
        mapping=self.supplemental();before=copy.deepcopy(self.draft)
        result=import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)
        row=result['additional_cost_rows'][0]
        self.assertEqual((row['draft_quantity'],row['unit'],row['markup_pct']),(1282,'block',15))
        self.assertIsNone(row['line_cost']);self.assertIsNone(row['unit_cost'])
        self.assertEqual(row['parent_row_id'],'assembly')
        self.assertEqual(self.draft,before)
        mapping['pier-blocks']['quantity_path']='outputs.bags'
        result=import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)
        self.assertIsNone(result['additional_cost_rows'][0]['draft_quantity'])

    def test_supplemental_rejects_duplicate_and_priced_parent(self):
        mapping=self.supplemental()
        self.draft['additional_cost_rows']=[{'row_id':'pier-blocks'}]
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)
        self.draft.pop('additional_cost_rows')
        self.draft['rows'][1]['line_cost']=100
        with self.assertRaisesRegex(ValueError,'unpriced assembly'):
            import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)
        self.draft['rows'][1]['line_cost']=None
        self.draft['rows'][0]['markup_pct']='-1'
        with self.assertRaisesRegex(ValueError,'markup'):
            import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)

    def test_purchase_replacement_has_one_owner_and_keeps_template_units(self):
        mapping=self.supplemental()
        mapping['pier-blocks']['replaces_row_id']='block'
        result=import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)
        self.assertEqual(result['rows'][0]['cost_owner_row_id'],'pier-blocks')
        self.assertEqual(result['rows'][0]['unit'],'ft2')
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(result['additional_cost_rows'][0]['replaces_row_id'],'block')
        duplicate=copy.deepcopy(mapping)
        duplicate['second']=copy.deepcopy(mapping['pier-blocks'])
        with self.assertRaisesRegex(ValueError,'Replacement'):
            import_foundation_snapshot(self.draft,self.path,self.mapping,duplicate)
        for key,value in [('draft_quantity',100),('line_cost',0),('covered_by_package','quote')]:
            draft=copy.deepcopy(self.draft);draft['rows'][0][key]=value
            with self.assertRaises(ValueError):import_foundation_snapshot(draft,self.path,self.mapping,mapping)
        mapping['pier-blocks']['quantity_path']='outputs.bags'
        with self.assertRaisesRegex(ValueError,'Replacement'):
            import_foundation_snapshot(self.draft,self.path,self.mapping,mapping)

if __name__=='__main__':unittest.main()
