import copy
import math
import unittest
import test_elevation_trim_routes as fixtures
from measurement_quantities import rollup


class ElevationTrimQuantities(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.ElevationTrimRoutes();fixture.setUp()
        for m in fixture.sources.values():m.update(width_pt=500,height_pt=500)
        self.state={'plan_sha256':'test','version':1,'measurements':fixture.sources}
        self.rule={'id':'frieze','label':'Installed frieze allowance','measurement_ids':list(fixture.sources),
            'template_rows':['234'],'unit':'LF','rounding':'whole_up','use':'template_quantity',
            'basis':'Roof-following route, excluding unselected base bands','remaining':['Final trim details'],
            'elevation_trim_route':{'mapping':fixture.mapping,
                'groups':['horizontal_wall_top','sloped_gable','recessed_porch_return']}}
    def result(self):return rollup(self.state,{'plan_sha256':'test','rules':[self.rule]})
    def test_linear_units_round_once_and_keep_bands_separate(self):
        q=self.result()['quantities'][0]
        self.assertAlmostEqual(q['measured_quantity'],17+8*math.sqrt(2))
        self.assertEqual(q['quantity'],29)
        self.assertEqual(q['elevation_trim_route']['group_lf']['gable_base_scope_pending'],8)
        self.rule['elevation_trim_route']['groups']=['gable_base_scope_pending']
        self.rule['use']='assembly_input'
        self.assertEqual(self.result()['quantities'][0]['quantity'],8)
    def test_gable_edit_recalculates_but_invalid_mapping_withholds(self):
        self.state['measurements']['gable']['points'][1][1]=20
        self.assertEqual(self.result()['quantities'][0]['quantity'],35)
        self.state['measurements']['wall']['points'].append([0,150])
        r=self.result();self.assertEqual(r['quantities'],[])
        self.assertIsNone(r['pending_quantities'][0]['quantity'])
    def test_invalid_units_duplicate_groups_and_mixed_rules_rejected(self):
        original=copy.deepcopy(self.rule)
        for change in ('units','groups','mixed'):
            self.rule=copy.deepcopy(original)
            if change=='units':self.rule['unit']='SF'
            elif change=='groups':self.rule['elevation_trim_route']['groups']*=2
            else:self.rule['linear_components']=[]
            with self.assertRaises(ValueError):self.result()


if __name__=='__main__':unittest.main()
