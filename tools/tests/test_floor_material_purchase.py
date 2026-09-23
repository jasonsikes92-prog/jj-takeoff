import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from floor_material_purchase import carton_allocation, apply_material_purchase


class CartonsTest(unittest.TestCase):
    def test_pool_rounds_once_and_preserves_all_purchased_area(self):
        result = carton_allocation([307.1599741968255,91.94500911563021,39.975301411629616,1020.7576113193563],25.89,10)
        self.assertEqual(result['cartons'],63)
        self.assertEqual(result['purchased_sf'],1631.07)
        self.assertAlmostEqual(sum(result['allocated_sf']),1631.07)
        self.assertGreaterEqual(result['purchased_sf'],result['required_sf'])
        self.assertLess(result['purchased_sf']-25.89,result['required_sf'])

    def test_exact_boundary_zero_and_one_more(self):
        self.assertEqual(carton_allocation([25.89],25.89,0)['cartons'],1)
        self.assertEqual(carton_allocation([25.8901],25.89,0)['cartons'],2)
        self.assertEqual(carton_allocation([0,0],25.89,10)['allocated_sf'],[0,0])
        self.assertEqual(carton_allocation([10,10,10],10,0)['allocated_sf'],[10,10,10])

    def test_invalid_inputs(self):
        for areas,coverage,waste in [([-1],25.89,10),([1],0,10),([1],25.89,-1),([float('nan')],25.89,10),([True],25.89,10),([1],1.001,0),([],25.89,10)]:
            with self.assertRaises(ValueError):carton_allocation(areas,coverage,waste)

    def test_source_binding_and_material_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);invoice=root/'invoice.txt';invoice.write_text('source invoice')
            ref=lambda p:{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            proof={'plan_sha256':'plan','material_cost_owner_ids':['m'], 'basis':'dated_invoice_carton_allowance',
                   'product_sku':'sku','current_carton_spec_verified':False,'coverage_sf':25.89,'source_document':ref(invoice)}
            path=root/'proof.json';path.write_text(json.dumps(proof));config=ref(path)
            material={'row_id':'m','cost_type':'MATERIAL','unit':'ft2','draft_quantity':None,'line_cost':None,'assembly_inputs':[{'id':'g'}]}
            labor={'row_id':'l','draft_quantity':30,'line_cost':45}
            draft={'plan_sha256':'plan','rows':[material,labor], 'floor_finish_review':{
                'billing_review':{'material_waste_pct':10},'cost_allocation':{'groups':[{'id':'g','net_sf':30,'cost_rows':['m','l']}]}}}
            old=copy.deepcopy(draft);apply_material_purchase(draft,config,root)
            self.assertEqual(material['draft_quantity'],51.78)
            self.assertEqual(labor,old['rows'][1])
            self.assertFalse(material['quantity_sources'][0]['order_released'])
            with self.assertRaises(ValueError):apply_material_purchase(draft,config,root)
            invoice.write_text('changed invoice')
            with self.assertRaises(ValueError):apply_material_purchase(old,config,root)


if __name__=='__main__':unittest.main()
