import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup, geometry_digest


class QuantityRollup(unittest.TestCase):
    def setUp(self):
        area={'kind':'area','points':[[0,0],[101,0],[101,100],[0,100]],
            'width_pt':500,'height_pt':500,'points_per_foot':10}
        self.state={'plan_sha256':'drawing','version':1,'measurements':{'a':area,'b':copy.deepcopy(area)}}
        self.rule={'id':'roof','label':'Roof gross area','measurement_ids':['a','b'],'unit':'SF',
            'rounding':'whole_up','template_rows':['104'],'use':'template_quantity','basis':'Gross area','remaining':['Waste and layout']}
        self.rules={'plan_sha256':'drawing','rules':[self.rule]}
    def test_round_after_sum_and_apply_slope(self):
        self.state['measurements']['a']['surface_factor']=2**0.5
        value=rollup(self.state,self.rules)['quantities'][0]
        self.assertAlmostEqual(value['measured_quantity'],101*2**0.5+101)
        self.assertEqual(value['quantity'],244)
        self.assertIsNone(value['current_price']);self.assertFalse(value['order_released'])
    def test_edit_changes_quantity_without_mutating_other_measurements(self):
        before=copy.deepcopy(self.state['measurements']['b'])
        self.state['measurements']['a']['points'][1][0]=201
        self.state['measurements']['a']['points'][2][0]=201
        self.state['version']=2
        value=rollup(self.state,self.rules)
        self.assertEqual(value['quantities'][0]['quantity'],302)
        self.assertEqual(value['measurement_version'],2)
        self.assertEqual(self.state['measurements']['b'],before)
    def test_missing_duplicate_wrong_plan_and_mixed_units_refused(self):
        for change in ('missing','duplicate','plan','unit'):
            rules=copy.deepcopy(self.rules)
            if change=='missing':rules['rules'][0]['measurement_ids']=['absent']
            if change=='duplicate':rules['rules'][0]['measurement_ids']=['a','a']
            if change=='plan':rules['plan_sha256']='another'
            if change=='unit':rules['rules'][0]['unit']='LF'
            with self.assertRaises(ValueError):rollup(self.state,rules)
    def test_unchanged_integer_not_rounded_twice(self):
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],202)

    def test_sourced_waste_applied_once_before_rounding(self):
        self.rule.update(waste_percent=20,waste_source='Owner answer 3')
        self.state['measurements']['a']['surface_factor']=2**0.5
        value=rollup(self.state,self.rules)['quantities'][0]
        self.assertAlmostEqual(value['measured_quantity'],101*2**0.5+101)
        self.assertAlmostEqual(value['waste_adjusted_quantity'],(101*2**0.5+101)*1.2)
        self.assertEqual(value['quantity'],293)
        self.assertEqual(value['waste_percent'],20)
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0],value)

    def test_purchase_packs_round_once_and_recalculate_after_edit(self):
        self.rule.update(waste_percent=20,waste_source='Owner answer',purchase_pack={
            'coverage_quantity':100,'packs_per_coverage':3,'coverage_unit':'SF',
            'unit':'bundle','product':'HDZ','source':'Manufacturer specification'})
        before=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(before['purchase_pack']['quantity'],8)
        self.assertEqual(before['quantity'],243)
        self.state['measurements']['a']['points'][1][0]=201
        self.state['measurements']['a']['points'][2][0]=201
        after=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(after['purchase_pack']['quantity'],11)
        self.assertFalse(after['purchase_pack']['order_released'])

    def test_pack_uses_unrounded_area_and_exact_coverage_multiple(self):
        self.rule['purchase_pack']={'coverage_quantity':100,'packs_per_coverage':3,
            'coverage_unit':'SF','unit':'bundle','product':'HDZ','source':'Manufacturer'}
        for width,expected in [(100/3,2),(100,6)]:
            for item in self.state['measurements'].values():
                item['points']=[[0,0],[width,0],[width,100],[0,100]]
            value=rollup(self.state,self.rules)['quantities'][0]
            self.assertEqual(value['purchase_pack']['quantity'],expected)

    def test_invalid_or_unsourced_pack_refused(self):
        valid={'coverage_quantity':100,'packs_per_coverage':3,'coverage_unit':'SF',
            'unit':'bundle','product':'HDZ','source':'Manufacturer'}
        for field,value in [('coverage_quantity',0),('coverage_quantity',float('nan')),
                            ('packs_per_coverage',True),('packs_per_coverage',1.5),
                            ('coverage_unit','LF'),('source',''),('product',None)]:
            self.rule['purchase_pack']={**valid,field:value}
            with self.subTest(field=field,value=value):
                with self.assertRaisesRegex(ValueError,'Purchase pack'):rollup(self.state,self.rules)

    def test_unsourced_or_invalid_waste_rejected(self):
        for waste,source in [(20,None),(20,''),(-1,'owner'),(True,'owner'),(float('nan'),'owner'),(float('inf'),'owner')]:
            with self.subTest(waste=waste,source=source):
                self.rule.update(waste_percent=waste,waste_source=source)
                with self.assertRaisesRegex(ValueError,'Waste allowance'):
                    rollup(self.state,self.rules)

    def test_engine_candidate_requires_scope_review_and_rejected_stays_blocked(self):
        item=self.state['measurements']['a'];item['engine_line_ids']=['engine-area']
        for decision in (None,'not_suitable_for_estimate','candidate_requires_independent_verification'):
            self.rule['geometry_reviews']={'a':{'decision':decision,
                'geometry_sha256':geometry_digest(item),'scope':'Floor footprint'}}
            with self.assertRaisesRegex(ValueError,'current scope review'):rollup(self.state,self.rules)

    def test_review_is_invalidated_by_geometry_scale_or_surface_change(self):
        item=self.state['measurements']['a'];item['engine_line_ids']=['engine-area']
        self.rule['geometry_reviews']={'a':{'decision':'approved_for_draft',
            'geometry_sha256':geometry_digest(item),'scope':'Floor footprint'}}
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],202)
        for key,value in (('points',[[0,0],[110,0],[110,100],[0,100]]),
                          ('points_per_foot',11),('surface_factor',1.2),('page',2)):
            state=copy.deepcopy(self.state);state['measurements']['a'][key]=value
            with self.assertRaisesRegex(ValueError,'current scope review'):rollup(state,self.rules)

if __name__=='__main__':unittest.main()
