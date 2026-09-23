import copy
import unittest
from tools.subfloor_panel_layout import calculate
from tools.subfloor_joints import from_layout


class SubfloorJoints(unittest.TestCase):
    def test_single_panel_has_no_internal_seams(self):
        result=from_layout(calculate([[0,0],[8,0],[8,4],[0,4]],1))
        self.assertEqual(result['seams'],[])
        self.assertEqual(result['footprint_perimeter_lf'],24)
        self.assertIsNone(result['adhesive_purchase_quantity'])
        self.assertIsNone(result['fastener_purchase_quantity'])

    def test_staggered_rectangle_counts_shared_seams_once(self):
        layout=calculate([[0,0],[16,0],[16,8],[0,8]],1,stagger_inches=48)
        result=from_layout(layout)
        self.assertEqual(result['tongue_and_groove_lf'],16)
        self.assertEqual(result['butt_joint_lf'],12)
        self.assertEqual(result['total_shared_joint_lf'],28)
        self.assertEqual(result['footprint_perimeter_lf'],48)
        layout['pieces'].reverse()
        self.assertEqual(from_layout(layout),result)

    def test_recess_boundary_is_not_a_shared_seam(self):
        result=from_layout(calculate([[0,0],[16,0],[16,4],[8,4],[8,8],[0,8]],1,stagger_inches=48))
        self.assertEqual(result['tongue_and_groove_lf'],8)
        self.assertEqual(result['butt_joint_lf'],8)
        self.assertEqual(result['footprint_perimeter_lf'],48)

    def test_product_width_and_reversed_source_preserve_lengths(self):
        points=[[0,0],[16,0],[16,95/12],[0,95/12]]
        a=from_layout(calculate(points,1,course_inches=47.5,panel_width_inches=47.5,stagger_inches=48))
        b=from_layout(calculate(list(reversed(points)),1,course_inches=47.5,panel_width_inches=47.5,stagger_inches=48))
        self.assertEqual(a['tongue_and_groove_lf'],16)
        self.assertAlmostEqual(a['butt_joint_lf'],3*47.5/12)
        for key in ['tongue_and_groove_lf','butt_joint_lf','total_shared_joint_lf']:
            self.assertEqual(a[key],b[key])

    def test_missing_duplicate_overlapping_and_wrong_course_rejected(self):
        original=calculate([[0,0],[16,0],[16,8],[0,8]],1)
        missing=copy.deepcopy(original);missing['pieces'].pop()
        duplicate=copy.deepcopy(original);duplicate['pieces'].append(duplicate['pieces'][0])
        overlap=copy.deepcopy(original);overlap['pieces'][1]['footprint_polygons_ft']=overlap['pieces'][0]['footprint_polygons_ft']
        wrong_course=copy.deepcopy(original);wrong_course['pieces'][1]['course']=99
        for layout in [missing,duplicate,overlap,wrong_course]:
            with self.assertRaises(ValueError):from_layout(layout)


if __name__=='__main__':unittest.main()
