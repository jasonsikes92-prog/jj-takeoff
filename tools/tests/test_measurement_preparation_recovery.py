"""Failed preparation must never occupy or overwrite the editable draft."""
import json
import unittest
from unittest.mock import patch
import test_new_plan_measure as fixture
from new_plan_measure import measure_job
from measurement_store import MeasurementStore


class PreparationRecovery(unittest.TestCase):
    setUp = fixture.NewPlanMeasure.setUp

    def attempts(self):
        return list(self.job.glob('.takeoff-attempt-*'))

    def test_late_failure_preserves_evidence_and_retry_publishes_usable_draft(self):
        with patch('jnj_takeoff.run_takeoff', return_value=self.result), patch(
                'opening_quantity_review.default_mapping', side_effect=OSError('Disk failure')):
            with self.assertRaises(OSError):
                measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff').exists())
        failed, = self.attempts()
        before = {p.name:p.read_bytes() for p in failed.iterdir() if p.is_file()}
        self.assertIn('measurements.json', before)
        self.assertIn('template_rows.json', before)
        self.assertEqual(json.loads(before['preparation_failure.json'])['error_type'], 'OSError')
        with patch('jnj_takeoff.run_takeoff', return_value=self.result):
            result = measure_job(self.job)
        self.assertTrue(result['editor_available'])
        self.assertFalse(result['estimate_released'])
        self.assertEqual(len(MeasurementStore(self.job/'draft_takeoff').read()['measurements']), 1)
        self.assertEqual(before, {p.name:p.read_bytes() for p in failed.iterdir() if p.is_file()})
        self.assertEqual(self.attempts(), [failed])

    def test_existing_draft_and_saved_edits_are_never_replaced(self):
        target = self.job/'draft_takeoff'; target.mkdir()
        edit = target/'measurement_edits.sqlite3'; edit.write_bytes(b'existing edits')
        with patch('jnj_takeoff.run_takeoff') as engine, self.assertRaises(FileExistsError):
            measure_job(self.job)
        engine.assert_not_called()
        self.assertEqual(edit.read_bytes(), b'existing edits')
        self.assertEqual(self.attempts(), [])

    def test_competing_publication_is_preserved(self):
        def engine(*args, **kwargs):
            target = self.job/'draft_takeoff'; target.mkdir()
            (target/'keep.txt').write_text('other completed run')
            return self.result
        with patch('jnj_takeoff.run_takeoff', side_effect=engine), self.assertRaises(FileExistsError):
            measure_job(self.job)
        self.assertEqual((self.job/'draft_takeoff/keep.txt').read_text(), 'other completed run')
        self.assertEqual(len(self.attempts()), 1)

    def test_interrupted_staging_is_preserved_and_does_not_block_a_new_attempt(self):
        interrupted = self.job/'.takeoff-attempt-interrupted'; interrupted.mkdir()
        (interrupted/'keep.txt').write_text('partial work from interrupted process')
        with patch('jnj_takeoff.run_takeoff', return_value=self.result):
            measure_job(self.job)
        self.assertEqual((interrupted/'keep.txt').read_text(), 'partial work from interrupted process')
        self.assertEqual(self.attempts(), [interrupted])

    def test_failed_source_review_publishes_nothing(self):
        with patch('new_plan_measure.read_sheet_review', side_effect=ValueError('Changed source')):
            with self.assertRaises(ValueError): measure_job(self.job)
        self.assertFalse((self.job/'draft_takeoff').exists())
        self.assertEqual(self.attempts(), [])


if __name__ == '__main__': unittest.main()
