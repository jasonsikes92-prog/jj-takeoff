import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from new_plan_intake import create_job,inventory


class NewPlanIntake(unittest.TestCase):
    def test_failed_schedule_leaves_no_job_and_corrected_retry_succeeds(self):
        self.pdf(['FLOOR PLAN']);job=self.root/'retry'
        with self.assertRaisesRegex(ValueError,'another plan'):
            create_job(self.plan,job,inputs={'door_schedule':{'plan_sha256':'wrong'}})
        self.assertFalse(job.exists())
        self.assertEqual(list(self.root.glob('.intake-*')),[])
        result=create_job(self.plan,job)
        intake=json.loads((job/'estimate_intake.json').read_bytes())
        self.assertEqual(intake['plan_file'],str((job/'plan.pdf').resolve()))
        self.assertEqual(result['company_intake'],str((job/'estimate_intake.json').resolve()))
        from door_specifications import read_door_specifications
        from door_hardware_specifications import read_hardware_specifications
        self.assertIsNotNone(read_door_specifications(job))
        self.assertIsNotNone(read_hardware_specifications(job))

    def test_late_intake_failure_cannot_publish_incomplete_job(self):
        self.pdf(['FLOOR PLAN']);job=self.root/'failed'
        with patch('new_plan_intake.requirements_context',side_effect=ValueError('bad jurisdiction')):
            with self.assertRaisesRegex(ValueError,'bad jurisdiction'):create_job(self.plan,job)
        self.assertFalse(job.exists())
        self.assertEqual(list(self.root.glob('.intake-*')),[])

    def test_job_created_during_preparation_is_preserved(self):
        self.pdf(['FLOOR PLAN']);job=self.root/'competing'
        def competing_inventory(plan):
            result=inventory(plan)
            job.mkdir();(job/'owner-notes.txt').write_text('Keep these decisions')
            return result
        with patch('new_plan_intake.inventory',side_effect=competing_inventory):
            with self.assertRaises(FileExistsError):create_job(self.plan,job)
        self.assertEqual((job/'owner-notes.txt').read_text(),'Keep these decisions')
        self.assertEqual([p.name for p in job.iterdir()],['owner-notes.txt'])
        self.assertEqual(list(self.root.glob('.intake-*')),[])

    def test_bad_plan_fact_is_rejected_before_copying_or_extracting_plan(self):
        self.pdf(['FLOOR PLAN'])
        job=self.root/'invalid-job'
        with patch('new_plan_intake.inventory') as extract:
            with self.assertRaisesRegex(ValueError,'backfilled_slab'):
                create_job(self.plan,job,inputs={'facts':{'backfilled_slab':'yes'}})
            extract.assert_not_called()
        self.assertFalse(job.exists())

    def test_conflicting_slab_facts_do_not_create_a_partial_job(self):
        self.pdf(['FLOOR PLAN']);job=self.root/'contradictory-job'
        with patch('new_plan_intake.inventory') as extract:
            with self.assertRaisesRegex(ValueError,'facts conflict'):
                create_job(self.plan,job,inputs={'facts':{'concrete_slab':False,'backfilled_slab':True}})
            extract.assert_not_called()
        self.assertFalse(job.exists())
        self.assertEqual(list(self.root.glob('.intake-*')),[])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.plan=self.root/'source.pdf'
    def tearDown(self):self.tmp.cleanup()
    def pdf(self,texts):
        doc=fitz.open()
        for text in texts:doc.new_page().insert_text((30,30),text)
        doc.save(self.plan);doc.close()
    def test_index_is_not_misidentified_as_every_plan_role(self):
        self.pdf(['INDEX OF DRAWINGS\nFLOOR PLAN\nROOF PLAN','FLOOR PLAN','ROOF PLAN'])
        result=inventory(self.plan)
        self.assertEqual(result['unique_role_pages'],{'floor':2,'roof':3})
        self.assertTrue(all(p['image_review_required'] for p in result['pages']))
    def test_duplicate_floor_pages_are_not_silently_chosen(self):
        self.pdf(['FLOOR PLAN','FLOOR PLAN'])
        result=inventory(self.plan)
        self.assertNotIn('floor',result['unique_role_pages'])
        self.assertEqual(result['roles_requiring_disambiguation']['floor'],[1,2])

    def test_basement_and_main_floor_are_both_retained(self):
        self.pdf(['BASEMENT FLOOR\nPLAN','MAIN FLOOR PLAN','REFER TO BASEMENT FLOOR PLAN'])
        result=inventory(self.plan)
        self.assertEqual(result['roles_requiring_disambiguation']['floor'],[1,2])
        self.assertNotIn('floor',result['unique_role_pages'])
        self.assertEqual(result['pages'][2]['role_candidates'],[])

    def test_wrapped_foundation_title_and_area_sheet_alias(self):
        self.pdf(['FOUNDATION\nPLAN','SQFT SHEET'])
        result=inventory(self.plan)
        self.assertEqual(result['unique_role_pages'],{'foundation':1,'area_schedule':2})
        self.assertEqual(result['measured_quantities'],{})
        self.assertTrue(all(p['image_review_required'] for p in result['pages']))

    def test_wrapped_cover_title_still_excludes_index_candidates(self):
        self.pdf(['COVER\nSHEET\nFOUNDATION\nPLAN','FOUNDATION\nPLAN'])
        result=inventory(self.plan)
        self.assertTrue(result['pages'][0]['drawing_index'])
        self.assertEqual(result['unique_role_pages'],{'foundation':2})

    def test_separated_words_and_notes_are_not_sheet_titles(self):
        self.pdf(['FOUNDATION\nGENERAL NOTES\nPLAN\nREFER TO FOUNDATION PLAN'])
        self.assertEqual(inventory(self.plan)['unique_role_pages'],{})

    def test_area_reference_excludes_uncovered_patio_and_is_not_a_measurement(self):
        self.pdf(['SQFT SHEET\nHEATED AREA 1000.00\nCOVERED PATIO 250.00\nUNCOVERED PATIO 300.00'])
        result=inventory(self.plan)
        reference=result['area_schedule_references'][0]
        self.assertEqual(reference['page'],1)
        self.assertEqual(len(reference['rows']),3)
        self.assertEqual(reference['under_roof_reference_sf'],1250)
        self.assertEqual(reference['use'],'comparison_only')
        self.assertFalse(reference['measured_from_geometry'])
        self.assertFalse(reference['certified'])
        self.assertEqual(result['measured_quantities'],{})
        self.assertFalse(result['estimate_released'])

    def test_empty_area_schedule_does_not_claim_zero_area(self):
        self.pdf(['SQFT SHEET'])
        reference=inventory(self.plan)['area_schedule_references'][0]
        self.assertEqual(reference['rows'],[])
        self.assertIsNone(reference['under_roof_reference_sf'])
    @patch('new_plan_intake.ocr_page',return_value=('COVER SHEET\nFOUNDATION PLAN\nFIRST FLOOR PLAN\nSECOND FLOOR PLAN\nROOF PLAN',None))
    def test_ocr_cover_index_does_not_compete_with_actual_sheets(self,mock_ocr):
        self.pdf(['','FOUNDATION PLAN','FIRST FLOOR PLAN','SECOND FLOOR PLAN','ROOF PLAN'])
        result=inventory(self.plan)
        self.assertTrue(result['pages'][0]['drawing_index'])
        self.assertEqual(result['pages'][0]['role_candidates'],[])
        self.assertEqual(result['unique_role_pages'],{'foundation':2,'roof':5})
        self.assertEqual(result['roles_requiring_disambiguation'],{'floor':[3,4]})
    @patch('new_plan_intake.ocr_page',return_value=('',None))
    def test_company_practices_transfer_but_roberts_quantities_and_prices_do_not(self,mock_ocr):
        self.pdf(['FLOOR PLAN',''])
        job=self.root/'new-job'
        create_job(self.plan,job,inputs={'project_overrides':{'framing.stud_size':'2x6'}})
        intake=json.loads((job/'estimate_intake.json').read_text())
        self.assertEqual(intake['settings']['framing.outside_corner_studs'],3)
        self.assertEqual(intake['settings']['framing.stud_size'],'2x6')
        self.assertEqual(intake['current_prices'],{});self.assertEqual(intake['quantity_measurements'],{})
        self.assertEqual(Path(intake['plan_file']),job/'plan.pdf')
        self.assertEqual(hashlib.sha256(self.plan.read_bytes()).hexdigest(),intake['plan_sha256'])
        inv=json.loads((job/'plan_inventory.json').read_text())
        self.assertTrue(inv['pages'][1]['text_extraction_empty']);self.assertFalse(inv['estimate_released'])
        original=(job/'estimate_intake.json').read_bytes()
        with self.assertRaises(FileExistsError):create_job(self.plan,job)
        self.assertEqual((job/'estimate_intake.json').read_bytes(),original)
    @patch('new_plan_intake.ocr_page',return_value=('FLOOR PLAN',None))
    def test_scanned_text_is_labeled_and_never_certifies_geometry(self,mock_ocr):
        self.pdf([''])
        value=inventory(self.plan)
        self.assertEqual(value['unique_role_pages'],{'floor':1})
        self.assertEqual(value['pages'][0]['text_method'],'local_ocr')
        self.assertTrue(value['pages'][0]['image_review_required'])
        self.assertEqual(value['measured_quantities'],{})
    @patch('new_plan_intake.ocr_page',return_value=('','OCR timed out'))
    def test_ocr_failure_remains_visible(self,mock_ocr):
        self.pdf([''])
        value=inventory(self.plan)
        self.assertEqual(value['pages'][0]['ocr_issue'],'OCR timed out')
        self.assertEqual(value['unique_role_pages'],{})

    def test_intake_binds_dated_public_requirement_snapshot_to_plan(self):
        from datetime import date
        self.pdf(['FLOOR PLAN'])
        for name,state,basis,count in [('new','GA','2026-09-16',1),('historical','GA','2025-09-16',0),('other','SC','2026-09-16',0)]:
            job=self.root/name
            with patch('new_plan_intake.date') as clock:
                clock.today.return_value=date(2026,9,16)
                create_job(self.plan,job,inputs={'jurisdiction':{'state':state,'code_basis_date':basis}})
            context=json.loads((job/'local_requirements.json').read_text())
            self.assertEqual(len(context['candidates']),count)
            self.assertEqual(context['registry_sha256'],hashlib.sha256((job/'official_requirements_snapshot.json').read_bytes()).hexdigest())
            self.assertEqual(context['plan_sha256'],hashlib.sha256(self.plan.read_bytes()).hexdigest())
            self.assertFalse(context['coverage_complete']);self.assertFalse(context['permit_compliance_verified'])

    def test_jasper_documents_are_dated_review_items_not_current_code_approval(self):
        from datetime import date
        self.pdf(['FLOOR PLAN']);job=self.root/'jasper'
        with patch('new_plan_intake.date') as clock:
            clock.today.return_value=date(2026,9,19)
            create_job(self.plan,job,inputs={'jurisdiction':{'state':'GA','code_basis_date':'2026-09-19',
                'authority_id':'GA-JASPER-COUNTY','authority_verified':True,
                'conditions':{'agricultural_zoning':False,'crawlspace':True,'residential_new_construction':True}}})
        context=json.loads((job/'local_requirements.json').read_bytes())
        self.assertEqual(len(context['needs_review']),6)
        self.assertTrue(all(r['effective_from'] is None for r in context['needs_review']))
        self.assertTrue(all(r['source_sha256']=='d92c191d1577c78cf4ecfb85fb8733ff80f69c4dac75b2a1b6476d11f5b0675a'
                            for r in context['needs_review']))
        self.assertEqual(context['registry_sha256'],hashlib.sha256((job/'official_requirements_snapshot.json').read_bytes()).hexdigest())
        self.assertFalse(context['permit_compliance_verified'])
        self.assertEqual(json.loads((job/'estimate_intake.json').read_bytes())['current_prices'],{})

if __name__=='__main__':unittest.main()
