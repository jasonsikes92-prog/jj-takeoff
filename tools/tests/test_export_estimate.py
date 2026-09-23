import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from export_estimate import validate_sources
from measurement_store import encode


class ExportSources(unittest.TestCase):
    def check(self,mutate=None,bad_hash=False):
        row={'row_id':'T-original-R0002','excel_row':'2','cost_type':'MATERIAL','markup_pct':'15'}
        original={'template_sha256':'template','rows':[dict(row)]}
        if mutate:mutate(row)
        body={'draft':{'rows':[row]},'readiness':{}}
        snapshot={**body,'snapshot_sha256':hashlib.sha256(encode(body).encode()).hexdigest()}
        if bad_hash:snapshot['snapshot_sha256']='changed'
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'snapshot.json';p.write_text(json.dumps(snapshot))
            with patch('export_estimate.read_template',return_value=original):
                return validate_sources(p,Path(temp)/'template.xlsx')

    def test_valid_source(self):
        self.assertEqual(self.check()[1],'template')

    def test_changed_snapshot_rejected(self):
        with self.assertRaisesRegex(ValueError,'snapshot content changed'):self.check(bad_hash=True)

    def test_wrong_template_rejected(self):
        with self.assertRaisesRegex(ValueError,'selected original template'):
            self.check(lambda row:row.update(row_id='another-template'))

    def test_changed_markup_rejected(self):
        with self.assertRaisesRegex(ValueError,'markup changed'):
            self.check(lambda row:row.update(markup_pct='7'))

    def test_changed_cost_type_rejected(self):
        with self.assertRaisesRegex(ValueError,'cost type'):
            self.check(lambda row:row.update(cost_type='LABOR'))


if __name__=='__main__':unittest.main()
