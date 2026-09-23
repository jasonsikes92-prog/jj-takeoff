import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup


class VaultRollup(unittest.TestCase):
    def setUp(self):
        self.boundary={'id':'room','page':1,'kind':'area','points':[[0,0],[200,0],[200,180],[0,180]],
            'points_per_foot':10,'width_pt':500,'height_pt':500,'surface_factor':(1+(8/12)**2)**.5}
        self.state={'version':1,'plan_sha256':'plan','measurements':{'room':self.boundary}}
        self.term={'id':'upper-walls','measurement_id':'room','kind':'symmetric_vault_upper_wall',
            'transverse_direction':[0,1],'pitch_rise':8,'pitch_run':12,'pitch_source':'Reviewed section','operation':'add'}
        self.rules={'plan_sha256':'plan','rules':[{'id':'vault','label':'Upper walls','measurement_ids':['room'],
            'unit':'SF','rounding':'none','template_rows':['222'],'use':'assembly_input',
            'basis':'Geometry above equal low sides; material backing pending','remaining':['Finish scope'],
            'surface_components':[self.term]}]}

    def result(self):return rollup(self.state,self.rules)

    def test_two_gables_without_ceiling_slope_double_count(self):
        result=self.result();q=result['quantities'][0]
        self.assertAlmostEqual(q['quantity'],108)
        profile=q['surface_assembly']['components'][0]['vault_profile']
        self.assertEqual(profile['rise_above_low_sides_ft'],6)
        self.assertFalse(profile['finish_scope_confirmed'])
        self.assertIsNone(profile['low_side_height_ft'])
        self.assertFalse(q['order_released']);self.assertFalse(result['estimate_released'])

    def test_projecting_chase_and_changed_span_recompute(self):
        self.boundary['points']=[[0,0],[200,0],[200,60],[180,60],[180,120],[200,120],[200,180],[0,180]]
        self.assertAlmostEqual(self.result()['quantities'][0]['quantity'],124)
        self.boundary['points_per_foot']=20
        self.assertAlmostEqual(self.result()['quantities'][0]['quantity'],31)

    def test_invalid_pitch_or_direction_does_not_create_area(self):
        for key,value in [('pitch_source',''),('pitch_rise',True),('transverse_direction',[0,0]),('pitch_run',0)]:
            original=copy.deepcopy(self.term);self.term[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.result()
            self.term.clear();self.term.update(original)

    def test_foreign_plan_and_wrong_measurement_kind_rejected(self):
        self.rules['plan_sha256']='other'
        with self.assertRaises(ValueError):self.result()
        self.rules['plan_sha256']='plan';self.boundary.update(kind='length',points=[[0,0],[200,0]])
        with self.assertRaises(ValueError):self.result()


if __name__=='__main__':unittest.main()
