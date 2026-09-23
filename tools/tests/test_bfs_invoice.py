import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bfs_invoice import HEADERS, parse_page


def word(x, y, text):
    return (x, y, x + 10, y + 10, text)


def fixture(ordered='', shipped='12', sku='1460340000', unit='BOM', price='0.00', extension='.00'):
    words = [word(x, 198.37, name) for name, x in HEADERS.items()]
    for x, text in [(45, ordered), (84, shipped), (145, sku), (246, '14 BCI-6000 34 FT'),
                    (420, unit), (470, price), (543, extension), (566, 'T')]:
        if text:
            words.append(word(x, 356.34, text))
    return words


class BfsInvoiceTests(unittest.TestCase):
    def test_numeric_sku_cannot_become_shipped_quantity(self):
        row = parse_page(fixture(), 612)[0]
        self.assertEqual(row['sku'], '1460340000')
        self.assertEqual(row['shipped_quantity'], 12)
        self.assertIsNone(row['ordered_quantity'])
        self.assertTrue(row['description'].startswith('14 '))

    def test_zero_shipment_is_not_ordered_quantity(self):
        row = parse_page(fixture(ordered='12', shipped='0'), 612)[0]
        self.assertEqual((row['ordered_quantity'], row['shipped_quantity']), (12, 0))

    def test_missing_shipment_is_unknown_even_at_zero_cost(self):
        for ordered, shipped in [('12', ''), ('', ''), ('', 'O')]:
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                parse_page(fixture(ordered=ordered, shipped=shipped), 612)

    def test_wrong_columns_or_units_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'width'):
            parse_page(fixture(), 700)
        words = copy.deepcopy(fixture())
        words[0] = word(80, 198.37, 'ORDERED')
        with self.assertRaisesRegex(ValueError, 'column header'):
            parse_page(words, 612)
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            parse_page(fixture(unit='LF'), 612)

    def test_extension_check_and_repeated_lines(self):
        with self.assertRaisesRegex(ValueError, 'extension'):
            parse_page(fixture(price='2.00', extension='22.00'), 612)
        words = fixture(price='2.00', extension='24.00')
        words += [(x, y+25, x1, y1+25, t) for x, y, x1, y1, t in words if y > 210]
        rows = parse_page(words, 612)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(r['shipped_quantity'] for r in rows), 24)


if __name__ == '__main__':
    unittest.main()
