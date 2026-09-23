import copy
import unittest
from elevation_finish_allocation import allocate_elevations
from measurement_quantities import geometry_digest


class ElevationFinishAllocation(unittest.TestCase):
    def setUp(self):
        self.room={'kind':'area','page':1,'points_per_foot':1,'width_pt':100,'height_pt':100,
                   'points':[[10,10],[30,10],[30,30],[10,30]]}
        metadata={'kind':'area','page':2,'points_per_foot':10,'width_pt':300,'height_pt':200}
        self.m={'finish':{**metadata,'points':[[0,40],[100,40],[100,70],[60,70],[60,80],[0,80]]},
                'hood':{**metadata,'points':[[20,40],[40,40],[40,60],[20,60]]}}
        self.field={'id':'backsplash','room_edge_index':0,'anchor_end':'start','direction':1,
            'elevation_anchor_x_pt':0,'elevation_floor_y_pt':100,'include':['finish'],'exclude':['hood'],
            'datum_source':'Reviewed elevation floor baseline and corner'}
        self.digest=geometry_digest(self.room)

    def result(self,fields=None):
        return allocate_elevations(self.room,9,self.m,fields or [self.field],self.digest)

    def test_stepped_elevated_field_and_cutout_keep_true_area(self):
        result=self.result()
        self.assertEqual(result['gross_wall_sf'],720)
        self.assertEqual(result['excluded_wall_sf'],32)
        self.assertEqual(result['remaining_wall_reference_sf'],688)
        heights=[p[1] for p in result['mapped_elevation_fields'][0]['wall_plane_geometry_ft']['coordinates'][0]]
        self.assertEqual((min(heights),max(heights)),(2,6))
        self.assertIsNone(result['purchase_quantity'])
        self.assertFalse(result['paint_quantity_certified'])

    def test_repeated_physical_patch_is_unioned(self):
        result=self.result([self.field,{**self.field,'id':'same-wall-second-description'}])
        self.assertEqual(result['excluded_wall_sf'],32)
        self.assertEqual(result['overlapping_exclusion_sf'],32)

    def test_reversed_elevation_uses_opposite_wall_end(self):
        self.field.update(anchor_end='end',direction=-1)
        result=self.result()
        self.assertEqual(result['excluded_wall_sf'],32)
        horizontal=[p[0] for p in result['mapped_elevation_fields'][0]['wall_plane_geometry_ft']['coordinates'][0]]
        self.assertEqual((min(horizontal),max(horizontal)),(10,20))

    def test_room_edit_requires_anchor_review(self):
        self.room['points'].insert(1,[20,10])
        with self.assertRaisesRegex(ValueError,'anchors'):self.result()

    def test_cutout_frame_and_containment_are_required(self):
        original=copy.deepcopy(self.m['hood'])
        self.m['hood']['page']=3
        with self.assertRaisesRegex(ValueError,'frame'):self.result()
        self.m['hood']=original
        self.m['hood']['points']=[[110,40],[130,40],[130,60],[110,60]]
        with self.assertRaisesRegex(ValueError,'cutout'):self.result()

    def test_invalid_datums_and_outside_wall_fail(self):
        for key,value in [('room_edge_index',True),('direction',True),('direction',0),
                          ('datum_source',''),('elevation_floor_y_pt',float('nan')),
                          ('elevation_anchor_x_pt',-1),('elevation_floor_y_pt',200)]:
            field={**self.field,key:value}
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.result([field])
        self.field['direction']=-1
        with self.assertRaisesRegex(ValueError,'outside'):self.result()


if __name__=='__main__':unittest.main()
