import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historical_material_rates import build_catalog, checked_catalog


def line(**updates):
    result = {'sku': '2616SYP2', 'unit': 'EA', 'description': '2X6-16 #2 SYP',
              'invoice': '100', 'invoice_date': '12-22-25', 'source_file': 'invoice.pdf',
              'pdf_page': 1, 'shipped_quantity': 10,
              'historical_unit_price': '7.41', 'historical_extension': '74.10'}
    result.update(updates)
    return result


class HistoricalMaterialRatesTests(unittest.TestCase):
    def catalog(self, rows): return build_catalog(rows, as_of='2026-09-18')

    def test_latest_price_is_not_an_average_and_species_stay_separate(self):
        rows = [line(), line(invoice='101', invoice_date='01-07-26',
                historical_unit_price='8.00', historical_extension='80.00'),
                line(sku='2616S2', description='2X6-16 SPF'),
                line(invoice_date='10-01-26', historical_unit_price='9', historical_extension='90')]
        catalog = self.catalog(rows)
        rates = {r['sku']: r for r in catalog['rates']}
        self.assertEqual(rates['2616SYP2']['unit_price'], '8.00')
        self.assertEqual(rates['2616S2']['unit_price'], '7.41')
        self.assertEqual(len(catalog['excluded_lines']), 1)

    def test_zero_price_package_total_and_unshipped_stock_do_not_become_rates(self):
        rows = [line(unit='PKG'), line(package_component_no_separate_charge=True,
                historical_unit_price='0', historical_extension='0'),
                line(shipped_quantity=0, historical_extension='0'),
                line(historical_unit_price='0', historical_extension='0')]
        result = self.catalog(rows)
        self.assertEqual(result['rates'], [])
        self.assertEqual(len(result['excluded_lines']), 4)

    def test_same_date_conflict_is_not_chosen_by_input_order(self):
        first, second = line(), line(historical_unit_price='8', historical_extension='80')
        for rows in ([first, second], [second, first]):
            rate = self.catalog(rows)['rates'][0]
            self.assertIsNone(rate['unit_price'])
            self.assertEqual(rate['status'], 'conflicting_latest_sources')
        rate = self.catalog([line(), line(description='Different product')])['rates'][0]
        self.assertIsNone(rate['unit_price'])

    def test_units_stay_separate_and_each_duplicate_source_is_retained(self):
        result = self.catalog([line(), line(), line(unit='BOX')])
        self.assertEqual(len(result['rates']), 2)
        each = next(r for r in result['rates'] if r['unit']=='EA')
        self.assertEqual(len(each['selected_sources']), 2)
        self.assertEqual(each['unit_price'], '7.41')

    def test_invalid_quantity_and_extension_rejected(self):
        for row in [line(shipped_quantity=True), line(historical_unit_price='NaN'),
                    line(historical_extension='75'), line(sku='')]:
            with self.assertRaises(ValueError): self.catalog([row])

    def test_changed_pdf_cannot_supply_a_rate(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pdf=root/'invoice.pdf';pdf.write_bytes(b'original')
            ledger=root/'ledger.json'
            ledger.write_text(json.dumps({'lines':[line()], 'source_pdf_hashes':{
                pdf.name:hashlib.sha256(pdf.read_bytes()).hexdigest()}}))
            result=checked_catalog(ledger,root,as_of='2026-09-18')
            self.assertEqual(len(result['rates']),1)
            pdf.write_bytes(b'revised')
            with self.assertRaisesRegex(ValueError,'source changed'):
                checked_catalog(ledger,root,as_of='2026-09-18')


if __name__ == '__main__':
    unittest.main()
