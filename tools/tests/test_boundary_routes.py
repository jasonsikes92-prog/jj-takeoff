import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from boundary_routes import calculate
from measurement_quantities import rollup


class BoundaryRoutes(unittest.TestCase):
    def setUp(self):
        common={'page':1,'width_pt':500,'height_pt':500,'points_per_foot':10}
        self.measurements={'wall':{**common,'kind':'area','points':[[10,10],[110,10],[110,110],[10,110]]},
            'door':{**common,'kind':'length','points':[[30,10],[60,10]]}}
        self.rule={'id':'route','label':'Horizontal flashing','measurement_ids':['wall','door'],
            'unit':'LF','rounding':'none','use':'assembly_input','template_rows':['235'],
            'boundary_route':{'outline_id':'wall','deduction_ids':['door']},'basis':'Synthetic geometry','remaining':['Flashing details']}

    def calculate(self):return calculate(self.measurements,'wall',[i for i in self.measurements if i!='wall'])

    def rollup(self):
        return rollup({'plan_sha256':'test','version':1,'measurements':self.measurements},
                      {'plan_sha256':'test','rules':[self.rule]})

    def test_located_opening_is_removed_once_with_reusable_segment_coordinates(self):
        original=copy.deepcopy(self.measurements);result=self.calculate()
        self.assertEqual((result['gross_lf'],result['deductions_lf'],result['net_lf']),(40,3,37))
        self.assertEqual(len(result['segments']),5)
        self.assertAlmostEqual(sum(math.dist(*s['points'])/10 for s in result['segments']),37)
        self.assertEqual(self.measurements,original);self.assertIsNone(result['purchase_quantity'])

    def test_opening_and_outline_edits_recompute_both_segments_and_length(self):
        self.measurements['door']['points'][1][0]=70
        self.assertEqual(self.calculate()['net_lf'],36)
        self.measurements['wall']['points'][2][1]=210
        self.measurements['wall']['points'][3][1]=210
        self.assertEqual(self.calculate()['net_lf'],56)

    def test_rotated_and_reversed_geometry_has_same_route(self):
        result=self.calculate()
        for m in self.measurements.values():
            m['points']=[[x*.6-y*.8+150,x*.8+y*.6+50] for x,y in m['points']]
            m['points'].reverse()
        self.assertAlmostEqual(self.calculate()['net_lf'],result['net_lf'])

    def test_gap_may_cross_an_added_collinear_vertex(self):
        self.measurements['wall']['points'].insert(1,[50,10])
        result=self.calculate()
        self.assertEqual(result['net_lf'],37)
        self.assertEqual(len(result['gaps'][0]['edge_spans']),2)

    def test_off_boundary_crossing_or_extending_gap_is_withheld_not_snapped(self):
        for points in ([[30,11],[60,11]],[[30,10],[60,20]],[[0,10],[60,10]],[[10,10],[110,110]]):
            self.measurements['door']['points']=points
            with self.assertRaisesRegex(ValueError,'not wholly'):self.calculate()
            report=self.rollup()
            self.assertFalse(report['quantities']);self.assertIsNone(report['pending_quantities'][0]['quantity'])

    def test_overlapping_openings_are_not_hidden_by_subtraction(self):
        self.measurements['other']={**self.measurements['door'],'points':[[50,10],[80,10]]}
        with self.assertRaisesRegex(ValueError,'overlap'):self.calculate()

    def test_touching_openings_and_full_edge_gap(self):
        self.measurements['other']={**self.measurements['door'],'points':[[60,10],[110,10]]}
        self.assertEqual(self.calculate()['net_lf'],32)
        self.measurements['door']['points']=[[10,10],[60,10]]
        self.assertEqual(self.calculate()['net_lf'],30)

    def test_unselected_windows_do_not_reduce_the_route(self):
        self.measurements['window']={**self.measurements['door'],'points':[[20,110],[60,110]]}
        report=self.rollup()
        self.assertEqual(report['quantities'][0]['quantity'],37)
        with self.assertRaisesRegex(ValueError,'exactly'):calculate(self.measurements,'wall',['door'])

    def test_page_scale_and_slope_mismatches_are_rejected(self):
        initial=copy.deepcopy(self.measurements['door'])
        for key,value in [('page',2),('points_per_foot',20),('width_pt',600),('surface_factor',1.2),('plane_gradients',[[0,0]])]:
            self.measurements['door']={**initial,key:value}
            with self.assertRaises(ValueError):self.calculate()

    def test_wrong_geometry_and_duplicate_mapping_rejected(self):
        with self.assertRaisesRegex(ValueError,'distinct'):calculate(self.measurements,'wall',['door','door'])
        self.measurements['door']['points']=[[30,10],[50,10],[60,10]]
        with self.assertRaisesRegex(ValueError,'straight'):self.calculate()
        self.measurements['door']['kind']='count'
        with self.assertRaises(ValueError):self.calculate()

    def test_rollup_retains_source_segments_and_partial_status(self):
        result=self.rollup();quantity=result['quantities'][0]
        self.assertEqual(quantity['quantity'],37);self.assertEqual(len(quantity['boundary_route']['segments']),5)
        self.assertEqual(quantity['use'],'assembly_input');self.assertFalse(quantity['certified'])
        self.assertFalse(result['estimate_released']);self.assertIsNone(result['whole_house_total'])

    def test_conflicting_rule_operations_are_rejected(self):
        for key,value in [('unit','SF'),('count_openings',True),('linear_components',[]),('footprint',{})]:
            original=copy.deepcopy(self.rule);self.rule[key]=value
            with self.assertRaises(ValueError):self.rollup()
            self.rule=original


if __name__=='__main__':unittest.main()
