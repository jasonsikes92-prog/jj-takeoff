import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from local_requirements import requirements_context


class LocalRequirements(unittest.TestCase):
    def setUp(self):
        self.project={'state':'GA','code_basis_date':'2026-09-16'}
        self.record={'id':'test','state':'GA','source_kind':'official_public','review_status':'reviewed',
            'parcel_specific':False,'jurisdiction_scope':'state','checked_on':'2026-09-16',
            'review_due':'2026-10-16','effective_from':'2026-01-01','topic':'code',
            'summary':'Synthetic code adoption','source_url':'https://example.gov/code','authority':'Synthetic authority'}

    def check(self,p=None,r=None,as_of='2026-09-16'):
        return requirements_context(p or self.project,[r or self.record],as_of)

    def test_future_adoption_not_applied_to_historical_permit(self):
        p={**self.project,'code_basis_date':'2025-09-16'}
        self.assertEqual(self.check(p)['candidates'],[])
        current=self.check();self.assertEqual(len(current['candidates']),1)
        self.assertFalse(current['permit_compliance_verified']);self.assertFalse(current['coverage_complete'])

    def test_missing_basis_or_stale_source_requires_review(self):
        self.assertEqual(len(self.check({'state':'GA'})['needs_review']),1)
        self.assertEqual(len(self.check(as_of='2026-11-01')['needs_review']),1)

    def test_private_site_facts_and_homeowner_answers_never_transfer(self):
        for changes in ({'parcel_specific':True},{'source_kind':'homeowner_answer'},{'review_status':'unverified'}):
            r={**self.record,**changes};self.assertEqual(self.check(r=r)['candidates'],[])
        self.assertEqual(self.check({'state':'SC','code_basis_date':'2026-09-16'})['candidates'],[])

    def test_local_authority_and_site_conditions_must_match(self):
        r={**self.record,'jurisdiction_scope':'local','authority_id':'GA-Example','conditions':{'septic':True}}
        unknown=self.check(r=r)
        self.assertEqual(unknown['needs_review'],[])
        self.assertIn('authority_id',unknown['missing_project_fields'])
        p={**self.project,'authority_verified':True,'authority_id':'GA-Elsewhere','conditions':{'septic':True}}
        self.assertEqual(self.check(p,r)['candidates'],[])
        p['authority_id']='GA-Example';p['conditions']['septic']=False
        self.assertEqual(self.check(p,r)['candidates'],[])
        p['conditions']['septic']=True
        self.assertEqual(len(self.check(p,r)['candidates']),1)

    def test_truthy_authority_claim_is_not_verification(self):
        r={**self.record,'jurisdiction_scope':'local','authority_id':'GA-Example'}
        for value in ('yes','false',1,False,None):
            p={**self.project,'authority_id':'GA-Example','authority_verified':value}
            with self.subTest(value=value):
                result=self.check(p,r)
                self.assertEqual(result['candidates'],[]);self.assertEqual(len(result['needs_review']),1)
                self.assertFalse(result['local_authority_verified'])

    def test_document_revision_is_not_a_legal_effective_date(self):
        r={**self.record,'effective_from':None,'published_revision':'2024-09','source_page':4,
            'source_sha256':'source','effective_date_note':'Adoption date not given'}
        result=self.check(r=r)
        self.assertEqual(result['candidates'],[]);item=result['needs_review'][0]
        self.assertIsNone(item['effective_from']);self.assertEqual(item['published_revision'],'2024-09')
        self.assertEqual(item['source_page'],4);self.assertEqual(item['source_sha256'],'source')
        self.assertIn('Confirm effective dates and applicability of this published document',item['review_issues'])

    def test_boolean_conditions_do_not_accept_zero_one_or_text_as_facts(self):
        r={**self.record,'conditions':{'agricultural_zoning':False}}
        for value in (0,1,'false','true','unknown'):
            p={**self.project,'conditions':{'agricultural_zoning':value}}
            with self.subTest(value=value):
                result=self.check(p,r)
                self.assertEqual(result['candidates'],[]);self.assertEqual(len(result['needs_review']),1)
        p={**self.project,'conditions':{'agricultural_zoning':True}}
        result=self.check(p,r);self.assertEqual(result['candidates'],[]);self.assertEqual(result['needs_review'],[])

    def test_same_place_name_cannot_select_another_authority(self):
        r={**self.record,'jurisdiction_scope':'local','authority_id':'GA-JASPER-COUNTY'}
        for authority in ('GA-JASPER-CITY','SC-JASPER-COUNTY','Jasper',None):
            p={**self.project,'authority_id':authority,'authority_verified':True}
            with self.subTest(authority=authority):
                result=self.check(p,r);self.assertEqual(result['candidates'],[]);self.assertEqual(result['needs_review'],[])

    def test_verified_flag_without_authority_is_still_unknown(self):
        result=self.check({**self.project,'authority_verified':True})
        self.assertFalse(result['local_authority_verified'])
        self.assertIn('authority_id',result['missing_project_fields'])


if __name__=='__main__':unittest.main()
