import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from stair_quantity_review import straight_stair,import_stair


class StairReference(unittest.TestCase):
    def test_one_intermediate_step_has_two_rises_and_no_upper_landing_added(self):
        result=straight_stair(48,15,11,7.75)
        self.assertEqual((result['riser_count'],result['riser_height_inches'],result['intermediate_treads']),(2,7.5,1))
        self.assertAlmostEqual(result['tread_surface_sf'],11/3)
        self.assertAlmostEqual(result['intermediate_riser_face_sf'],2.5)
        self.assertAlmostEqual(result['two_side_faces_sf'],55/48)
        self.assertAlmostEqual(result['gross_step_envelope_cf'],55/24)

    def test_more_risers_and_boundary_rounding(self):
        self.assertEqual(straight_stair(48,15.5,11,7.75)['riser_count'],2)
        result=straight_stair(48,16,11,7.75)
        self.assertEqual((result['riser_count'],result['intermediate_treads'],result['run_inches']),(3,2,22))
        self.assertAlmostEqual(result['gross_step_envelope_cf'],48*11*(16/3)*(1+2)/1728)
        self.assertEqual(straight_stair(48,7.5,11,7.75)['gross_step_envelope_cf'],0)

    def test_invalid_dimensions_rejected(self):
        for value in (None,True,0,-1,float('nan'),float('inf'),'15'):
            with self.subTest(value=value),self.assertRaises(ValueError):straight_stair(48,value,11,7.75)

    def test_source_plan_count_and_parent_checked_without_assigning_purchases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'source.json'
            source={'plan_sha256':'plan','dimensions':{'width_inches':48,'total_rise_inches':15,'tread_inches':11,'max_riser_inches':7.75},
                'owner_intermediate_step_count':1,'basis':'Owner dimensions; layout inferred','remaining':['Footing and brick coursing unresolved']}
            path.write_text(json.dumps(source));config={'id':'front','plan_sha256':'plan','source_file':'source.json',
                'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'parent_row_id':'brick'}
            draft={'plan_sha256':'plan','rows':[{'row_id':'brick','cost_type':'ASSEMBLY','line_cost':None}]}
            result=import_stair(draft,config,root)
            self.assertEqual(len(result['rows'][0]['assembly_inputs']),5)
            self.assertIsNone(result['stair_quantity_review']['brick_purchase_count'])
            self.assertNotIn('assembly_inputs',draft['rows'][0])
            with self.assertRaisesRegex(ValueError,'already imported'):import_stair(result,config,root)
            changed=copy.deepcopy(draft);changed['plan_sha256']='another'
            with self.assertRaisesRegex(ValueError,'another drawing'):import_stair(changed,config,root)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'evidence'):import_stair(draft,config,root)
            source['dimensions']['total_rise_inches']=16;path.write_text(json.dumps(source))
            config['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'owner step count'):import_stair(draft,config,root)

if __name__=='__main__':unittest.main()
