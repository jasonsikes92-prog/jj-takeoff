import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from estimate_job import main


class EstimateJobTests(unittest.TestCase):
    def test_missing_job_never_calculates_an_implicit_house(self):
        with patch('estimate_job.calculate') as calculate, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main([])
            calculate.assert_not_called()

    def test_missing_files_and_existing_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);output=root/'existing.json';output.write_text('owner data')
            for target in (output,root/'new.json'):
                with patch('estimate_job.calculate') as calculate, contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):main(['--job',str(root),'--output',str(target)])
                    calculate.assert_not_called()
            self.assertEqual(output.read_text(),'owner data')
            self.assertFalse((root/'new.json').exists())

    def test_explicit_job_is_passed_and_snapshot_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);job=root/'job with spaces';job.mkdir()
            for name in ('measurements.json','quantity_rules.json','template_rows.json'):(job/name).write_text('{}')
            snapshot={'draft':{'estimate_released':False},'readiness':{'plan_sha256':'this-house',
                'rows_with_open_issues':3,'additional_rows_with_open_issues':1}}
            out=root/'snapshot.json'
            with patch('estimate_job.calculate',return_value=snapshot) as calculate, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--job',str(job),'--output',str(out)]),0)
                calculate.assert_called_once_with(job.resolve())
            self.assertEqual(json.loads(out.read_text()),snapshot)

    def test_failed_calculation_leaves_no_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('measurements.json','quantity_rules.json','template_rows.json'):(root/name).write_text('{}')
            out=root/'failed.json'
            with patch('estimate_job.calculate',side_effect=ValueError('Drawing changed')),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):main(['--job',str(root),'--output',str(out)])
            self.assertFalse(out.exists())

    def test_legacy_requires_explicit_job_and_all_scripts_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch('estimate_job.subprocess.run') as run,contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):main(['--job',temp,'--legacy'])
                run.assert_not_called()

    def test_workbook_preflight_rejects_invalid_outputs_before_calculation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);template=root/'template.xlsx';node=root/'node.exe'
            template.write_text('template');node.write_text('runtime')
            book=root/'existing.xlsx';book.write_text('owner workbook')
            base=['--job',temp,'--output',str(root/'new.json')]
            valid=['--template',str(template),'--node',str(node)]
            for extra in (['--workbook',str(root/'new.xlsx')],
                          ['--workbook',str(book),*valid],
                          ['--workbook',str(root/'new.csv'),*valid],
                          ['--workbook',str(root/'new.xlsx'),*valid,'--legacy']):
                with self.subTest(extra=extra),patch('estimate_job.calculate') as calculate,contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):main(base+extra)
                    calculate.assert_not_called()
            self.assertEqual(book.read_text(),'owner workbook')
            self.assertFalse((root/'new.json').exists())

    def test_workbook_uses_current_snapshot_and_propagates_export_failure(self):
        for code in (0,7):
            with self.subTest(export_code=code),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);job=root/'job';job.mkdir()
                for name in ('measurements.json','quantity_rules.json','template_rows.json'):(job/name).write_text('{}')
                template=root/'template.xlsx';template.write_text('template')
                node=root/'node.exe';node.write_text('runtime')
                snapshot={'draft':{'estimate_released':False},'readiness':{'plan_sha256':'selected-plan',
                    'rows_with_open_issues':3,'additional_rows_with_open_issues':1}}
                output=root/'current.json';book=root/'new.xlsx'
                def export(command):
                    self.assertEqual(Path(command[command.index('--snapshot')+1]),output.resolve())
                    self.assertEqual(json.loads(output.read_text()),snapshot)
                    self.assertEqual(Path(command[command.index('--output')+1]),book.resolve())
                    return SimpleNamespace(returncode=code)
                stdout=io.StringIO();stderr=io.StringIO()
                with patch('estimate_job.calculate',return_value=snapshot),patch('estimate_job.subprocess.run',side_effect=export) as run,contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
                    self.assertEqual(main(['--job',str(job),'--output',str(output),'--workbook',str(book),
                        '--template',str(template),'--node',str(node)]),code)
                    run.assert_called_once()
                self.assertEqual(json.loads(output.read_text()),snapshot)
                if code:
                    self.assertEqual(stdout.getvalue(),'')
                    self.assertIn('snapshot retained',stderr.getvalue())
                else:self.assertEqual(json.loads(stdout.getvalue())['workbook'],str(book.resolve()))


if __name__=='__main__':unittest.main()
