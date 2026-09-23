import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import fitz
from roof_coverage_review import read_review


class RoofCoverageReview(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.job=Path(temporary.name)
        with fitz.open() as doc:
            page=doc.new_page(width=300,height=300);page.draw_rect((30,30,200,200))
            page.draw_rect((40,40,190,190),dashes='[3 2] 0')
            doc.save(self.job/'plan.pdf')
        self.sha=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.review={'plan_sha256':self.sha,'page':1,'reviewer':'Test','basis':'Independent outer source strokes',
            'points':[[30,30],[200,30],[200,200],[30,200]],'source_cad_paths':[0]}

    def write(self,review):
        (self.job/'roof_coverage_review.json').write_text(json.dumps(review))

    def test_native_trace_is_source_bound_but_not_scope_certified(self):
        self.assertIsNone(read_review(self.job,self.sha,1))
        self.write(self.review);result=read_review(self.job,self.sha,1)
        self.assertTrue(result['review_sha256']);self.assertFalse(result['scope_certified'])
        self.assertFalse(result['reviewer_identity_authenticated'])

    def test_explicit_subpoint_tolerance_requires_basis_and_rejects_larger_shift(self):
        shifted={**self.review,'points':[[30.12,30],[200,30],[200,200],[30.12,200]]}
        self.write(shifted)
        with self.assertRaises(ValueError):read_review(self.job,self.sha,1)
        shifted.update(source_tolerance_pt=.125,tolerance_basis='Trace remains within printed stroke; tiny CAD discrepancy')
        self.write(shifted)
        self.assertEqual(read_review(self.job,self.sha,1)['source_tolerance_pt'],.125)
        for fields in ({'source_tolerance_pt':1},{'source_tolerance_pt':True},{'source_tolerance_pt':float('nan')},
                       {'tolerance_basis':''},{'points':[[31,30],[200,30],[200,200],[31,200]]}):
            self.write({**shifted,**fields})
            with self.assertRaises(ValueError):read_review(self.job,self.sha,1)

    def test_tolerance_cannot_exceed_printed_line_half_width(self):
        with fitz.open() as doc:
            page=doc.new_page(width=300,height=300);page.draw_rect((30,30,200,200),width=.1)
            doc.save(self.job/'thin.pdf')
        (self.job/'plan.pdf').write_bytes((self.job/'thin.pdf').read_bytes())
        digest=hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest()
        self.write({**self.review,'plan_sha256':digest,'source_tolerance_pt':.125,'tolerance_basis':'Too wide for this stroke'})
        with self.assertRaisesRegex(ValueError,'half-width'):read_review(self.job,digest,1)

    def test_wrong_source_page_or_unexplained_review_fails(self):
        for change in ({'plan_sha256':'other'},{'page':2},{'basis':''},{'reviewer':''}):
            self.write({**self.review,**change})
            with self.assertRaises(ValueError):read_review(self.job,self.sha,1)

    def test_invented_trace_and_wrong_or_dashed_paths_fail(self):
        for change in ({'points':[[31,30],[200,30],[200,200],[31,200]]},
                       {'source_cad_paths':[]},{'source_cad_paths':[1]},{'source_cad_paths':[99]}):
            self.write({**self.review,**change})
            with self.assertRaises(ValueError):read_review(self.job,self.sha,1)


if __name__=='__main__':unittest.main()
