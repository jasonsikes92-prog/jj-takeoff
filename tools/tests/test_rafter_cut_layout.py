import copy
import math
import unittest
from tools.rafter_cut_layout import stations,allocate


class RafterCuts(unittest.TestCase):
    def face(self):return {'id':'R1','points':[[0,0],[10,0],[10,4],[0,4]],
                          'points_per_foot':1,'surface_factor':math.sqrt(2)}
    def stock(self):return [{'sku':'S16','length_ft':16,'size':'2x6','invoice_grade_species':'SYP No.2'},
                            {'sku':'S26','length_ft':26,'size':'2x6','invoice_grade_species':'SPF/HF FJ'}]
    def test_stations_along_slope_at_sixteen_inches(self):
        segments=stations(self.face(),[1,0])
        self.assertEqual(len(segments),3)
        for i,s in enumerate(segments):
            self.assertAlmostEqual(s['station_coordinate_pt'],.0625+i*16/12)
            self.assertAlmostEqual(s['sloped_segment_ft'],10*math.sqrt(2))
        self.assertEqual(stations(self.face(),[-1,0]),segments)

    def test_multiple_disconnected_segments_are_not_one_long_member(self):
        f=self.face();f['points']=[[0,0],[10,0],[10,4],[7,4],[7,1],[3,1],[3,4],[0,4]]
        segments=stations(f,[1,0]);self.assertEqual(len(segments),5)
        self.assertEqual(len({s['id'] for s in segments}),5)
        self.assertAlmostEqual(segments[-1]['sloped_segment_ft'],3*math.sqrt(2))

    def test_exact_stock_limit_and_oversized_piece_accounted_without_auto_splice(self):
        s={'id':'A','roof_face':'R','pitch':12,'sloped_segment_ft':(312-5.5)/12}
        fit=allocate([s],self.stock());self.assertEqual(fit['boards'][0]['length_ft'],26)
        self.assertFalse(fit['requires_splice_layout'])
        s['sloped_segment_ft']+=.125/12;large=allocate([s],self.stock())
        self.assertFalse(large['boards']);self.assertEqual(len(large['requires_splice_layout']),1)
        self.assertFalse(large['structural_adequacy_verified'])

    def test_edit_and_restore_recalculate_cuts_and_preserve_grade(self):
        f=self.face();first=allocate(stations(f,[1,0]),self.stock())
        wider=copy.deepcopy(f);wider['points'][1][0]=wider['points'][2][0]=17
        after=allocate(stations(wider,[1,0]),self.stock())
        self.assertTrue(all(p['sku']=='S26' and p['invoice_species_grade']=='SPF/HF FJ' for p in after['pieces']))
        self.assertNotEqual(first['pieces'],after['pieces'])
        self.assertEqual(allocate(stations(f,[1,0]),self.stock()),first)

    def test_invalid_pitch_stock_and_duplicate_segments_rejected(self):
        with self.assertRaises(ValueError):stations(self.face(),[1,1])
        with self.assertRaises(ValueError):stations(self.face(),[.5,0])
        bad=self.stock();bad[1]['length_ft']=28
        with self.assertRaises(ValueError):allocate(stations(self.face(),[1,0]),bad)
        segments=stations(self.face(),[1,0])
        with self.assertRaises(ValueError):allocate(segments+[segments[0]],self.stock())
        thin=self.face();thin['points']=[[0,0],[10,0],[10,.01],[0,.01]]
        with self.assertRaisesRegex(ValueError,'no stations'):stations(thin,[1,0])
        duplicate_length=self.stock()+[{'sku':'OTHER16','length_ft':16,'size':'2x6','invoice_grade_species':'HF'}]
        with self.assertRaisesRegex(ValueError,'one material per stock length'):allocate(segments,duplicate_length)


if __name__=='__main__':unittest.main()
