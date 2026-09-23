import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from permit_report_context import from_workspace


class PermitReportContext(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.record={'id':'synthetic','state':'GA','jurisdiction_scope':'local','authority_id':'GA-Test',
            'source_kind':'official_public','review_status':'reviewed','parcel_specific':False,
            'authority':'Synthetic county','source_url':'https://example.gov/permit','source_page':4,
            'checked_on':'2026-09-19','review_due':'2026-10-19','effective_from':'2026-01-01',
            'topic':'Synthetic permit item','summary':'Test source, not a real regulation.'}
        self.project={'state':'GA','code_basis_date':'2026-09-19','authority_id':'GA-Test',
            'authority_verified':True,'private_notes':'PRIVATE CONTEXT DO NOT DISCLOSE'}
        self.saved={'plan_sha256':'plan','project_basis':self.project}
        self.bind()

    def write(self,name,value):
        path=self.root/name;path.write_text(json.dumps(value));return hashlib.sha256(path.read_bytes()).hexdigest()

    def bind(self):
        self.saved['registry_sha256']=self.write('official_requirements_snapshot.json',[self.record])
        inventory={'plan_sha256':'plan','local_requirements_sha256':self.write('local_requirements.json',self.saved)}
        digest=self.write('plan_inventory.json',inventory)
        self.write('case_workspace.json',{'initial_file_sha256':{'plan_inventory.json':digest}})

    def test_current_snapshot_rechecks_dates_and_does_not_expose_private_basis(self):
        before={p:p.read_bytes() for p in self.root.iterdir()}
        current=from_workspace(self.root,'plan','2026-09-19')
        self.assertEqual(len(current['candidates']),1);self.assertEqual(current['needs_review'],[])
        stale=from_workspace(self.root,'plan','2026-10-20')
        self.assertEqual(stale['candidates'],[]);self.assertIn('Refresh official source',stale['needs_review'][0]['review_issues'])
        self.assertNotIn('PRIVATE',json.dumps(current));self.assertNotIn('project_basis',current)
        self.assertFalse(current['permit_compliance_verified']);self.assertFalse(current['coverage_complete'])
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_each_frozen_link_rejects_changed_or_missing_evidence(self):
        for name,message in [('plan_inventory.json','inventory changed'),('local_requirements.json','project basis changed'),
                             ('official_requirements_snapshot.json','requirement evidence changed')]:
            self.bind();self.write(name,{})
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,message):
                from_workspace(self.root,'plan','2026-09-19')
        self.bind();(self.root/'official_requirements_snapshot.json').unlink()
        with self.assertRaisesRegex(ValueError,'evidence is missing'):from_workspace(self.root,'plan','2026-09-19')

    def test_different_plan_and_missing_project_basis_fail(self):
        with self.assertRaisesRegex(ValueError,'another drawing'):from_workspace(self.root,'other-plan','2026-09-19')
        self.saved['plan_sha256']='other-plan';self.bind()
        with self.assertRaisesRegex(ValueError,'another drawing'):from_workspace(self.root,'plan','2026-09-19')
        self.saved['plan_sha256']='plan';self.saved.pop('project_basis');self.bind()
        with self.assertRaisesRegex(ValueError,'lacks its project basis'):from_workspace(self.root,'plan','2026-09-19')

    def test_old_unbound_snapshot_is_not_upgraded_or_trusted(self):
        digest=self.write('plan_inventory.json',{'plan_sha256':'plan'})
        self.write('case_workspace.json',{'initial_file_sha256':{'plan_inventory.json':digest}})
        self.write('local_requirements.json',{'candidates':[self.record],'permit_compliance_verified':True})
        result=from_workspace(self.root,'plan','2026-09-19')
        self.assertEqual(result['status'],'unbound_legacy_snapshot')
        self.assertEqual(result['candidates'],[]);self.assertFalse(result['permit_compliance_verified'])

    def test_cached_candidate_list_is_not_used_as_a_time_independent_answer(self):
        self.saved['candidates']=[{**self.record,'summary':'Invented cached result'}];self.bind()
        result=from_workspace(self.root,'plan','2026-09-19')
        self.assertEqual(result['candidates'][0]['summary'],self.record['summary'])
        self.assertNotIn('Invented',json.dumps(result))


if __name__=='__main__':unittest.main()
