import copy
import unittest
from wall_run_candidates import from_state,WALL_METHOD
from wall_enclosure_candidates import candidates


class WallEnclosures(unittest.TestCase):
    def setUp(self):
        self.state={'plan_sha256':'plan','version':1,'measurements':{}}
        for identity,points in [('top',[[4,2],[116,2]]),('bottom',[[4,118],[116,118]]),
                ('left',[[2,4],[2,116]]),('right',[[118,4],[118,116]])]:
            self.add(identity,points)

    def add(self,identity,points,page=1,ppf=12):
        self.state['measurements'][identity]={'id':identity,'kind':'length','source_method':WALL_METHOD,
            'points':points,'page':page,'points_per_foot':ppf,'drawn_thickness_inches':4}

    def sources(self,opening_reviewed=False):
        runs=from_state(self.state)
        gaps={k:runs[k] for k in ('plan_sha256','measurement_version')};gaps['gaps']=[]
        openings={**gaps,'openings':[],'unresolved_opening_ids':[],'stale_or_missing_label_ids':[]}
        for run in runs['run_candidates']:
            for i,gap in enumerate(run['gaps']):
                identity=run['id']+':'+str(i)
                gaps['gaps'].append({**gap,'id':identity,'run_id':run['id'],'page':run['page'],
                    'status':'unique_tag_location_candidate' if opening_reviewed else 'no_aligned_tag'})
                if opening_reviewed:openings['openings'].append({'gap_id':identity,'opening_id':'door',
                    'review_status':'current_source_review'})
        return runs,gaps,openings

    def calculate(self,opening_reviewed=False):return candidates(self.state,*self.sources(opening_reviewed))

    def test_touching_corners_close_exact_outer_faces_without_double_counting(self):
        before=copy.deepcopy(self.state);result=self.calculate();enclosure=result['candidate_enclosures'][0]
        self.assertEqual(enclosure['gross_boundary_sf'],100)
        self.assertEqual(len(result['junction_rectangles']),4)
        self.assertAlmostEqual(enclosure['enclosed_void_sf'],(112/12)**2)
        self.assertAlmostEqual(enclosure['enclosed_void_sf']+enclosure['wall_and_closure_footprint_sf'],100)
        self.add('duplicate',[[4,2],[116,2]])
        self.assertEqual(self.calculate()['candidate_enclosures'][0]['gross_boundary_sf'],100)
        self.assertEqual(before['measurements']['top'],self.state['measurements']['top'])
        self.assertFalse(result['certified']);self.assertIsNone(result['whole_floor_area'])

    def test_opening_requires_current_review_and_uses_drawn_not_nominal_span(self):
        self.state['measurements']['top']['points'][1][0]=48
        self.add('top2',[[72,2],[116,2]])
        self.assertEqual(self.calculate()['candidate_enclosures'],[])
        runs,gaps,openings=self.sources(True)
        openings['openings'][0]['printed_nominal_size']={'width_inches':36}
        result=candidates(self.state,runs,gaps,openings)
        self.assertEqual(result['candidate_enclosures'][0]['gross_boundary_sf'],100)
        self.assertEqual(result['gap_closures'][0]['bounds_pt'],[48,0,72,4])
        openings['openings'][0]['review_status']='stale_source_review'
        self.assertEqual(candidates(self.state,runs,gaps,openings)['candidate_enclosures'],[])

    def test_separate_wall_gap_and_detached_piece_are_not_filled(self):
        self.state['measurements']['top']['points'][1][0]=48
        self.add('top2',[[72,2],[116,2]])
        runs,gaps,openings=self.sources();gaps['gaps'][0]['status']='separate_wall_runs'
        result=candidates(self.state,runs,gaps,openings)
        self.assertEqual(result['candidate_enclosures'],[])
        self.assertEqual(result['gap_closures'],[])
        self.assertTrue(result['unclosed_wall_components'])

    def test_near_but_not_touching_walls_do_not_gain_a_corner(self):
        self.state['measurements']['top']['points'][0][0]=5
        self.assertEqual(self.calculate()['candidate_enclosures'],[])

    def test_concave_footprint_keeps_recess_instead_of_bounding_box(self):
        self.state['measurements']['right']['points'][1][1]=56
        self.state['measurements']['bottom']['points'][1][0]=56
        self.add('step',[[60,58],[116,58]])
        self.add('inner',[[58,60],[58,116]])
        result=self.calculate()
        self.assertEqual(result['candidate_enclosures'][0]['gross_boundary_sf'],75)

    def test_pages_and_scales_never_connect_and_disconnected_enclosures_stay_separate(self):
        self.state['measurements']['top']['page']=2
        self.assertEqual(self.calculate()['candidate_enclosures'],[])
        self.state['measurements']['top']['page']=1
        self.state['measurements']['top']['points_per_foot']=6
        self.assertEqual(self.calculate()['candidate_enclosures'],[])
        self.state['measurements']['top']['points_per_foot']=12
        for identity,m in list(self.state['measurements'].items()):
            self.add(identity+'2',[[x+240,y] for x,y in m['points']])
        self.assertEqual([e['gross_boundary_sf'] for e in self.calculate()['candidate_enclosures']],[100,100])

    def test_mismatched_sources_are_rejected_and_changed_geometry_has_new_digest(self):
        first=self.calculate();runs,gaps,openings=self.sources()
        openings['measurement_version']=2
        with self.assertRaises(ValueError):candidates(self.state,runs,gaps,openings)
        openings['measurement_version']=1;openings['plan_sha256']='other'
        with self.assertRaises(ValueError):candidates(self.state,runs,gaps,openings)
        self.state['measurements']['top']['points'][0][0]=5
        self.assertNotEqual(first['source_sha256'],self.calculate()['source_sha256'])

    def test_interior_regions_subtract_detached_column_and_keep_gross_boundary(self):
        original=self.calculate()['candidate_enclosures']
        self.add('column',[[60,54],[60,66]])
        self.state['measurements']['column']['drawn_thickness_inches']=12
        result=self.calculate();region=result['interior_region_candidates'][0]
        self.assertEqual(result['candidate_enclosures'],original)
        self.assertEqual(len(region['holes']),1)
        self.assertAlmostEqual(region['boundary_area_sf'],(112/12)**2-1)
        self.assertIsNone(region['floor_finish_quantity'])

    def test_nested_wall_room_does_not_double_count_internal_space(self):
        for identity,points in [('inner-top',[[44,42],[76,42]]),('inner-bottom',[[44,78],[76,78]]),
                ('inner-left',[[42,44],[42,76]]),('inner-right',[[78,44],[78,76]])]:self.add(identity,points)
        result=self.calculate();regions=result['interior_region_candidates']
        self.assertEqual(len(regions),2)
        self.assertAlmostEqual(sum(r['boundary_area_sf'] for r in regions),(112**2-40**2+32**2)/144)
        from shapely.geometry import Polygon
        a,b=[Polygon(r['points'],r['holes']) for r in regions]
        self.assertEqual(a.intersection(b).area,0)


if __name__=='__main__':unittest.main()
