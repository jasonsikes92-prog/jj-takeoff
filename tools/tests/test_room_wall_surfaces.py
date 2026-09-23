import copy
import unittest
from room_wall_surfaces import attach


class WallSurfaces(unittest.TestCase):
    def setUp(self):
        self.r={'id':'room','points':[[0,0],[100,0],[100,120],[0,120]],'holes':[],'points_per_foot':10,
            'ceiling_reference':{'noted_height_inches':108},'ceiling_surface':{'status':'current_source_review',
                'surface_type':'flat','surface_area_sf':120,'source_sha256':'current-review'}}
        self.result={'source_sha256':'source','regions':[self.r]}

    def test_wall_area_is_perimeter_times_height_not_floor_area(self):
        output=attach(self.result);r=output['regions'][0]['wall_surface_reference']
        self.assertEqual(r['boundary_perimeter_lf'],44);self.assertEqual(r['gross_wall_surface_sf'],396)
        self.assertEqual(r['gross_wall_plus_ceiling_sf'],516)
        self.assertFalse(r['opening_deductions_applied']);self.assertFalse(r['waste_applied'])
        self.assertIsNone(output['wall_surface_review']['billing_quantity'])
        self.assertNotIn('wall_surface_reference',self.r)

    def test_nonrectangular_and_hole_boundaries_use_measured_edges(self):
        self.r['points']=[[0,0],[100,0],[100,50],[50,50],[50,120],[0,120]]
        self.r['holes']=[[[10,10],[20,10],[20,20],[10,20]]]
        r=attach(self.result)['regions'][0]['wall_surface_reference']
        self.assertEqual(r['boundary_perimeter_lf'],48);self.assertEqual(r['gross_wall_surface_sf'],432)

    def test_vault_missing_height_or_stale_surface_stays_unresolved(self):
        for field,value in [('surface_type','uniform_pitch'),('surface_type','partitioned'),('status','stale_source_review'),('status','unreviewed')]:
            source=copy.deepcopy(self.result);source['regions'][0]['ceiling_surface'][field]=value
            output=attach(source);self.assertIsNone(output['wall_surface_review']['gross_wall_subtotal_sf'])
            self.assertEqual(output['wall_surface_review']['unresolved_region_ids'],['room'])
        self.r['ceiling_reference']['noted_height_inches']=None
        self.assertIsNone(attach(self.result)['wall_surface_review']['gross_wall_subtotal_sf'])

    def test_partial_coverage_never_becomes_whole_house_drywall(self):
        other=copy.deepcopy(self.r);other['id']='other';other['ceiling_surface']['status']='unreviewed'
        self.result['regions'].append(other);output=attach(self.result)['wall_surface_review']
        self.assertEqual(output['gross_wall_subtotal_sf'],396);self.assertEqual(output['measured_region_count'],1)
        self.assertIsNone(output['whole_house_drywall_quantity']);self.assertFalse(output['estimate_released'])

    def test_changed_height_or_scale_changes_quantity_and_fingerprint(self):
        before=attach(self.result);self.r['ceiling_reference']['noted_height_inches']=120
        after=attach(self.result);self.assertEqual(after['wall_surface_review']['gross_wall_subtotal_sf'],440)
        self.assertNotEqual(before['source_sha256'],after['source_sha256'])
        self.r['points_per_foot']=20
        self.assertEqual(attach(self.result)['wall_surface_review']['gross_wall_subtotal_sf'],220)

    def test_invalid_height_rejects_instead_of_silently_adding_zero(self):
        for height in (0,-1,True,float('nan')):
            self.r['ceiling_reference']['noted_height_inches']=height
            with self.assertRaises(ValueError):attach(self.result)


if __name__=='__main__':unittest.main()
