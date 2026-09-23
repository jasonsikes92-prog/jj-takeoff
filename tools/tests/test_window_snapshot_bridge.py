import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from window_snapshot_bridge import import_window_snapshot


class WindowSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        spec=self.root/'spec.pdf';spec.write_bytes(b'synthetic specification evidence')
        self.saved={'plan_sha256':'plan','owner_answer':'Per individual window unit',
            'template_row':114,'unit':'each','installation_quantity':5,'basis':'Component installation',
            'assemblies':[{'opening_id':'A','assembly_quantity':1,'component_count':3,'source_plan_sheet':5},
                          {'opening_id':'B','assembly_quantity':1,'component_count':2,'source_plan_sheet':9}]}
        self.saved['material_schedule']={'specification_file':'spec.pdf',
            'specification_sha256':hashlib.sha256(spec.read_bytes()).hexdigest(),
            'quote_id':'test','basis':'Material per assembled opening; current pricing pending',
            'assemblies':copy.deepcopy(self.saved['assemblies'])}
        self.draft={'plan_sha256':'plan','rows':[{'row_id':str(r),'excel_row':str(r),'unit':'each',
            'cost_type':kind,'draft_quantity':None,'line_cost':None,'completion_status':'pending'}
            for r,kind in [(112,'ALLOWANCE'),(114,'LABOR')]]}
        self.mapping={'row_id':'114','material_row_id':'112'}

    def run_import(self):
        source=self.root/'windows.json';source.write_text(json.dumps(self.saved))
        return import_window_snapshot(self.draft,source,self.mapping)

    def test_assembly_count_and_installation_units_differ_without_prices(self):
        before=copy.deepcopy(self.draft)
        result=self.run_import()
        self.assertEqual([r['draft_quantity'] for r in result['rows']],[2,5])
        self.assertTrue(all(r['line_cost'] is None for r in result['rows']))
        self.assertEqual(before,self.draft)
        self.assertFalse(result['estimate_released'])

    def test_legacy_installation_only_mapping_preserved(self):
        self.mapping.pop('material_row_id');self.saved.pop('material_schedule')
        self.assertEqual([r['draft_quantity'] for r in self.run_import()['rows']],[None,5])

    def test_cleaning_uses_individual_units_without_doubling_faces_or_pricing(self):
        self.mapping['cleaning_row_id']='700'
        self.draft['rows'].append({'row_id':'700','unit':'each','cost_type':'SUBCONTRACTOR',
            'draft_quantity':None,'line_cost':None,'completion_status':'pending'})
        before=copy.deepcopy(self.draft)
        result=self.run_import();cleaning=result['rows'][-1]
        self.assertEqual(cleaning['draft_quantity'],5)
        self.assertIsNone(cleaning['line_cost'])
        self.assertIn('Historical billed counts',cleaning['quantity_sources'][0]['remaining'][0])
        self.assertEqual(before,self.draft)
        for change in ({'draft_quantity':26},{'line_cost':546},{'unit':'SF'},
                       {'cost_owner_row_id':'other'},{'completion_status':'not_applicable_owner'}):
            self.draft=copy.deepcopy(before);self.draft['rows'][-1].update(change)
            with self.assertRaisesRegex(ValueError,'cleaning target'):self.run_import()

    def test_duplicate_missing_or_changed_material_member_rejected(self):
        original=copy.deepcopy(self.saved)
        for members in ([original['assemblies'][0]]*2, original['assemblies'][:1],
                        [{**original['assemblies'][0],'component_count':4},original['assemblies'][1]]):
            self.saved=copy.deepcopy(original);self.saved['material_schedule']['assemblies']=members
            with self.assertRaises(ValueError):self.run_import()

    def test_wrong_drawing_and_changed_specification_rejected(self):
        self.saved['plan_sha256']='other'
        with self.assertRaises(ValueError):self.run_import()
        self.saved['plan_sha256']='plan'
        (self.root/'spec.pdf').write_bytes(b'changed')
        with self.assertRaises(ValueError):self.run_import()

    def test_outside_specification_path_rejected(self):
        self.saved['material_schedule']['specification_file']='../outside.pdf'
        with self.assertRaises(ValueError):self.run_import()

    def test_incompatible_or_duplicate_owner_rejected(self):
        for change in ({'cost_type':'ASSEMBLY'},{'draft_quantity':0},{'line_cost':0},
                       {'covered_by_package':'p'},{'cost_owner_row_id':'other'},{'unit':'ft2'}):
            before=copy.deepcopy(self.draft)
            self.draft['rows'][0].update(change)
            with self.assertRaises(ValueError):self.run_import()
            self.draft=before
        self.mapping['material_row_id']='114'
        with self.assertRaises(ValueError):self.run_import()

    def perimeter_mapping(self):
        self.mapping['perimeter_row_id']='229'
        self.draft['rows'].append({'row_id':'229','excel_row':'229','unit':'feet','cost_type':'SUBCONTRACTOR',
            'draft_quantity':None,'line_cost':None,'completion_status':'pending'})
        for member,width,height in zip(self.saved['material_schedule']['assemblies'],[108,72],[72,60]):
            member.update(rough_opening_width_in=width,rough_opening_height_in=height)

    def test_perimeter_counts_assembled_groups_not_component_panes(self):
        self.perimeter_mapping()
        result=self.run_import();row=result['rows'][-1]
        self.assertEqual(row['assembly_inputs'][0]['quantity'],52)
        self.assertEqual([p['perimeter_lf'] for p in row['assembly_inputs'][0]['opening_perimeters']],[30,22])
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
        self.assertFalse(row['assembly_inputs'][0]['order_released'])
        self.saved['assemblies'][1]['assembly_quantity']=2
        self.saved['material_schedule']['assemblies'][1]['assembly_quantity']=2
        self.saved['installation_quantity']=7
        self.assertEqual(self.run_import()['rows'][-1]['assembly_inputs'][0]['quantity'],74)

    def test_perimeter_refuses_missing_or_invalid_dimensions(self):
        self.perimeter_mapping();member=self.saved['material_schedule']['assemblies'][0]
        for value in (None,0,-1,True,float('inf'),float('nan')):
            member['rough_opening_height_in']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'positive supplier'):self.run_import()

    def test_perimeter_requires_verified_schedule_and_unassigned_target(self):
        self.perimeter_mapping()
        for change in ({'unit':'each'},{'assembly_inputs':[{}]},{'draft_quantity':0},{'covered_by_package':'siding'}):
            old=copy.deepcopy(self.draft['rows'][-1]);self.draft['rows'][-1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.run_import()
            self.draft['rows'][-1]=old
        self.mapping.pop('material_row_id')
        with self.assertRaisesRegex(ValueError,'verified material schedule'):self.run_import()

    def test_trim_billing_uses_assemblies_and_retains_separate_lf_reference(self):
        self.perimeter_mapping();self.mapping['trim_pricing_basis']='per_assembled_opening'
        self.draft['rows'][-1]['unit']='each'
        result=self.run_import();trim=result['rows'][-1]
        self.assertEqual(trim['draft_quantity'],2)
        self.assertEqual(trim['quantity_sources'][0]['unit'],'each')
        self.assertEqual(trim['assembly_inputs'][0]['quantity'],52)
        self.assertEqual(trim['assembly_inputs'][0]['unit'],'LF')
        self.assertEqual(result['rows'][1]['draft_quantity'],5)
        self.assertIsNone(trim['line_cost']);self.assertFalse(trim['certified'])

    def test_trim_basis_cannot_silently_change_unit_or_apply_without_target(self):
        self.perimeter_mapping();self.mapping['trim_pricing_basis']='per_assembled_opening'
        with self.assertRaisesRegex(ValueError,'incompatible'):self.run_import()
        self.draft['rows'][-1]['unit']='each';self.mapping['trim_pricing_basis']='per_individual_window'
        with self.assertRaisesRegex(ValueError,'assembled-opening'):self.run_import()
        self.mapping['trim_pricing_basis']='per_assembled_opening';self.mapping.pop('perimeter_row_id')
        with self.assertRaisesRegex(ValueError,'assembled-opening'):self.run_import()


if __name__=='__main__':unittest.main()
