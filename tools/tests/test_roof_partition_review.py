import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roof_partition_review import audit_faces


def face(identity, points, factor=1):
    return {'id':identity,'kind':'area','page':1,'width_pt':1000,'height_pt':1000,
            'points_per_foot':1,'points':points,'surface_factor':factor}


class RoofPartitionReview(unittest.TestCase):
    def test_shared_edge_with_different_segmentation_is_not_a_gap(self):
        a=face('a',[[0,0],[10,0],[10,5],[0,5]],1.25)
        b=face('b',[[0,5],[4,5],[10,5],[10,10],[0,10]],1.5)
        result=audit_faces([a,b],[[0,0],[10,0],[10,10],[0,10]])
        self.assertEqual(result['overlap_excess_sf'],0)
        self.assertEqual(result['coverage']['missing_projected_sf'],0)
        self.assertEqual(result['covered_sloped_lower_sf'],137.5)
        self.assertEqual(result['covered_sloped_upper_sf'],137.5)
        self.assertFalse(result['certified'])

    def test_overlap_retains_slope_ambiguity_and_does_not_change_input(self):
        a=face('a',[[0,0],[10,0],[10,10],[0,10]],1)
        b=face('b',[[5,0],[15,0],[15,10],[5,10]],2)
        before=copy.deepcopy([a,b]); result=audit_faces([a,b])
        self.assertEqual([a,b],before)
        self.assertEqual(result['overlap_excess_sf'],50)
        self.assertEqual(result['raw_sloped_sum_sf'],300)
        self.assertEqual(result['covered_sloped_lower_sf'],200)
        self.assertEqual(result['covered_sloped_upper_sf'],250)
        self.assertIsNone(result['coverage'])

    def test_triple_overlap_distinguishes_excess_from_physical_overlap(self):
        items=[face(str(i),[[0,0],[10,0],[10,10],[0,10]]) for i in range(3)]
        result=audit_faces(items)
        self.assertEqual(result['overlap_excess_sf'],200)
        self.assertEqual(result['overlapped_footprint_sf'],100)

    def test_overlap_location_preserves_holes_scale_and_source_ownership(self):
        from shapely.geometry import Polygon
        a=face('a',[[0,0],[20,0],[20,20],[0,20]])
        b=face('b',[[5,5],[15,5],[15,15],[5,15]])
        cut=face('cut',[[7,7],[13,7],[13,13],[7,13]])
        terms=[{'measurement_id':i,'kind':'area','operation':'add'} for i in ('a','b')]
        terms.append({'measurement_id':'cut','kind':'area','operation':'deduct','cutout_of':'b'})
        result=audit_faces([a,b,cut],cutout_terms=terms)
        region,=result['overlap_cells']
        self.assertEqual(region['area_sf'],64)
        self.assertEqual(len(region['holes']),1)
        self.assertEqual(Polygon(region['points'],region['holes']).area/region['points_per_foot']**2,64)
        self.assertEqual(set(region['source_ids']),{'a','b'})
        self.assertEqual(region['page'],1)
        reversed_result=audit_faces([cut,b,a],cutout_terms=terms)
        self.assertEqual(region['id'],reversed_result['overlap_cells'][0]['id'])
        changed=copy.deepcopy(b);changed['points'][1][0]=16
        changed_result=audit_faces([a,changed,cut],cutout_terms=terms)
        self.assertNotEqual(region['id'],changed_result['overlap_cells'][0]['id'])

    def test_outline_detects_missing_and_outside_scope_separately(self):
        a=face('a',[[0,0],[4,0],[4,10],[0,10]])
        b=face('b',[[6,0],[11,0],[11,10],[6,10]])
        result=audit_faces([a,b],[[0,0],[10,0],[10,10],[0,10]])
        self.assertEqual(result['connected_components'],2)
        self.assertEqual(result['coverage']['missing_projected_sf'],20)
        self.assertEqual(result['coverage']['outside_projected_sf'],10)

    def test_translation_and_scale_do_not_change_physical_quantities(self):
        original=face('a',[[0,0],[10,0],[10,10],[0,10]],math.sqrt(2))
        changed={**original,'points':[[2*x+100,2*y+50] for x,y in original['points']],
                 'points_per_foot':2}
        a=audit_faces([original]); b=audit_faces([changed])
        self.assertAlmostEqual(a['covered_sloped_upper_sf'],b['covered_sloped_upper_sf'])

    def test_invalid_or_mixed_frame_inputs_refused(self):
        a=face('a',[[0,0],[10,0],[10,10],[0,10]])
        for items in ([],[a,a],[a,{**a,'id':'b','page':2}],
                      [{**a,'points_per_foot':True}],[{**a,'surface_factor':float('nan')}],
                      [{**a,'points':[[0,0],[10,10],[0,10],[10,0]]}]):
            with self.subTest(items=items),self.assertRaises(ValueError): audit_faces(items)

    def assembly(self):
        main=face('main',[[0,0],[10,0],[10,10],[0,10]],1.25)
        cut=face('cut',[[3,3],[7,3],[7,7],[3,7]],1.25)
        dormer=face('dormer',cut['points'],1.5)
        terms=[{'measurement_id':m['id'],'kind':'area','operation':'add'} for m in (main,dormer)]
        terms.append({'measurement_id':'cut','kind':'area','operation':'deduct','cutout_of':'main'})
        return [main,cut,dormer],terms

    def test_cutout_then_dormer_uses_each_plane_factor_once(self):
        measurements,terms=self.assembly();before=copy.deepcopy(measurements)
        result=audit_faces(measurements,measurements[0]['points'],terms)
        self.assertEqual(result['face_count'],2)
        self.assertEqual(result['raw_projected_sum_sf'],100)
        self.assertEqual(result['overlap_excess_sf'],0)
        self.assertEqual(result['raw_sloped_sum_sf'],84*1.25+16*1.5)
        self.assertEqual(result['coverage']['missing_regions'],[])
        self.assertEqual(result['parent_cutout_deductions'][0]['cutout_ids'],['cut'])
        self.assertEqual(measurements,before)
        self.assertFalse(result['certified'])

    def test_unfilled_cutout_is_located_as_missing_geometry(self):
        measurements,terms=self.assembly()
        result=audit_faces(measurements[:2],measurements[0]['points'],[t for t in terms if t['measurement_id']!='dormer'])
        self.assertEqual(result['coverage']['missing_projected_sf'],16)
        self.assertEqual(len(result['coverage']['missing_regions']),1)
        self.assertEqual(result['enclosed_voids'][0]['projected_area_sf'],16)

    def test_component_mappings_cannot_omit_duplicate_or_unparent_deductions(self):
        measurements,terms=self.assembly()
        bad=copy.deepcopy(terms);bad[-1].pop('cutout_of')
        for candidate in (bad,terms[:-1],terms+[terms[0]]):
            with self.assertRaises(ValueError):audit_faces(measurements,cutout_terms=candidate)

    def test_invalid_cutout_placement_or_slope_is_not_subtracted(self):
        measurements,terms=self.assembly()
        for updates in ({'surface_factor':2},{'points':[[9,3],[12,3],[12,7],[9,7]]}):
            changed=copy.deepcopy(measurements);changed[1].update(updates)
            with self.assertRaisesRegex(ValueError,'Invalid roof cutout'):audit_faces(changed,cutout_terms=terms)

    def test_dormer_crossing_cutout_reports_overlap_without_hiding_it(self):
        measurements,terms=self.assembly()
        measurements[2]['points']=[[3,3],[8,3],[8,7],[3,7]]
        result=audit_faces(measurements,cutout_terms=terms)
        self.assertEqual(result['overlap_excess_sf'],4)
        self.assertEqual(result['overlapped_footprint_sf'],4)
        self.assertEqual(set(result['overlap_cells'][0]['source_ids']),{'main','dormer'})


if __name__=='__main__': unittest.main()
