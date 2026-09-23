import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from slab_geometry import area, compare_area, concrete_volume, grade_beam_volume, horizontal_band_area, offset_edges, rebar_grid, roll_layout


class SlabGeometryTests(unittest.TestCase):
    def test_roll_layout_counts_laps_trim_and_whole_cuts(self):
        r=roll_layout([[0,0],[30,0],[30,20],[0,20]],5,150,6)
        self.assertEqual(r['direction'],'vertical')
        self.assertEqual(r['strip_count'],7);self.assertEqual(r['roll_count'],1)
        self.assertEqual(r['cut_area_sf'],700)
        self.assertEqual(r['net_coverage_sf'],600)
        self.assertEqual(r['lap_area_sf'],60);self.assertEqual(r['trim_area_sf'],40)
        self.assertEqual(r['uncut_remaining_sf'],50)
        self.assertFalse(r['certifies_quantity'])

    def test_roll_count_does_not_divide_total_length_when_cuts_cannot_fit(self):
        r=roll_layout([[0,0],[26,0],[26,11],[0,11]],5,20,6)
        self.assertEqual(r['strip_count'],6);self.assertEqual(r['roll_count'],6)
        self.assertEqual([s['roll'] for s in r['strips']],list(range(1,7)))
        self.assertEqual(r['total_cut_length_ft'],66)

    def test_roll_notch_is_counted_as_trim_and_exact_width_needs_no_seam(self):
        r=roll_layout([[0,0],[20,0],[20,10],[10,10],[10,20],[0,20]],5,150,6)
        self.assertEqual(r['net_coverage_sf'],300)
        self.assertEqual(r['trim_area_sf'],160)
        self.assertEqual(r['net_coverage_sf']+r['trim_area_sf']+r['lap_area_sf'],r['cut_area_sf'])
        r=roll_layout([[0,0],[5,0],[5,10],[0,10]],5,150,6)
        self.assertEqual(r['strip_count'],1);self.assertEqual(r['lap_area_sf'],0)

    def test_roll_invalid_dimensions_or_unplanned_end_splices_refused(self):
        p=[[0,0],[100,0],[100,100],[0,100]]
        for width,length,lap in [(5,20,6),(5,150,60),(0,150,6),(5,None,6),(5,150,float('nan'))]:
            with self.subTest(values=(width,length,lap)),self.assertRaises(ValueError):roll_layout(p,width,length,lap)

    def test_grid_rectangle_net_laps_and_feasible_stock_cuts(self):
        g=rebar_grid([[0,0],[30,0],[30,20],[0,20]],[12,12],6,6,20)
        # 30 vertical runs at 19 feet, 20 horizontal runs at 29 feet.
        self.assertEqual(g['net_lf'],30*19+20*29)
        self.assertEqual(g['splice_count'],20)
        self.assertEqual(g['cut_lf'],1160)
        self.assertEqual(g['stock_count'],60)
        self.assertEqual(g['offcut_lf'],40)
        actual=[]
        for stock in g['stocks']:
            self.assertAlmostEqual(sum(c['length_ft'] for c in stock['cuts'])+stock['remaining_ft'],20)
            self.assertGreaterEqual(stock['remaining_ft'],-1e-9)
            actual.extend((c['run_id'],c['piece']) for c in stock['cuts'])
        expected=[(r['id'],i+1) for r in g['segments'] for i in range(len(r['cuts_ft']))]
        self.assertCountEqual(actual,expected)
        for run in g['segments']:
            self.assertAlmostEqual(sum(run['cuts_ft'])-run['splice_count']*.5,run['net_lf'])

    def test_grid_clips_notch_and_includes_boundary_runs(self):
        g=rebar_grid([[0,0],[10,0],[10,3],[4,3],[4,6],[0,6]],[12,12],6,6,20)
        self.assertEqual(g['net_lf'],3*9+3*3+4*5+6*2)
        self.assertTrue(all(p[0]<=3.5 or p[1]<=2.5 for r in g['segments'] for p in (r['start_ft'],r['end_ft'])))
        self.assertEqual(g['splice_count'],0)

    def test_grid_translation_and_unequal_spacing(self):
        points=[[0,0],[30,0],[30,20],[0,20]]
        a=rebar_grid(points,[24,12],6,6,20)
        b=rebar_grid([[x+43.25,y+71.125] for x,y in points],[24,12],6,6,20)
        self.assertEqual(a['net_lf'],16*19+20*29)
        self.assertEqual(a['net_lf'],b['net_lf'])
        self.assertEqual(a['stock_count'],b['stock_count'])

    def test_grid_invalid_dimensions_and_collapsed_setback_refused(self):
        p=[[0,0],[30,0],[30,20],[0,20]]
        for spacing,setback,lap,stock in [([12,0],6,6,20),([12,12],0,6,20),([12,12],6,240,20),([12,12],180,6,20),([12,12],6,float('nan'),20)]:
            with self.subTest(values=(spacing,setback,lap,stock)),self.assertRaises(ValueError):
                rebar_grid(p,spacing,setback,lap,stock)

    def test_grid_balances_tiny_final_bay_without_changing_setbacks_or_count(self):
        points=[[0,0],[25,0],[25,10.006],[0,10.006]]
        old=rebar_grid(points,[12,12],6,30,20)
        new=rebar_grid(points,[12,12],6,30,20,balance_far_edge=True)
        self.assertEqual(old['run_count'],new['run_count'])
        for direction,cross in [('horizontal',1),('vertical',0)]:
            coordinates=sorted({r['start_ft'][cross] for r in new['segments'] if r['direction']==direction})
            self.assertAlmostEqual(coordinates[0],.5)
            self.assertAlmostEqual(coordinates[-1],(10.006 if cross else 25)-.5)
            gaps=[b-a for a,b in zip(coordinates,coordinates[1:])]
            self.assertGreaterEqual(min(gaps),.5)
            self.assertLessEqual(max(gaps),1+1e-9)
        self.assertEqual(old['net_lf'],new['net_lf'])
        self.assertEqual(old['stock_count'],new['stock_count'])
        exact=[[0,0],[25,0],[25,10],[0,10]]
        a=rebar_grid(exact,[12,12],6,30,20)
        b=rebar_grid(exact,[12,12],6,30,20,balance_far_edge=True)
        self.assertEqual(a['segments'],b['segments'])

    def test_grade_beam_two_45_degree_sides(self):
        r=grade_beam_volume(100,4,8,12,10,45)
        # 12x4 rectangle plus two 4x4/2 triangles; excludes the uniform slab.
        expected_section=12*4+2*(4*4/2)
        self.assertAlmostEqual(r['side_run_inches'],4)
        self.assertAlmostEqual(r['top_width_inches'],20)
        self.assertAlmostEqual(r['additional_section_square_inches'],expected_section)
        self.assertAlmostEqual(r['extra_beam_cy'],100*expected_section/144/27)
        self.assertAlmostEqual(r['with_waste_cy'],100*expected_section/144/27*1.10)

    def test_grade_beam_invalid_side_angle_refused(self):
        for angle in (0,-45,91,None,float('nan')):
            with self.subTest(angle=angle),self.assertRaises(ValueError):
                grade_beam_volume(100,4,8,12,10,angle)

    def test_grade_beam_uses_only_depth_below_slab(self):
        r=grade_beam_volume(100,4,8,12,10)
        self.assertEqual(r['additional_depth_inches'],4)
        self.assertAlmostEqual(r['extra_beam_cy'],100/81)
        self.assertAlmostEqual(r['waste_cy'],10/81)
        self.assertAlmostEqual(r['with_waste_cy'],110/81)
        self.assertTrue(r['intersection_review_required'])
        self.assertFalse(r['certifies_quantity'])

    def test_grade_beam_zero_length_and_flush_depth(self):
        for length,depth in [(0,8),(100,4)]:
            r=grade_beam_volume(length,4,depth,12,10)
            self.assertEqual(r['with_waste_cy'],0)
            self.assertFalse(r['intersection_review_required'])

    def test_grade_beam_rejects_missing_or_invalid_dimensions(self):
        cases=[(-1,4,8,12,10),(100,4,3,12,10),(100,4,8,0,10),
               (100,4,8,12,-10),(None,4,8,12,10),(100,4,8,None,10),
               (float('nan'),4,8,12,10),(100,4,float('inf'),12,10)]
        for args in cases:
            with self.subTest(args=args),self.assertRaises(ValueError):grade_beam_volume(*args)

    def test_four_inch_overlap_two_sides(self):
        p=[[0,0],[20,0],[20,10],[0,10]]
        q=offset_edges(p,[1/3,1/3,0,0])
        expected=(20+1/3)*(10+1/3)
        self.assertAlmostEqual(area(q),expected)
        self.assertAlmostEqual(horizontal_band_area(q),expected)

    def test_concave_offsets_keep_notch(self):
        p=[[0,0],[20,0],[20,10],[10,10],[10,20],[0,20]]
        q=offset_edges(p,[1,1,1,1,1,1])
        self.assertAlmostEqual(area(q),22*22-10*10)
        self.assertAlmostEqual(horizontal_band_area(q),area(q))

    def test_mixed_faces_are_independent(self):
        q=offset_edges([[0,0],[20,0],[20,10],[0,10]],[1/3,1/3,2/3,2/3])
        self.assertAlmostEqual(area(q),21*11)

    def test_reject_nonorthogonal_or_reverse_source(self):
        for p in [[[0,0],[10,1],[10,10],[0,10]],[[0,0],[0,10],[10,10],[10,0]]]:
            with self.assertRaises(ValueError):offset_edges(p,[1]*4)

    def test_tolerance_includes_both_five_percent_boundaries(self):
        for n in (95,100,105):
            self.assertTrue(compare_area(n,100,5,True)['within_tolerance'])
        for n in (94.99,105.01):
            self.assertFalse(compare_area(n,100,5,True)['within_tolerance'])

    def test_different_scope_cannot_pass_by_proximity(self):
        check=compare_area(101,100,5,False)
        self.assertIsNone(check['within_tolerance'])
        self.assertFalse(check['certifies_quantity'])

    def test_invalid_comparison_is_refused(self):
        for n in (0,-1,float('nan')):
            with self.assertRaises(ValueError):compare_area(n,100,5,True)

    def test_sloped_edge_starts_eight_inches_above_bottom(self):
        p=[[0,0],[20,0],[20,10],[0,10]]
        r=concrete_volume(p,[2,3],4,24,16,8,45,10)
        # Two adjacent edges: band area = 30w - w^2; its corner is counted once.
        a,b=16/12,28/12
        expected=(8/12*(30*a-a*a)+1*(30*(a+b)/2-(a*a+a*b+b*b)/3))/27
        self.assertAlmostEqual(r['extra_edge_cy'],expected)
        self.assertAlmostEqual(r['slab_cy'],200/81)
        self.assertAlmostEqual(r['haunch_rise_inches'],12)
        self.assertAlmostEqual(r['haunch_run_inches'],12)
        self.assertAlmostEqual(r['with_waste_cy'],(200/81+expected)*1.10)
        self.assertAlmostEqual(r['independent_extra_cy'],expected,places=6)

    def test_full_perimeter_corner_corrections(self):
        p=[[0,0],[20,0],[20,10],[0,10]]
        r=concrete_volume(p,[0,1,2,3],4,24,16,8,45,10)
        a,b=16/12,28/12
        expected=(8/12*(60*a-4*a*a)+60*(a+b)/2-4*(a*a+a*b+b*b)/3)/27
        self.assertAlmostEqual(r['extra_edge_cy'],expected)

    def test_stepped_exposed_chain_counts_inside_and_outside_corners_once(self):
        p=[[0,0],[40,0],[40,27],[20,27],[20,30],[0,30]]
        r=concrete_volume(p,[2,3,4,5],4,24,16,8,45,10)
        # 73 LF; two outside turns subtract 2w^2, one inside turn adds w^2.
        # The 3-foot step exceeds the maximum 28-inch haunch width.
        a,b=16/12,28/12
        expected=(8/12*(73*a-a*a)+73*(a+b)/2-(a*a+a*b+b*b)/3)/27
        self.assertAlmostEqual(r['extra_edge_cy'],expected)
        self.assertAlmostEqual(r['slab_cy'],(40*30-20*3)/81)
        self.assertAlmostEqual(r['with_waste_cy'],(r['slab_cy']+expected)*1.10)

    def test_invalid_section_or_collapsed_haunch_refused(self):
        p=[[0,0],[20,0],[20,10],[0,10]]
        for depth,width in [(10,16),(24,240)]:
            with self.assertRaises(ValueError):concrete_volume(p,[2,3],4,depth,width,8,45,10)

    def test_haunch_stops_at_short_attached_wall_offset(self):
        p=[[0,1],[1,1],[1,0],[20,0],[20,10],[0,10]]
        r=concrete_volume(p,[5],4,24,16,8,45,10)
        # A nine-foot run terminates at the wall; it cannot extend into the upper notch.
        expected=9*(16*20+12*12/2)/144/27
        self.assertAlmostEqual(r['extra_edge_cy'],expected)


if __name__=='__main__':unittest.main()
