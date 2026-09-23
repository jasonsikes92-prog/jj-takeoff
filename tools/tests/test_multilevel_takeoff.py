import hashlib
import json
import unittest
from unittest.mock import patch
import test_plan_sheet_review as fixtures
from plan_sheet_review import read_sheet_review
from multilevel_takeoff import run,project_allowances
from company_profile import scope_allowances


class MultiLevelTakeoffTests(unittest.TestCase):
    def test_project_allowance_remains_four_not_twelve(self):
        items=scope_allowances({'plumbing.exterior_hose_bibbs':4},{})
        scopes=[{'id':i,'summary':{'unlocated_scope_allowances':items}} for i in ['basement','main','shared']]
        r=project_allowances(scopes)
        self.assertEqual(len(r['items']),1)
        self.assertEqual(r['items'][0]['quantity'],4)
        self.assertEqual(r['items'][0]['source_scopes'],['basement','main','shared'])

    def test_conflicting_allowances_are_not_silently_combined(self):
        scopes=[{'id':str(count),'summary':{'unlocated_scope_allowances':
            scope_allowances({'plumbing.exterior_hose_bibbs':count},{})}} for count in [4,5]]
        with self.assertRaisesRegex(ValueError,'Conflicting project allowance'):project_allowances(scopes)

    def test_allowance_without_scope_remains_unresolved(self):
        r=project_allowances([{'id':'main','summary':{'unlocated_scope_allowances':[{'id':'other','quantity':2}]}}])
        self.assertEqual(r['items'],[])
        self.assertEqual(len(r['unresolved_scope_items']),1)

    def setUp(self):
        self.fixture=fixtures.SheetReviewTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.job=self.fixture.job
        # Change the fixture cover into a second reviewed floor, retaining the
        # foundation/roof/elevation pages needed for complete sheet coverage.
        self.fixture.review['pages'][0].update(role='floor_plan',title='Basement floor plan')
        self.fixture.save();routing=read_sheet_review(self.job)
        self.config={'plan_sha256':self.fixture.sha,'sheet_review_sha256':routing['review_sha256'],
                     'levels':[{'id':'basement','page':1},{'id':'main','page':3}]}
        self.save()

    def save(self):(self.job/'multilevel_review.json').write_text(json.dumps(self.config))

    def test_each_floor_routes_once_and_shared_roles_are_not_repeated(self):
        seen=[]
        def measure(child):
            review=read_sheet_review(child);roles=review['measurement_role_pages'];seen.append(roles)
            self.assertEqual(review['measurement_scope'],'reviewed_subset')
            return {'estimate_released':False}
        with patch('multilevel_takeoff.measure_job',side_effect=measure):report=run(self.job)
        self.assertEqual(seen,[{'floor':1},{'floor':3},{'foundation':2,'roof':4,'elevations':5}])
        self.assertEqual(report['floor_pages_assigned_once'],[1,3]);self.assertEqual(report['shared_scope_count'],1)
        self.assertIsNone(report['whole_house_total'])
        with self.assertRaises(FileExistsError):run(self.job)

    def test_missing_level_and_unsafe_identity_rejected_before_child_creation(self):
        self.config['levels']=self.config['levels'][:1];self.save()
        with self.assertRaises(ValueError):run(self.job)
        self.assertFalse((self.job/'level_takeoffs').exists())
        self.config['levels']=[{'id':'../outside','page':1},{'id':'main','page':3}];self.save()
        with self.assertRaises(ValueError):run(self.job)

    def test_failed_child_does_not_publish_combined_manifest(self):
        with patch('multilevel_takeoff.measure_job',side_effect=ValueError('scale source changed')):
            with self.assertRaisesRegex(ValueError,'scale source changed'):run(self.job)
        self.assertFalse((self.job/'level_takeoffs/summary.json').exists())
        self.assertFalse((self.job/'level_takeoffs/combined_measurements.json').exists())

    def test_combined_measurements_keep_distinct_level_identity(self):
        def measure(child):
            roles=read_sheet_review(child)['measurement_role_pages']
            folder=child/'draft_takeoff';folder.mkdir()
            (folder/'measurements.json').write_text(json.dumps({'measurements':[
                {'id':'wall-1','page':next(iter(roles.values())),'points':[[0,0],[10,0]]}]}))
            return {}
        with patch('multilevel_takeoff.measure_job',side_effect=measure):report=run(self.job)
        measurements=json.loads((self.job/'level_takeoffs/combined_measurements.json').read_bytes())['measurements']
        self.assertEqual([m['id'] for m in measurements],['basement:wall-1','main:wall-1','shared:wall-1'])
        self.assertEqual(report['candidate_measurement_count'],3)

    def test_parent_change_prevents_combined_publication(self):
        def measure(child):
            (self.job/'multilevel_review.json').write_text('{}')
            return {}
        with patch('multilevel_takeoff.measure_job',side_effect=measure):
            with self.assertRaisesRegex(ValueError,'Parent sources changed'):run(self.job)
        self.assertFalse((self.job/'level_takeoffs/summary.json').exists())

    def test_scope_review_copied_only_to_assigned_level(self):
        source=self.job/'main-view.json';source.write_text('{"page":3}')
        self.config['scope_files']={'main':{'floor_wall_view_review.json':
            {'file':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}}};self.save()
        def measure(child):
            self.assertEqual((child/'floor_wall_view_review.json').exists(),child.name=='main')
            return {}
        with patch('multilevel_takeoff.measure_job',side_effect=measure):report=run(self.job)
        self.assertIn(str(source.resolve()),report['source_files'])

    def test_changed_scope_review_rejected_before_extraction(self):
        source=self.job/'main-view.json';source.write_text('{}')
        self.config['scope_files']={'main':{'floor_wall_view_review.json':
            {'file':source.name,'sha256':'old'}}};self.save()
        with patch('multilevel_takeoff.measure_job') as measure:
            with self.assertRaisesRegex(ValueError,'input changed'):run(self.job)
            measure.assert_not_called()
        self.assertFalse((self.job/'level_takeoffs').exists())

    def test_level_selection_must_acknowledge_other_floor_pages(self):
        self.fixture.review['partial_measurement_review']={'role_pages':{'floor':1},'basis':'One level',
            'missing_roles':[],'unresolved_issues':[],
            'floor_level':{'id':'basement','page':1,'other_floor_pages':[]}}
        self.fixture.save()
        with self.assertRaisesRegex(ValueError,'acknowledge every other'):read_sheet_review(self.job)


if __name__=='__main__':unittest.main()
