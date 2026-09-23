import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bid_routes import validate, reconcile_applicability, supplemental_scope_digest, supplemental_bid_entry, validate_supplemental_routes


class BidRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("current.md", "old.md"):
            (self.root / name).write_text("Draft")
        self.index = self.root / "index.json"
        self.index.write_text(json.dumps({"files": ["current.md"], "coverage": "coverage.json"}))
        self.rows = [{"excel_row": "676", "status": "draft_scope_routed", "draft_file": "current.md"}]

    def check(self):
        (self.root / "coverage.json").write_text(json.dumps({"rows": self.rows}))
        return validate(self.index)

    def test_existing_old_draft_is_rejected(self):
        self.rows[0]["draft_file"] = "old.md"
        result = self.check()
        self.assertFalse(result["valid"])
        self.assertIn("unindexed draft", result["errors"][0])

    def test_current_draft_and_unrouted_summary_are_valid(self):
        self.rows.append({"excel_row": "714", "status": "retained_GC_inputs_fees_or_summary", "draft_file": None})
        self.assertTrue(self.check()["valid"])

    def test_missing_current_file_is_rejected(self):
        (self.root / "current.md").unlink()
        self.assertFalse(self.check()["valid"])

    def test_duplicate_rows_and_missing_assignment_are_rejected(self):
        self.rows[0]["draft_file"] = None
        self.rows.append(dict(self.rows[0]))
        result = self.check()
        self.assertFalse(result["valid"])
        self.assertEqual(len(result["errors"]), 3)

    def test_exclusion_is_reference_and_idempotent_then_reopens(self):
        coverage = {'rows': [{'excel_row': '57', 'name': 'Parge', 'parent': 'CMU',
                             'status': 'draft_scope_routed', 'draft_file': 'current.md'}]}
        draft = {'plan_sha256': 'plan', 'measurement_version': 3, 'rows': [
            {'excel_row': '57', 'name': 'Parge', 'parent': 'CMU', 'row_id': 'R57',
             'completion_status': 'not_applicable_source_reviewed',
             'applicability_review': {'row_id': 'R57', 'status': 'excluded_by_review',
                                      'reason': 'Brick instead', 'sources': [{'file': 'review.json', 'sha256': 'hash'}]}}]}
        actual = reconcile_applicability(coverage, draft)
        self.assertEqual(actual, reconcile_applicability(actual, draft))
        row = actual['rows'][0]
        self.assertIsNone(row['draft_file'])
        self.assertEqual(row['excluded_scope_reference'], 'current.md')
        self.assertEqual(coverage['rows'][0]['draft_file'], 'current.md')
        self.rows = actual['rows']
        self.assertTrue(self.check()['valid'])
        self.rows[0]['draft_file'] = 'current.md'
        self.assertFalse(self.check()['valid'])
        draft['rows'][0]['completion_status'] = 'applicability_review_required'
        draft['measurement_version'] = 4
        reopened = reconcile_applicability(actual, draft)['rows'][0]
        self.assertEqual(reopened['status'], 'scope_review_required')
        self.assertEqual(reopened['draft_file'], 'current.md')
        self.assertNotIn('applicability_review', reopened)

    def test_applicability_requires_matching_rows_and_evidence(self):
        coverage = {'rows': [{'excel_row': '1', 'name': 'A', 'parent': 'P', 'status': 'draft_scope_routed', 'draft_file': 'current.md'}]}
        draft = {'plan_sha256': 'plan', 'measurement_version': 1,
                 'rows': [{'excel_row': '1', 'name': 'A', 'parent': 'P', 'row_id': 'R1',
                           'completion_status': 'not_applicable_source_reviewed'}]}
        with self.assertRaisesRegex(ValueError, 'source evidence'):
            reconcile_applicability(coverage, draft)
        draft['rows'][0]['completion_status'] = 'evidence_in_progress'
        actual = reconcile_applicability(coverage, draft)
        draft['plan_sha256'] = 'other'
        with self.assertRaisesRegex(ValueError, 'Different plan'):
            reconcile_applicability(actual, draft)
        draft['rows'][0]['name'] = 'B'
        with self.assertRaisesRegex(ValueError, 'identity or scope'):
            reconcile_applicability(coverage, draft)
        draft['rows'] = []
        with self.assertRaisesRegex(ValueError, 'same unique'):
            reconcile_applicability(coverage, draft)

    def additional_scope(self):
        index = json.loads(self.index.read_text())
        index['required_additional_scope_ids'] = ['porch']
        self.index.write_text(json.dumps(index))
        source = self.root / 'porch.json'
        source.write_text(json.dumps({'scope_id': 'porch', 'plan_sha256': 'plan', 'measurement_version': 3}))
        scope = {'id': 'porch', 'name': 'Front porch slab', 'status': 'draft_scope_routed',
                 'draft_owner': 'concrete', 'draft_file': 'current.md',
                 'quantity_or_price_verified_by_routing': False,
                 'source_review': {'file': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}}
        coverage = {'rows': self.rows, 'additional_scopes': [scope],
                    'applicability_basis': {'plan_sha256': 'plan', 'measurement_version': 3}}
        return coverage, scope, source

    def validate_coverage(self, coverage):
        (self.root / 'coverage.json').write_text(json.dumps(coverage))
        return validate(self.index)

    def test_missing_physical_scope_has_a_separate_route_without_invented_cost(self):
        coverage, scope, _ = self.additional_scope()
        result = self.validate_coverage(coverage)
        self.assertTrue(result['valid'])
        self.assertEqual(result['additional_scopes'], 1)
        self.assertEqual(result['template_rows'], 1)
        omitted = dict(coverage)
        omitted.pop('additional_scopes')
        self.assertFalse(self.validate_coverage(omitted)['valid'])
        scope['draft_file'] = 'old.md'
        self.assertFalse(self.validate_coverage(coverage)['valid'])
        scope['draft_file'] = None
        self.assertFalse(self.validate_coverage(coverage)['valid'])

    def test_additional_scope_cannot_reuse_changed_missing_or_wrong_revision_evidence(self):
        coverage, scope, source = self.additional_scope()
        original = source.read_bytes()
        source.write_bytes(original + b' ')
        self.assertFalse(self.validate_coverage(coverage)['valid'])
        source.unlink()
        self.assertFalse(self.validate_coverage(coverage)['valid'])
        source.write_bytes(original)
        for key, value in [('plan_sha256', 'other'), ('measurement_version', 4)]:
            changed = json.loads(json.dumps(coverage))
            changed['applicability_basis'][key] = value
            self.assertFalse(self.validate_coverage(changed)['valid'])
        scope['id'] = 'different-scope'
        self.assertFalse(self.validate_coverage(coverage)['valid'])

    def test_duplicate_scope_and_unsupported_verified_claim_fail(self):
        coverage, scope, _ = self.additional_scope()
        coverage['additional_scopes'].append(dict(scope))
        self.assertFalse(self.validate_coverage(coverage)['valid'])
        coverage['additional_scopes'].pop()
        scope['quantity_or_price_verified_by_routing'] = True
        self.assertFalse(self.validate_coverage(coverage)['valid'])

    def test_published_estimate_detects_stale_exclusions_and_follows_new_checkpoint(self):
        index=json.loads(self.index.read_text())
        index['published_estimate']={'workspace':'.','checkpoint':'checkpoint.json'}
        self.index.write_text(json.dumps(index))
        coverage={'rows':[{'excel_row':'57','name':'Parge','parent':'CMU',
                          'status':'draft_scope_routed','draft_file':'current.md'}]}
        draft={'plan_sha256':'plan','measurement_version':3,'rows':[
            {'excel_row':'57','name':'Parge','parent':'CMU','row_id':'R57',
             'completion_status':'not_applicable_source_reviewed',
             'applicability_review':{'row_id':'R57','status':'excluded_by_review',
                                     'reason':'Brick instead','sources':[{'file':'review.json','sha256':'hash'}]}}]}
        def publish(revision):
            folder=self.root/revision;folder.mkdir()
            body={'draft':draft,'readiness':{}}
            digest=hashlib.sha256(json.dumps(body,allow_nan=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            snapshot={**body,'snapshot_sha256':digest}
            (folder/'source_snapshot.json').write_text(json.dumps(snapshot))
            (self.root/'checkpoint.json').write_text(json.dumps({'current_workbook':revision+'/estimate.xlsx','live_snapshot_sha256':digest}))
            return folder
        publish('v1')
        stale=self.validate_coverage(coverage)
        self.assertFalse(stale['valid']);self.assertTrue(stale['estimate_basis_checked'])
        self.assertTrue(any('Row 57 bid scope is stale' in e for e in stale['errors']))
        coverage=reconcile_applicability(coverage,draft)
        self.assertTrue(self.validate_coverage(coverage)['valid'])
        draft['measurement_version']=4;draft['rows'][0]['completion_status']='applicability_review_required'
        folder=publish('v2')
        self.assertFalse(self.validate_coverage(coverage)['valid'])
        coverage=reconcile_applicability(coverage,draft)
        self.assertTrue(self.validate_coverage(coverage)['valid'])
        snapshot=json.loads((folder/'source_snapshot.json').read_text())
        snapshot['draft']['measurement_version']=5
        (folder/'source_snapshot.json').write_text(json.dumps(snapshot))
        result=self.validate_coverage(coverage)
        self.assertFalse(result['valid']);self.assertFalse(result['estimate_basis_checked'])
        (self.root/'checkpoint.json').unlink()
        self.assertFalse(self.validate_coverage(coverage)['valid'])

    def test_supplemental_cost_scope_is_complete_unique_and_bound_to_quantity(self):
        row={'row_id':'JJ-LEAF','name':'Pocket leaf','parent_row_id':'R10','draft_quantity':1,
             'unit':'each','covered_by_package':'R20'}
        note='Included once in the door supply package; installation separate.'
        draft={'additional_cost_rows':[row]}
        route={'row_id':row['row_id'],'draft_file':'current.md','draft_owner':'trim',
               'status':'draft_scope_routed','scope_binding':supplemental_scope_digest(row),
               'scope_note':note,'quantity_or_price_verified_by_routing':False}
        coverage={'supplemental_cost_routes':[route]};files=[self.root/'current.md']
        entry=supplemental_bid_entry(row,note);files[0].write_text(entry,encoding='utf-8')
        check=lambda:validate_supplemental_routes(coverage,draft,self.index,files)
        self.assertEqual(check(),[])
        coverage['supplemental_cost_routes']=[];self.assertTrue(check())
        coverage['supplemental_cost_routes']=[route,dict(route)];self.assertTrue(check())
        coverage['supplemental_cost_routes']=[route]
        files[0].write_text('Draft only');self.assertTrue(check())
        files[0].write_text(entry+'\n'+entry);self.assertTrue(check())
        files[0].write_text(entry);files.append(self.root/'old.md');files[1].write_text(entry)
        self.assertTrue(check());files[1].write_text('Other draft')
        self.assertEqual(check(),[])
        row['draft_quantity']=2;self.assertTrue(check());row['draft_quantity']=1
        row['covered_by_package']='R21';self.assertTrue(check());row['covered_by_package']='R20'
        route['quantity_or_price_verified_by_routing']=True;self.assertTrue(check())
        route['quantity_or_price_verified_by_routing']=False
        route['draft_file']='missing.md';self.assertTrue(check())

    def test_unresolved_supplemental_quantity_is_explicit_and_remains_unpriced(self):
        row={'row_id':'JJ-CARPET','name':'Carpet | pad','unit':'sq yd','draft_quantity':None}
        entry=supplemental_bid_entry(row,'Provide cut plan and price; dimensions remain unresolved.')
        self.assertIn('Unresolved sq yd',entry);self.assertIn('Carpet \\| pad',entry)
        self.assertIsNone(row['draft_quantity'])
        for value in [True,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):supplemental_bid_entry({**row,'draft_quantity':value},'Scope')
        with self.assertRaises(ValueError):supplemental_bid_entry(row,'')


if __name__ == "__main__":
    unittest.main()
