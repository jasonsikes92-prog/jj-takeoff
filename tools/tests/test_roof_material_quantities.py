import copy
import unittest
from bid_comparison import scope_digest
from roof_material_quantities import calculate


class RoofMaterialQuantities(unittest.TestCase):
    def setUp(self):
        self.scope={'plan_sha256':'plan','measurement_version':1,
            'items':[{'id':'a','surface':'roof','reference_unit':'SF','reference_quantity':40},
                {'id':'b','surface':'roof','reference_unit':'SF','reference_quantity':60}],
            'source_exceptions':{'coverage':{'missing_projected_sf':2},'inferred_pitch_face_ids':['a']}}
        self.scope['scope_sha256']=scope_digest(self.scope)
        self.group={'id':'field','product_id':'specified-color-SKU','face_ids':['a','b'],
            'roofing_system':'shingle','purchase_unit':'bundle','waste_percent':0,
            'package_coverage':{'area_sf':100,'bundles':3},
            'selection_source_ref':'selection p1','waste_source_ref':'review p1','coverage_source_ref':'label p1'}
        self.review={'plan_sha256':'plan','scope_sha256':self.scope['scope_sha256'],
            'reviewer':'test reviewer','basis':'Synthetic arithmetic example','groups':[self.group]}

    def test_missing_selections_keep_every_face_pending(self):
        result=calculate(self.scope)
        self.assertEqual(result['groups'],[])
        self.assertEqual(result['pending_face_ids'],['a','b'])
        self.assertIsNone(result['whole_roof_order_quantity'])

    def test_product_is_rounded_once_after_combining_its_faces(self):
        row=calculate(self.scope,self.review)['groups'][0]
        self.assertEqual(row['purchase_quantity'],3)
        self.assertEqual(row['purchased_coverage_sf'],100)
        self.assertEqual(row['rounding_surplus_sf'],0)

    def test_waste_once_and_purchase_coverage_do_not_become_billing_approval(self):
        self.group['waste_percent']=20
        row=calculate(self.scope,self.review)['groups'][0]
        self.assertEqual(row['required_with_waste_sf'],120)
        self.assertEqual(row['purchase_quantity'],4)
        self.assertEqual(row['measured_roofing_squares'],1)
        self.assertEqual(row['waste_inclusive_roofing_squares'],1.2)
        self.assertAlmostEqual(row['purchased_roofing_squares'],4/3)
        for key in ('unit_price','line_cost','billing_basis'):self.assertIsNone(row[key])

    def test_decimal_coverage_at_exact_pack_boundary_does_not_buy_extra_bundle(self):
        self.group['package_coverage']={'area_sf':'33.333333','bundles':1}
        self.scope['items']=[{'id':'a','surface':'roof','reference_unit':'SF','reference_quantity':'99.999999'}]
        self.scope['scope_sha256']=scope_digest(self.scope)
        self.review['scope_sha256']=self.scope['scope_sha256'];self.group['face_ids']=['a']
        self.assertEqual(calculate(self.scope,self.review)['groups'][0]['purchase_quantity'],3)

    def test_partial_allocation_preserves_other_faces_as_unknown(self):
        self.group['face_ids']=['a']
        result=calculate(self.scope,self.review)
        self.assertEqual(result['pending_face_ids'],['b'])
        self.assertFalse(result['ready_to_order']);self.assertFalse(result['scope_coverage_certified'])
        self.assertEqual(result['source_exceptions'],self.scope['source_exceptions'])

    def test_linear_edges_cannot_be_counted_as_shingle_area(self):
        self.scope['items'].append({'id':'edge','surface':'roof_edge','reference_unit':'LF',
            'reference_quantity':200})
        self.scope['scope_sha256']=scope_digest(self.scope)
        self.review['scope_sha256']=self.scope['scope_sha256']
        self.assertEqual(calculate(self.scope)['pending_face_ids'],['a','b'])
        result=calculate(self.scope,self.review)
        self.assertEqual(result['pending_face_ids'],[])
        self.assertEqual(result['groups'][0]['measured_surface_sf'],100)
        self.assertEqual(result['groups'][0]['purchase_quantity'],3)
        self.group['face_ids']=['edge']
        with self.assertRaisesRegex(ValueError,'known roof faces'):calculate(self.scope,self.review)

    def test_missing_or_incompatible_dimensions_are_rejected(self):
        for surface,unit in ((None,None),('roof','LF'),('roof_edge','SF'),('wall','SF')):
            with self.subTest(surface=surface,unit=unit):
                scope=copy.deepcopy(self.scope)
                scope['items'][0].update(surface=surface,reference_unit=unit)
                scope['scope_sha256']=scope_digest(scope)
                with self.assertRaisesRegex(ValueError,'roof faces in SF'):calculate(scope)

    def test_duplicate_scope_ids_are_rejected(self):
        self.scope['items'].append(copy.deepcopy(self.scope['items'][0]))
        self.scope['scope_sha256']=scope_digest(self.scope)
        with self.assertRaisesRegex(ValueError,'unique'):calculate(self.scope)

    def test_changed_revision_withholds_previously_reviewed_purchases(self):
        self.scope['measurement_version']=2;self.scope['scope_sha256']=scope_digest(self.scope)
        result=calculate(self.scope,self.review)
        self.assertEqual(result['groups'],[]);self.assertIn('withheld',result['status'])

    def test_tampered_scope_is_not_accepted(self):
        self.scope['items'][0]['reference_quantity']=400
        with self.assertRaisesRegex(ValueError,'fingerprint'):calculate(self.scope,self.review)

    def test_duplicate_or_unknown_face_rejected(self):
        for ids in (['a','a'],['missing']):
            self.group['face_ids']=ids
            with self.assertRaises(ValueError):calculate(self.scope,self.review)

    def test_split_product_and_overlapping_allocations_are_rejected(self):
        second=copy.deepcopy(self.group);second['id']='second'
        self.review['groups'].append(second)
        with self.assertRaises(ValueError):calculate(self.scope,self.review)
        second['product_id']='other-SKU'
        with self.assertRaises(ValueError):calculate(self.scope,self.review)

    def test_no_implicit_waste_or_coverage_and_no_nonfinite_values(self):
        for value in (-1,True,'NaN','Infinity',None):
            self.group['waste_percent']=value
            with self.assertRaises(ValueError):calculate(self.scope,self.review)
        self.group['waste_percent']=0
        for value in (0,-1,True,'NaN'):
            self.group['package_coverage']['area_sf']=value
            with self.assertRaises(ValueError):calculate(self.scope,self.review)

    def test_metal_area_does_not_produce_a_panel_cut_list(self):
        self.group.update(roofing_system='metal',purchase_unit='panel')
        with self.assertRaisesRegex(ValueError,'panel cut list'):calculate(self.scope,self.review)

    def test_inputs_not_mutated_and_missing_source_is_rejected(self):
        before=copy.deepcopy((self.scope,self.review));calculate(self.scope,self.review)
        self.assertEqual((self.scope,self.review),before)
        self.group['coverage_source_ref']=''
        with self.assertRaises(ValueError):calculate(self.scope,self.review)


if __name__=='__main__':unittest.main()
