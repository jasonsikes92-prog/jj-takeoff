import copy
import unittest
import tempfile
from unittest.mock import patch
from opening_schedule import from_folder
from test_wall_run_candidates import line,state
from wall_run_candidates import from_state
from wall_gap_labels import match_labels
from opening_schedule import schedule,printed_size


class OpeningSchedule(unittest.TestCase):
    def test_cardinal_direction_metadata_preserves_exact_legacy_review(self):
        label={**self.label,'direction':[1.0,0.0]}
        gaps=match_labels(self.runs,[label])
        row=schedule(self.state,self.runs,gaps,self.review)['openings'][0]
        self.assertEqual(row['review_status'],'current_source_review')
        self.assertEqual(row['review_binding_basis'],'legacy_cardinal_label_without_direction')
        self.assertEqual(row['window_component_count'],1)
        for direction in ([0,1],[.999,.001],[0,0],None):
            changed=match_labels(self.runs,[{**label,'direction':direction}])
            self.assertEqual(schedule(self.state,self.runs,changed,self.review)['openings'][0]['review_status'],'stale_source_review')

    def test_legacy_compatibility_does_not_accept_changed_label_or_geometry(self):
        for key,value in [('text','3050MU'),('bbox_pt',[21,-1,23,1])]:
            label={**self.label,'direction':[1.0,0.0],key:value}
            gaps=match_labels(self.runs,[label])
            result=schedule(self.state,self.runs,gaps,self.review)
            self.assertTrue(result['unresolved_opening_ids'])
            self.assertIsNone(result['enumerated_window_unit_count'])
        changed=copy.deepcopy(self.state);changed['measurements']['b']['points'][0][0]+=2
        runs=from_state(changed);gaps=match_labels(runs,[{**self.label,'direction':[1.0,0.0]}])
        self.assertEqual(schedule(changed,runs,gaps,self.review)['openings'][0]['review_status'],'stale_source_review')

    def test_unmatched_printed_tag_cannot_silently_disappear(self):
        gaps=copy.deepcopy(self.gaps);gaps['gaps']=[]
        result=schedule(self.state,self.runs,gaps)
        self.assertEqual(result['openings'],[])
        self.assertEqual(result['unresolved_opening_ids'],['opening-test'])
        self.assertEqual(result['unlocated_opening_tags'][0]['tag'],'3050SH')
        self.assertIsNone(result['enumerated_window_unit_count'])

    def setUp(self):
        self.state=state(line('a',[0,100],[20,100],ppf=12),line('b',[56,100],[80,100],ppf=12))
        self.label={'id':'printed-tag-test','page':1,'axis':'horizontal','text':'3050SH','bbox_pt':[30,99,40,101]}
        self.runs=from_state(self.state);self.gaps=match_labels(self.runs,[self.label])
        candidate=schedule(self.state,self.runs,self.gaps)['openings'][0]
        self.review={'plan_sha256':self.state['plan_sha256'],'reviewer':'Drawing reviewer','openings':[
            {'label_id':self.label['id'],'source_sha256':candidate['source_sha256'],'role':'window',
             'window_component_count':1,'location':'Test bedroom','basis':'Reviewed drawing'}]}

    def test_nominal_dimensions_and_gap_remain_distinct(self):
        result=schedule(self.state,self.runs,self.gaps,self.review)
        row=result['openings'][0]
        self.assertEqual(row['printed_nominal_size']['width_inches'],36)
        self.assertEqual(row['printed_nominal_size']['height_inches'],60)
        self.assertEqual(row['drawn_gap_width_inches'],36)
        self.assertIsNone(row['product_rough_opening_width_inches'])
        self.assertEqual(result['enumerated_window_unit_count'],1)
        self.assertFalse(result['coverage_certified']);self.assertIsNone(result['purchase_quantity'])

    def test_geometry_and_label_changes_withhold_roles_and_counts(self):
        s=copy.deepcopy(self.state);s['measurements']['b']['points'][0][0]=58
        r=from_state(s);g=match_labels(r,[self.label]);result=schedule(s,r,g,self.review)
        self.assertEqual(result['openings'][0]['drawn_gap_width_inches'],38)
        self.assertEqual(result['openings'][0]['printed_nominal_size']['width_inches'],36)
        self.assertEqual(result['openings'][0]['review_status'],'stale_source_review')
        self.assertIsNone(result['enumerated_window_unit_count'])
        g=match_labels(self.runs,[{**self.label,'text':'3050MU'}])
        self.assertEqual(schedule(self.state,self.runs,g,self.review)['openings'][0]['review_status'],'stale_source_review')

    def test_bare_numeric_tag_is_not_automatically_a_door(self):
        g=match_labels(self.runs,[{**self.label,'text':'3068'}]);r=copy.deepcopy(self.review)
        candidate=schedule(self.state,self.runs,g)['openings'][0]
        self.assertIsNone(candidate['role'])
        r['openings'][0].update(source_sha256=candidate['source_sha256'],role='open_passage')
        r['openings'][0].pop('window_component_count')
        result=schedule(self.state,self.runs,g,r)
        self.assertEqual(result['reviewed_role_counts']['open_passage'],1)
        self.assertEqual(result['reviewed_role_counts']['interior_door'],0)

    def test_hinged_configuration_requires_review_and_is_withheld_after_edit(self):
        r=copy.deepcopy(self.review);r['openings'][0].pop('window_component_count')
        r['openings'][0].update(role='interior_door',door_configuration='single_hinged')
        result=schedule(self.state,self.runs,self.gaps,r)
        self.assertEqual(result['openings'][0]['door_configuration'],'single_hinged')
        changed=copy.deepcopy(self.state);changed['measurements']['b']['points'][0][0]+=1
        runs=from_state(changed);gaps=match_labels(runs,[self.label])
        self.assertIsNone(schedule(changed,runs,gaps,r)['openings'][0]['door_configuration'])
        for role in ('window','open_passage','special_interior_door'):
            r['openings'][0]['role']=role
            with self.assertRaises(ValueError):schedule(self.state,self.runs,self.gaps,r)

    def test_mull_count_requires_explicit_source_count(self):
        g=match_labels(self.runs,[{**self.label,'text':'3050MU'}]);r=copy.deepcopy(self.review)
        candidate=schedule(self.state,self.runs,g)['openings'][0]
        r['openings'][0]['source_sha256']=candidate['source_sha256'];r['openings'][0].pop('window_component_count')
        self.assertIsNone(schedule(self.state,self.runs,g,r)['enumerated_window_unit_count'])
        r['openings'][0]['window_component_count']=3
        self.assertEqual(schedule(self.state,self.runs,g,r)['enumerated_window_unit_count'],3)

    def test_special_and_exterior_configurations_keep_drawn_panels_separate(self):
        r=copy.deepcopy(self.review);row=r['openings'][0];row.pop('window_component_count')
        for role,config in [('exterior_door','double_hinged'),('exterior_door','sliding'),
                ('special_interior_door','pocket'),('special_interior_door','bypass'),('special_interior_door','bifold'),
                ('special_interior_door','double_hinged')]:
            row.update(role=role,door_configuration=config,drawn_panel_count=2)
            result=schedule(self.state,self.runs,self.gaps,r)
            self.assertEqual(result['openings'][0]['drawn_panel_count'],2)
            self.assertIsNone(result['purchase_quantity'])
        for count in (True,0,-1,1.5):
            row['drawn_panel_count']=count
            with self.assertRaises(ValueError):schedule(self.state,self.runs,self.gaps,r)

    def test_missing_label_retains_stale_record_instead_of_silent_zero(self):
        g=match_labels(self.runs,[]);result=schedule(self.state,self.runs,g,self.review)
        self.assertEqual(result['stale_or_missing_label_ids'],['printed-tag-test'])
        self.assertIsNone(result['enumerated_window_unit_count'])

    def test_unsupported_sizes_and_invalid_review_are_explicit(self):
        for tag in ('10100','3050XYZ1','0000','30680'):
            self.assertIsNone(printed_size(tag))
        self.assertEqual(printed_size('2868')['height_inches'],80)
        for mutation in ('plan','duplicate','count','role','basis'):
            r=copy.deepcopy(self.review)
            if mutation=='plan':r['plan_sha256']='wrong'
            elif mutation=='duplicate':r['openings'].append(r['openings'][0])
            elif mutation=='count':r['openings'][0]['window_component_count']=True
            elif mutation=='role':r['openings'][0]['role']='assumed_door'
            else:r['openings'][0]['basis']=''
            with self.assertRaises(ValueError):schedule(self.state,self.runs,self.gaps,r)

    def test_source_only_read_does_not_load_private_company_policy(self):
        with tempfile.TemporaryDirectory() as folder,patch('opening_schedule.from_state',return_value=self.runs), \
                patch('opening_schedule.from_plan_state',return_value=self.gaps), \
                patch('opening_schedule.read_policy',side_effect=AssertionError('Private policy must not be read')) as policy:
            result=from_folder(folder,self.state,include_company_policy=False)
            self.assertNotIn('door_core_review',result);policy.assert_not_called()


if __name__=='__main__':unittest.main()
