import unittest
from owner_height_selection import select


class OwnerHeightSelectionTests(unittest.TestCase):
    def setUp(self):
        self.scenarios=[{'id':'printed','wall_height_inches':108},{'id':'precut','wall_height_inches':109.125}]
        self.evidence={'source_kind':'owner_confirmation','plan_sha256':'plan','selected_scenario':'precut','wall_height_inches':109.125}

    def test_owner_choice_matches_project_scenario(self):
        self.assertEqual(select(self.evidence,'plan',self.scenarios),self.scenarios[1])

    def test_invalid_or_mismatched_evidence_rejected(self):
        for key,value in [('source_kind','guess'),('plan_sha256','other'),('selected_scenario','missing'),
                          ('wall_height_inches',108),('wall_height_inches',True),('wall_height_inches',float('nan'))]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                select({**self.evidence,key:value},'plan',self.scenarios)
        with self.assertRaises(ValueError):select(self.evidence,'plan',self.scenarios+[self.scenarios[1]])
