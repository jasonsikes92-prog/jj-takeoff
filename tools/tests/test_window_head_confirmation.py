import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from below_window_stock_review import confirmed_head


class WindowHeadConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.record={'owner_confirmed':True,'plan_sha256':'plan',
            'datum':'rough_opening_head_above_main_subfloor','head_inches':96}

    def test_confirmed_project_rough_head(self):
        self.assertEqual(confirmed_head(self.record,'plan',96)['head_inches'],96)

    def test_another_plan_and_changed_height_rejected(self):
        for plan,height in [('other',96),('plan',95)]:
            with self.subTest(plan=plan,height=height),self.assertRaises(ValueError):
                confirmed_head(self.record,plan,height)

    def test_unit_head_does_not_confirm_rough_opening(self):
        with self.assertRaises(ValueError):
            confirmed_head({**self.record,'datum':'window_unit_head'},'plan',96)

    def test_unconfirmed_and_invalid_measurements_rejected(self):
        for field,value in [('owner_confirmed',False),('owner_confirmed','yes'),
                ('head_inches',True),('head_inches',0),('head_inches',float('nan'))]:
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                confirmed_head({**self.record,field:value},'plan',96)


if __name__=='__main__':unittest.main()
