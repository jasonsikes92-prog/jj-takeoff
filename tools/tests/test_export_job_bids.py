import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from export_job_bids import collect,export


class JobBids(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.job=self.root/'job';self.job.mkdir()
        (self.job/'drywall_practice_review.json').write_text('{}')
        self.state={'plan_sha256':'plan','version':1}
        self.scope={'plan_sha256':'plan','measurement_version':1,'sent':False,'items':[]}
        self.out=self.root/'bids'

    def test_exports_only_available_scopes_and_labels_missing_inputs(self):
        with patch('export_job_bids.MeasurementStore') as store,patch('export_job_bids.drywall',return_value=self.scope),patch('export_job_bids.render_drywall',return_value='Unsent draft'):
            store.return_value.read.return_value=self.state
            result=export(self.job,self.out)
        self.assertEqual(result['drafts'],1);self.assertEqual(len(result['missing_supported_scopes']),3)
        self.assertFalse(result['complete_trade_coverage']);self.assertFalse(result['sent'])
        manifest=json.loads((self.out/'manifest.json').read_bytes())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((self.out/name).read_bytes()).hexdigest(),digest)
        with self.assertRaises(FileExistsError):export(self.job,self.out)

    def test_bad_plan_revision_or_fingerprint_rejects_scope(self):
        for update in ({'plan_sha256':'wrong'},{'measurement_version':2},{'scope_sha256':'bad'},{'sent':True}):
            with self.subTest(update=update),patch('export_job_bids.drywall',return_value={**self.scope,**update}),patch('export_job_bids.render_drywall',return_value='draft'):
                with self.assertRaises(ValueError):collect(self.job,self.state)

    def test_mid_export_revision_change_leaves_no_partial_directory(self):
        with patch('export_job_bids.MeasurementStore') as store,patch('export_job_bids.drywall',return_value=self.scope),patch('export_job_bids.render_drywall',return_value='draft'):
            store.return_value.read.side_effect=[self.state,{**self.state,'version':2}]
            with self.assertRaisesRegex(ValueError,'Job changed'):export(self.job,self.out)
        self.assertFalse(self.out.exists());self.assertEqual(list(self.root.glob('.job-bids-*')),[])

    def test_no_available_scopes_does_not_publish_empty_bid_package(self):
        (self.job/'drywall_practice_review.json').unlink()
        with patch('export_job_bids.MeasurementStore') as store:
            store.return_value.read.return_value=self.state
            with self.assertRaisesRegex(ValueError,'No supported scope'):export(self.job,self.out)
        self.assertFalse(self.out.exists())


if __name__=='__main__':unittest.main()
