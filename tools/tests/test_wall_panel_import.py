import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from wall_panel_review import import_wall_panels


class WallPanelImport(unittest.TestCase):
    def setUp(self):
        self.draft={'plan_sha256':'plan','rows':[
            {'excel_row':'100','cost_type':'MATERIAL','completion_status':'evidence_in_progress',
             'unit':'ft2','markup_pct':'15','draft_quantity':None,'line_cost':None,
             'assembly_inputs':[{'id':'studs','quantity':232}]},
            {'excel_row':'82','line_cost':190,'draft_quantity':1}],
            'whole_house_total':None,'estimate_released':False}
        self.panels={'plan_sha256':'plan','mapping_sha256':'mapping','basis_sha256':'basis',
            'measurement_versions':{'exterior':1,'upper':1},'source_geometry_sha256':{'exterior':'geometry'},
            'combined':{'candidate_sheets':95,'gross_surface_sf':2752,'cut_sections':160,
                        'faces':[{'face_id':'W01'},{'face_id':'GABLE'}]},
            'precut_height_sensitivity':{'candidate_sheets':95},
            'conditional_floor_band':{'candidate_sheets':103},'remaining':['Wall height unresolved']}

    def run_import(self):
        with patch('wall_panel_review.from_folder',return_value=self.panels):
            return import_wall_panels(self.draft,Path('.'),'100','mapping')

    def test_one_candidate_not_sum_of_alternatives_and_no_price_change(self):
        original=copy.deepcopy(self.draft);result=self.run_import();row=result['rows'][0]
        self.assertEqual(len(row['assembly_inputs']),2)
        self.assertEqual(row['assembly_inputs'][-1]['quantity'],95)
        self.assertEqual(result['wall_panel_review']['alternative_totals_not_additions'],
                         {'precut_height_sensitivity':95,'conditional_floor_band':103})
        self.assertEqual(row['unit'],'ft2');self.assertEqual(row['markup_pct'],'15')
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
        self.assertFalse(row['assembly_inputs'][-1]['certified'])
        self.assertEqual(result['rows'][1],original['rows'][1]);self.assertEqual(self.draft,original)
        self.assertIsNone(result['whole_house_total']);self.assertFalse(result['estimate_released'])

    def test_recalculation_and_restore_never_reuse_previous_candidate(self):
        first=self.run_import();self.panels['combined']['candidate_sheets']=97
        self.panels['source_geometry_sha256']['exterior']='edited'
        changed=self.run_import()
        self.assertEqual(changed['rows'][0]['assembly_inputs'][-1]['quantity'],97)
        self.assertNotEqual(changed['wall_panel_review']['source_geometry_sha256'],
                            first['wall_panel_review']['source_geometry_sha256'])
        self.panels['combined']['candidate_sheets']=95
        self.panels['source_geometry_sha256']['exterior']='geometry'
        self.assertEqual(self.run_import(),first)

    def test_owner_height_evidence_travels_with_one_selected_quantity(self):
        self.panels.update(selected_scenario='nominal-precut-wall',selected_wall_height_inches=109.125,
            height_selection_source={'path':'owner.json','sha256':'proof'},printed_height_comparison={'candidate_sheets':94})
        result=self.run_import();source=result['rows'][0]['assembly_inputs'][-1]['source_snapshot']
        self.assertEqual(source['height_selection_source']['sha256'],'proof')
        self.assertEqual(result['rows'][0]['assembly_inputs'][-1]['quantity'],95)
        self.assertEqual(result['wall_panel_review']['alternative_totals_not_additions'],
                         {'printed_height_comparison':94,'conditional_floor_band':103})

    def test_wrong_plan_mapping_and_invalid_geometry_have_no_fallback(self):
        for key in ['plan_sha256','mapping_sha256']:
            old=self.panels[key];self.panels[key]='changed'
            with self.assertRaisesRegex(ValueError,'drawing or mapping'):self.run_import()
            self.panels[key]=old
        with patch('wall_panel_review.from_folder',side_effect=ValueError('Disconnected gable')):
            with self.assertRaisesRegex(ValueError,'Disconnected gable'):
                import_wall_panels(self.draft,Path('.'),'100','mapping')

    def test_duplicate_or_assigned_target_refused(self):
        original=copy.deepcopy(self.draft);self.draft=self.run_import()
        with self.assertRaisesRegex(ValueError,'already imported'):self.run_import()
        del self.draft['wall_panel_review']
        with self.assertRaisesRegex(ValueError,'already assigned'):self.run_import()
        for values in [{'draft_quantity':95},{'line_cost':100},{'covered_by_package':'quote'},
                       {'completion_status':'not_applicable_source_reviewed'},{'cost_type':'LABOR'}]:
            self.draft=copy.deepcopy(original);self.draft['rows'][0].update(values)
            with self.assertRaisesRegex(ValueError,'excluded, assigned or priced'):self.run_import()


if __name__=='__main__':unittest.main()
