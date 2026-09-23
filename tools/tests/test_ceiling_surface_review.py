import copy
import math
import unittest
from ceiling_surface_review import apply,binding


class CeilingSurfaces(unittest.TestCase):
    def setUp(self):
        self.r={'id':'room','page':1,'points_per_foot':10,'points':[[0,0],[100,0],[100,100],[0,100]],
            'holes':[],'ceiling_notes':[],'ceiling_reference':{'status':'height_note_only'}}
        self.result={'plan_sha256':'plan','source_sha256':'notes','regions':[self.r]}
        self.d={'region_id':'room','source_sha256':binding('plan',self.r),'scope':'entire_region',
            'surface_type':'flat','rise_per_12':0,'basis':'Flat ceiling over entire measured room in source section'}
        self.review={'plan_sha256':'plan','reviewer':'Source reviewer','decisions':[self.d]}

    def test_flat_area_is_recomputed_from_geometry_and_no_purchase_total(self):
        self.r['boundary_area_sf']=999
        result=apply(self.result,self.review);surface=result['regions'][0]['ceiling_surface']
        self.assertEqual(surface['surface_area_sf'],100);self.assertIsNone(surface['purchase_quantity'])
        self.assertTrue(result['ceiling_surface_review']['all_represented_regions_reviewed'])
        self.assertIsNone(result['ceiling_surface_review']['whole_house_ceiling_surface_sf'])
        self.assertNotIn('ceiling_surface',self.r)

    def test_uniform_pitch_and_holes_use_actual_surface_factor_once(self):
        self.r['holes']=[[[20,20],[40,20],[40,40],[20,40]]]
        self.d.update(source_sha256=binding('plan',self.r),surface_type='uniform_pitch',rise_per_12=4)
        surface=apply(self.result,self.review)['regions'][0]['ceiling_surface']
        self.assertAlmostEqual(surface['surface_area_sf'],96*math.sqrt(10)/3)

    def test_partial_and_empty_coverage_are_explicit(self):
        other=copy.deepcopy(self.r);other['id']='other';self.result['regions'].append(other)
        result=apply(self.result,self.review)['ceiling_surface_review']
        self.assertEqual(result['reviewed_surface_subtotal_sf'],100);self.assertFalse(result['all_represented_regions_reviewed'])
        self.assertEqual(result['unreviewed_region_ids'],['other'])
        self.assertIsNone(apply(self.result,None)['ceiling_surface_review']['reviewed_surface_subtotal_sf'])

    def test_geometry_scale_page_and_ceiling_note_changes_withhold_and_restore(self):
        for fields in ({'page':2},{'points_per_foot':12},{'points':[[0,0],[110,0],[110,100],[0,100]]},
                       {'ceiling_notes':[{'kind':'vaulted'}]}):
            result=copy.deepcopy(self.result);result['regions'][0].update(fields)
            self.assertEqual(apply(result,self.review)['regions'][0]['ceiling_surface']['status'],'stale_source_review')
        self.assertEqual(apply(self.result,self.review)['regions'][0]['ceiling_surface']['surface_area_sf'],100)

    def test_review_cannot_override_vault_or_pitch_conflicts(self):
        self.r['ceiling_notes']=[{'kind':'vault_pitch','rise_inches':4,'run_inches':12}]
        self.d['source_sha256']=binding('plan',self.r)
        with self.assertRaises(ValueError):apply(self.result,self.review)
        self.d.update(surface_type='uniform_pitch',rise_per_12=6)
        with self.assertRaises(ValueError):apply(self.result,self.review)
        self.d['rise_per_12']=4
        self.assertGreater(apply(self.result,self.review)['regions'][0]['ceiling_surface']['surface_area_sf'],100)

    def mixed_review(self):
        review=copy.deepcopy(self.review);d=review['decisions'][0]
        d.pop('rise_per_12');d.update(surface_type='partitioned',parts=[
            {'id':'flat','points':[[0,0],[40,0],[40,100],[0,100]],'rise_per_12':0,'basis':'Hall boundary'},
            {'id':'vault','points':[[40,0],[100,0],[100,100],[40,100]],'rise_per_12':4,'basis':'Vault boundary'}])
        return review

    def test_mixed_surface_sums_separate_pitches_without_releasing_purchase(self):
        result=apply(self.result,self.mixed_review());s=result['regions'][0]['ceiling_surface']
        self.assertEqual(s['projected_area_sf'],100)
        self.assertAlmostEqual(s['surface_area_sf'],40+60*math.sqrt(10)/3)
        self.assertIsNone(s['purchase_quantity'])
        self.assertIsNone(result['ceiling_surface_review']['whole_house_ceiling_surface_sf'])
        changed=copy.deepcopy(self.result);changed['regions'][0]['points_per_foot']=11
        self.assertEqual(apply(changed,self.mixed_review())['regions'][0]['ceiling_surface']['status'],'stale_source_review')

    def test_mixed_partition_rejects_gaps_overlaps_outside_and_invalid_parts(self):
        for fields in (
            {'points':[[41,0],[100,0],[100,100],[41,100]]},
            {'points':[[39,0],[100,0],[100,100],[39,100]]},
            {'points':[[40,0],[101,0],[101,100],[40,100]]},
            {'id':'flat'},{'basis':''},{'rise_per_12':float('nan')},
            {'points':[[40,0],[100,0],[float('inf'),100]]}):
            with self.subTest(fields=fields):
                review=self.mixed_review();review['decisions'][0]['parts'][1].update(fields)
                with self.assertRaises(ValueError):apply(self.result,review)

    def test_mixed_holes_are_excluded_and_vault_notes_cannot_be_flattened(self):
        self.r['holes']=[[[10,10],[20,10],[20,20],[10,20]]]
        self.d['source_sha256']=binding('plan',self.r)
        review=self.mixed_review();review['decisions'][0]['parts'][0]['holes']=copy.deepcopy(self.r['holes'])
        self.assertAlmostEqual(apply(self.result,review)['regions'][0]['ceiling_surface']['surface_area_sf'],39+60*math.sqrt(10)/3)
        self.r['ceiling_notes']=[{'kind':'vaulted'}]
        review['decisions'][0]['source_sha256']=binding('plan',self.r)
        review['decisions'][0]['parts'][1]['rise_per_12']=0
        with self.assertRaises(ValueError):apply(self.result,review)
        self.r['ceiling_notes']=[{'kind':'vault_pitch','rise_inches':6,'run_inches':12}]
        review['decisions'][0]['source_sha256']=binding('plan',self.r)
        review['decisions'][0]['parts'][1]['rise_per_12']=4
        with self.assertRaises(ValueError):apply(self.result,review)

    def test_invalid_scope_pitch_and_duplicate_reviews_reject(self):
        for fields in ({'scope':'partial'},{'rise_per_12':-1},{'rise_per_12':True},
                       {'rise_per_12':float('nan')},{'surface_type':'uniform_pitch'},{'basis':''}):
            r=copy.deepcopy(self.review);r['decisions'][0].update(fields)
            with self.assertRaises(ValueError):apply(self.result,r)
        with self.assertRaises(ValueError):apply(self.result,{**self.review,'decisions':[self.d,self.d]})
        with self.assertRaises(ValueError):apply(self.result,{**self.review,'plan_sha256':'another'})


if __name__=='__main__':unittest.main()
