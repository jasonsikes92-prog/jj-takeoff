import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from framing_component_review import import_components
from measurement_quantities import geometry_digest


class FramingComponentReview(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.state={'plan_sha256':'plan','version':1,'measurements':{
            'W1':{'id':'W1','page':1,'kind':'length','points':[[0,0],[96,0]],'points_per_foot':12}}}
        self.draft={'plan_sha256':'plan','rows':[{'excel_row':'100','cost_type':'MATERIAL',
            'completion_status':'evidence_in_progress','draft_quantity':None,'line_cost':None,
            'assembly_inputs':[{'id':'existing','quantity':17}],'markup_pct':'15'},
            {'excel_row':'82','line_cost':190,'draft_quantity':1}],
            'whole_house_total':None,'estimate_released':False}
        inputs={'plan_sha256':'plan','points_per_foot':12,'first_center_inches':.75,
            'runs':[{'id':'W1','orientation':'horizontal','coordinate_pt':0,
                     'start_pt':0,'end_pt':96,'source':'fixture wall'}],
            'zones':[{'run':'W1','assembly':name,'interval':span,'source':'fixture zone'}
                     for name,span in [('A',[-4,4]),('B',[92,100])]]}
        profile=json.loads((Path(__file__).resolve().parents[2]/'company/jnj_profile.json').read_bytes())
        assemblies={'openings':[{'id':'O1','classification':'ordinary_interior_door','source':'fixture opening'}],
                    'junctions':[]}
        self.config={'plan_sha256':'plan','template_row':'100','dependencies':[{
            'job':'.','measurements':{'W1':geometry_digest(self.state['measurements']['W1'])}}]}
        for key,value in [('field_inputs',inputs),('assembly_inputs',assemblies),('profile',profile)]:
            raw=json.dumps(value).encode();(self.folder/(key+'.json')).write_bytes(raw)
            self.config[key]={'path':key+'.json','sha256':hashlib.sha256(raw).hexdigest()}

    def run_import(self):return import_components(self.draft,self.state,self.config,self.folder)

    def test_append_partial_components_without_changing_prices_or_template_units(self):
        original=copy.deepcopy(self.draft);result=self.run_import()
        row=result['rows'][0]
        self.assertEqual(len(row['assembly_inputs']),6)
        self.assertEqual(row['assembly_inputs'][1]['quantity'],5)
        self.assertEqual(result['wall_component_review']['assembly_component_totals']['king_studs'],2)
        self.assertIsNone(row['draft_quantity']);self.assertEqual(row['markup_pct'],'15')
        self.assertEqual(result['rows'][1],original['rows'][1]);self.assertEqual(self.draft,original)
        self.assertFalse(result['estimate_released'])

    def test_edit_withholds_and_exact_restoration_recovers(self):
        original=copy.deepcopy(self.state);self.state['measurements']['W1']['points'][1][0]=108
        result=self.run_import()
        self.assertEqual(result['rows'],self.draft['rows'])
        self.assertEqual(result['wall_component_review']['status'],'withheld_geometry_changed')
        self.assertEqual(result['pending_quantities'][0]['quantity'],None)
        self.state=original
        self.assertEqual(len(self.run_import()['rows'][0]['assembly_inputs']),6)

    def test_changed_evidence_wrong_plan_or_unbound_dependencies_refused(self):
        for mutation in ({'plan_sha256':'other'},{'dependencies':[]}):
            old=copy.deepcopy(self.config);self.config.update(mutation)
            with self.assertRaises(ValueError):self.run_import()
            self.config=old
        (self.folder/'field_inputs.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'evidence changed'):self.run_import()

    def live_result(self):
        return {'plan_sha256':'plan','profile_sha256':self.config['profile']['sha256'],
            'spacing_inches':16,'first_center_inches':.75,'field_count':7,'reserved_count':2,
            'field_studs':[{'id':f'live-{i}'} for i in range(7)],'basis':'live fixture','remaining':[],
            'measurement_dependencies':[{'job':str(self.folder.resolve()),'version':1}],
            'evidence_sha256':'interior','exterior_evidence_sha256':'exterior',
            'geometry_sha256':{'W1':'live'},'exterior_geometry_sha256':{}}

    def test_live_field_updates_after_edit_without_releasing_stale_assemblies(self):
        self.config['live_field_layout']=True
        self.state['measurements']['W1']['points'][1][0]=108
        with patch('framing_component_review.live_field_layout',return_value=self.live_result()):
            result=self.run_import()
        items=result['rows'][0]['assembly_inputs']
        self.assertEqual([q['id'] for q in items],['existing','wall-component-field-studs'])
        self.assertEqual(items[-1]['quantity'],7)
        self.assertFalse(items[-1]['certified']);self.assertFalse(items[-1]['order_released'])
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(result['wall_component_review']['status'],'field_recalculated_assemblies_withheld')
        self.assertNotIn('assembly_component_totals',result['wall_component_review'])
        self.assertIsNone(result['pending_quantities'][0]['quantity'])

    def test_live_field_preserves_other_allowances_when_geometry_is_unchanged(self):
        self.config['live_field_layout']=True
        with patch('framing_component_review.live_field_layout',return_value=self.live_result()):
            result=self.run_import()
        self.assertEqual(len(result['rows'][0]['assembly_inputs']),6)
        self.assertEqual(result['wall_component_review']['assembly_component_totals']['king_studs'],2)
        self.assertEqual(result['rows'][1],self.draft['rows'][1])

    def test_live_field_rejects_inconsistent_practices_or_versions_and_never_falls_back(self):
        self.config['live_field_layout']=True
        for changes in [{'profile_sha256':'wrong'},{'spacing_inches':24},{'plan_sha256':'other'},
                        {'measurement_dependencies':[{'job':str(self.folder.resolve()),'version':2}]}]:
            with patch('framing_component_review.live_field_layout',return_value={**self.live_result(),**changes}):
                with self.assertRaises(ValueError):self.run_import()
        with patch('framing_component_review.live_field_layout',side_effect=ValueError('Disconnected wall')):
            with self.assertRaisesRegex(ValueError,'Disconnected wall'):self.run_import()

    def test_duplicate_import_and_incompatible_row_refused(self):
        original=copy.deepcopy(self.draft);self.draft=self.run_import()
        with self.assertRaisesRegex(ValueError,'already imported'):self.run_import()
        for mutation in ({'line_cost':100},{'draft_quantity':100},{'covered_by_package':'bid'},
                         {'completion_status':'not_applicable_source_reviewed'}):
            self.draft=copy.deepcopy(original);self.draft['rows'][0].update(mutation)
            with self.assertRaises(ValueError):self.run_import()


if __name__=='__main__':unittest.main()
