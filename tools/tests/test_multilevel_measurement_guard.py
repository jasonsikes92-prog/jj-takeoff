import unittest
from unittest.mock import patch
import test_new_plan_measure as fixtures
from new_plan_measure import measure_job


class MultiLevelMeasurementGuard(unittest.TestCase):
    def test_multiple_floor_pages_cannot_silently_disappear_from_sheet_map(self):
        # Reuse the existing valid isolated job; replace only its reviewed routing.
        fixture=fixtures.NewPlanMeasure();fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.addCleanup(fixture.doCleanups)
        review={'coverage_passed':True,'measurement_allowed':True,'unique_role_pages':{'foundation':1},
                'measurement_scope':'reviewed_set','roles_requiring_disambiguation':{'floor':[2,3]}}
        with patch('new_plan_measure.read_sheet_review',return_value=review),patch('jnj_takeoff.run_takeoff') as engine:
            with self.assertRaisesRegex(ValueError,'Multiple floor-plan pages'):measure_job(fixture.job)
            engine.assert_not_called()
        self.assertFalse((fixture.job/'draft_takeoff').exists())


if __name__=='__main__':unittest.main()
