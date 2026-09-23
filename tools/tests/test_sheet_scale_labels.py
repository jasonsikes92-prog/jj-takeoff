import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sheet_scale_labels import scale_labels,corroborate_dimension_scale


class SheetScaleLabels(unittest.TestCase):
    def read(self,lines):
        with fitz.open() as doc:
            page=doc.new_page()
            for i,line in enumerate(lines):page.insert_text((30,30+20*i),line)
            return scale_labels(page)

    def test_different_view_scales_and_no_scale_require_assignment(self):
        self.assertTrue(self.read(['1/4"=1\'','3/16"=1\''])['mixed_view_scales'])
        self.assertTrue(self.read(['1/4"=1\'','FOR ILLUSTRATION ONLY NO SCALE'])['mixed_view_scales'])

    def test_repeated_same_scale_is_not_a_conflict_or_calibration(self):
        r=self.read(['1/4"=1\'','SCALE: 1/4" = 1\'-0"'])
        self.assertFalse(r['mixed_view_scales']);self.assertFalse(r['calibrated'])
        self.assertEqual([l['nominal_points_per_foot'] for l in r['labels']],[18,18])

    def test_reviewed_view_excludes_adjacent_detail_scale(self):
        with fitz.open() as doc:
            page=doc.new_page(width=600,height=600)
            page.insert_text((30,30),'1/4 in = 1 ft')
            page.insert_text((400,30),'1 in = 1 ft')
            self.assertTrue(scale_labels(page)['mixed_view_scales'])
            result=scale_labels(page,[0,0,300,500])
            self.assertFalse(result['mixed_view_scales']);self.assertEqual(len(result['labels']),1)
            self.assertFalse(result['calibrated'])

    def test_dimensions_and_invalid_labels_are_not_scales(self):
        self.assertEqual(self.read(['16\'-4"','0/0"=1\'','1/4"=0\''])['labels'],[])

    def test_written_units_match_symbol_units_and_detect_mixed_views(self):
        result = self.read(['1/4 in = 1 ft', 'Scale: 0.25 inches = 1 foot'])
        self.assertEqual([item['nominal_points_per_foot'] for item in result['labels']], [18,18])
        self.assertFalse(result['calibrated'])
        self.assertTrue(self.read(['1/4 in = 1 ft', '1"=1\''])['mixed_view_scales'])

    def test_two_axes_and_printed_label_must_all_agree(self):
        controls = [{'axis':'horizontal','points_per_foot':18},
                    {'axis':'vertical','points_per_foot':18.002}]
        dimensions = {'controls':controls,'usable_candidate':False,'points_per_foot':None}
        printed = self.read(['1/4 in = 1 ft'])
        result = corroborate_dimension_scale(dimensions, printed)
        self.assertTrue(result['usable_candidate'])
        self.assertAlmostEqual(result['points_per_foot'],18.001)
        self.assertFalse(result['certified'])
        for invalid in ([], controls[:1], [controls[0], {'axis':'vertical','points_per_foot':36}]):
            refused = corroborate_dimension_scale({**dimensions,'controls':invalid}, printed)
            self.assertFalse(refused['usable_candidate'])
        for labels in ([], ['1/8 in = 1 ft'], ['1/4 in = 1 ft', 'NO SCALE'],
                       ['1/4 in = 1 ft', '1/8 in = 1 ft']):
            self.assertFalse(corroborate_dimension_scale(dimensions,self.read(labels))['usable_candidate'])


if __name__=='__main__':unittest.main()
