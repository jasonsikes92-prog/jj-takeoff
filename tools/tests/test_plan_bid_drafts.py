import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from plan_bid_drafts import from_workspace
from bid_comparison import scope_digest


class PlanBidDrafts(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.job=self.root/'case'/'workspace';self.folder=self.job/'draft_takeoff'
        self.folder.mkdir(parents=True)
        for name in ('sheet_review.json','plan_inventory.json','estimate_intake.json','company_profile_snapshot.json'):
            (self.job/name).write_text('{}')
        manifest={'initial_file_sha256':{name:hashlib.sha256((self.job/name).read_bytes()).hexdigest()
            for name in ('estimate_intake.json','company_profile_snapshot.json','plan_inventory.json')}}
        (self.job/'case_workspace.json').write_text(json.dumps(manifest))
        for name in ('summary.json','measurements.json','quantity_rules.json','roof_partition_inputs.json'):
            (self.folder/name).write_text('{}')
        self.status={'measurement_status':'candidates_require_review','plan_sha256':'plan'}
        self.workspaces=SimpleNamespace(root=self.root,read=Mock(return_value=self.status))
        self.state={'version':1};self.store=Mock();self.store.read.side_effect=lambda:copy.deepcopy(self.state)
        self.scope={'title':'Roof','plan_sha256':'plan','measurement_version':1,'sent':False,'items':[]}
        self.sign()
        self.saved=self.folder/'roof_bid_scope/roofing.json';self.saved.parent.mkdir()
        self.saved.write_text(json.dumps(self.scope))

    def sign(self):self.scope['scope_sha256']=scope_digest(self.scope)

    def result(self,reader=None):
        with patch('plan_bid_drafts.MeasurementStore',return_value=self.store), \
             patch('plan_bid_drafts.roof_scope',side_effect=reader or (lambda _:copy.deepcopy(self.scope))), \
             patch('plan_bid_drafts.render_roof',return_value='Current unsent draft'):
            return from_workspace(self.workspaces,'case','workspace')

    def test_current_scope_and_saved_match_are_returned_without_rewriting(self):
        before={p:p.read_bytes() for p in self.job.rglob('*') if p.is_file()}
        result=self.result();item=result['drafts'][0]
        self.assertEqual(item['saved_snapshot_status'],'current')
        self.assertEqual(item['scope'],self.scope)
        self.assertFalse(result['sent']);self.assertFalse(result['homeowner_release_approved'])
        self.assertFalse(result['complete_trade_coverage'])
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_current_revision_does_not_pass_off_older_saved_scope_as_current(self):
        original=self.saved.read_bytes();self.state['version']=2
        self.scope['measurement_version']=2;self.sign()
        result=self.result()['drafts'][0]
        self.assertEqual(result['saved_snapshot_status'],'older_revision')
        self.assertNotEqual(result['saved_scope_sha256'],result['scope']['scope_sha256'])
        self.assertEqual(self.saved.read_bytes(),original)

    def test_missing_saved_draft_is_explicit_and_no_file_is_created(self):
        self.saved.unlink();result=self.result()['drafts'][0]
        self.assertEqual(result['saved_snapshot_status'],'not_saved')
        self.assertIsNone(result['saved_scope_sha256']);self.assertFalse(self.saved.exists())

    def test_frozen_intake_and_saved_bid_tampering_are_rejected(self):
        self.saved.write_text(json.dumps({**self.scope,'title':'Changed'}))
        with self.assertRaisesRegex(ValueError,'Saved bid'):self.result()
        self.saved.write_text(json.dumps(self.scope));(self.job/'estimate_intake.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Frozen intake'):self.result()

    def test_stale_sheet_review_and_mixed_measurement_revisions_are_rejected(self):
        self.status['measurement_status']='source_or_review_changed'
        with self.assertRaisesRegex(ValueError,'sheet-reviewed'):self.result()
        self.status['measurement_status']='candidates_require_review';self.state['version']=2
        with self.assertRaisesRegex(ValueError,'measurements differ'):self.result()

    def test_concurrent_geometry_and_source_change_are_rejected(self):
        def change_state(_):
            self.state['version']=2
            return copy.deepcopy(self.scope)
        with self.assertRaisesRegex(ValueError,'Workspace changed'):self.result(change_state)
        self.state['version']=1
        def change_file(_):
            (self.folder/'roof_coverage_review.json').write_text('{}')
            return copy.deepcopy(self.scope)
        with self.assertRaisesRegex(ValueError,'source files changed'):self.result(change_file)

    def opening_result(self,reader=None,framing_reader=None):
        with patch('plan_bid_drafts.opening_scope',side_effect=reader or (lambda *_:{
                'title':'Windows and doors','plan_sha256':'plan','measurement_version':1,'sent':False,'items':[]})), \
             patch('plan_bid_drafts.render_openings',return_value='Unsent window and door request'), \
             patch('plan_bid_drafts.framing_scope',side_effect=framing_reader or (lambda *_:copy.deepcopy(self.scope))), \
             patch('plan_bid_drafts.render_framing',return_value='Unsent framing request'):
            return self.result()

    def prepare_openings(self):
        (self.folder/'opening_schedule_review.json').write_text('{}')
        intake=self.job/'estimate_intake.json'
        intake.write_text(json.dumps({'company_profile_snapshot':'company_profile_snapshot.json'}))
        path=self.job/'case_workspace.json';manifest=json.loads(path.read_bytes())
        manifest['initial_file_sha256']['estimate_intake.json']=hashlib.sha256(intake.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))

    def test_opening_draft_is_fingerprinted_unsent_and_not_saved_by_retrieval(self):
        self.prepare_openings();result=self.opening_result()
        item=result['drafts'][-1]
        self.assertEqual(item['trade'],'Windows and doors')
        self.assertEqual(item['scope_kind'],'opening_assembly_request')
        self.assertEqual(item['scope']['scope_sha256'],scope_digest(item['scope']))
        self.assertIn(item['scope']['scope_sha256'],item['markdown'])
        self.assertEqual(item['saved_snapshot_status'],'not_saved')
        self.assertFalse((self.folder/'opening_bid_scope').exists())
        self.assertFalse(item['sent'])

    def test_opening_saved_status_uses_current_scope_without_overwriting(self):
        self.prepare_openings();item=self.opening_result()['drafts'][-1]
        path=self.folder/'opening_bid_scope/windows_doors.json';path.parent.mkdir()
        path.write_text(json.dumps(item['scope']));before=path.read_bytes()
        self.assertEqual(self.opening_result()['drafts'][-1]['saved_snapshot_status'],'current')
        scope={**item['scope'],'items':[{'id':'new-hardware-question'}]};scope.pop('scope_sha256')
        self.assertEqual(self.opening_result(lambda *_:scope)['drafts'][-1]['saved_snapshot_status'],'older_revision')
        self.assertEqual(path.read_bytes(),before)

    def test_framing_draft_has_separate_identity_and_saved_revision(self):
        self.prepare_openings();item=self.opening_result()['drafts'][-2]
        self.assertEqual((item['trade'],item['scope_kind']),('Framing','opening_framing_request'))
        self.assertFalse(item['sent']);self.assertEqual(item['saved_snapshot_status'],'not_saved')
        path=self.folder/'opening_bid_scope/framing.json';path.parent.mkdir()
        path.write_text(json.dumps(item['scope']));before=path.read_bytes()
        self.assertEqual(self.opening_result()['drafts'][-2]['saved_snapshot_status'],'current')
        changed={**self.scope,'items':[{'id':'window:rough-sill'}]}
        changed['scope_sha256']=scope_digest(changed)
        result=self.opening_result(framing_reader=lambda *_:changed)
        self.assertEqual(result['drafts'][-2]['saved_snapshot_status'],'older_revision')
        self.assertEqual(result['drafts'][-1]['trade'],'Windows and doors')
        self.assertEqual(path.read_bytes(),before)

    def test_framing_cannot_return_a_different_measurement_revision(self):
        self.prepare_openings();changed={**self.scope,'measurement_version':2}
        changed['scope_sha256']=scope_digest(changed)
        with self.assertRaisesRegex(ValueError,'measurements differ'):
            self.opening_result(framing_reader=lambda *_:changed)

    def test_framing_source_change_during_retrieval_is_rejected(self):
        self.prepare_openings()
        def change(*_):
            (self.folder/'opening_schedule_review.json').write_text('{"changed":true}')
            return copy.deepcopy(self.scope)
        with self.assertRaisesRegex(ValueError,'source files changed'):
            self.opening_result(framing_reader=change)

    def test_opening_source_changes_during_retrieval_are_rejected(self):
        self.prepare_openings()
        for name in ('opening_schedule_review.json','wall_classification_review.json','wall_alignment_breaks.json',
                     'opening_quantity_review.json','door_policy_revision.json','door_hardware_policy_revision.json','room_use_review.json'):
            path=self.folder/name;before=path.read_bytes() if path.exists() else None
            def change(*_):
                path.write_text('{"changed":true}')
                return {'plan_sha256':'plan','measurement_version':1,'sent':False,'items':[]}
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'source files changed'):
                self.opening_result(change)
            if before is None:path.unlink()
            else:path.write_bytes(before)

    def test_revised_profile_is_watched_and_outside_job_paths_are_rejected(self):
        self.prepare_openings();profile=self.folder/'revised-profile.json';profile.write_text('{}')
        path=self.folder/'door_policy_revision.json'
        path.write_text(json.dumps({'base_intake_path':'../estimate_intake.json','profile_path':profile.name}))
        def change(*_):
            profile.write_text('{"changed":true}')
            return {'plan_sha256':'plan','measurement_version':1,'sent':False,'items':[]}
        with self.assertRaisesRegex(ValueError,'source files changed'):self.opening_result(change)
        path.write_text(json.dumps({'base_intake_path':'../../outside.json','profile_path':profile.name}))
        with self.assertRaisesRegex(ValueError,'inside their job'):self.opening_result()

    def prepare_drywall(self):
        self.prepare_openings()
        (self.folder/'opening_schedule_review.json').unlink()
        (self.folder/'drywall_practice_review.json').write_text('{}')

    def drywall_result(self,reader=None):
        with patch('plan_bid_drafts.drywall_scope',side_effect=reader or (lambda *_:copy.deepcopy(self.scope))), \
             patch('plan_bid_drafts.render_drywall',return_value='Unsent wall and ceiling references'):
            return self.result()

    def test_drywall_is_returned_as_current_unsent_surface_request(self):
        self.prepare_drywall()
        item=self.drywall_result()['drafts'][-1]
        self.assertEqual((item['trade'],item['scope_kind']),('Drywall','drywall_surface_request'))
        self.assertFalse(item['sent']);self.assertEqual(item['saved_snapshot_status'],'not_saved')
        self.assertFalse((self.folder/'drywall_bid_scope').exists())
        saved=self.folder/'drywall_bid_scope/drywall.json';saved.parent.mkdir()
        saved.write_text(json.dumps(item['scope']));raw=saved.read_bytes()
        self.assertEqual(self.drywall_result()['drafts'][-1]['saved_snapshot_status'],'current')
        self.assertEqual(saved.read_bytes(),raw)

    def test_drywall_changed_geometry_or_source_cannot_be_returned_as_current(self):
        self.prepare_drywall()
        changed={**self.scope,'measurement_version':2};changed['scope_sha256']=scope_digest(changed)
        with self.assertRaisesRegex(ValueError,'measurements differ'):
            self.drywall_result(lambda *_:changed)
        for name in ('ceiling_surface_review.json','drywall_practice_review.json','room_use_review.json','plan.pdf'):
            p=self.folder/name;raw=p.read_bytes() if p.exists() else None
            def change(*_):
                p.write_bytes(b'changed');return copy.deepcopy(self.scope)
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'source files changed'):
                self.drywall_result(change)
            if raw is None:p.unlink()
            else:p.write_bytes(raw)


if __name__=='__main__':unittest.main()
