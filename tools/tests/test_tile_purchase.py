import unittest
import copy
import hashlib
import json
import tempfile
from pathlib import Path
from tile_purchase import purchase, apply_purchase


class TilePurchaseTests(unittest.TestCase):
    def test_roberts_floor_uses_box_price_not_rounded_sf_price(self):
        result=purchase([151.14179323500014],15.5,10,54.08)
        self.assertEqual(result['purchase_units'],11)
        self.assertEqual(result['purchased_sf'],170.5)
        self.assertEqual(result['pretax_material_cost'],594.88)
        self.assertEqual(result['installation_area_sf'],151.14179323500014)
        self.assertNotEqual(result['pretax_material_cost'],round(170.5*3.49,2))

    def test_pool_same_product_before_rounding(self):
        self.assertEqual(purchase([6,6],13.37,10,46.69)['purchase_units'],1)
        self.assertEqual(purchase([6],13.37,10,46.69)['purchase_units']*2,2)

    def test_exact_boundary_and_small_excess(self):
        self.assertEqual(purchase([10],11,10,20)['purchase_units'],1)
        self.assertEqual(purchase([10.00001],11,10,20)['purchase_units'],2)
        self.assertEqual(purchase([0],11,10,20)['pretax_material_cost'],0)

    def test_mosaic_uses_sheet_coverage(self):
        self.assertEqual(purchase([18.60146819940229],.964,10,15.74)['purchase_units'],22)

    def test_invalid_inputs_do_not_become_zero(self):
        for args in [([],1,10,1),([None],1,10,1),([True],1,10,1),([-1],1,10,1),
                     ([1],0,10,1),([1],1,-1,1),([1],1,10,-1),([float('nan')],1,10,1)]:
            with self.subTest(args=args),self.assertRaises(ValueError):purchase(*args)

    def test_purchase_requires_sources_and_respects_saved_waste(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            item={'row_id':'tile','assembly_input_id':'floor','coverage_sf':15.5,
                  'waste_percent':10,'package_price':54.08,'product_sku':'floor','sources':[]}
            config={'plan_sha256':'plan','purchases':[item]}
            draft={'plan_sha256':'plan','rows':[{'row_id':'tile','cost_type':'MATERIAL','unit':'SF',
                'assembly_inputs':[{'id':'floor','unit':'SF','quantity':100}]}]}
            def calculate():
                (root/'tile_material_purchase.json').write_text(json.dumps(config))
                return apply_purchase(draft,root)
            with self.assertRaisesRegex(ValueError,'source evidence'):calculate()
            proof={'records':[{'normalized_decision':{'tile_waste_fraction':.1}}]}
            raw=json.dumps(proof).encode();(root/'owner.json').write_bytes(raw)
            item['sources']=[{'file':'owner.json','sha256':hashlib.sha256(raw).hexdigest()}]
            self.assertEqual(calculate()['rows'][0]['draft_quantity'],124)
            item['waste_percent']=20
            with self.assertRaisesRegex(ValueError,'saved owner waste'):calculate()

    def test_live_niche_purchase_rejects_conflicting_or_missing_owner_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proof={'plan_sha256':'plan','answers':[{'normalized_decision':{'shower_niches':[
                {'count':1,'finished_width_inches':36,'finished_height_inches':18,'finished_depth_inches':3.5}]}}]}
            raw=json.dumps(proof).encode()
            (root/'owner.json').write_bytes(raw)
            item={'row_id':'tile','assembly_input_id':'floor','coverage_sf':.964,
                  'waste_percent':10,'package_price':15.74,'product_sku':'mosaic',
                  'niche_inches':{'width':36,'height':18,'depth':3.5,'count':1},
                  'sources':[{'file':'owner.json','sha256':hashlib.sha256(raw).hexdigest()}]}
            config={'plan_sha256':'plan','purchases':[item]}
            draft={'plan_sha256':'plan','rows':[{'row_id':'tile','cost_type':'MATERIAL','unit':'each',
                'assembly_inputs':[{'id':'floor','unit':'SF','quantity':18.60146819940229}]}]}
            original=copy.deepcopy(draft)
            def calculate():
                (root/'tile_material_purchase.json').write_text(json.dumps(config))
                return apply_purchase(draft,root)['rows'][0]['draft_quantity']
            self.assertEqual(calculate(),30)
            self.assertEqual(draft,original)
            item['niche_row_id']='niche'
            draft['rows'].append({'row_id':'niche','cost_type':'MATERIAL','draft_quantity':1})
            self.assertEqual(calculate(),30)
            result=apply_purchase(draft,root)
            self.assertEqual(result['rows'][1]['cost_owner_row_id'],'tile')
            self.assertEqual(result['rows'][0]['quantity_sources'][0]['included_row_ids'],['niche'])
            self.assertNotIn('cost_owner_row_id',draft['rows'][1])
            for field,value in [('line_cost',0),('unit_cost',15.74),('cost_owner_row_id','other'),
                                ('covered_by_package','package')]:
                draft['rows'][1][field]=value
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,'already has pricing'):calculate()
                del draft['rows'][1][field]
            item['niche_row_id']='tile'
            with self.assertRaisesRegex(ValueError,'distinct included'):calculate()
            item['niche_row_id']='niche'
            item['niche_inches']['width']=48
            with self.assertRaisesRegex(ValueError,'match saved owner'):calculate()
            item['niche_inches']['width']=36
            item['sources']=[]
            with self.assertRaisesRegex(ValueError,'source evidence'):calculate()
            # Even a matching hash cannot authorize evidence for another plan.
            proof['plan_sha256']='other-plan'
            raw=json.dumps(proof).encode()
            (root/'owner.json').write_bytes(raw)
            item['sources']=[{'file':'owner.json','sha256':hashlib.sha256(raw).hexdigest()}]
            with self.assertRaisesRegex(ValueError,'another plan'):calculate()
