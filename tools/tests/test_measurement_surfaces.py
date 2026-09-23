import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup
from measurement_estimate import template_draft


class SurfaceAssemblies(unittest.TestCase):
    def setUp(self):
        metadata={'width_pt':500,'height_pt':500,'points_per_foot':10}
        self.state={'plan_sha256':'plan','version':1,'measurements':{
            'room':{**metadata,'kind':'area','points':[[0,0],[100,0],[100,100],[0,100]]},
            'door':{**metadata,'kind':'length','points':[[20,0],[50,0]]}}}
        self.rule={'id':'walls','label':'Wall field','measurement_ids':['room','door'],
            'unit':'SF','rounding':'whole_up','use':'assembly_input','template_rows':['222'],
            'basis':'Test geometry','remaining':['Finish exclusions'],
            'surface_components':[
                {'id':'room-walls','measurement_id':'room','kind':'perimeter_wall','height_ft':9,
                 'height_source':'Test plan','operation':'add'},
                {'id':'door-room-side','measurement_id':'door','kind':'length_wall','height_ft':7,
                 'height_source':'Test opening schedule','operation':'deduct'}]}
        self.rules={'plan_sha256':'plan','rules':[self.rule]}

    def test_geometry_edit_recalculates_surface_and_template_retains_partial_scope(self):
        q=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(q['quantity'],339)
        self.assertEqual(q['surface_assembly']['gross_sf'],360)
        self.state['measurements']['door']['points'][1][0]=60
        template={'rows':[{'excel_row':'222','row_id':'drywall','cost_type':'SUBCONTRACTOR',
                          'completion_status':'evidence_in_progress','unit':'sq ft','markup_pct':'7'}]}
        draft=template_draft(self.state,self.rules,template)
        self.assertEqual(draft['rows'][0]['assembly_inputs'][0]['quantity'],332)
        self.assertIsNone(draft['rows'][0]['draft_quantity'])
        self.assertEqual(draft['rows'][0]['markup_pct'],'7')
        self.assertIsNone(draft['whole_house_total'])

    def test_two_physical_sides_can_share_one_opening_measurement(self):
        term=copy.deepcopy(self.rule['surface_components'][1]);term['id']='other-side'
        self.rule['surface_components'].append(term)
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],318)

    def test_invalid_dimensions_duplicate_faces_and_missing_dependencies_refused(self):
        for change in ('height','source','duplicate','missing','unused','unit','excess'):
            rules=copy.deepcopy(self.rules);r=rules['rules'][0];terms=r['surface_components']
            if change=='height':terms[0]['height_ft']=float('nan')
            if change=='source':terms[0]['height_source']=''
            if change=='duplicate':terms.append(copy.deepcopy(terms[0]))
            if change=='missing':terms[0]['measurement_id']='absent'
            if change=='unused':terms.pop()
            if change=='unit':terms[0]['kind']='length_wall'
            if change=='excess':terms[1]['height_ft']=200
            with self.subTest(change=change),self.assertRaises(ValueError):rollup(self.state,rules)

    def test_candidate_review_gate_still_applies_to_surface_assemblies(self):
        self.state['measurements']['room']['engine_line_ids']=['candidate']
        with self.assertRaisesRegex(ValueError,'current scope review'):rollup(self.state,self.rules)

    def test_vault_increment_deducts_projection_not_sloped_surface(self):
        self.state['measurements']['room']['surface_factor']=1.25
        self.rule['measurement_ids']=['room']
        self.rule['surface_components']=[
            {'id':'vault-face','measurement_id':'room','kind':'area','operation':'add'},
            {'id':'already-counted-horizontal','measurement_id':'room','kind':'projected_area','operation':'deduct'}]
        value=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(value['quantity'],25)
        self.assertEqual(value['surface_assembly']['gross_sf'],125)
        self.assertEqual(value['surface_assembly']['deductions_sf'],100)

    def measured_height_rule(self):
        self.state['measurements']['height']={**self.state['measurements']['door'],
            'points_per_foot':20,'points':[[150,0],[150,140]]}
        self.state['measurements']['other']={**self.state['measurements']['door'],'points':[[0,10],[50,10]]}
        self.rule['measurement_ids']=['door','other','height']
        self.rule['surface_components']=[{'id':identity,'measurement_id':identity,'kind':'length_wall',
            'height_measurement_id':'height','height_source':'Reviewed elevation band','operation':'add'}
            for identity in ['door','other']]

    def test_shared_measured_height_recalculates_both_faces_and_uses_each_scale(self):
        self.measured_height_rule()
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],56)
        self.state['measurements']['height']['points'][1][1]=160
        result=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(result['quantity'],64)
        self.assertEqual([t['resolved_height_ft'] for t in result['surface_assembly']['components']],[8,8])
        self.state['measurements']['door']['points'][1][0]=60
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],72)

    def test_bent_or_diagonal_height_is_pending_not_a_wall_area(self):
        self.measured_height_rule()
        for points in [[[150,0],[160,140]],[[150,0],[150,70],[150,140]],[[150,0],[150,0]]]:
            self.state['measurements']['height']['points']=points
            with self.subTest(points=points):
                result=rollup(self.state,self.rules)
                self.assertEqual(result['quantities'],[])
                self.assertEqual(result['pending_quantities'][0]['invalid_measurement_ids'],['height'])

    def test_measured_height_requires_unambiguous_declared_dependency_and_source(self):
        for invalid in ['fixed','missing','source']:
            self.setUp();self.measured_height_rule()
            term=self.rule['surface_components'][0]
            if invalid=='fixed':term['height_ft']=9
            if invalid=='missing':term['height_measurement_id']='absent'
            if invalid=='source':term['height_source']=''
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):rollup(self.state,self.rules)

    def chimney_rule(self):
        self.measured_height_rule()
        self.state['measurements']['height']['points']=[[150,0],[150,120]]
        self.state['measurements']['rear']={**self.state['measurements']['height'],'points':[[180,0],[180,40]]}
        self.state['measurements']['other']['points']=[[0,10],[100,10]]
        self.rule['measurement_ids']=['door','other','height','rear']
        self.rule['rounding']='none'
        self.rule['surface_components']=[
            {'id':'front','measurement_id':'door','kind':'length_wall','height_measurement_id':'height','height_source':'Elevation','operation':'add'},
            {'id':'rear','measurement_id':'door','kind':'length_wall','height_measurement_id':'rear','height_source':'Elevation','operation':'add'},
            *[{'id':side,'measurement_id':'other','kind':'trapezoid_wall','height_measurement_id':'height',
               'end_height_measurement_id':'rear','height_source':'Two elevation heights; level cap over one roof plane','operation':'add'} for side in ['left','right']]]

    def test_four_faces_share_dimensions_without_duplicating_controls(self):
        self.chimney_rule()
        q=rollup(self.state,self.rules)['quantities'][0]
        self.assertEqual(q['quantity'],104)  # Two ends 3*(6+2), two sides 2*10*(6+2)/2.
        self.assertEqual([c['surface_sf'] for c in q['surface_assembly']['components']],[18,6,40,40])
        self.state['measurements']['rear']['points'][1][1]+=20
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],117)
        self.state['measurements']['other']['points'][1][0]+=10
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],126)

    def test_invalid_trapezoid_end_height_is_withheld_and_restoration_recovers(self):
        self.chimney_rule()
        original=copy.deepcopy(self.state['measurements']['rear']['points'])
        for points in [[[180,0],[190,40]],[[180,0],[180,20],[180,40]],[[180,0],[180,0]]]:
            self.state['measurements']['rear']['points']=points
            with self.subTest(points=points):
                result=rollup(self.state,self.rules)
                self.assertEqual(result['quantities'],[])
                self.assertEqual(result['pending_quantities'][0]['invalid_measurement_ids'],['rear'])
        self.state['measurements']['rear']['points']=original
        self.assertEqual(rollup(self.state,self.rules)['quantities'][0]['quantity'],104)

    def test_trapezoid_requires_both_height_dependencies(self):
        self.chimney_rule()
        self.rule['surface_components'][2]['end_height_measurement_id']='absent'
        with self.assertRaisesRegex(ValueError,'two declared measured heights'):rollup(self.state,self.rules)

    def test_trapezoid_depth_rejects_bent_zero_or_sloped_run(self):
        for points,sloped in [([[0,10],[50,20],[100,10]],False),([[0,10],[0,10]],False),([[0,10],[100,10]],True)]:
            self.setUp();self.chimney_rule()
            self.state['measurements']['other']['points']=points
            if sloped:self.state['measurements']['other']['plane_gradients']=[[.5,0]]
            with self.subTest(points=points,sloped=sloped):
                result=rollup(self.state,self.rules)
                self.assertEqual(result['quantities'],[])
                self.assertEqual(result['pending_quantities'][0]['invalid_measurement_ids'],['other'])

if __name__=='__main__':unittest.main()
