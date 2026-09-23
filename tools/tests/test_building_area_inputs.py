import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import fitz
from new_plan_template import read_template,initial_rules
from measurement_store import MeasurementStore
from measurement_scope_reviews import ScopeReviews
from measurement_estimate import template_draft


class BuildingAreaInputs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.template=read_template()
        with fitz.open() as doc:
            doc.new_page(width=1000,height=1000);doc.save(self.folder/'plan.pdf')
        self.sha=hashlib.sha256((self.folder/'plan.pdf').read_bytes()).hexdigest()

    def prepare(self,labels):
        self.measurements=[{'id':f'area-{i}','label':label+' source area','source_area_label':label,
            'kind':'area','page':1,'points':[[10+i*110,10],[110+i*110,10],[110+i*110,110],[10+i*110,110]],
            'points_per_foot':10,'width_pt':1000,'height_pt':1000,'color':'#00ff00','dependent_rows':[]}
            for i,label in enumerate(labels)]
        self.rules=initial_rules(self.sha,self.measurements,[],self.template,area_ids=[m['id'] for m in self.measurements])
        (self.folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':self.measurements}))
        self.store=MeasurementStore(self.folder);self.review=ScopeReviews(self.store,self.rules)

    def draft(self):return template_draft(self.store.read(),self.review.effective_rules(),self.template)

    def approve(self):
        for rule in self.rules['rules']:
            for identity in rule['measurement_ids']:
                self.review.save(rule['id'],identity,'approved_for_draft','Synthetic source label, full extent and scale checked',
                    'Test',self.store.read()['version'],self.sha,self.review.rules_sha256)

    def test_area_inputs_require_review_then_remain_unpriced(self):
        self.prepare(['GARAGE'])
        self.assertEqual(len(self.draft()['pending_quantities']),1)
        self.assertTrue(all(r['draft_quantity'] is None for r in self.draft()['rows']))
        self.approve();draft=self.draft();row=next(r for r in draft['rows'] if r['excel_row']=='8')
        self.assertEqual(row['draft_quantity'],100)
        self.assertEqual(row['pricing_role'],'input_only')
        self.assertTrue(all(r['line_price'] is None and r['line_cost'] is None for r in draft['rows']))
        self.assertFalse(draft['estimate_released'])

    def test_boundary_edit_withholds_prior_approval_until_new_review(self):
        self.prepare(['GARAGE']);self.approve()
        self.store.save('area-0',[[10,10],[210,10],[210,110],[10,110]],1,self.sha,'Synthetic expansion')
        self.assertEqual(self.store.read()['invalidated_rows'],['8'])
        self.assertEqual(len(self.draft()['pending_quantities']),1)
        self.assertIsNone(next(r for r in self.draft()['rows'] if r['excel_row']=='8')['draft_quantity'])
        self.approve()
        self.assertEqual(next(r for r in self.draft()['rows'] if r['excel_row']=='8')['draft_quantity'],200)

    def test_story_and_cover_ambiguities_do_not_become_cost_quantities(self):
        self.prepare(['HEATED','LIVING AREA','FRONT PATIO','REAR PATIO','FRONT PORCH','COVERED PORCH'])
        self.assertEqual(len(self.rules['rules']),1)
        self.assertEqual(self.rules['rules'][0]['template_rows'],['9'])
        draft=self.draft();self.assertEqual(len(draft['unmapped_measurements']),5)
        self.assertTrue(all('does not identify' in m['reason'] for m in draft['unmapped_measurements']))
        self.approve()
        populated=[r['excel_row'] for r in self.draft()['rows'] if r['draft_quantity'] is not None]
        self.assertEqual(populated,['9'])

    def test_explicit_floor_names_map_to_the_correct_original_inputs(self):
        self.prepare(['BASEMENT','FIRST FLOOR','SECOND FLOOR','THIRD FLOOR','GARAGE'])
        self.approve()
        self.assertEqual({r['excel_row']:r['draft_quantity'] for r in self.draft()['rows'] if r['draft_quantity'] is not None},
            {'4':100,'5':100,'6':100,'7':100,'8':100,'10':500})

    def test_explicitly_covered_patios_propose_one_reviewed_input(self):
        self.prepare(['BACK COVERED PATIO','FRONT COVERED PATIO',
                      'UNCOVERED PATIO LEFT','UNCOVERED PATIO RIGHT','HEATED AREA'])
        self.assertEqual(len(self.rules['rules']),1)
        rule=self.rules['rules'][0]
        self.assertEqual(rule['template_rows'],['9'])
        self.assertEqual(rule['measurement_ids'],['area-0','area-1'])
        self.assertEqual(len(self.draft()['pending_quantities']),1)
        self.assertIsNone(next(r for r in self.draft()['rows'] if r['excel_row']=='9')['draft_quantity'])
        self.approve()
        row=next(r for r in self.draft()['rows'] if r['excel_row']=='9')
        self.assertEqual(row['draft_quantity'],200)
        self.assertIsNone(row['line_cost'])
        self.assertEqual(len(self.draft()['unmapped_measurements']),3)

    def test_duplicate_same_story_outlines_do_not_double_count(self):
        self.prepare(['FIRST FLOOR','MAIN FLOOR']);self.approve()
        self.store.save('area-1',self.measurements[0]['points'],1,self.sha,'Synthetic duplicate outline')
        self.approve();draft=self.draft()
        self.assertEqual(len(draft['pending_quantities']),2)
        self.assertIn('Overlapping',draft['pending_quantities'][0]['reason'])
        self.assertIsNone(next(r for r in draft['rows'] if r['excel_row']=='5')['draft_quantity'])

    def test_total_excludes_uncovered_patio_and_edit_withholds_total(self):
        self.prepare(['FIRST FLOOR','GARAGE','COVERED PORCH','UNCOVERED PATIO LEFT'])
        self.assertIsNone(next(r for r in self.draft()['rows'] if r['excel_row']=='10')['draft_quantity'])
        self.approve()
        total=next(r for r in self.draft()['rows'] if r['excel_row']=='10')
        self.assertEqual(total['draft_quantity'],300)
        self.assertIsNone(total['line_cost'])
        self.store.save('area-1',[[120,10],[220,10],[220,120],[120,120]],1,self.sha,'Garage correction')
        rows={r['excel_row']:r for r in self.draft()['rows']}
        self.assertIsNone(rows['10']['draft_quantity'])
        self.assertIsNone(rows['8']['draft_quantity'])
        self.assertEqual(rows['5']['draft_quantity'],100)

    def test_ambiguous_patio_prevents_total_proposal(self):
        self.prepare(['FIRST FLOOR','FRONT PATIO'])
        self.assertFalse(any(r['id']=='candidate-building-area-total' for r in self.rules['rules']))

    def test_wrong_measurement_or_template_identity_is_rejected(self):
        self.prepare(['GARAGE'])
        for ids in (['area-0','area-0'],['missing']):
            with self.assertRaises(ValueError):initial_rules(self.sha,self.measurements,[],self.template,area_ids=ids)
        changed=copy.deepcopy(self.template)
        next(r for r in changed['rows'] if r['excel_row']=='8')['parent']='Concrete Slab'
        with self.assertRaisesRegex(ValueError,'template input missing'):initial_rules(self.sha,self.measurements,[],changed,area_ids=['area-0'])

    def test_heated_area_with_story_caption_is_only_a_pending_proposal(self):
        self.prepare(['HEATED AREA'])
        self.assertEqual(self.rules['rules'],[])
        self.measurements[0]['source_story_caption']={'story':'SECOND FLOOR'}
        proposed=initial_rules(self.sha,self.measurements,[],self.template,area_ids=['area-0'])['rules'][0]
        self.assertEqual(proposed['template_rows'],['6'])
        self.assertTrue(proposed['requires_geometry_review'])
        self.assertTrue(proposed['defer_pending_scope'])


if __name__=='__main__':unittest.main()
