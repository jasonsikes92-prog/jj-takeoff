import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_sheathing_layout import calculate,upper_faces


class WallSheathing(unittest.TestCase):
    def setUp(self):
        self.outline={'points':[[0,0],[10,0],[10,10],[0,10]],'points_per_foot':1}
        self.basis={'wall_ids':['A','B','C','D'],'garage_wall_ids':[],
            'half_wall_inches':1.75,'plate_height_inches':108,'precut_plate_height_inches':109.125,
            'floor_band_height_inches':14.71875,'garage_height_adjustment_inches':10.71875,
            'upper_faces':[],'remaining':['Unverified product and supports']}

    def test_outline_width_edit_changes_only_two_wall_faces_and_restores(self):
        original=copy.deepcopy(self.outline);before=calculate(self.outline,{},self.basis)
        self.outline['points'][1][0]+=4;self.outline['points'][2][0]+=4
        after=calculate(self.outline,{},self.basis)
        self.assertAlmostEqual(after['combined']['gross_surface_sf']-before['combined']['gross_surface_sf'],72)
        for index in (1,3):self.assertEqual(after['combined']['faces'][index],before['combined']['faces'][index])
        self.assertEqual(calculate(original,{},self.basis),before)
        self.assertIsNone(after['purchase_quantity']);self.assertFalse(after['price_applied'])

    def test_garage_height_and_conditional_band_do_not_double_count_rim(self):
        self.basis['garage_wall_ids']=['A']
        result=calculate(self.outline,{},self.basis)
        faces=result['combined']['faces']
        self.assertAlmostEqual(faces[0]['height_ft'],118.71875/12)
        self.assertEqual(faces[1]['height_ft'],9)
        self.assertAlmostEqual(result['floor_band_area_sf'],sum(f['length_ft'] for f in faces[1:])*14.71875/12)
        self.assertEqual(len(result['conditional_floor_band']['faces']),7)
        self.assertIsNone(result['complete_wall_sheathing_quantity'])

    def test_selected_height_drives_combined_and_conditional_without_adding_comparison(self):
        self.basis['garage_wall_ids']=['A']
        before=calculate(self.outline,{},self.basis)
        result=calculate(self.outline,{},self.basis,selected_wall_height_inches=109.125)
        self.assertEqual(result['selected_wall_height_inches'],109.125)
        self.assertEqual(result['combined'],before['precut_height_sensitivity'])
        self.assertEqual(result['printed_height_comparison'],before['combined'])
        self.assertEqual(result['conditional_floor_band']['faces'][:4],result['combined']['faces'])
        self.assertEqual(result['floor_band_area_sf'],before['floor_band_area_sf'])
        self.assertAlmostEqual(result['combined']['faces'][0]['height_ft'],119.84375/12)
        self.assertEqual(result['combined']['faces'][1]['height_ft'],109.125/12)
        self.assertIsNone(result['purchase_quantity'])
        with self.assertRaises(ValueError):calculate(self.outline,{},self.basis,selected_wall_height_inches=120)

    def test_disconnected_or_overlapping_upper_parts_fail(self):
        a={'kind':'area','page':1,'points_per_foot':1,'points':[[0,0],[4,0],[4,2],[0,2]]}
        binding={'id':'G','kind':'area_union','measurement_ids':['a','b'],'basis':'Fixture'}
        for y in (1,3):
            b={**a,'points':[[0,y],[4,y],[4,y+2],[0,y+2]]}
            with self.subTest(y=y),self.assertRaisesRegex(ValueError,'gap, overlap'):upper_faces({'a':a,'b':b},[binding])

    def test_reconstruction_contains_visible_face_and_tracks_peak(self):
        m={'kind':'area','page':1,'points_per_foot':1,
            'points':[[2,2],[4,0],[8,4],[8,5],[2,5]]}
        binding={'id':'G','kind':'reconstructed_gable','measurement_ids':['g'],'basis':'Fixture',
                 'vertex_count':5,'rake_indices':[0,1,2]}
        first=upper_faces({'g':m},[binding])[0]
        self.assertEqual(first['surface_sf'],24)
        self.assertEqual(first['reconstructed_hidden_sf'],4)
        changed=copy.deepcopy(m);changed['points'][1][1]=-2
        self.assertGreater(upper_faces({'g':changed},[binding])[0]['surface_sf'],24)
        changed['points'].append([0,5])
        with self.assertRaisesRegex(ValueError,'topology'):upper_faces({'g':changed},[binding])

    def test_wrong_sheet_or_scale_cannot_union_polygons(self):
        a={'kind':'area','page':1,'points_per_foot':1,'points':[[0,0],[4,0],[4,2],[0,2]]}
        binding={'id':'G','kind':'area_union','measurement_ids':['a','b'],'basis':'Fixture'}
        for key,value in [('page',2),('points_per_foot',2)]:
            b={**a,key:value}
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'sheet and scale'):upper_faces({'a':a,'b':b},[binding])

    def test_bad_wall_mapping_and_diagonal_outline_rejected(self):
        self.basis['wall_ids']=['A','A','C','D']
        with self.assertRaisesRegex(ValueError,'identities'):calculate(self.outline,{},self.basis)
        self.basis['wall_ids']=['A','B','C','D'];self.outline['points'][1][1]=1
        with self.assertRaisesRegex(ValueError,'orthogonal'):calculate(self.outline,{},self.basis)
