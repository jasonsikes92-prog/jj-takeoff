import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup


class GableSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.state={'version':1,'plan_sha256':'fixed','measurements':{'end':{
            'kind':'length','points':[[0,0],[180,0]],'points_per_foot':10,
            'width_pt':400,'height_pt':400}}}
        self.term={'id':'end-face','measurement_id':'end','kind':'symmetric_gable_wall',
                   'pitch_rise':8,'pitch_run':12,'pitch_source':'Reviewed section','operation':'add'}
        self.rules={'plan_sha256':'fixed','rules':[{'id':'gable','label':'Gable','measurement_ids':['end'],
            'surface_components':[self.term],'unit':'SF','rounding':'none','template_rows':['222'],
            'use':'assembly_input','basis':'Triangle above equal-height eaves','remaining':['Finish scope']} ]}

    def quantity(self):return rollup(self.state,self.rules)['quantities'][0]['quantity']

    def test_known_triangle_and_changed_span(self):
        self.assertEqual(self.quantity(),54)  # 18-ft base, 6-ft rise
        self.state['measurements']['end']['points'][1][0]=240
        self.assertEqual(self.quantity(),96)  # 24-ft base, 8-ft rise

    def test_invalid_pitch_and_missing_evidence(self):
        for key,value in [('pitch_rise',0),('pitch_rise',True),('pitch_run',float('inf')),('pitch_run',-12),('pitch_source','')]:
            with self.subTest(key=key,value=value):
                original=copy.deepcopy(self.term);self.term[key]=value
                with self.assertRaises(ValueError):self.quantity()
                self.term.clear();self.term.update(original)

    def test_bent_span_and_sloped_length_refused(self):
        self.state['measurements']['end']['points']=[[0,0],[90,20],[180,0]]
        result=rollup(self.state,self.rules)
        self.assertEqual(result['quantities'],[])
        self.assertIn('straight',result['pending_quantities'][0]['reason'])
        self.state['measurements']['end']['points']=[[0,0],[180,0]]
        self.state['measurements']['end']['plane_gradients']=[[.5,0]]
        self.assertEqual(rollup(self.state,self.rules)['quantities'],[])

    def test_scale_controls_area_and_result_stays_partial(self):
        self.state['measurements']['end']['points_per_foot']=20
        self.assertEqual(self.quantity(),13.5)
        result=rollup(self.state,self.rules)
        self.assertIsNone(result['whole_house_total'])
        self.assertFalse(result['estimate_released'])


if __name__=='__main__':unittest.main()
