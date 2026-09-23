import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'viewer'))
from area_overlap import overlaps, overlapping_measurements
from measurement_quantities import rollup
from measurement_store import MeasurementStore
from linked_quantity_reviews import import_linked_quantities
from estimate_readiness import readiness


def box(x, y, width, height):
    return [[x,y],[x+width,y],[x+width,y+height],[x,y+height]]


class AreaOverlapTests(unittest.TestCase):
    def test_rectangles_against_independent_interval_formula(self):
        for x in range(-3, 5):
            for y in range(-3, 5):
                expected = min(3,x+2)>max(0,x) and min(3,y+2)>max(0,y)
                self.assertEqual(overlaps(box(0,0,3,3),box(x,y,2,2)),expected,(x,y))

    def test_identical_contained_edge_and_point_contact(self):
        a=box(0,0,4,4)
        self.assertTrue(overlaps(a,a))
        self.assertTrue(overlaps(a,list(reversed(box(1,1,1,1)))))
        self.assertFalse(overlaps(a,box(4,0,4,4)))
        self.assertFalse(overlaps(a,box(4,4,4,4)))

    def test_concave_notch_is_not_occupied_area(self):
        l=[[0,0],[6,0],[6,2],[2,2],[2,6],[0,6]]
        self.assertFalse(overlaps(l,box(3,3,2,2)))
        self.assertTrue(overlaps(l,box(1,3,2,2)))

    def test_crossing_sloped_polygons_and_narrow_overlap(self):
        a=[[0,0],[8,7],[8,8],[0,1]]
        b=[[0,7],[8,0],[8,1],[0,8]]
        self.assertTrue(overlaps(a,b))
        self.assertTrue(overlaps(box(0,0,4,4),box(3.9999,0,4,4)))

    def fixture(self):
        measurements={identity:{'id':identity,'kind':'area','page':1,'points_per_foot':10,
                               'width_pt':500,'height_pt':500,'points':points,'dependent_rows':['267']}
                      for identity,points in [('a',box(0,0,100,100)),('b',box(100,0,100,100))]}
        state={'plan_sha256':'plan','version':1,'measurements':measurements}
        rules={'plan_sha256':'plan','rules':[{'id':'counter','label':'Counter surfaces',
            'measurement_ids':['a','b'],'unit':'SF','rounding':'none','template_rows':['267'],
            'use':'assembly_input','basis':'Two distinct surfaces','remaining':[], 'disjoint_areas':True}]}
        return state,rules

    def test_rollup_withholds_overlap_and_recovers_after_correction(self):
        state,rules=self.fixture()
        self.assertEqual(rollup(state,rules)['quantities'][0]['quantity'],200)
        state['measurements']['b']['points']=box(90,0,100,100)
        result=rollup(state,rules)
        self.assertEqual(result['quantities'],[])
        self.assertIsNone(result['pending_quantities'][0]['quantity'])
        self.assertEqual(result['pending_quantities'][0]['overlapping_measurement_ids'],[['a','b']])
        state['measurements']['b']['points']=box(100,0,100,100)
        self.assertEqual(rollup(state,rules)['quantities'][0]['quantity'],200)

    def test_different_views_scales_or_sloped_faces_are_not_comparable(self):
        for change in ({'page':2},{'points_per_foot':20},{'surface_factor':1.4}):
            state,_=self.fixture()
            state['measurements']['b'].update(change)
            with self.assertRaisesRegex(ValueError,'same calibrated'):
                overlapping_measurements(list(state['measurements'].values()))

    def test_projected_overlap_guard_preserves_sloped_surface_area(self):
        state,rules=self.fixture();rule=rules['rules'][0]
        rule.pop('disjoint_areas');rule['disjoint_projected_areas']=True
        state['measurements']['a']['surface_factor']=2**.5
        self.assertAlmostEqual(rollup(state,rules)['quantities'][0]['quantity'],100*2**.5+100)
        state['measurements']['b']['points']=box(99,0,100,100)
        result=rollup(state,rules)
        self.assertEqual(result['quantities'],[])
        self.assertEqual(result['pending_quantities'][0]['overlapping_measurement_ids'],[['a','b']])
        state['measurements']['b']['points']=box(100,0,100,100)
        self.assertAlmostEqual(rollup(state,rules)['quantities'][0]['quantity'],100*2**.5+100)

    def test_projected_overlap_still_requires_matching_view_and_scale(self):
        for change in ({'page':2},{'points_per_foot':20}):
            state,rules=self.fixture();rule=rules['rules'][0]
            rule.pop('disjoint_areas');rule['disjoint_projected_areas']=True
            state['measurements']['a']['surface_factor']=2**.5
            state['measurements']['b'].update(change)
            with self.assertRaisesRegex(ValueError,'same calibrated'):rollup(state,rules)

    def test_projected_overlap_does_not_allow_invalid_slope_factors(self):
        for factor in (0,-1,float('nan')):
            state,rules=self.fixture();rule=rules['rules'][0]
            rule.pop('disjoint_areas');rule['disjoint_projected_areas']=True
            state['measurements']['a']['surface_factor']=factor
            with self.assertRaisesRegex(ValueError,'Surface factor'):rollup(state,rules)

    def test_linked_pending_keeps_evidence_and_reserves_cost_owner(self):
        state,rules=self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);job=folder/'counter';job.mkdir()
            plan=b'fixed source';digest=hashlib.sha256(plan).hexdigest()
            (job/'plan.pdf').write_bytes(plan)
            rules['plan_sha256']=digest
            config={'plan_sha256':digest,'measurements':list(state['measurements'].values())}
            for name,value in [('measurements',config),('quantity_rules',rules)]:
                (job/(name+'.json')).write_text(json.dumps(value))
            store=MeasurementStore(job)
            store.save('b',box(90,0,100,100),1,digest,'Overlap test')
            link={'job':'counter','template_rows':['267'],
                  'config_sha256':hashlib.sha256((job/'measurements.json').read_bytes()).hexdigest(),
                  'rules_sha256':hashlib.sha256((job/'quantity_rules.json').read_bytes()).hexdigest()}
            draft={'plan_sha256':digest,'measurement_version':1,'rows':[{'row_id':'r267','name':'Countertop',
                   'parent':'Kitchen','unit':'SF','markup_pct':'15','excel_row':'267','cost_type':'MATERIAL',
                   'completion_status':'evidence_in_progress','draft_quantity':None,'assembly_inputs':[]}]}
            result=import_linked_quantities(draft,[link],folder)
            self.assertEqual(result['rows'],draft['rows'])
            self.assertEqual(result['pending_quantities'][0]['linked_review']['measurement_version'],2)
            self.assertEqual(result['pending_quantities'][0]['overlapping_measurement_ids'],[['a','b']])
            issues=readiness(result,{'rows':draft['rows']})['rows'][0]['issues']
            self.assertIn('Quantity unresolved',issues)
            self.assertIn('Measurement scope review outstanding: Counter surfaces',issues)
            with self.assertRaisesRegex(ValueError,'duplicate'):
                import_linked_quantities(draft,[link,link],folder)
            blocked=copy.deepcopy(draft);blocked['rows'][0]['draft_quantity']=100
            with self.assertRaisesRegex(ValueError,'already assigned'):
                import_linked_quantities(blocked,[link],folder)


if __name__=='__main__':
    unittest.main()
