import copy
import tempfile
import unittest
from pathlib import Path
from quote_pricing_review import review_pricing
from bid_comparison import compare_quotes,scope_digest,required_scope_items
from quote_intake import intake_quote
import json


class QuotePricing(unittest.TestCase):
    def setUp(self):
        self.scope={'plan_sha256':'plan','measurement_version':1,'requires_pricing_basis_review':True,
            'items':[{'id':'wall','label':'Walls','reference_unit':'gross wall SF','reference_quantity':400},
                     {'id':'ceiling','label':'Ceiling','reference_unit':'ceiling surface SF','reference_quantity':100}],
            'scope_requirements':[{'id':'basis','request':'Confirm pricing basis'}]}
        self.line={'id':'price','scope_ids':['wall','ceiling'],'work':'complete','basis':'wall_ceiling_sf',
            'quantity_source':'measured_reference','quantity':500,'unit_rate':'2.50','amount':'1250.00','source_ref':'p1 line1'}
        self.quote={'total':'1250.00','pricing_lines':[self.line],
            'scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'p1'} for i in required_scope_items(self.scope)]}

    def test_rate_math_and_separate_reference_units_pass_without_purchase(self):
        result=review_pricing(self.scope,self.quote)
        self.assertEqual(result['issues'],[]);self.assertEqual(result['charged_line_total'],'1250.00')
        self.assertFalse(result['purchase_authorized'])

    def test_installed_scope_requires_materials_and_labor_per_surface(self):
        self.scope['required_work']='complete'
        self.line['work']='materials'
        issues=review_pricing(self.scope,self.quote)['issues']
        self.assertTrue(any('wall: required labor is missing' in i for i in issues))
        self.assertTrue(any('ceiling: required labor is missing' in i for i in issues))
        self.line['work']='labor'
        self.assertTrue(any('required materials is missing' in i for i in review_pricing(self.scope,self.quote)['issues']))
        self.line['work']='complete'
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])

    def test_split_work_coverage_cannot_hide_missing_installation_on_one_surface(self):
        self.scope['required_work']='complete'
        self.line.update(work='materials',basis='lump_sum',quantity=None,unit_rate=None,amount='500')
        labor={**self.line,'id':'labor','work':'labor','amount':'750','scope_ids':['wall']}
        self.quote['pricing_lines'].append(labor)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],['ceiling: required labor is missing from the priced lines'])
        labor['scope_ids'].append('ceiling')
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])

    def test_supply_only_scope_does_not_require_labor(self):
        self.scope['required_work']='materials';self.line['work']='materials'
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])
        self.scope['required_work']='unknown'
        with self.assertRaisesRegex(ValueError,'Required work'):
            review_pricing(self.scope,self.quote)

    def test_floor_basis_cannot_reuse_wall_area_but_reviewed_floor_basis_is_allowed(self):
        self.line['basis']='floor_sf'
        self.assertTrue(any('unit does not match' in i for i in review_pricing(self.scope,self.quote)['issues']))
        self.line.update(quantity_source='quoted_basis',quantity_basis_source_ref='p2 framed floor schedule',quantity_basis_reviewed=True)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])
        self.line['quantity_basis_reviewed']=False
        self.assertTrue(review_pricing(self.scope,self.quote)['issues'])

    def test_unknown_references_and_wrong_multiplication_are_flagged(self):
        self.scope['items'][0]['reference_quantity']=None
        self.assertTrue(any('coverage is incomplete' in i for i in review_pricing(self.scope,self.quote)['issues']))
        self.line['amount']='1251'
        self.assertTrue(any('times rate' in i for i in review_pricing(self.scope,self.quote)['issues']))
        self.assertTrue(any('package total' in i for i in review_pricing(self.scope,self.quote)['issues']))

    def test_package_components_not_added_twice_when_explicitly_included(self):
        self.line.update(basis='lump_sum',quantity=None,unit_rate=None)
        component={'id':'detail','scope_ids':['wall'],'work':'materials','basis':'lump_sum',
            'amount':'300','source_ref':'p1 line2','included_in':'price'}
        self.quote['pricing_lines'].append(component)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])
        component.pop('included_in');self.quote['total']='1550'
        self.assertTrue(any('overlapping charges' in i for i in review_pricing(self.scope,self.quote)['issues']))

    def test_separate_material_and_labor_prices_are_not_duplicate_scope(self):
        self.line.update(work='materials',basis='lump_sum',quantity=None,unit_rate=None,amount='500')
        labor={**self.line,'id':'labor','work':'labor','amount':'750'}
        self.quote['pricing_lines'].append(labor)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])

    def test_missing_pricing_invalid_numbers_and_package_cycles_do_not_pass(self):
        self.assertTrue(review_pricing(self.scope,{})['issues'])
        for amount in (True,'NaN',-1):
            q=copy.deepcopy(self.quote);q['pricing_lines'][0]['amount']=amount
            with self.assertRaises(ValueError):review_pricing(self.scope,q)
        self.line['included_in']='price'
        self.assertIsNone(review_pricing(self.scope,self.quote)['charged_line_total'])

    def test_scope_fingerprint_is_canonical_and_content_changes_cannot_hide_behind_it(self):
        original=scope_digest(self.scope);self.scope['scope_sha256']=original
        self.assertEqual(scope_digest(self.scope),original)
        self.scope['items'][0]['reference_quantity']=401
        self.assertNotEqual(scope_digest(self.scope),original)

    def test_intake_and_comparison_require_questions_and_pricing_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);document=root/'synthetic.txt';document.write_text('Synthetic test only\nTotal: $1,250.00')
            target=root/'intake';intake_quote(document,target,self.scope,'test','Synthetic supplier')
            intake=json.loads((target/'quotes.json').read_text())[0]
            self.assertEqual(len(intake['scope_items']),3)
            q={**intake,**self.quote,'reviewed':True,'reviewed_scope_sha256':scope_digest(self.scope),
                'date':'2026-09-19','valid_through':'2026-09-30','currency':'USD','evidence_kind':'current_subcontractor_quote'}
            result=compare_quotes(self.scope,[q],'2026-09-19',target)['quotes'][0]
            self.assertTrue(result['same_scope_current_quote'])
            q['scope_items']=q['scope_items'][:2]
            self.assertFalse(compare_quotes(self.scope,[q],'2026-09-19',target)['quotes'][0]['same_scope_current_quote'])
            q['scope_items']=self.quote['scope_items'];q.pop('pricing_lines')
            self.assertFalse(compare_quotes(self.scope,[q],'2026-09-19',target)['quotes'][0]['same_scope_current_quote'])


class DrywallAdjustmentPricing(unittest.TestCase):
    def setUp(self):
        self.scope={'requires_pricing_basis_review':True,
            'estimating_practice':{'deduct_window_door_openings':False,'billing_waste_percent':0},
            'items':[{'id':'wall','label':'Walls','reference_unit':'gross wall SF','reference_quantity':400}]}
        self.adjustments={'reviewed':True,'source_ref':'Synthetic measurement clause',
            'basis':'billing_quantity','deduct_window_door_openings':False,'billing_waste_percent':0}
        self.line={'id':'labor','scope_ids':['wall'],'work':'labor','basis':'wall_sf',
            'quantity_source':'measured_reference','quantity':400,'unit_rate':2,'amount':800,
            'source_ref':'Synthetic price line','measurement_adjustments':self.adjustments}
        self.quote={'total':800,'pricing_lines':[self.line],'scope_items':[{'scope_id':'wall','status':'included'}]}

    def issues(self):return review_pricing(self.scope,self.quote)['issues']

    def test_matching_zero_and_false_are_preserved_without_changing_quote(self):
        before=copy.deepcopy(self.quote)
        self.assertEqual(self.issues(),[])
        self.assertEqual(self.quote,before)
        self.line.pop('measurement_adjustments')
        self.assertTrue(any('source-linked review' in i for i in self.issues()))

    def test_mismatches_flag_even_when_arithmetic_and_total_agree(self):
        self.adjustments.update(deduct_window_door_openings=True,billing_waste_percent=10)
        issues=self.issues()
        self.assertTrue(any('deductions differ' in i for i in issues))
        self.assertTrue(any('billing waste (10%) differs' in i for i in issues))
        self.assertTrue(any('unadjusted measured reference' in i for i in issues))
        self.assertFalse(any('times rate' in i or 'package total' in i for i in issues))

    def test_unknown_and_unreviewed_values_are_not_matches(self):
        for field,value in [('reviewed',False),('source_ref',''),('basis',None),
                ('deduct_window_door_openings',None),('billing_waste_percent',None)]:
            with self.subTest(field=field):
                original=copy.deepcopy(self.adjustments);self.adjustments[field]=value
                self.assertTrue(self.issues());self.adjustments.clear();self.adjustments.update(original)
        self.scope['estimating_practice']['billing_waste_percent']=None
        self.assertTrue(any('job billing-waste practice is unresolved' in i for i in self.issues()))

    def test_project_override_requires_its_own_quoted_quantity_basis(self):
        self.scope['estimating_practice']['billing_waste_percent']=5
        self.adjustments['billing_waste_percent']='5.0'
        self.assertTrue(any('unadjusted measured reference' in i for i in self.issues()))
        self.line.update(quantity=420,amount=840,quantity_source='quoted_basis',
            quantity_basis_reviewed=True,quantity_basis_source_ref='Synthetic 400 gross SF plus 5 percent billing waste')
        self.quote['total']=840
        self.assertEqual(self.issues(),[])

    def test_fixed_package_needs_explicit_source_basis_and_no_conflicting_values(self):
        self.line['measurement_adjustments']={'reviewed':True,'source_ref':'Synthetic fixed-price clause',
            'basis':'fixed_package','reason':'Fixed complete package; no measurement-based adjustments'}
        self.assertTrue(any('fixed-package' in i for i in self.issues()))
        self.line.update(basis='lump_sum',quantity=None,unit_rate=None)
        self.assertEqual(self.issues(),[])
        self.line['measurement_adjustments']['billing_waste_percent']=0
        self.assertTrue(any('conflicting adjustment values' in i for i in self.issues()))

    def test_included_component_uses_parent_but_separate_charges_each_need_review(self):
        self.line['work']='complete'
        component={'id':'material','scope_ids':['wall'],'work':'materials','basis':'lump_sum',
            'amount':100,'source_ref':'Synthetic included detail','included_in':'labor'}
        self.quote['pricing_lines'].append(component)
        self.assertEqual(self.issues(),[])
        component.pop('included_in');self.line['work']='labor';self.quote['total']=900
        self.assertTrue(any('material: opening deductions' in i for i in self.issues()))

    def test_invalid_adjustment_types_reject(self):
        for field,value in [('deduct_window_door_openings','false'),('deduct_window_door_openings',0),
                ('billing_waste_percent',True),('billing_waste_percent',-1),('billing_waste_percent','NaN')]:
            with self.subTest(field=field,value=value):
                original=copy.deepcopy(self.adjustments);self.adjustments[field]=value
                with self.assertRaises(ValueError):self.issues()
                self.adjustments.clear();self.adjustments.update(original)


class RoofQuotePricing(unittest.TestCase):
    def setUp(self):
        self.scope={'requires_pricing_basis_review':True,'items':[
            {'id':'roof','surface':'roof','reference_unit':'SF','reference_quantity':2000}]}
        self.line={'id':'roof-price','scope_ids':['roof'],'work':'complete','basis':'roofing_square',
            'quantity_source':'measured_reference','quantity':20,'unit_rate':100,'amount':2000,
            'source_ref':'Synthetic fixture p1'}
        self.quote={'total':2000,'pricing_lines':[self.line],
            'scope_items':[{'scope_id':'roof','status':'included'}]}

    def test_roofing_square_converts_100_sf_without_changing_quote(self):
        before=copy.deepcopy(self.quote)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])
        self.assertEqual(self.quote,before)
        self.line.update(basis='roof_sf',quantity=2000,unit_rate=1)
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])

    def test_hundredfold_unit_error_is_flagged_even_when_arithmetic_matches(self):
        self.line.update(quantity=2000,amount=200000);self.quote['total']=200000
        issues=review_pricing(self.scope,self.quote)['issues']
        self.assertTrue(any('differs from the measured reference' in i for i in issues))
        self.assertFalse(any('times rate' in i for i in issues))

    def test_other_square_footage_is_not_a_roof_reference(self):
        self.scope['items'][0]['surface']='floor'
        self.assertTrue(any('unit does not match' in i for i in review_pricing(self.scope,self.quote)['issues']))

    def test_measured_edge_price_uses_linear_feet_and_checks_quantity(self):
        self.scope['items']=[{'id':'eave','surface':'roof_edge','reference_unit':'LF','reference_quantity':80},
            {'id':'rake','surface':'roof_edge','reference_unit':'LF','reference_quantity':120}]
        self.line.update(scope_ids=['eave','rake'],basis='linear_foot',quantity=200,unit_rate=10)
        self.quote['scope_items']=[{'scope_id':i,'status':'included'} for i in ('eave','rake')]
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])
        self.line.update(quantity=201,amount=2010);self.quote['total']=2010
        self.assertTrue(any('differs from the measured reference' in i
            for i in review_pricing(self.scope,self.quote)['issues']))
        self.scope['items'][1]['reference_quantity']=None
        self.assertTrue(any('coverage is incomplete' in i
            for i in review_pricing(self.scope,self.quote)['issues']))

    def test_mixed_area_and_length_cannot_share_a_measured_billing_quantity(self):
        self.scope['items'].append({'id':'edge','surface':'roof_edge','reference_unit':'LF','reference_quantity':100})
        self.line['scope_ids']=['roof','edge']
        for basis in ('linear_foot','roof_sf','roofing_square'):
            with self.subTest(basis=basis):
                self.line['basis']=basis
                self.assertTrue(any('unit does not match' in i
                    for i in review_pricing(self.scope,self.quote)['issues']))

    def test_bundles_panels_and_linear_feet_require_separate_quoted_basis(self):
        for basis in ('shingle_bundle','metal_panel','linear_foot'):
            self.line.update(basis=basis,quantity_source='measured_reference')
            self.assertTrue(any('unit does not match' in i for i in review_pricing(self.scope,self.quote)['issues']))
            self.line.update(quantity_source='quoted_basis',quantity_basis_reviewed=True,
                quantity_basis_source_ref='Synthetic package coverage or cut-list fixture')
            self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])

    def test_waste_inclusive_roof_squares_are_not_mislabeled_as_measured_area(self):
        self.line.update(quantity=24,amount=2400);self.quote['total']=2400
        self.assertTrue(any('differs from the measured reference' in i for i in review_pricing(self.scope,self.quote)['issues']))
        self.line.update(quantity_source='quoted_basis',quantity_basis_reviewed=True,
            quantity_basis_source_ref='Synthetic fixture: 20 measured squares plus 20 percent waste')
        self.assertEqual(review_pricing(self.scope,self.quote)['issues'],[])


if __name__=='__main__':unittest.main()
