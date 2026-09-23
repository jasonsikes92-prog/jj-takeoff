import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_store import MeasurementStore,EditConflict
from measurement_scope_reviews import ScopeReviews
from measurement_quantities import rollup


class ScopeReviewTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name);raw=b'fixed drawing identity'
        (self.folder/'plan.pdf').write_bytes(raw)
        self.sha=hashlib.sha256(raw).hexdigest()
        measurement={'id':'lights','page':1,'kind':'count','width_pt':500,'height_pt':500,
                     'points':[[10,10],[20,20]],'dependent_rows':['204'],'engine_line_ids':['symbol']}
        (self.folder/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[measurement]}))
        self.store=MeasurementStore(self.folder)
        self.rules={'plan_sha256':self.sha,'rules':[{'id':'lighting','label':'Lights','measurement_ids':['lights'],
            'unit':'EA','rounding':'whole_up','template_rows':['204'],'use':'assembly_input','basis':'Drawing legend','remaining':['Other devices']}]}
        self.reviews=ScopeReviews(self.store,self.rules)
        self.payload={'rule_id':'lighting','measurement_id':'lights','decision':'approved_for_draft',
            'scope':'Located recessed labels only, excluding legend','reviewer':'Test reviewer',
            'base_version':1,'plan_sha256':self.sha,'rules_sha256':self.reviews.rules_sha256}

    def test_durable_decision_rejection_and_history(self):
        with self.assertRaisesRegex(ValueError,'current scope review'):rollup(self.store.read(),self.rules)
        self.reviews.save(**self.payload)
        reopened=ScopeReviews(MeasurementStore(self.folder),self.rules)
        self.assertEqual(rollup(self.store.read(),reopened.effective_rules())['quantities'][0]['quantity'],2)
        reopened.save(**{**self.payload,'decision':'not_suitable_for_estimate','scope':'Wrong physical meaning'})
        with self.assertRaisesRegex(ValueError,'current scope review'):rollup(self.store.read(),reopened.effective_rules())
        self.assertEqual(len(reopened.history()),2)
        self.assertFalse(reopened.history()[0]['reviewer_identity_authenticated'])

    def test_saved_count_edit_requires_new_review_and_stale_submit_fails(self):
        self.reviews.save(**self.payload)
        changed=self.store.save('lights',[[10,10]],1,self.sha,'Remove duplicate')
        with self.assertRaisesRegex(ValueError,'current scope review'):rollup(changed,self.reviews.effective_rules())
        with self.assertRaises(EditConflict):self.reviews.save(**self.payload)
        self.reviews.save(**{**self.payload,'base_version':2})
        self.assertEqual(rollup(changed,self.reviews.effective_rules())['quantities'][0]['quantity'],1)

    def test_changed_rule_cannot_inherit_review(self):
        self.reviews.save(**self.payload)
        changed=copy.deepcopy(self.rules);changed['rules'][0]['basis']='Different interpretation'
        reopened=ScopeReviews(self.store,changed)
        with self.assertRaisesRegex(ValueError,'current scope review'):rollup(self.store.read(),reopened.effective_rules())
        with self.assertRaises(EditConflict):reopened.save(**self.payload)

    def test_invalid_scope_or_wrong_mapping_never_saved(self):
        for update in ({'scope':' '},{'reviewer':''},{'decision':'certified'},
                       {'measurement_id':'other'},{'rule_id':'missing'},{'base_version':True}):
            with self.assertRaises(ValueError):self.reviews.save(**{**self.payload,**update})
        self.assertEqual(self.reviews.history(),[])

if __name__=='__main__':unittest.main()
