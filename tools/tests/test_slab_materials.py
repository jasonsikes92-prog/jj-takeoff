import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from slab_materials import whole_units, substrate_coverage, plastic_layout, material_allowances, grid_crossings, footer_stock_allowance, gravel_truckloads
from slab_geometry import concrete_volume, material_coverage_cells, rebar_grid


class MaterialTests(unittest.TestCase):
    def test_full_stone_trucks_convert_unrounded_volume_and_round_once(self):
        delivery={'tons_per_cy':1.35,'tons_per_load':16}
        for cy,loads in [(0,0),(8.038325,1),(10,1),(16/1.35+0.01,2)]:
            r=gravel_truckloads(cy,delivery)
            self.assertEqual(r['truckloads'],loads);self.assertAlmostEqual(r['required_tons'],cy*1.35)
            self.assertEqual(r['purchased_tons'],loads*16)
            self.assertAlmostEqual(r['cy_per_load'],16/1.35)
        self.assertEqual(gravel_truckloads(10,{'tons_per_cy':1.6,'tons_per_load':16})['truckloads'],1)
        for density in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError):gravel_truckloads(8,dict(delivery,tons_per_cy=density))

    def test_purchase_rounding_uses_package_size_and_does_not_add_to_exact_units(self):
        for q,size,expected in [(15.865693,1,16),(16,1,16),(2400,2000,2),(2000,2000,1),(101,100,2),(0,20,0),(0.0000000001,1,1),(16.0000000001,1,17)]:
            self.assertEqual(whole_units(q,size),expected)
        for q,size in [(-1,20),(1,0),(float('nan'),1),(True,20)]:
            with self.assertRaises(ValueError):whole_units(q,size)

    def profile(self):
        return {'edge_roles':['thickened']*4,'exterior':{'bottom_width_inches':16,'angle_degrees':45,'total_depth_inches':24,'vertical_inches_above_bottom':8},
            'material_specs':{'substrate_extent':'footer_haunch_junction','bearing_overlap_inches':4,'gravel_thickness_direction':'perpendicular','gravel_depth_inches':4,
                'vapor_product':{'width_ft':20,'length_ft':100},'vapor_lap_inches':6}}

    def test_junction_surface_and_normal_gravel_on_rectangle(self):
        p=[[0,0],[10,0],[10,10],[0,10]]
        c=concrete_volume(p,list(range(4)),4,24,16,8,45,10)
        r=substrate_coverage(p,self.profile(),c)
        flat=(10-2*28/12)**2;projected=(10-2*16/12)**2
        self.assertAlmostEqual(r['flat']['net_sf'],flat)
        self.assertAlmostEqual(r['projected']['net_sf'],projected)
        self.assertAlmostEqual(r['surface_sf'],flat+(projected-flat)*math.sqrt(2))
        self.assertAlmostEqual(r['gravel_in_place_cy'],r['surface_sf']/81)
        self.assertEqual(r['stopping_depth_below_slab_top_inches'],16)
        vertical=self.profile();vertical['material_specs']['gravel_thickness_direction']='vertical'
        self.assertAlmostEqual(substrate_coverage(p,vertical,c)['gravel_in_place_cy'],projected/81)
        self.assertGreater(r['gravel_in_place_cy'],projected/81)
        layout=plastic_layout(r,self.profile()['material_specs'],c)
        self.assertGreaterEqual(layout['cut_area_sf'],r['surface_sf']+layout['lap_area_sf'])
        self.assertAlmostEqual(layout['net_coverage_sf']+layout['lap_area_sf']+layout['trim_area_sf'],layout['cut_area_sf'])
        self.assertAlmostEqual(layout['cut_area_sf']+layout['uncut_remaining_sf'],layout['purchased_area_sf'])

    def test_mixed_edges_and_small_notch_partition_without_double_counting(self):
        p=[[0,0],[2,0],[2,-.3],[12,-.3],[12,10],[0,10]]
        roles=['bearing','bearing','bearing','bearing','thickened','thickened']
        r=material_coverage_cells(p,roles,4,28)
        for i,(a,b,c,d) in enumerate(r['rectangles_ft']):
            for e,f,g,h in r['rectangles_ft'][i+1:]:self.assertLessEqual(max(0,min(c,g)-max(a,e))*max(0,min(d,h)-max(b,f)),1e-9)
        shifted=material_coverage_cells([[x+40,y+70] for x,y in p],roles,4,28)
        self.assertAlmostEqual(r['net_sf'],shifted['net_sf'])
        with self.assertRaises(ValueError):material_coverage_cells([[0,0],[2,0],[2,2],[0,2]],['thickened']*4,4,28)

    def test_chairs_follow_actual_grid_crossings_and_separate_deep_edges(self):
        p=[[0,0],[10,0],[10,10],[0,10]];profile=self.profile()
        profile['material_specs'].update(rebar_grid_included=True,footer_rebar_runs=2,footer_rebar_size='#4',rebar_stock_length_ft=20)
        profile['support_rules']={'grid':{'model':'911','pack_size':50,'source':'TEST manufacturer'},
            'mesh':{'model':'944','pack_size':100,'spacing_inches':24,'source':'TEST manufacturer'},
            'footer':{'model':'928','pack_size':40,'spacing_inches':48,'source':'TEST manufacturer'}}
        c=concrete_volume(p,list(range(4)),4,24,16,8,45,10)
        g=rebar_grid(p,[12,12],6,6,20)
        self.assertEqual(len(grid_crossings(g)),100)
        result={'concrete':c,'substrate_coverage':substrate_coverage(p,profile,c),'rebar_grid':g,'thickened_edge_lf':40}
        items,chairs=material_allowances(p,profile,result)
        self.assertEqual(chairs['grid']['count'],100)
        self.assertEqual(chairs['grid']['standard_height_count'],36)
        self.assertEqual(chairs['grid']['special_height_count'],64)
        self.assertEqual(chairs['mesh']['count'],25)
        self.assertEqual(chairs['footer']['count'],16)
        self.assertEqual(items['footer_chairs']['quantity'],1)
        self.assertEqual(result['footer_rebar']['measured_lf'],80)
        self.assertIsNone(items['footer_rebar']['quantity'])
        self.assertEqual(items['grid']['quantity'],g['stock_count'])
        result.pop('rebar_grid');profile['material_specs']['rebar_grid_included']=False
        items,chairs=material_allowances(p,profile,result)
        self.assertNotIn('grid',items);self.assertNotIn('grid',chairs)

    def test_wall_starter_laps_are_inside_run_and_stocks_round_per_run(self):
        profile=self.profile();profile['edge_roles']=['bearing','bearing','thickened','thickened']
        profile['material_specs'].update(footer_end_connection='lap_to_projecting_wall_rebar',footer_stock_basis='gross_boundary_budget',
            footer_rebar_runs=2,rebar_stock_length_ft=20,footer_rebar_lap_inches=30,
            rebar_lap_rule='irc2024_no4_grade60',rebar_grade=60,footer_rebar_size='#4')
        # Two 56-foot L-shaped runs need four stock bars each once internal laps are included.
        p=[[0,0],[28,0],[28,28],[0,28]];r=footer_stock_allowance(p,profile)
        self.assertEqual(r['budget_sticks'],8);self.assertEqual(r['internal_splice_count'],6)
        self.assertEqual(r['budget_length_lf'],127);self.assertEqual(r['budget_purchase_lf'],160)
        self.assertEqual(r['wall_connection_count'],4);self.assertEqual(r['wall_lap_zone_lf'],10)
        self.assertEqual(r['added_wall_lap_lf'],0);self.assertFalse(r['fabrication_schedule_verified'])
        # Exact 20-foot run fits one stick; exceeding it requires an additional lapped stick per run.
        for width,expected in [(10,2),(10.00001,4)]:
            q=[[0,0],[width,0],[width,width],[0,width]]
            self.assertEqual(footer_stock_allowance(q,profile)['budget_sticks'],expected)
        profile['edge_roles']=['thickened']*4
        with self.assertRaisesRegex(ValueError,'one open chain'):footer_stock_allowance(p,profile)
        profile['edge_roles']=['thickened','bearing','thickened','bearing']
        with self.assertRaisesRegex(ValueError,'one open chain'):footer_stock_allowance(p,profile)
        profile['edge_roles']=['bearing','bearing','thickened','thickened']
        profile['material_specs']['footer_rebar_lap_inches']=240
        with self.assertRaisesRegex(ValueError,'shorter than stock'):footer_stock_allowance(p,profile)
        profile['material_specs']['footer_rebar_lap_inches']=6
        with self.assertRaisesRegex(ValueError,'at least 30'):footer_stock_allowance(p,profile)

    def test_mesh_span_excludes_only_mesh_edge_chairs_and_keeps_grid_chairs(self):
        p=[[0,0],[10,0],[10,10],[0,10]];profile=self.profile()
        profile['material_specs']['deep_edge_support']={'mesh':'mesh_spans_slope','grid':'chairs'}
        profile['support_rules']={'grid':{'model':'911','pack_size':50,'source':'TEST manufacturer'},
            'mesh':{'model':'944','pack_size':100,'spacing_inches':24,'source':'TEST manufacturer'}}
        c=concrete_volume(p,list(range(4)),4,24,16,8,45,10)
        result={'concrete':c,'substrate_coverage':substrate_coverage(p,profile,c),'rebar_grid':rebar_grid(p,[12,12],6,30,20)}
        items,chairs=material_allowances(p,profile,result)
        mesh=chairs['mesh'];grid=chairs['grid']
        self.assertEqual(mesh['count'],9);self.assertEqual(mesh['spanned_edge_candidate_count'],16)
        self.assertEqual(mesh['special_height_count'],0);self.assertEqual(len(mesh['positions_ft']),9)
        self.assertEqual(len(mesh['candidate_positions_ft']),25)
        self.assertEqual(grid['count'],100);self.assertEqual(grid['special_height_count'],64)
        self.assertEqual(grid['edge_support_method'],'chairs')
        self.assertEqual(items['mesh_chairs']['quantity'],1);self.assertEqual(items['grid_chairs']['quantity'],1)
        self.assertFalse(mesh['placement_verified']);self.assertNotIn('tie_wire',items)
        profile['material_specs']['grid_edge_chair_height_inches']=2
        profile['support_rules']['grid_edge']={'model':'GRPROLK42B','pack_size':40,'height_inches':2}
        items,chairs=material_allowances(p,profile,result)
        self.assertEqual(items['grid_edge_chairs']['measured_quantity'],64)
        self.assertEqual(items['grid_edge_chairs']['quantity'],2)
        self.assertEqual(items['grid_edge_chairs']['unit'],'bucket')
        self.assertEqual(items['grid_chairs']['quantity'],1)
        self.assertEqual(chairs['mesh']['special_height_count'],0)
        self.assertFalse(chairs['grid']['placement_verified'])
        profile['support_rules']['grid_edge']['height_inches']=3
        with self.assertRaisesRegex(ValueError,'differs'):material_allowances(p,profile,result)
        result.pop('substrate_coverage')
        with self.assertRaisesRegex(ValueError,'resolved flat-substrate'):material_allowances(p,profile,result)


if __name__=='__main__':unittest.main()
