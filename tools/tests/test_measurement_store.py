import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_store import MeasurementStore, EditConflict, calculate

class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'plan.pdf').write_bytes(b'fixed-plan-fixture')
        self.sha=hashlib.sha256((self.root/'plan.pdf').read_bytes()).hexdigest()
        common={'page':1,'width_pt':1000,'height_pt':1000,'points_per_foot':10,'dependent_rows':['100']}
        self.area={**common,'id':'floor','kind':'area','color':'#8b5cf6','label':'Floor','points':[[0,0],[100,0],[100,100],[0,100]]}
        self.line={**common,'id':'wall','kind':'length','color':'#f59e0b','label':'Wall','points':[[0,0],[100,0]]}
        (self.root/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[self.area,self.line]}))
        self.store=MeasurementStore(self.root)
    def tearDown(self):self.tmp.cleanup()
    def save(self,points,**kw):return self.store.save(kw.get('id','floor'),points,kw.get('version',1),kw.get('sha',self.sha),'test edit')
    def test_area_change_recalculates_and_invalidates_without_changing_other_measurement(self):
        result=self.save([[0,0],[200,0],[200,100],[0,100]])
        self.assertEqual(result['measurements']['floor']['result']['quantity'],200)
        self.assertEqual(result['measurements']['wall']['result']['quantity'],10)
        self.assertEqual(result['invalidated_rows'],['100']);self.assertFalse(result['estimate_released'])
        self.assertEqual(MeasurementStore(self.root).read(),result)
        self.assertEqual(self.store.read(1)['measurements']['floor']['result']['quantity'],100)
    def test_stale_save_rejected(self):
        self.save([[0,0],[200,0]],id='wall')
        with self.assertRaises(EditConflict):self.save(self.area['points'])
        self.assertEqual(self.store.read()['version'],2)

    def test_new_quantity_mapping_is_invalidated_without_replacing_geometry_history(self):
        rules={'plan_sha256':self.sha,'rules':[
            {'measurement_ids':['floor'],'template_rows':['217']},
            {'measurement_ids':['wall'],'template_rows':['999']}]}
        (self.root/'quantity_rules.json').write_text(json.dumps(rules))
        result=self.save([[0,0],[200,0],[200,100],[0,100]])
        self.assertEqual(result['invalidated_rows'],['100','217'])
        self.assertEqual(self.store.read(1)['measurements']['floor']['points'],self.area['points'])
        self.assertEqual(result['measurements']['floor']['dependent_rows'],['100'])

    def test_wrong_source_quantity_mapping_cannot_save_an_edit(self):
        (self.root/'quantity_rules.json').write_text(json.dumps({'plan_sha256':'wrong','rules':[]}))
        with self.assertRaisesRegex(EditConflict,'another drawing'):
            self.save([[0,0],[200,0],[200,100],[0,100]])
        self.assertEqual(self.store.read()['version'],1)

    def test_mapping_change_during_edit_rolls_back_the_geometry(self):
        path=self.root/'quantity_rules.json'
        rules={'plan_sha256':self.sha,'rules':[{'measurement_ids':['floor'],'template_rows':['217']}]}
        path.write_text(json.dumps(rules))
        def change_mapping(measurement):
            if measurement['id']=='floor' and measurement['points'][1][0]==200:
                path.write_text(json.dumps({**rules,'rules':[]}))
            return calculate(measurement)
        with patch('measurement_store.calculate',side_effect=change_mapping):
            with self.assertRaisesRegex(EditConflict,'changed during'):
                self.save([[0,0],[200,0],[200,100],[0,100]])
        self.assertEqual(self.store.read()['version'],1)
        self.assertEqual(self.store.read()['measurements']['floor']['points'],self.area['points'])
    def test_self_crossing_polygon_rejected(self):
        with self.assertRaises(ValueError):self.save([[0,0],[100,100],[0,100],[100,0]])
        self.assertEqual(self.store.read()['version'],1)
    def test_wrong_plan_and_changed_plan_rejected(self):
        with self.assertRaises(EditConflict):self.save(self.area['points'],sha='wrong')
        (self.root/'plan.pdf').write_bytes(b'different revision')
        with self.assertRaises(EditConflict):self.store.read()
    def test_nonfinite_or_off_page_points_rejected(self):
        for points in ([[0,0],[float('nan'),0]],[[0,0],[1001,0]],[[0,0],[0,0]]):
            with self.assertRaises(ValueError):self.save(points,id='wall')
    def test_tampered_result_rejected(self):
        state=self.store.read();state['measurements']['floor']['result']['quantity']=999
        with closing(sqlite3.connect(self.store.database)) as db,db:db.execute('UPDATE versions SET body=?',(json.dumps(state),))
        with self.assertRaises(EditConflict):self.store.read()
    def test_count_is_whole_number(self):
        value=calculate({**self.line,'kind':'count','points':[[2,2],[8,8],[9,9]]})
        self.assertEqual(value,{'quantity':3,'unit':'EA'})
    def test_count_can_save_zero_and_restore_without_losing_history(self):
        folder=self.root/'counts';folder.mkdir()
        (folder/'plan.pdf').write_bytes((self.root/'plan.pdf').read_bytes())
        count={**self.line,'kind':'count','points':[[2,2],[8,8]]}
        (folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[count]}))
        store=MeasurementStore(folder)
        cleared=store.save('wall',[],1,self.sha,'Remove both counted items')
        self.assertEqual(cleared['measurements']['wall']['result'],{'quantity':0,'unit':'EA'})
        self.assertEqual(MeasurementStore(folder).read(),cleared)
        restored=store.save('wall',count['points'],2,self.sha,'Restore counted items')
        self.assertEqual(restored['measurements']['wall']['result']['quantity'],2)
        self.assertEqual(store.read(1)['measurements']['wall']['result']['quantity'],2)
        with self.assertRaises(ValueError):calculate({**count,'points':None})
        with self.assertRaises(ValueError):calculate({**count,'kind':'length','points':[]})
    def test_count_needs_no_linear_scale_but_lengths_and_areas_do(self):
        measurement={**self.line,'kind':'count'};measurement.pop('points_per_foot')
        self.assertEqual(calculate(measurement),{'quantity':2,'unit':'EA'})
        for kind in ('length','area'):
            with self.assertRaises(ValueError):calculate({**measurement,'kind':kind})
    def test_sloped_area_and_invalid_factor(self):
        value=calculate({**self.area,'surface_factor':2**0.5})
        self.assertAlmostEqual(value['quantity'],100*2**0.5)
        self.assertEqual(value['projected_area_sf'],100)
        for factor in (0,float('nan')):
            with self.assertRaises(ValueError):calculate({**self.area,'surface_factor':factor})
    def test_roof_line_uses_direction_not_blanket_pitch_factor(self):
        rake=calculate({**self.line,'plane_gradients':[[1,0]]})
        self.assertAlmostEqual(rake['quantity'],10*2**.5)
        hip=calculate({**self.line,'points':[[0,0],[100,100]],'plane_gradients':[[1,0],[0,1]]})
        self.assertAlmostEqual(hip['quantity'],10*3**.5)
        level=calculate({**self.line,'points':[[0,0],[0,100]],'plane_gradients':[[1,0]]})
        self.assertEqual(level['quantity'],10)
    def test_roof_planes_must_agree_along_shared_edge(self):
        with self.assertRaisesRegex(ValueError,'disagree'):
            calculate({**self.line,'plane_gradients':[[1,0],[0,1]]})
        for gradients in ([],[[float('nan'),0]],[[True,0]],[[1]]):
            with self.assertRaises(ValueError):calculate({**self.line,'plane_gradients':gradients})
    def test_saved_sloped_line_recomputes_after_direction_edit(self):
        config=json.loads((self.root/'measurements.json').read_text())
        config['measurements'][1]['plane_gradients']=[[1,0]]
        separate=self.root/'slope_job';separate.mkdir()
        (separate/'plan.pdf').write_bytes((self.root/'plan.pdf').read_bytes())
        (separate/'measurements.json').write_text(json.dumps(config))
        store=MeasurementStore(separate)
        state=store.save('wall',[[0,0],[0,100]],1,self.sha,'Rotate synthetic slope line')
        self.assertEqual(state['measurements']['wall']['result']['quantity'],10)
        self.assertAlmostEqual(store.read(1)['measurements']['wall']['result']['quantity'],10*2**.5)
        self.assertEqual(MeasurementStore(separate).read(),state)

if __name__=='__main__':unittest.main()
