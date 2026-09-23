import copy
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from framing_stock_review import import_stock


class FramingStockReview(unittest.TestCase):
    def setUp(self):
        self.draft={'plan_sha256':'plan','measurement_version':3,'rows':[
            {'excel_row':'100','cost_type':'MATERIAL','completion_status':'evidence_in_progress',
             'unit':'ft2','markup_pct':'15','draft_quantity':None,'line_cost':None,
             'assembly_inputs':[{'id':'wall-sheathing-combined-candidate','quantity':95}]},
            {'excel_row':'82','line_cost':190,'draft_quantity':1}],
            'whole_house_total':None,'estimate_released':False}
        self.config={'plan_sha256':'plan','template_row':'100',
                     'mapping_sha256':{'roof':'roof','plates':'plates','headers':'headers'}}
        common={'plan_sha256':'plan','basis':'Fixture cut scenario','remaining':['Review support and material']}
        self.reviews={'roof':{**common,'mapping_sha256':'roof','source_version':1,
            'candidate_sheets':171,'faces':[{'face_id':'R01'}]},
            'plates':{**common,'mapping_sha256':'plates','source_version':1,
                'boards':[{'id':'B01','sku':'TOP','length_ft':16},{'id':'B02','sku':'BOTTOM','length_ft':16}]},
            'headers':{**common,'mapping_sha256':'headers','measurement_version':3,
                'boards':[{'id':'B01','sku':'2616','length_ft':16}],
                'header_issues':{'H27':['Supplier conflict']},'candidate_cut_piece_count':2}}

    def run_import(self):
        with ExitStack() as stack:
            for key,name in [('roof','roof_panels'),('plates','plate_stock'),('headers','header_cuts')]:
                stack.enter_context(patch('framing_stock_review.'+name,return_value=copy.deepcopy(self.reviews[key])))
            return import_stock(self.draft,Path('.'),self.config)

    def test_distinct_materials_and_existing_components_without_prices(self):
        original=copy.deepcopy(self.draft);result=self.run_import();row=result['rows'][0]
        self.assertEqual(len(row['assembly_inputs']),5)
        self.assertEqual(row['assembly_inputs'][0],original['rows'][0]['assembly_inputs'][0])
        stock={q['id']:q['quantity'] for q in row['assembly_inputs'][1:]}
        self.assertEqual(stock,{'framing-stock-roof':171,'framing-stock-plates-BOTTOM-16':1,
                               'framing-stock-plates-TOP-16':1,'framing-stock-headers-2616-16':1})
        self.assertEqual(row['unit'],'ft2');self.assertEqual(row['markup_pct'],'15')
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
        self.assertFalse(result['estimate_released']);self.assertIsNone(result['whole_house_total'])
        self.assertEqual(self.draft,original);self.assertEqual(result['rows'][1],original['rows'][1])
        self.assertEqual(result['framing_stock_review']['sources']['headers']['header_issues'],
                         {'H27':['Supplier conflict']})

    def test_changed_candidates_and_empty_header_group_do_not_keep_old_stock(self):
        self.reviews['roof']['candidate_sheets']=182
        self.reviews['headers']['boards']=[];self.reviews['headers']['candidate_cut_piece_count']=0
        result=self.run_import();items=result['rows'][0]['assembly_inputs']
        self.assertEqual(next(q['quantity'] for q in items if q['id']=='framing-stock-roof'),182)
        self.assertFalse(any(q['id'].startswith('framing-stock-headers-') for q in items))
        self.assertIn('H27',result['framing_stock_review']['sources']['headers']['header_issues'])

    def test_plan_mapping_and_inconsistent_versions_rejected(self):
        original=copy.deepcopy(self.reviews)
        for key,values in [('roof',{'plan_sha256':'other'}),('plates',{'mapping_sha256':'changed'}),
                           ('plates',{'source_version':2}),('headers',{'measurement_version':4})]:
            self.reviews=copy.deepcopy(original);self.reviews[key].update(values)
            with self.assertRaises(ValueError):self.run_import()

    def test_subfloor_is_separate_and_mismatched_source_version_rejected(self):
        self.config['mapping_sha256']['subfloor']='subfloor'
        floor={'plan_sha256':'plan','mapping_sha256':'subfloor','source_version':1,
               'candidate_sheets':77,'pieces':[{'id':'P001'}],'basis':'Nominal T&G',
               'remaining':['Exact installed coverage unresolved']}
        with patch('framing_stock_review.subfloor_panels',return_value=floor):
            result=self.run_import()
            self.assertEqual(result['rows'][0]['assembly_inputs'][-1]['quantity'],77)
            self.assertEqual(result['rows'][0]['assembly_inputs'][-1]['id'],'framing-stock-subfloor')
            floor['source_version']=2
            with self.assertRaisesRegex(ValueError,'Subfloor and roof'):self.run_import()

    def test_oversized_rafters_stay_explicit_without_invented_boards(self):
        self.config['mapping_sha256']['rafters']='rafters'
        rafters={'plan_sha256':'plan','mapping_sha256':'rafters','source_version':1,
                 'boards':[],'requires_splice_layout':[{'id':'R1-S001','cut_inches':313}],
                 'basis':'Provisional rafter cuts','remaining':['Supports require review']}
        with patch('framing_stock_review.rafter_cuts',return_value=rafters):
            result=self.run_import()
            self.assertFalse(any(q['id'].startswith('framing-stock-rafters-') for q in result['rows'][0]['assembly_inputs']))
            self.assertEqual(result['framing_stock_review']['sources']['rafters']['requires_splice_layout'],
                             rafters['requires_splice_layout'])
            self.assertIsNone(result['pending_quantities'][0]['quantity'])
            self.assertEqual(result['pending_quantities'][0]['component_ids'],['R1-S001'])
            rafters['source_version']=2
            with self.assertRaisesRegex(ValueError,'Rafter and roof'):self.run_import()

    def test_window_sill_stock_has_one_owner_and_changed_geometry_withholds_it(self):
        self.config['mapping_sha256']['sills']='sills'
        sills={'plan_sha256':'plan','mapping_sha256':'sills','measurement_version':3,
            'boards':[{'id':'B01','sku':'2412S2','length_ft':12}],
            'changed_measurements':[],'basis':'Single sill allowance','remaining':['Review assembly']}
        with patch('framing_stock_review.window_sills',return_value=sills):
            result=self.run_import()
            item=next(q for q in result['rows'][0]['assembly_inputs'] if q['id']=='framing-stock-sills-2412S2-12')
            self.assertEqual(item['quantity'],1);self.assertFalse(item['certified'])
            self.assertIsNone(result['rows'][0]['line_cost'])
            sills['boards']=[];sills['changed_measurements']=['EO01']
            changed=self.run_import()
            self.assertFalse(any(q['id'].startswith('framing-stock-sills-') for q in changed['rows'][0]['assembly_inputs']))
            self.assertEqual(changed['pending_quantities'][0]['component_ids'],['EO01'])
            sills['measurement_version']=4
            with self.assertRaisesRegex(ValueError,'Sill and estimate'):self.run_import()

    def test_below_window_stock_preserves_pending_gable_and_source_versions(self):
        self.config['mapping_sha256'].update(sills='sills',below_windows='lower')
        common={'plan_sha256':'plan','measurement_version':3,'basis':'Documented allowance','remaining':['Final framing detail']}
        sills={**common,'mapping_sha256':'sills','boards':[],'changed_measurements':[]}
        lower={**common,'mapping_sha256':'lower','sill_mapping_sha256':'sills','source_version':1,
            'boards':[{'id':'B1','sku':'PRECUT','length_ft':104.625/12}],
            'pending':[{'id':'gable','reason':'Needs wall datum'}]}
        with patch('framing_stock_review.window_sills',return_value=sills),patch('framing_stock_review.below_windows',return_value=lower):
            result=self.run_import()
            items=[q for q in result['rows'][0]['assembly_inputs'] if q['id'].startswith('framing-stock-below_windows-')]
            self.assertEqual(len(items),1);self.assertEqual(items[0]['quantity'],1)
            self.assertEqual(result['pending_quantities'][0]['component_ids'],['gable'])
            lower['boards']=[]
            self.assertFalse(any(q['id'].startswith('framing-stock-below_windows-') for q in self.run_import()['rows'][0]['assembly_inputs']))
            lower['sill_mapping_sha256']='changed'
            with self.assertRaisesRegex(ValueError,'source revisions'):self.run_import()

    def test_duplicates_priced_targets_and_incomplete_mapping_rejected(self):
        original=copy.deepcopy(self.draft);self.draft=self.run_import()
        with self.assertRaisesRegex(ValueError,'already imported'):self.run_import()
        del self.draft['framing_stock_review']
        with self.assertRaisesRegex(ValueError,'already assigned'):self.run_import()
        for values in [{'line_cost':1},{'draft_quantity':1},{'covered_by_package':'package'},
                       {'completion_status':'not_applicable_source_reviewed'}]:
            self.draft=copy.deepcopy(original);self.draft['rows'][0].update(values)
            with self.assertRaisesRegex(ValueError,'excluded, assigned or priced'):self.run_import()
        self.draft=copy.deepcopy(original);del self.config['mapping_sha256']['headers']
        with self.assertRaisesRegex(ValueError,'source mappings required'):self.run_import()


if __name__=='__main__':unittest.main()
