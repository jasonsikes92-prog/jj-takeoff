import copy
import sys
import unittest
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from header_cut_scope import calculate, estimate_replacements


class HeaderCutScope(unittest.TestCase):
    def setUp(self):
        self.headers=[{'id':'H1','pieces':2,'length_inches':35},
                      {'id':'H2','pieces':2,'length_inches':90},
                      {'id':'H3','pieces':2,'length_inches':45}]
        self.study={'plan_sha256':'plan','pieces':[
            {'id':f'{h["id"]}-{n}','header_id':h['id'],'cut_inches':h['length_inches'],
             'sku':'2X6-16','stock_length_ft':16} for h in self.headers[:2] for n in (1,2)],
            'unresolved_material_or_stock':[],
            'withheld_conflicting_headers':[{'header':self.headers[2],'reason':'Short fireplace header'}],
            'kerf_inches_assumed':.125,'end_trim_allowance_inches':0,
            'end_trim_basis':'Fixture factory ends','remaining':['Unresolved fireplace and gable']}
        self.baseline={'plan_sha256':'plan','measurement_version':1,
            'opening_geometry_sha256':{'O1':'geom1','O2':'geom2','O3':'geom3','G':None},
            'openings':[{'opening_id':f'O{i}','header_id':h['id'],
                'header_cut_length_inches':h['length_inches'],'status':'end_support_length_unverified'}
                for i,h in enumerate(self.headers,1)]+[{'opening_id':'G','header_id':None}]}
        self.baseline['openings'][2]['status']='header_shorter_than_opening_reference'
        self.current=copy.deepcopy(self.baseline)
    def calculate(self):return calculate(self.headers,self.study,self.baseline,self.current)

    def test_baseline_preserves_cuts_and_source_exceptions_without_order_release(self):
        before=copy.deepcopy((self.headers,self.study,self.baseline,self.current))
        result=self.calculate()
        self.assertEqual(result['pieces'],self.study['pieces'])
        self.assertEqual(result['candidate_board_counts'],{'2X6-16':2})
        self.assertEqual(result['source_piece_count'],6)
        self.assertEqual(result['additional_missing_headers'],['G'])
        self.assertEqual(result['withheld_source_headers'],self.study['withheld_conflicting_headers'])
        self.assertIsNone(result['purchase_quantity']);self.assertFalse(result['order_released'])
        self.assertEqual((self.headers,self.study,self.baseline,self.current),before)

    def test_changed_opening_withholds_only_its_pieces_reallocates_and_restores(self):
        before=self.calculate()
        self.current['opening_geometry_sha256']['O1']='widened'
        self.current['measurement_version']=2
        after=self.calculate()
        self.assertEqual([p['id'] for p in after['pieces']],['H2-1','H2-2'])
        self.assertEqual(after['candidate_board_counts'],{'2X6-16':1})
        self.assertEqual([x['piece']['id'] for x in after['withheld_changed_or_conflicting_cuts']],['H1-1','H1-2'])
        self.current=copy.deepcopy(self.baseline)
        self.assertEqual(self.calculate(),before)

    def test_same_width_relocation_still_requires_header_review(self):
        self.current['opening_geometry_sha256']['O1']='relocated'
        result=self.calculate()
        self.assertEqual(result['candidate_cut_piece_count'],2)
        self.assertIn('Opening geometry changed',result['header_issues']['H1'][0])

    def test_missing_geometry_short_header_and_supplier_conflict_never_use_old_cuts(self):
        for mutation in ('missing','short','supplier'):
            self.current=copy.deepcopy(self.baseline)
            if mutation=='missing':self.current['opening_geometry_sha256']['O1']=None
            elif mutation=='short':self.current['openings'][0]['status']='header_shorter_than_opening_reference'
            else:self.current['openings'][0]['supplier_alternative']={'flags':['supplier_stock_shorter_than_plan_cut']}
            with self.subTest(mutation=mutation):self.assertEqual(self.calculate()['candidate_cut_piece_count'],2)

    def test_supplier_alternative_with_sufficient_length_does_not_release_plan_material(self):
        self.current['openings'][0]['supplier_alternative']={
            'member_id':'BM1','product':'LVL','flags':[],
            'stock_length_inches':48,'stock_minus_plan_cut_inches':13,
            'revision_matches_plan_verified':False,'adopted_as_replacement':False}
        result=self.calculate()
        self.assertEqual([p['id'] for p in result['pieces']],['H2-1','H2-2'])
        self.assertEqual(result['source_piece_count'],6)
        self.assertIn('Supplier alternative requires material and revision reconciliation',result['header_issues']['H1'])
        self.assertIsNone(result['purchase_quantity'])

    def test_adopted_supplier_cannot_reuse_old_plan_cuts(self):
        self.current['openings'][0]['supplier_alternative']={
            'member_id':'BM1','product':'LVL','flags':[],
            'revision_matches_plan_verified':True,'adopted_as_replacement':True}
        self.assertEqual(self.calculate()['candidate_cut_piece_count'],2)

    def test_missing_duplicate_or_reassigned_header_mapping_rejected(self):
        for mutation in ('missing','duplicate','reassigned'):
            self.current=copy.deepcopy(self.baseline)
            if mutation=='missing':self.current['openings'].pop(0)
            elif mutation=='duplicate':self.current['openings'].append(self.current['openings'][0])
            else:self.current['openings'][0]['header_id']='H2'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.calculate()

    def test_lost_duplicated_changed_or_double_classified_source_pieces_rejected(self):
        original=copy.deepcopy(self.study)
        for mutation in ('missing','duplicate','length','double_classified'):
            self.study=copy.deepcopy(original)
            if mutation=='missing':self.study['pieces'].pop()
            elif mutation=='duplicate':self.study['pieces'].append(self.study['pieces'][0])
            elif mutation=='length':self.study['pieces'][0]['cut_inches']=36
            else:self.study['unresolved_material_or_stock'].append(self.headers[0])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.calculate()

    def test_wrong_drawing_and_changed_inventory_length_rejected(self):
        self.current['plan_sha256']='other'
        with self.assertRaises(ValueError):self.calculate()
        self.current=copy.deepcopy(self.baseline);self.headers[0]['length_inches']=36
        with self.assertRaises(ValueError):self.calculate()

    def test_unresolved_material_is_retained_instead_of_disappearing_or_becoming_zero(self):
        self.study['pieces']=self.study['pieces'][:2]
        self.study['unresolved_material_or_stock']=[self.headers[1]]
        result=self.calculate()
        self.assertEqual(result['source_piece_count'],6)
        self.assertEqual(result['unresolved_material_or_stock'],[self.headers[1]])
        self.assertEqual(result['candidate_cut_piece_count'],2)

    def replacement(self):
        self.headers[2]['material_label']='2X6'
        self.study['stock_scenarios']={'2X6':{'sku':'2X6-16','length_ft':16}}
        self.current['openings'][2]['product_rough_opening_width_inches']=48
        return {'plan_sha256':'plan','header_id':'H3','opening_id':'O3','original_cut_inches':45,
            'pieces':2,'rough_opening_width_inches':48,'end_support_allowance_inches':1.5,
            'sku':'2X6-16','stock_length_ft':16,'opening_geometry_sha256':'geom3',
            'status':'documented_estimating_allowance','basis':'Manufacturer width plus estimating end supports'}

    def test_replacement_cut_count_packing_and_original_conflict_preserved(self):
        record=self.replacement();original=self.calculate();baseline=copy.deepcopy(original)
        r=estimate_replacements(original,self.study,self.current,[record])
        self.assertEqual(original,baseline)
        self.assertEqual(r['candidate_cut_piece_count'],6)
        self.assertEqual([p['cut_inches'] for p in r['pieces'] if p.get('estimating_replacement')],[51,51])
        self.assertEqual(r['withheld_source_headers'],original['withheld_source_headers'])
        self.assertIn('H3',r['header_issues']);self.assertFalse(r['order_released'])
        self.assertIsNone(r['purchase_quantity'])
        self.assertEqual(Counter(c['piece_id'] for b in r['boards'] for c in b['cuts']),Counter(p['id'] for p in r['pieces']))

    def test_replacement_withheld_on_relocation_product_change_or_overlength(self):
        record=self.replacement();original=self.calculate();baseline=copy.deepcopy(self.current)
        for kind in ('relocated','product','supplier','long'):
            self.current=copy.deepcopy(baseline);candidate=copy.deepcopy(record)
            if kind=='relocated':self.current['opening_geometry_sha256']['O3']='changed'
            elif kind=='product':self.current['openings'][2]['product_rough_opening_width_inches']=49
            elif kind=='supplier':self.current['openings'][2]['supplier_alternative']={'id':'new'}
            else:
                candidate['rough_opening_width_inches']=200
                self.current['openings'][2]['product_rough_opening_width_inches']=200
            r=estimate_replacements(original,self.study,self.current,[candidate])
            self.assertEqual(r['pieces'],original['pieces']);self.assertEqual(len(r['withheld_estimating_replacements']),1)
        self.current=baseline
        self.assertEqual(len(estimate_replacements(original,self.study,self.current,[record])['estimating_replacements']),1)

    def test_replacement_rejects_invalid_count_duplicate_source_and_stock_substitution(self):
        record=self.replacement();original=self.calculate()
        for change in ({'pieces':3},{'pieces':True},{'original_cut_inches':44},{'header_id':'H1'},
                       {'rough_opening_width_inches':float('nan')},{'end_support_allowance_inches':0},
                       {'sku':'other'},{'stock_length_ft':12},{'plan_sha256':'other'},{'basis':''}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                estimate_replacements(original,self.study,self.current,[{**record,**change}])
        with self.assertRaises(ValueError):estimate_replacements(original,self.study,self.current,[record,record])


if __name__=='__main__':unittest.main()
