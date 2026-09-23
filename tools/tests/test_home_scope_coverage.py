import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jnj_takeoff import ingest_bid, report_from_takeoff, review_bid_scopes
from levelground_scope import PRE_BID_SCOPE_CHECKLIST


class HomeScopeCoverageTests(unittest.TestCase):
    def report(self,lines=None,home=None):
        bid=None if lines is None else ingest_bid(lines)
        return report_from_takeoff({'lines':[]},home or {},{},bid=bid)

    def line(self,title,**changes):
        return {'desc':'Entire reviewed scope listed in the signed attachment.','amount':None,
                'scope_status':'included','source_ref':'bid page 2',
                'confirmed_scopes':[title],**changes}

    def test_major_trades_and_contract_topics_are_not_silently_absent(self):
        report=self.report([])
        by_id={c['id']:c for c in report['scope_checks']}
        required={'foundation','concrete','framing','roofing','windows','cladding',
                  'plumbing','electrical','hvac','insulation','drywall','interior_trim',
                  'flooring','tile','cabinets','countertops','painting','appliances',
                  'water_supply','wastewater','site_work','permits','site_operations',
                  'allowances','change_orders','cleaning'}
        self.assertTrue(required<=set(by_id))
        self.assertEqual(len(by_id),len(report['scope_checks']))
        self.assertEqual(len({c['title'] for c in report['scope_checks']}),len(by_id))
        self.assertTrue(all(by_id[k]['status']=='unverified' for k in required))
        self.assertTrue(all(f['realistic_low'] is None and f['realistic_high'] is None for f in report['findings']))
        self.assertIsNone(report['meta']['bid_total'])

    def test_confirmed_topic_leaves_question_list_but_keeps_source_record(self):
        title='Framing materials and labor'
        report=self.report([self.line(title)])
        check=next(c for c in report['scope_checks'] if c['title']==title)
        self.assertEqual(check['status'],'included_per_source_review')
        self.assertEqual(check['evidence_lines'][0]['source_ref'],'bid page 2')
        self.assertNotIn(check['question'],report['questions'])
        self.assertFalse(any(f['title']==title for f in report['findings']))
        self.assertTrue(any(f['title']=='Plumbing systems and fixtures' for f in report['findings']))

    def test_keyword_and_partial_scope_do_not_close_trade(self):
        report=self.report([self.line('Other scope',desc='Framing connectors only')])
        check=next(c for c in report['scope_checks'] if c['id']=='framing')
        self.assertEqual(check['status'],'unverified')
        self.assertIn(check['question'],report['questions'])

    def test_contract_process_topics_need_source_review_too(self):
        title='Change-order pricing is in the contract'
        pending=self.report([])
        self.assertTrue(any(f['title']==title for f in pending['findings']))
        approved=self.report([self.line(title)])
        check=next(c for c in approved['scope_checks'] if c['title']==title)
        self.assertNotIn(check['question'],approved['questions'])

    def test_exclusions_conflicts_and_intake_conflicts_stay_visible(self):
        title='Plumbing systems and fixtures'
        excluded=self.line(title,scope_status='excluded')
        r=self.report([excluded])
        self.assertEqual(next(f for f in r['findings'] if f['title']==title)['category'],'excluded_scope')
        r=self.report([excluded,self.line(title,source_ref='addendum page 1')])
        self.assertEqual(next(c for c in r['scope_checks'] if c['title']==title)['status'],'conflicting_wording')
        tech='Home technology, security & low-voltage'
        r=self.report([self.line(tech)],{'home_technology':False})
        self.assertEqual(next(c for c in r['scope_checks'] if c['title']==tech)['status'],'intake_bid_conflict')

    def test_optional_intake_is_consistent_in_prebid_and_bid_modes(self):
        for lines in (None,[]):
            pending=self.report(lines)
            check=next(c for c in pending['scope_checks'] if c['id']=='low_voltage')
            self.assertEqual(check['status'],'selection_unconfirmed')
            self.assertIn(check['question'],pending['questions'])
            declined=self.report(lines,{'home_technology':False})
            check=next(c for c in declined['scope_checks'] if c['id']=='low_voltage')
            self.assertEqual(check['status'],'not_selected')
            self.assertNotIn(check['question'],declined['questions'])
            self.assertFalse(any(f['title']==check['title'] for f in declined['findings']))

    def test_all_reviewed_topics_still_do_not_certify_complete_home(self):
        report=self.report([self.line(c['title']) for c in PRE_BID_SCOPE_CHECKLIST])
        self.assertEqual(report['questions'],[])
        self.assertEqual(report['findings'],[])
        self.assertFalse(report['complete_home_scope_review'])
        self.assertIsNone(report['meta']['our_range'])
        self.assertEqual(report['quantities'],[])
        self.assertTrue(report['unknowns'])
        custom=report_from_takeoff({'lines':[]},{},{},bid=ingest_bid([]),checklist=[])
        self.assertEqual(custom['scope_checks'],[])
        self.assertEqual(custom['scope_checklist_version'],'custom')


if __name__=='__main__':unittest.main()
