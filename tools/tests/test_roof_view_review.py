import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import fitz
from roof_view_review import read_roof_view_review
from roof_face_candidates import candidates


class RoofViewReview(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.job=Path(tmp.name)
        with fitz.open() as doc:
            p=doc.new_page(width=400,height=400)
            p.draw_line((30,30),(200,30),color=(.2,.4,.1),width=2)
            p.draw_line((200,30),(200,200),color=(.2,.4,.1),width=2)
            p.draw_line((200,200),(30,200),color=(.2,.4,.1),width=2)
            p.draw_line((30,200),(30,30),color=(.2,.4,.1),width=2)
            p.draw_rect((40,40,190,190),color=(.6,.6,.6),width=.5)
            p.draw_line((40,210),(190,210),dashes='[3 2] 0')
            p.insert_text((80,100),'6 : 12',fontsize=10)
            doc.save(self.job/'plan.pdf')
        self.review={'plan_sha256':hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest(),
            'page':1,'reviewer':'Synthetic source inspection','basis':'Roof edges distinguish underlying room outline',
            'view_bounds_pt':[10,10,250,250],'roof_edge_examples':[
                {'path':0,'item':0,'points_pt':[[30,30],[200,30]]},
                {'path':1,'item':0,'points_pt':[[200,30],[200,200]]}]}

    def read(self,review):
        (self.job/'roof_view_review.json').write_text(json.dumps(review))
        return read_roof_view_review(self.job,1)

    def test_review_selects_source_styles_without_certifying_coverage(self):
        review=self.read(self.review)
        self.assertEqual(len(review['allowed_styles']),1)
        self.assertFalse(review['scope_certified'])
        with fitz.open(self.job/'plan.pdf') as doc:
            raw=candidates(doc[0],10,review['view_bounds_pt'])
            filtered=candidates(doc[0],10,review['view_bounds_pt'],review['allowed_styles'])
        self.assertEqual(len(raw['measurements']),2)
        self.assertEqual(len(filtered['measurements']),1)
        self.assertEqual(set(filtered['measurements'][0]['source_cad_paths']),{0,1,2,3})
        self.assertFalse(filtered['certified'])

    def test_changed_example_coordinates_are_rejected(self):
        review=copy.deepcopy(self.review);review['roof_edge_examples'][0]['points_pt'][0][0]+=1
        with self.assertRaises(ValueError):self.read(review)

    def test_missing_duplicate_or_invalid_examples_are_rejected(self):
        anchors=self.review['roof_edge_examples']
        for examples in (None,[],anchors[:1],[anchors[0],anchors[0]],[anchors[0],{'path':999,'item':0}],
                         [anchors[0],{'path':True,'item':0}]):
            with self.subTest(examples=examples),self.assertRaises(ValueError):
                self.read({**self.review,'roof_edge_examples':examples})

    def test_dashed_and_out_of_view_examples_are_rejected(self):
        review=copy.deepcopy(self.review)
        review['roof_edge_examples'][1]={'path':5,'item':0,'points_pt':[[40,210],[190,210]]}
        with self.assertRaises(ValueError):self.read(review)
        with self.assertRaises(ValueError):self.read({**self.review,'view_bounds_pt':[50,50,250,250]})

    def test_wrong_drawing_and_page_are_rejected(self):
        for change in ({'plan_sha256':'wrong'},{'page':2},{'reviewer':''}):
            with self.assertRaises(ValueError):self.read({**self.review,**change})

    def test_view_only_review_preserves_unfiltered_behavior(self):
        review={k:v for k,v in self.review.items() if k!='roof_edge_examples'}
        self.assertNotIn('allowed_styles',self.read(review))

    def test_empty_style_selection_cannot_silently_drop_every_face(self):
        with fitz.open(self.job/'plan.pdf') as doc:
            with self.assertRaises(ValueError):candidates(doc[0],10,[10,10,250,250],[])


if __name__=='__main__':unittest.main()
