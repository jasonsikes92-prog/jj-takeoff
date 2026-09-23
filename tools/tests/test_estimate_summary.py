import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from new_plan_template import read_template
from estimate_summary import summary_layout,review_summary
from estimate_readiness import readiness
from measurement_estimate import template_draft,price_draft
import test_package_pricing as package_tests
from package_pricing import scope_digest


class SummaryReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=read_template()

    def setUp(self):
        self.template=copy.deepcopy(self.source)
        self.state={'plan_sha256':'synthetic','version':1,'measurements':{}}
        self.rules={'plan_sha256':'synthetic','rules':[]}
        self.draft=template_draft(self.state,self.rules,self.template)

    def test_original_footer_is_layout_and_unresolved_summary_not_costs(self):
        report=readiness(self.draft,self.template)
        self.assertEqual([r['role'] for r in report['rows'][-10:]],
                         ['summary_heading']*2+['summary_field']*8)
        self.assertEqual([r['issues'] for r in report['rows'][-10:-8]],[[],[]])
        result=review_summary(self.draft,self.template)
        self.assertTrue(result['summary_layout_recognized'])
        self.assertTrue(all(r['amount'] is None for r in result['summary_fields']))
        self.assertTrue(all(r['issues'] for r in result['summary_fields'][2:]))
        self.assertIsNone(result['known_line_subtotals'])
        self.assertIsNone(result['whole_house_total'])
        self.assertFalse(result['estimate_released'])
        self.assertEqual(self.template,self.source)

    def test_incomplete_changed_or_cost_line_footer_is_not_guessed(self):
        for key,value in [('name','Tax'),('unit','each'),('parent','Trade'),
                          ('markup_pct','15'),('cost_type','FEE'),('cost_type','NaN'),('excel_row','900')]:
            with self.subTest(key=key,value=value):
                changed=copy.deepcopy(self.template);changed['rows'][-1][key]=value
                self.assertEqual(summary_layout(changed),{})
        for rows in (self.template['rows'][-1:],self.template['rows'][:-1],
                     self.template['rows']+[copy.deepcopy(self.template['rows'][0])]):
            self.assertEqual(summary_layout({'rows':rows}),{})

    def test_source_amounts_and_row_positions_do_not_become_job_values(self):
        for index,row in enumerate(self.template['rows'][-10:],800):
            row['excel_row']=str(index)
        self.template['rows'][-2]['cost_type']='-100.50'
        self.template['rows'][-1]['cost_type']='125000'
        self.assertEqual(len(summary_layout(self.template)),10)
        draft=template_draft(self.state,self.rules,self.template)
        result=review_summary(draft,self.template)
        self.assertTrue(all(r['amount'] is None for r in result['summary_fields']))

    def test_summary_cannot_receive_measured_or_partial_assembly_quantities(self):
        self.state['measurements']['floor']={'kind':'area','points':[[0,0],[100,0],[100,100],[0,100]],
            'width_pt':500,'height_pt':500,'points_per_foot':10}
        for use in ('template_quantity','assembly_input'):
            self.rules['rules']=[{'id':'bad','label':'Invalid summary target','measurement_ids':['floor'],
                'template_rows':['707'],'unit':'SF','rounding':'none','use':use,'basis':'Synthetic','remaining':[]}]
            with self.assertRaisesRegex(ValueError,'summary row'):
                template_draft(self.state,self.rules,self.template)

    def test_summary_cannot_receive_pending_measurement_or_unit_price(self):
        self.state['measurements']['floor']={'kind':'area','points':[[0,0],[100,0],[100,100],[0,100]],
            'width_pt':500,'height_pt':500,'points_per_foot':10,'engine_line_ids':['synthetic']}
        self.rules['rules']=[{'id':'bad','label':'Pending summary target','measurement_ids':['floor'],
            'template_rows':['707'],'unit':'SF','rounding':'none','use':'assembly_input',
            'defer_pending_scope':True,'basis':'Synthetic','remaining':[]}]
        with self.assertRaisesRegex(ValueError,'invalid template target'):
            template_draft(self.state,self.rules,self.template)
        pricing={'plan_sha256':'synthetic','measurement_version':1,
                 'rates':[{'row_id':self.draft['rows'][-1]['row_id']}]}
        with self.assertRaisesRegex(ValueError,'Summary or unknown'):
            price_draft(self.draft,pricing,'2026-09-19',Path('.'))

    def test_summary_overrides_do_not_hide_invalid_cost_ownership(self):
        row=self.draft['rows'][-1]
        row.update(draft_quantity=1,unit_cost=50,line_cost=50,line_price=55,
                   covered_by_package='other',completion_status='not_applicable')
        result=review_summary(self.draft,self.template)
        self.assertEqual(result['summary_fields'][-1]['role'],'summary_field')
        self.assertTrue(result['conflicts']);self.assertIsNone(result['known_line_subtotals'])
        self.assertIn('Summary row contains a construction quantity',result['summary_fields'][-1]['issues'])

    def priced_row(self):
        row=next(r for r in self.draft['rows'] if r['excel_row']=='101')
        row.update(line_cost=100.07,line_price=115.08,price_evidence={'source':'synthetic'},
                   pricing_basis='dated_allowance',purchase_tax=7.00)
        return row

    def test_partial_subtotal_uses_existing_line_amounts_once_and_preserves_inputs(self):
        self.priced_row();before=copy.deepcopy(self.draft)
        result=review_summary(self.draft,self.template)
        self.assertEqual(result['known_line_subtotals'],
                         {'line_cost':'100.07','line_price':'115.08','included_line_markup':'15.01'})
        self.assertEqual(len(result['priced_cost_rows']),1)
        self.assertTrue(result['unpriced_cost_row_ids'])
        self.assertEqual(self.draft,before)
        self.assertIsNone(result['whole_house_total'])

    def test_broken_group_or_summary_prices_withhold_entire_partial_subtotal(self):
        self.priced_row()
        for number in ('103','707'):
            changed=copy.deepcopy(self.draft)
            row=next(r for r in changed['rows'] if r['excel_row']==number)
            row.update(line_cost=100,line_price=115)
            result=review_summary(changed,self.template)
            self.assertTrue(result['conflicts']);self.assertIsNone(result['known_line_subtotals'])

    def test_missing_invalid_and_zero_money_are_distinct(self):
        row=self.priced_row()
        for value in (None,True,-1,float('nan'),float('inf')):
            row['line_price']=value
            self.assertTrue(review_summary(self.draft,self.template)['conflicts'])
        row.update(line_cost=0,line_price=0)
        self.assertEqual(review_summary(self.draft,self.template)['known_line_subtotals']['line_cost'],'0')

    def test_draft_cannot_change_template_summary_identity(self):
        self.draft['rows'][-1]['cost_type']='SUBCONTRACTOR'
        result=review_summary(self.draft,self.template)
        self.assertIn('Template field changed: cost_type',result['summary_fields'][-1]['issues'])


class SummaryPackageGuard(unittest.TestCase):
    def test_summary_cannot_be_covered_by_another_package(self):
        fixture=package_tests.Packages();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.draft['rows'][1]['cost_type']='0'
        fixture.package['reviewed_draft_sha256']=scope_digest(fixture.draft)
        with self.assertRaisesRegex(ValueError,'summary or unknown'):
            fixture.run_package()


if __name__=='__main__':unittest.main()
