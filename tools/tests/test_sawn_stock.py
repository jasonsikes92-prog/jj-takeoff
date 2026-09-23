import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linear_stock import pack_sawn_cuts


class SawnStockTests(unittest.TestCase):
    def piece(self, identity, length, sku='2X6-16', stock=16):
        return {'id':identity, 'sku':sku, 'stock_length_ft':stock, 'cut_inches':length}

    def test_oversized_piece_cannot_shrink_to_board_length(self):
        with self.assertRaisesRegex(ValueError, 'does not fit'):
            pack_sawn_cuts([self.piece('bad', 193)])

    def test_two_half_boards_need_kerf_but_factory_end_needs_none(self):
        self.assertEqual(len(pack_sawn_cuts([self.piece('a', 96), self.piece('b', 96)])), 2)
        result = pack_sawn_cuts([self.piece('a', 100), self.piece('b', 91.875)])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['remaining_inches'], 0)
        self.assertEqual(result[0]['cuts'][1]['consumed_inches'], 91.875)
        self.assertEqual(pack_sawn_cuts([self.piece('full', 192)])[0]['remaining_inches'], 0)

    def test_species_and_product_stock_are_never_pooled(self):
        pieces = [self.piece('a', 40, 'SYP'), self.piece('b', 40, 'SPF')]
        self.assertEqual(len(pack_sawn_cuts(pieces)), 2)
        with self.assertRaisesRegex(ValueError, 'per SKU'):
            pack_sawn_cuts([self.piece('a', 40), self.piece('b', 40, stock=12)])

    def test_material_conservation_and_every_piece_once(self):
        pieces = [self.piece(str(n), v) for n, v in enumerate([67, 67, 41.1875, 65, 41, 192])]
        before = copy.deepcopy(pieces)
        boards = pack_sawn_cuts(pieces)
        self.assertEqual(pieces, before)
        self.assertCountEqual([c['piece_id'] for b in boards for c in b['cuts']], [p['id'] for p in pieces])
        for board in boards:
            self.assertGreaterEqual(board['remaining_inches'], 0)
            self.assertAlmostEqual(sum(c['consumed_inches'] for c in board['cuts'])+board['remaining_inches'], 192)
            for cut in board['cuts']:
                self.assertGreaterEqual(cut['consumed_inches'], cut['cut_inches'])
                self.assertLessEqual(cut['consumed_inches']-cut['cut_inches'], .125)

    def test_invalid_numbers_and_duplicate_pieces_rejected(self):
        for bad in [0, -1, True, math.inf, math.nan]:
            with self.assertRaises(ValueError):pack_sawn_cuts([self.piece('a', bad)])
            with self.assertRaises(ValueError):pack_sawn_cuts([self.piece('a', 10, stock=bad)])
        for bad in [-1, True, math.inf, math.nan]:
            with self.assertRaises(ValueError):pack_sawn_cuts([], bad)
        with self.assertRaisesRegex(ValueError, 'Unique'):
            pack_sawn_cuts([self.piece('a', 40), self.piece('a', 40)])
        with self.assertRaisesRegex(ValueError, 'SKU'):
            pack_sawn_cuts([self.piece('a', 40, '')])
        self.assertEqual(pack_sawn_cuts([]), [])


if __name__ == '__main__':unittest.main()
