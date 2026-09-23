import copy
import hashlib
import json
import unittest
from window_bedding import bedding_takeoff
import test_window_snapshot_bridge as fixtures


class WindowBeddingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.WindowSnapshotTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f
        for a,w,h in zip(f.saved['material_schedule']['assemblies'],(108,72),(72,60)):
            a.update(rough_opening_width_in=w,rough_opening_height_in=h)
        f.draft['rows'] += [
            {'row_id':'110','cost_type':'ASSEMBLY','name':'Windows','completion_status':'pending'},
            {'row_id':'113','cost_type':'MATERIAL','parent':'Windows','markup_pct':'15'}]
        self.rule={'cap_return_in':1,'yield_lf_per_cartridge':30,'handling_percent':10}
        self.basis={'plan_sha256':'plan','status':'estimating_allowance','basis':'Test bedding only',
            'assumptions':['Estimating yield'],'remaining':['Installation review'],
            'documents':[{'file':'spec.pdf','sha256':hashlib.sha256((f.root/'spec.pdf').read_bytes()).hexdigest()}],
            'product':{'product_id':'sealant','model':'sealant'},'rule':self.rule}
        self.save()
    def save(self):
        p=self.f.root/'bedding.json';p.write_text(json.dumps(self.basis))
        self.f.mapping['bedding']={'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'row_id':'sealant','parent_row_id':'110','markup_source_row_id':'113'}
    def test_bedding_only_counts_groups_and_preserves_existing_rows(self):
        before=copy.deepcopy(self.f.draft);result=self.f.run_import()
        row=result['additional_cost_rows'][0];q=row['quantity_sources'][0]['takeoff']
        self.assertEqual(row['draft_quantity'],2);self.assertEqual(row['markup_pct'],'15')
        self.assertAlmostEqual(q['net_bedding_lf'],52+4/12)
        self.assertEqual(q['interior_perimeter_reference_lf'],52)
        self.assertFalse(row['certified']);self.assertIsNone(row['line_cost'])
        self.assertEqual(self.f.draft,before)
    def test_more_assemblies_and_larger_bead_yield_change_whole_purchase(self):
        assemblies=copy.deepcopy(self.f.saved['material_schedule']['assemblies'])
        assemblies[0]['assembly_quantity']=4
        result=bedding_takeoff(assemblies,self.rule)
        self.assertEqual(result['quantity'],6)
        self.assertGreater(bedding_takeoff(assemblies,{**self.rule,'yield_lf_per_cartridge':12})['quantity'],6)
    def test_duplicate_cost_owner_priced_parent_and_stale_source_rejected(self):
        self.f.draft['additional_cost_rows']=[{'row_id':'sealant'}]
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.f.run_import()
        self.f.draft.pop('additional_cost_rows');self.f.draft['rows'][-2]['line_cost']=100
        with self.assertRaisesRegex(ValueError,'unpriced'):self.f.run_import()
        self.f.draft['rows'][-2].pop('line_cost')
        self.basis['documents'][0]['sha256']='0'*64;self.save()
        with self.assertRaisesRegex(ValueError,'evidence'):self.f.run_import()
    def test_invalid_yield_geometry_and_missing_material_schedule_rejected(self):
        for value in (0,-1,None,True,float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):
                bedding_takeoff(self.f.saved['material_schedule']['assemblies'],{**self.rule,'yield_lf_per_cartridge':value})
        self.f.mapping.pop('material_row_id')
        with self.assertRaisesRegex(ValueError,'verified material'):self.f.run_import()


if __name__=='__main__':unittest.main()
