import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from measurement_store import encode
from saved_trade_snapshots import import_saved_trades


class SavedWindowGeometryTests(unittest.TestCase):
    def test_changed_dimensions_withhold_the_window_import_and_its_accessories(self):
        state={'plan_sha256':'plan','version':1,'measurements':{}}
        draft={'plan_sha256':'plan','rows':[]}
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'windows.json';source.write_bytes(b'window evidence')
            item={'trade':'windows','file':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'window_geometry_mapping_sha256':'mapping','mappings':{},
                'supplemental_mappings':{'sealant':{}}}
            config={'plan_sha256':'plan','measurements_sha256':hashlib.sha256(encode({}).encode()).hexdigest(),
                'snapshots':[item]}
            review={'mapping_sha256':'mapping','plan_sha256':'plan','measurement_version':1,'changed_measurements':[]}
            with patch('window_sill_stock_review.from_folder',return_value=review),patch('saved_trade_snapshots.import_window_snapshot',return_value=draft) as importer:
                self.assertEqual(import_saved_trades(draft,state,config,folder),draft)
                importer.assert_called_once();importer.reset_mock()
                review['changed_measurements']=['EG01']
                result=import_saved_trades(draft,state,config,folder)
                importer.assert_not_called()
                self.assertEqual(result['withheld_supplemental_cost_ids'],['sealant'])
                self.assertIn('Window dimensions changed',result['saved_trade_review_required'])
                self.assertNotIn('saved_trade_review_required',draft)
                review['mapping_sha256']='different'
                with self.assertRaisesRegex(ValueError,'mapping or revision changed'):
                    import_saved_trades(draft,state,config,folder)
                review['mapping_sha256']='mapping';review['measurement_version']=2
                with self.assertRaisesRegex(ValueError,'mapping or revision changed'):
                    import_saved_trades(draft,state,config,folder)
                item['trade']='framing'
                with self.assertRaisesRegex(ValueError,'window trade'):
                    import_saved_trades(draft,state,config,folder)


if __name__=='__main__':unittest.main()
