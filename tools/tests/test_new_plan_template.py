import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from new_plan_template import read_template,initial_rules
from measurement_estimate import template_draft
from measurement_scope_reviews import ScopeReviews
from measurement_store import MeasurementStore
from estimate_readiness import readiness


class NewPlanTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        with fitz.open() as doc:
            doc.new_page(width=500,height=500);doc.save(self.folder/'plan.pdf')
        self.sha=hashlib.sha256((self.folder/'plan.pdf').read_bytes()).hexdigest()
        roof={'id':'roof','label':'Synthetic roof face','page':1,'kind':'area',
            'points':[[10,10],[110,10],[110,110],[10,110]],'points_per_foot':10,
            'width_pt':500,'height_pt':500,'color':'#0e7490','dependent_rows':[],
            'engine_line_ids':['synthetic-roof']}
        self.measurements=[roof,{**copy.deepcopy(roof),'id':'unclassified','label':'Unknown region'}]
        self.template=read_template()
        self.rules=initial_rules(self.sha,self.measurements,['roof'],self.template)
        (self.folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':self.measurements}))
        self.store=MeasurementStore(self.folder)
        self.reviews=ScopeReviews(self.store,self.rules)

    def draft(self):
        return template_draft(self.store.read(),self.reviews.effective_rules(),self.template)

    def approve(self):
        self.reviews.save('candidate-roof-surfaces','roof','approved_for_draft',
            'Synthetic rectangle and scale checked for test','Test',self.store.read()['version'],
            self.sha,self.reviews.rules_sha256)

    def test_original_template_identity_without_old_job_values(self):
        self.assertEqual(len(self.template['rows']),711)
        row=next(r for r in self.template['rows'] if r['excel_row']=='104')
        self.assertEqual(row['markup_pct'],'7')
        self.assertEqual(row['row_id'],'T-fb54b3b33e48-R0104')
        self.assertEqual(row['completion_status'],'not_yet_reconciled')
        for r in self.template['rows']:
            self.assertFalse(r['evidence'])
            self.assertFalse(r['current_price_certified'])
            self.assertFalse(r['completion_status'].startswith('not_applicable'))
            self.assertFalse(set(r).intersection({'quantity','unit_cost','line_cost','line_price'}))

    def test_pending_scope_and_unmapped_geometry_remain_visible(self):
        draft=self.draft();report=readiness(draft,self.template)
        self.assertEqual(len(draft['pending_quantities']),1)
        self.assertEqual(draft['unmapped_measurements'][0]['id'],'unclassified')
        self.assertTrue(all(r['draft_quantity'] is None for r in draft['rows']))
        for number in ('104','105','106'):
            row=next(r for r in report['rows'] if r['excel_row']==number)
            self.assertTrue(any('scope review outstanding' in issue for issue in row['issues']))
        self.assertEqual(report['pending_quantities'],draft['pending_quantities'])
        self.assertEqual(report['unmapped_measurements'],draft['unmapped_measurements'])

    def test_reviewed_input_recalculates_after_saved_edit_and_new_review(self):
        self.approve()
        def areas():
            draft=self.draft()
            self.assertTrue(all(r['draft_quantity'] is None and r['line_price'] is None for r in draft['rows']))
            return [a['quantity'] for r in draft['rows'] for a in r['assembly_inputs']]
        self.assertEqual(areas(),[100,100,100])
        self.store.save('roof',[[10,10],[210,10],[210,110],[10,110]],1,self.sha,'Synthetic width change')
        self.assertEqual(areas(),[])
        self.assertEqual(len(self.draft()['pending_quantities']),1)
        self.assertEqual(self.store.read()['invalidated_rows'],['104','105','106'])
        self.approve();self.assertEqual(areas(),[200,200,200])
        self.assertIsNone(self.draft()['whole_house_total'])

    def test_unreviewed_roof_does_not_hide_independent_quantity_and_bad_targets_fail(self):
        state=self.store.read()
        state['measurements']['unclassified'].pop('engine_line_ids')
        rules=copy.deepcopy(self.rules)
        rules['rules'].append({'id':'floor','label':'Independent test floor','measurement_ids':['unclassified'],
            'template_rows':['101'],'unit':'SF','rounding':'whole_up','use':'template_quantity',
            'basis':'Synthetic classified input','remaining':[]})
        draft=template_draft(state,rules,self.template)
        self.assertEqual(next(r for r in draft['rows'] if r['excel_row']=='101')['draft_quantity'],100)
        for target in ('103','9999'):
            invalid=copy.deepcopy(rules);invalid['rules'][0]['template_rows']=[target]
            with self.assertRaisesRegex(ValueError,'invalid template target'):
                template_draft(state,invalid,self.template)


if __name__=='__main__':unittest.main()
