import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from export_opening_bid import export_bid
from opening_bid_scope import build_scope
import test_opening_bid_scope as fixtures


class ExportOpeningBid(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.job=self.root/'job';self.job.mkdir()
        self.review=self.job/'review.json';self.review.write_text('{}')
        self.output=self.root/'bid'
        fixture=fixtures.OpeningBidScope();fixture.setUp()
        self.scope=build_scope(fixture.schedule,fixture.policy)
        self.state={'plan_sha256':'plan','version':1}

    def test_saved_package_preserves_unit_basis_and_required_responses(self):
        with patch('export_opening_bid.MeasurementStore') as store,patch('export_opening_bid.from_folder',return_value=self.scope) as build:
            store.return_value.read.return_value=self.state
            result=export_bid(self.job,self.output)
            build.assert_called_once_with(self.job.resolve(),self.state)
        scope=json.loads((self.output/'scope.json').read_text())
        self.assertEqual(scope,self.scope)
        self.assertEqual(next(i for i in scope['items'] if i['id']=='window:installation')['reference_quantity'],3)
        self.assertIn('window:exterior-trim',(self.output/'request_DRAFT.md').read_text(encoding='utf-8'))
        manifest=json.loads((self.output/'manifest.json').read_text())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),digest)
        self.assertFalse(result['sent']);self.assertFalse(result['ready_to_order'])

    def test_existing_bid_is_preserved_before_reading_job(self):
        self.output.mkdir();(self.output/'owner.txt').write_text('saved quote')
        with patch('export_opening_bid.MeasurementStore') as store,self.assertRaises(FileExistsError):
            export_bid(self.job,self.output)
        store.assert_not_called()
        self.assertEqual((self.output/'owner.txt').read_text(),'saved quote')

    def test_drywall_package_preserves_missing_surfaces_and_content_hashes(self):
        from test_drywall_bid_scope import DrywallBidScope
        from drywall_bid_scope import build_scope as build_drywall
        fixture=DrywallBidScope();fixture.setUp()
        fixture.r['wall_surface_reference']['status']='unresolved_wall_height_or_profile'
        scope=build_drywall(fixture.rooms)
        with patch('export_opening_bid.MeasurementStore') as store,patch('export_opening_bid.drywall_scope',return_value=scope):
            store.return_value.read.return_value=self.state
            result=export_bid(self.job,self.output,'drywall')
        self.assertEqual(result['surfaces'],2);self.assertEqual(result['unmeasured_surfaces'],1)
        self.assertEqual(json.loads((self.output/'scope.json').read_text()),scope)
        self.assertIn('Not measured',(self.output/'request_DRAFT.md').read_text())
        manifest=json.loads((self.output/'manifest.json').read_text())
        self.assertEqual(manifest['trade'],'drywall')
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),digest)
        self.assertFalse(result['sent'])

    def test_drywall_source_pdf_change_prevents_publication(self):
        plan=self.job/'plan.pdf';plan.write_bytes(b'original')
        with patch('export_opening_bid.MeasurementStore') as store:
            store.return_value.read.return_value=self.state
            def changed(*args):
                plan.write_bytes(b'changed')
                return {'plan_sha256':'plan','measurement_version':1}
            with patch('export_opening_bid.drywall_scope',side_effect=changed),patch('export_opening_bid.render_drywall',return_value='draft'):
                with self.assertRaisesRegex(ValueError,'Job changed'):export_bid(self.job,self.output,'drywall')
        self.assertFalse(self.output.exists())

    def test_flooring_export_keeps_unselected_rooms_and_file_hashes(self):
        from test_flooring_bid_scope import FlooringBidTests
        from flooring_bid_scope import build_scope as build_flooring
        fixture=FlooringBidTests();fixture.setUp();scope=build_flooring(fixture.rooms)
        with patch('export_opening_bid.MeasurementStore') as store,patch('export_opening_bid.flooring_scope',return_value=scope):
            store.return_value.read.return_value=self.state
            result=export_bid(self.job,self.output,'flooring')
        self.assertEqual((result['rooms'],result['unresolved_finishes']),(1,1))
        saved=json.loads((self.output/'scope.json').read_bytes());self.assertEqual(saved,scope)
        self.assertIn('LIVING / KITCHEN',(self.output/'request_DRAFT.md').read_text(encoding='utf-8'))
        manifest=json.loads((self.output/'manifest.json').read_bytes())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((self.output/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(manifest['trade'],'flooring');self.assertFalse(result['sent'])

    def test_source_or_geometry_changes_publish_no_package(self):
        for change in ('review','geometry','wrong_plan'):
            with self.subTest(change=change),patch('export_opening_bid.MeasurementStore') as store:
                store.return_value.read.side_effect=[self.state,{**self.state,'version':2} if change=='geometry' else self.state]
                def build(*args):
                    if change=='review':self.review.write_text('{"changed":true}')
                    return {**self.scope,'plan_sha256':'other' if change=='wrong_plan' else 'plan'}
                with patch('export_opening_bid.from_folder',side_effect=build),self.assertRaises(ValueError):
                    export_bid(self.job,self.output)
                self.assertFalse(self.output.exists())
                self.assertEqual(list(self.root.glob('.opening-bid-*')),[])
                self.review.write_text('{}')


if __name__=='__main__':unittest.main()
