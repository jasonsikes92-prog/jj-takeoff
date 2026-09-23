import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from company_profile import resolve
from door_policy_revision import KEY,read_policy,apply_policy


class DoorPolicyRevision(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.job=Path(self.tmp.name);self.folder=self.job/'draft_takeoff';self.folder.mkdir()
        self.base={'profile_id':'fixture','version':1,'rules':[{'key':'unrelated','value':'original','source':'fixture'}]}
        self.latest={'profile_id':'fixture','version':2,'rules':[
            {'key':'unrelated','value':'changed','source':'fixture'},
            {'key':KEY,'value':{'bedroom':'solid','other_interior':'hollow'},'source':'Owner practice'}]}
        self.overrides={};self.write_base()
        self.profile=self.folder/'door_profile.json';self.profile.write_text(json.dumps(self.latest))
        self.revision={'plan_sha256':'plan','base_intake_path':'../estimate_intake.json',
            'base_intake_sha256':self.sha(self.job/'estimate_intake.json'),'profile_path':'door_profile.json',
            'profile_sha256':self.sha(self.profile),'reviewer':'Test reviewer','basis':'Apply saved door rule only'}
        self.path=self.folder/'door_policy_revision.json'

    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def write_base(self):
        profile=self.job/'company_profile_snapshot.json';profile.write_text(json.dumps(self.base))
        intake={**resolve(self.base,{},self.overrides),'plan_sha256':'plan','company_profile_snapshot':profile.name,
            'company_profile_sha256':self.sha(profile),'company_profile_id':'fixture','company_profile_version':self.base['version'],
            'project_facts':{},'project_overrides':self.overrides}
        (self.job/'estimate_intake.json').write_text(json.dumps(intake))
    def enable(self):self.path.write_text(json.dumps(self.revision))

    def test_old_job_needs_explicit_revision_and_other_settings_are_unchanged(self):
        before=(self.job/'estimate_intake.json').read_bytes()
        self.assertIsNone(read_policy(self.folder,'plan'))
        self.enable();policy=read_policy(self.folder,'plan')
        self.assertEqual(list(policy['settings']),[KEY]);self.assertEqual(policy['settings'][KEY]['bedroom'],'solid')
        self.assertEqual(policy['base_profile_version'],1);self.assertEqual(policy['company_profile_version'],2)
        self.assertEqual((self.job/'estimate_intake.json').read_bytes(),before)

    def test_existing_project_policy_override_survives_updated_default(self):
        self.overrides={KEY:{'bedroom':'hollow'}};self.write_base()
        self.revision['base_intake_sha256']=self.sha(self.job/'estimate_intake.json');self.enable()
        policy=read_policy(self.folder,'plan')
        self.assertEqual(policy['settings'][KEY]['bedroom'],'hollow')
        self.assertEqual(policy['provenance'][KEY]['basis'],'project_override')
        self.assertEqual(len(policy['resolved_conflicts']),1)

    def test_new_job_uses_its_frozen_door_rule_without_revision(self):
        self.base=self.latest;self.write_base()
        policy=read_policy(self.folder,'plan')
        self.assertEqual(policy['settings'][KEY]['bedroom'],'solid')
        self.assertIsNone(policy['revision_sha256'])

    def test_changed_inputs_and_escaped_paths_are_rejected(self):
        for field,value in [('plan_sha256','other'),('base_intake_sha256','bad'),('profile_sha256','bad'),
                ('profile_path','../../outside.json'),('base_intake_path','../../outside.json')]:
            r={**self.revision,field:value};self.path.write_text(json.dumps(r))
            with self.assertRaises(ValueError):read_policy(self.folder,'plan')
        self.enable();p=self.job/'company_profile_snapshot.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'Base company profile changed'):read_policy(self.folder,'plan')

    def test_core_resolution_uses_only_current_room_associations_and_project_selection_wins(self):
        self.enable();policy=read_policy(self.folder,'plan')
        base={'opening_id':'door','role':'interior_door','room_class':'bedroom','role_source':'Reviewed bedroom door'}
        schedule={'plan_sha256':'plan','review_sha256':'review','stale_or_missing_label_ids':[],
            'openings':[base,{**base,'opening_id':'unknown','role':None,'room_class':None,'role_source':None},
                {**base,'opening_id':'special','role':'special_interior_door'},
                {**base,'opening_id':'passage','role':'open_passage'},
                {**base,'opening_id':'selected','project_core':'hollow','project_core_source':'Explicit project selection'}]}
        result=apply_policy(schedule,policy)
        self.assertEqual([o['core'] for o in result['openings']],['solid',None,None,None,'hollow'])
        self.assertEqual(result['openings'][-1]['basis'],'project_specification')
        self.assertEqual(result['openings'][-1]['resolved_conflict']['company_default'],'solid')
        self.assertEqual(result['purchase_quantities'],{})
        project=copy.deepcopy(policy);project['provenance'][KEY]={'basis':'project_override'}
        self.assertEqual(apply_policy(schedule,project)['openings'][0]['basis'],'project_room_policy')

    def test_toilet_room_uses_bathroom_core_unless_explicitly_overridden(self):
        self.latest['rules'][-1]['value']['bathroom']='solid'
        self.profile.write_text(json.dumps(self.latest));self.revision['profile_sha256']=self.sha(self.profile)
        self.enable();policy=read_policy(self.folder,'plan')
        opening={'opening_id':'wc','role':'interior_door','room_class':'toilet_room','role_source':'Reviewed toilet compartment'}
        schedule={'plan_sha256':'plan','review_sha256':'review','stale_or_missing_label_ids':[],'openings':[opening]}
        self.assertEqual(apply_policy(schedule,policy)['openings'][0]['core'],'solid')
        policy['settings'][KEY]['toilet_room']='hollow'
        self.assertEqual(apply_policy(schedule,policy)['openings'][0]['core'],'hollow')
        opening.update(project_core='solid',project_core_source='Explicit selected door')
        self.assertEqual(apply_policy(schedule,policy)['openings'][0]['core'],'solid')
        opening.pop('project_core');opening.pop('project_core_source');opening['role']='exterior_door'
        self.assertIsNone(apply_policy(schedule,policy)['openings'][0]['core'])


if __name__=='__main__':unittest.main()
