import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import Polygon

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from floor_finish_faces import finish_room_geometry,reviewed_finish_faces,derive_linked_finish_field
from measurement_quantities import geometry_digest


class FinishFaceTests(unittest.TestCase):
    def setUp(self):
        def room(identity,x):
            return {'id':identity,'page':1,'kind':'area','points':[[x,12],[x+120,12],[x+120,132],[x,132]],
                    'points_per_foot':12,'width_pt':400,'height_pt':400}
        self.state={'plan_sha256':'plan','version':1,'measurements':{'a':room('a',12),'b':room('b',138),
            'door':{'id':'door','page':1,'kind':'length','points':[[135,48],[135,84]],'points_per_foot':12,'width_pt':400,'height_pt':400}}}
        self.passages=[{'measurement_id':'door','sides':[{'side':-1,'room_id':'a'},{'side':1,'room_id':'b'}]}]

    def calculate(self):return finish_room_geometry(self.state,['a','b'],self.passages,.5)

    def test_analytic_area_and_transition_not_treated_as_wall(self):
        original=copy.deepcopy(self.state);state,review=self.calculate()
        # Each 119x119-point finished room plus a 3.5x35-point jamb passage to centerline.
        expected=(119*119+3.5*35)/144
        for room in review['rooms']:self.assertAlmostEqual(room['finished_field_sf'],expected)
        self.assertEqual(self.state,original)
        a,b=[Polygon(state['measurements'][i]['points']) for i in ('a','b')]
        self.assertEqual(a.intersection(b).area,0)
        self.assertAlmostEqual(a.intersection(b).length,35)
        self.assertIsNone(review['purchase_quantity'])
        self.assertFalse(review['actual_jamb_and_transition_locations_verified'])

    def test_door_edit_recalculates_both_sides(self):
        _,before=self.calculate();self.state['measurements']['door']['points'][1][1]+=12
        _,after=self.calculate()
        for old,new in zip(before['rooms'],after['rooms']):
            self.assertAlmostEqual(new['finished_field_sf']-old['finished_field_sf'],3.5*12/144)

    def test_exterior_threshold_stops_at_centerline(self):
        self.passages[0]['sides'][1]['room_id']=None
        state,review=finish_room_geometry(self.state,['a'],self.passages,.5)
        self.assertAlmostEqual(review['rooms'][0]['finished_field_sf'],(119*119+3.5*35)/144)
        self.assertEqual(Polygon(state['measurements']['a']['points']).bounds[2],135)

    def test_detached_diagonal_and_duplicate_door_rejected(self):
        initial=copy.deepcopy(self.state)
        for points in ([[135,48],[140,84]],[[300,48],[300,84]]):
            self.state['measurements']['door']['points']=points
            with self.assertRaises(ValueError):self.calculate()
        self.state=initial;self.passages*=2
        with self.assertRaises(ValueError):self.calculate()

    def test_overlapping_rooms_wrong_scale_and_sides_rejected(self):
        initial=copy.deepcopy(self.state)
        self.state['measurements']['b']['points']=self.state['measurements']['a']['points']
        with self.assertRaises(ValueError):self.calculate()
        self.state=copy.deepcopy(initial);self.state['measurements']['door']['points_per_foot']=10
        with self.assertRaises(ValueError):self.calculate()
        self.state=initial;self.passages[0]['sides'][1]['room_id']='a'
        with self.assertRaises(ValueError):self.calculate()

    def test_source_and_job_evidence_change_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.json';dependency=root/'decision.json'
            dependency.write_text('{"drywall":0.5}')
            config={'room_ids':['a','b'],'passages':self.passages,'wall_finish_thickness_inches':.5,
                    'source_file':'source.json','basis':'Reviewed drawing'}
            source.write_text(json.dumps({**config,'plan_sha256':'plan','job_sources':[
                {'file':'decision.json','sha256':hashlib.sha256(dependency.read_bytes()).hexdigest()}]}))
            config['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
            reviewed_finish_faces(self.state,config,root)
            dependency.write_text('changed')
            with self.assertRaisesRegex(ValueError,'job evidence'):reviewed_finish_faces(self.state,config,root)
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'source changed'):reviewed_finish_faces(self.state,config,root)

    def test_linked_field_rejects_changed_missing_or_wrong_plan_owner_answers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'faces.json';recipe_path=root/'recipe.json';answer=root/'answer.json'
            config={'room_ids':['a','b'],'passages':self.passages,'wall_finish_thickness_inches':.5,
                    'source_file':'faces.json','basis':'Reviewed drawing'}
            source.write_text(json.dumps({**config,'plan_sha256':'plan'}))
            config['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
            answer.write_text(json.dumps({'plan_sha256':'plan','tile_under_cabinets':True}))
            original=answer.read_bytes()
            recipe={'plan_sha256':'plan','measurement_id':'a','room_ids':['a'],
                    'original_geometry_sha256':geometry_digest(self.state['measurements']['a']),
                    'finish_faces':config,'basis':'Live room finish field',
                    'owner_answer_source':{'file':'answer.json','sha256':hashlib.sha256(original).hexdigest()}}
            def binding():
                recipe_path.write_text(json.dumps(recipe))
                return {'source_file':'recipe.json','source_sha256':hashlib.sha256(recipe_path.read_bytes()).hexdigest()}
            bound=binding()
            baseline=derive_linked_finish_field(self.state,self.state,bound,root)
            answer.write_text(json.dumps({'plan_sha256':'plan','tile_under_cabinets':False}))
            with self.assertRaisesRegex(ValueError,'owner answer'):
                derive_linked_finish_field(self.state,self.state,bound,root)
            answer.unlink()
            with self.assertRaisesRegex(ValueError,'owner answer'):
                derive_linked_finish_field(self.state,self.state,bound,root)
            answer.write_bytes(original)
            self.assertEqual(derive_linked_finish_field(self.state,self.state,bound,root),baseline)
            answer.write_text(json.dumps({'plan_sha256':'another-plan','tile_under_cabinets':True}))
            recipe['owner_answer_source']['sha256']=hashlib.sha256(answer.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'owner answer'):
                derive_linked_finish_field(self.state,self.state,binding(),root)
            recipe['owner_answer_source']['file']='../outside-answer.json'
            with self.assertRaisesRegex(ValueError,'owner answer'):
                derive_linked_finish_field(self.state,self.state,binding(),root)

    def test_live_linked_field_rebuilds_and_preserves_other_footprints(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'faces.json';recipe_path=root/'recipe.json'
            config={'room_ids':['a','b'],'passages':self.passages,'wall_finish_thickness_inches':.5,
                    'source_file':'faces.json','basis':'Reviewed drawing'}
            source.write_text(json.dumps({**config,'plan_sha256':'plan'}))
            config['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
            linked=copy.deepcopy(self.state);original=copy.deepcopy(linked)
            recipe={'plan_sha256':'plan','measurement_id':'a','room_ids':['a'],
                    'original_geometry_sha256':geometry_digest(linked['measurements']['a']),
                    'finish_faces':config,'basis':'Live room finish field'}
            recipe_path.write_text(json.dumps(recipe))
            binding={'source_file':'recipe.json','source_sha256':hashlib.sha256(recipe_path.read_bytes()).hexdigest()}
            result,review=derive_linked_finish_field(linked,self.state,binding,root)
            self.assertAlmostEqual(result['measurements']['a']['result']['quantity'],(119*119+3.5*35)/144)
            self.assertEqual(result['measurements']['b'],linked['measurements']['b'])
            self.assertEqual(linked,original)
            self.state['version']=7;self.state['measurements']['door']['points'][1][1]+=12
            result,review=derive_linked_finish_field(linked,self.state,binding,root)
            self.assertEqual(review['source_measurement_version'],7)
            self.assertAlmostEqual(result['measurements']['a']['result']['quantity'],(119*119+3.5*47)/144)
            linked['measurements']['a']['points'][1][0]+=1
            with self.assertRaisesRegex(ValueError,'edited directly'):
                derive_linked_finish_field(linked,self.state,binding,root)
            linked=original;wrong=copy.deepcopy(self.state);wrong['plan_sha256']='another plan'
            with self.assertRaisesRegex(ValueError,'same plan'):
                derive_linked_finish_field(linked,wrong,binding,root)
            recipe_path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'evidence changed'):
                derive_linked_finish_field(linked,self.state,binding,root)


if __name__=='__main__':unittest.main()
