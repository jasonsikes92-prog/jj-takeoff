import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from estimate_readiness import readiness


class Readiness(unittest.TestCase):
    def setUp(self):
        row={'row_id':'1','excel_row':'1','name':'Work','parent':'Trade','cost_type':'SUBCONTRACTOR',
             'unit':'each','markup_pct':'7','completion_status':'evidence_in_progress'}
        self.template={'rows':[row]}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[copy.deepcopy(row)]}

    def test_partial_inputs_never_look_like_finished_quantity(self):
        self.draft['rows'][0]['assembly_inputs']=[{'id':'area'}]
        result=readiness(self.draft,self.template)
        self.assertIn('Only partial assembly inputs available',result['rows'][0]['issues'])
        self.assertIsNone(result['whole_house_total']);self.assertFalse(result['estimate_released'])

    def test_uncertified_source_scope_gaps_are_explained(self):
        row=self.draft['rows'][0]
        row.update(draft_quantity=960,line_cost=742.87,line_price=854.3,
                   certified=False,current_price_certified=True,price_evidence={'source':'test'},
                   quantity_sources=[{'remaining':['Field steps and bends unquantified.']},
                                     {'remaining':'Field steps and bends unquantified.'}])
        report=readiness(self.draft,self.template)
        self.assertEqual(report['rows'][0]['issues'],
                         ['Quantity and assembly certification outstanding',
                          'Quantity source needs resolution: Field steps and bends unquantified.'])
        self.assertEqual(report['rows_with_open_issues'],1)
        row['certified']=True
        self.assertEqual(readiness(self.draft,self.template)['rows'][0]['issues'],
                         ['Quantity source needs resolution: Field steps and bends unquantified.'])
        row['quantity_sources']=[]
        self.assertEqual(readiness(self.draft,self.template)['rows'][0]['issues'],[])

    def test_supplemental_source_scope_gaps_remain_visible(self):
        self.draft['additional_cost_rows']=[{
            **self.draft['rows'][0],'row_id':'extra','parent_row_id':'1',
            'quantity_sources':[{'remaining':['Final cuts unresolved.']}]}]
        result=readiness(self.draft,self.template)
        self.assertIn('Quantity source needs resolution: Final cuts unresolved.',
                      result['additional_cost_rows'][0]['issues'])
        self.draft['additional_cost_rows'][0]['certified']=True
        result=readiness(self.draft,self.template)
        self.assertIn('Quantity source needs resolution: Final cuts unresolved.',
                      result['additional_cost_rows'][0]['issues'])

    def test_missing_duplicate_and_changed_template_rows_detected(self):
        bad=copy.deepcopy(self.draft);bad['rows']=[]
        with self.assertRaises(ValueError):readiness(bad,self.template)
        bad=copy.deepcopy(self.draft);bad['rows']*=2
        with self.assertRaises(ValueError):readiness(bad,self.template)
        self.draft['rows'][0]['markup_pct']='15'
        self.assertIn('Template field changed: markup_pct',readiness(self.draft,self.template)['rows'][0]['issues'])

    def test_zero_is_known_but_not_automatically_certified(self):
        self.draft['rows'][0].update(draft_quantity=0,line_cost=0,line_price=0,price_evidence={'source':'test'})
        issues=readiness(self.draft,self.template)['rows'][0]['issues']
        self.assertNotIn('Quantity unresolved',issues);self.assertNotIn('Current line pricing unresolved',issues)
        self.assertIn('Quantity and assembly certification outstanding',issues)

    def test_assembly_tracks_children_without_hiding_child_gaps(self):
        assembly={**self.template['rows'][0],'row_id':'A','excel_row':'0','name':'Trade','cost_type':'ASSEMBLY'}
        self.template['rows'].insert(0,assembly)
        self.draft['rows'].insert(0,copy.deepcopy(assembly))
        report=readiness(self.draft,self.template)
        self.assertEqual(report['rows'][0]['role'],'assembly_rollup')
        self.assertEqual(report['rows'][0]['component_row_ids'],['1'])
        self.assertIn('Quantity unresolved',report['rows'][1]['issues'])
        self.draft['rows'][0]['line_cost']=100
        self.assertIn('Nonbillable row contains a price',readiness(self.draft,self.template)['rows'][0]['issues'])
        self.template['rows']=self.template['rows'][:1];self.draft['rows']=self.draft['rows'][:1]
        self.assertEqual(readiness(self.draft,self.template)['rows'][0]['role'],'template_role_unresolved')

    def test_invalid_quantities_and_broken_package_ownership_are_open(self):
        for value in (True,'NaN',-1):
            self.draft['rows'][0]['draft_quantity']=value
            self.assertIn('Quantity unresolved',readiness(self.draft,self.template)['rows'][0]['issues'])
        self.draft['rows'][0].update(covered_by_package='missing',line_cost=20)
        issues=readiness(self.draft,self.template)['rows'][0]['issues']
        self.assertIn('Package ownership is not supported by a priced package',issues)
        self.assertIn('Covered row has a duplicate price',issues)

    def test_supplemental_reference_keeps_purchase_gaps_visible(self):
        self.draft['rows'][0]['cost_owner_row_id']='purchase'
        extra={**self.draft['rows'][0],'row_id':'purchase','parent_row_id':'assembly','replaces_row_id':'1'}
        extra.pop('cost_owner_row_id')
        self.draft['additional_cost_rows']=[extra]
        report=readiness(self.draft,self.template)
        self.assertEqual(report['rows'][0]['role'],'cost_reference')
        self.assertEqual(report['rows'][0]['issues'],[])
        self.assertIn('Current line pricing unresolved',report['additional_cost_rows'][0]['issues'])
        self.draft['rows'][0]['line_cost']=0
        report=readiness(self.draft,self.template)
        self.assertIn('Reference row has a duplicate price',report['rows'][0]['issues'])
        self.draft['additional_cost_rows']=[]
        report=readiness(self.draft,self.template)
        self.assertIn('Supplemental purchase owner is missing or mismatched',report['rows'][0]['issues'])

    def test_shared_template_material_owner_and_duplicate_charge(self):
        owner=copy.deepcopy(self.draft['rows'][0])
        owner.update(row_id='purchase',excel_row='2',line_cost=100,line_price=115,
                     quantity_sources=[{'kind':'whole_tile_packages','included_row_ids':['1']}])
        self.template['rows'].append(copy.deepcopy(owner))
        self.draft['rows'].append(owner)
        self.draft['rows'][0]['cost_owner_row_id']='purchase'
        report=readiness(self.draft,self.template)
        self.assertEqual(report['rows'][0]['issues'],[])
        self.assertIn('Quantity and assembly certification outstanding',report['rows'][1]['issues'])
        self.draft['rows'][0]['line_cost']=0
        self.assertIn('Reference row has a duplicate price',readiness(self.draft,self.template)['rows'][0]['issues'])
        self.draft['rows'][0]['line_cost']=None
        owner['line_cost']=None
        self.assertIn('Shared material purchase owner is missing, unpriced or mismatched',
                      readiness(self.draft,self.template)['rows'][0]['issues'])
        owner['line_cost']=100
        owner['quantity_sources'][0]['included_row_ids']=[]
        self.assertIn('Shared material purchase owner is missing, unpriced or mismatched',
                      readiness(self.draft,self.template)['rows'][0]['issues'])

if __name__=='__main__':unittest.main()
