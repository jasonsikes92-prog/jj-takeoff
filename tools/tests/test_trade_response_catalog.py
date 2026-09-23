import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from trade_response_review import catalog_scope


class TradeResponseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.issued = {'plan_sha256': 'plan', 'snapshot_sha256': 'old',
                       'measurement_version': 1, 'items': [{'row_id': 'A'}, {'row_id': 'B'}]}
        (self.root / 'issued.json').write_text(json.dumps(self.issued))
        (self.root / 'current.json').write_text(json.dumps({**self.issued, 'snapshot_sha256': 'new'}))
        (self.root / 'baseline.xlsx').write_bytes(b'Preserved form identity fixture')
        self.entry = {'issued_scope': 'issued.json', 'current_scope': 'current.json',
                      'workbook': 'baseline.xlsx',
                      'sha256': hashlib.sha256((self.root / 'baseline.xlsx').read_bytes()).hexdigest()}
        self.catalog = {'snapshot_sha256': 'new', 'forms': [self.entry]}

    def resolve(self, identity=None, ids=None, snapshot='new'):
        return catalog_scope(self.catalog, self.root, identity or ['plan', 'old', 1],
                             ids if ids is not None else ['B', 'A'], snapshot)

    def test_older_issued_form_resolves_to_current_scope_without_filename_guess(self):
        self.assertEqual(self.resolve(), (self.root / 'current.json', self.root / 'issued.json'))

    def test_stale_catalog_or_wrong_plan_and_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'catalog differs'):
            self.resolve(snapshot='different')
        for identity in (['other', 'old', 1], ['plan', 'new', 1], ['plan', 'old', 2]):
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, 'no unique'):
                self.resolve(identity=identity)

    def test_missing_extra_duplicate_or_blank_ids_cannot_select_a_trade(self):
        for ids in (['A'], ['A', 'B', 'C'], ['A', 'A'], ['A', None], ['A', '']):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.resolve(ids=ids)

    def test_ambiguous_catalog_rejected(self):
        self.catalog['forms'].append(copy.deepcopy(self.entry))
        with self.assertRaisesRegex(ValueError, 'no unique'):
            self.resolve()

    def test_preserved_form_mutation_rejected(self):
        (self.root / 'baseline.xlsx').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Preserved issued form changed'):
            self.resolve()

    def test_paths_cannot_leave_workspace(self):
        for key in ('issued_scope', 'current_scope', 'workbook'):
            with self.subTest(key=key):
                value = self.entry[key]
                self.entry[key] = '../outside'
                with self.assertRaisesRegex(ValueError, 'leaves the workspace'):
                    self.resolve()
                self.entry[key] = value


if __name__ == '__main__':
    unittest.main()
