import copy
import unittest
from shapely.geometry import box
from shapely.affinity import translate
from floor_sundries import calculate_allowance,calculate_pooled_allowance


class FloorSundriesTests(unittest.TestCase):
    def products(self):
        specs={'board':(15,12.46),'screw_large':(750,40.47),'screw_small':(185,13.97),
            'bedding':(90,17.98),'setting':(34,22.97),'grout':(461,40.87),'tape':(150,10.01)}
        result={k:{'coverage':c,'price':p,'source_url':'https://supplier.example/product','observed_date':'2026-09-22'} for k,(c,p) in specs.items()}
        result['board']['dimensions_ft']=[3,5]
        return result

    def test_floor_edit_recalculates_separate_layers(self):
        p=self.products();original=copy.deepcopy(p)
        small=calculate_allowance(box(0,0,5,6),p)
        large=calculate_allowance(box(0,0,10,10),p)
        counts=lambda x:{r['component']:r['quantity'] for r in x['components']}
        self.assertEqual(counts(small)['setting'],1)
        self.assertEqual(counts(large)['setting'],3)
        self.assertEqual(counts(large)['bedding'],2)
        self.assertGreater(large['partial_pretax_cost'],small['partial_pretax_cost'])
        self.assertEqual(p,original)
        self.assertFalse(large['complete_sundries_scope'])

    def test_missing_price_or_source_is_not_zero(self):
        for key,value in [('price',None),('source_url','')]:
            p=self.products();p['setting'][key]=value
            with self.assertRaises(ValueError):calculate_allowance(box(0,0,5,6),p)

    def test_wrong_board_package_is_rejected(self):
        p=self.products();p['board']['coverage']=32
        with self.assertRaises(ValueError):calculate_allowance(box(0,0,5,6),p)

    def test_drawing_translation_does_not_add_mortar_at_package_boundary(self):
        p=self.products()
        original=calculate_allowance(box(0,0,3.4,10),p)
        shifted=calculate_allowance(translate(box(0,0,3.4,10),9.1,9.1),p)
        counts=lambda r:{x['component']:x['quantity'] for x in r['components']}
        self.assertEqual(counts(original)['setting'],1)
        self.assertEqual(counts(shifted),counts(original))
        larger=calculate_allowance(box(0,0,3.40001,10),p)
        self.assertEqual(counts(larger)['setting'],2)

    def test_shared_supplies_round_once_across_separate_rooms(self):
        products=self.products()
        fields=[{'id':'bath-a','geometry':box(0,0,5,6)},{'id':'bath-b','geometry':box(0,0,5,6)}]
        result=calculate_pooled_allowance(fields,products)
        counts={r['component']:r['quantity'] for r in result['components']}
        self.assertEqual(result['installed_area_sf'],60)
        self.assertEqual(counts['bedding'],1);self.assertEqual(counts['setting'],2)
        self.assertEqual(counts['grout'],1)
        self.assertLess(result['partial_pretax_cost'],result['separate_room_purchase_comparison_cost'])
        self.assertEqual(counts['board'],sum(r['calculation']['material_allowance']['candidate_sheets'] for r in result['fields']))
        self.assertGreaterEqual(counts['screw_large']*750+counts['screw_small']*185,result['pooled_fastener_allowance'])
        self.assertFalse(result['order_released']);self.assertFalse(result['complete_sundries_scope'])

    def test_single_room_pool_matches_existing_calculation_and_rejects_duplicate_ids(self):
        products=self.products();fields=[{'id':'bath','geometry':box(0,0,7,9)}]
        direct=calculate_allowance(fields[0]['geometry'],products)
        pooled=calculate_pooled_allowance(fields,products)
        self.assertEqual(pooled['components'],direct['components'])
        self.assertEqual(pooled['partial_pretax_cost'],direct['partial_pretax_cost'])
        with self.assertRaises(ValueError):calculate_pooled_allowance(fields*2,products)
        with self.assertRaises(ValueError):calculate_pooled_allowance([],products)
