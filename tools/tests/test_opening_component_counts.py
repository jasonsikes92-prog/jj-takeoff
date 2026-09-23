import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_quantities import rollup


class OpeningComponents(unittest.TestCase):
    def setUp(self):
        opening={'kind':'length','points':[[0,0],[60,0]],'points_per_foot':12,
            'width_pt':500,'height_pt':500}
        self.state={'version':1,'plan_sha256':'plan','measurements':{'O08':opening,'O09':copy.deepcopy(opening)}}
        self.rule={'id':'bypass','label':'Bypass panels','measurement_ids':['O08','O09'],
            'count_openings':True,'units_per_opening':2,'units_per_opening_source':'Owner R22',
            'unit':'EA','rounding':'whole_up','template_rows':['137'],'use':'assembly_input',
            'basis':'Two panels per closet opening','remaining':['Panel widths and selected product']}

    def result(self,rule=None):
        return rollup(self.state,{'plan_sha256':'plan','rules':[rule or self.rule]})['quantities'][0]

    def test_two_openings_four_panels_without_inventing_width(self):
        r=self.result()
        self.assertEqual((r['measured_quantity'],r['quantity']),(4,4))
        self.assertEqual(r['opening_assembly'],{'opening_count':2,'units_per_opening':2,'source':'Owner R22'})
        self.assertIsNone(r['current_price']);self.assertFalse(r['certified'])

    def test_width_change_is_not_an_extra_panel(self):
        self.state['measurements']['O08']['points'][1][0]=90
        self.assertEqual(self.result()['quantity'],4)
        self.rule['measurement_ids']=['O08']
        self.assertEqual(self.result()['quantity'],2)

    def test_waste_applied_after_panel_conversion(self):
        self.rule.update(waste_percent=10,waste_source='Separate estimating instruction')
        r=self.result();self.assertEqual(r['measured_quantity'],4)
        self.assertEqual(r['quantity'],5);self.assertAlmostEqual(r['waste_adjusted_quantity'],4.4)

    def test_invalid_count_or_unsourced_conversion_rejected(self):
        for value in (True,0,-1,1.5,'2',None):
            with self.subTest(value=value):
                self.rule['units_per_opening']=value
                with self.assertRaises(ValueError):self.result()
        self.rule['units_per_opening']=2;self.rule['units_per_opening_source']=' '
        with self.assertRaises(ValueError):self.result()
        self.rule['units_per_opening_source']='Owner';self.rule['count_openings']=False
        with self.assertRaises(ValueError):self.result()

    def test_default_keeps_existing_opening_count(self):
        self.rule.pop('units_per_opening');self.rule.pop('units_per_opening_source')
        r=self.result();self.assertEqual(r['quantity'],2);self.assertNotIn('opening_assembly',r)

    def test_duplicate_opening_is_rejected(self):
        self.rule['measurement_ids']=['O08','O08']
        with self.assertRaises(ValueError):self.result()


if __name__=='__main__':unittest.main()
