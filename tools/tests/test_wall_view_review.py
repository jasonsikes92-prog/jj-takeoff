import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_view_review import read_wall_view_review


class WallViewReview(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.job=Path(self.temp.name)
        with fitz.open() as doc:
            page=doc.new_page(width=600,height=600)
            page.draw_line((20,20),(140,20),width=1)
            page.draw_line((30,30),(30,150),width=1)
            doc.save(self.job/'plan.pdf')
        self.review={'plan_sha256':hashlib.sha256((self.job/'plan.pdf').read_bytes()).hexdigest(),
            'page':1,'reviewer':'Synthetic source review','basis':'Two wall faces; exclude adjacent detail',
            'view_bounds_pt':[10,10,400,400],'wall_face_examples':[
                {'path':0,'item':0,'points_pt':[[20,20],[140,20]]},
                {'path':1,'item':0,'points_pt':[[30,30],[30,150]]}]}

    def save(self,review):
        (self.job/'floor_wall_view_review.json').write_text(json.dumps(review))

    def test_missing_optional_review_and_valid_source_styles(self):
        self.assertIsNone(read_wall_view_review(self.job,1))
        self.save(self.review);r=read_wall_view_review(self.job,1)
        self.assertEqual(r['allowed_styles'],[{'color':[0,0,0],'width_pt':1}])
        self.assertFalse(r['scope_certified'])

    def test_wrong_plan_page_region_and_missing_reviewer_rejected(self):
        for field,value in [('plan_sha256','wrong'),('page',2),('view_bounds_pt',[0,0,700,500]),
                            ('view_bounds_pt',[0,0,float('nan'),400]),('reviewer','')]:
            r=copy.deepcopy(self.review);r[field]=value;self.save(r)
            with self.assertRaises(ValueError):read_wall_view_review(self.job,1)

    def test_changed_duplicate_or_out_of_region_examples_rejected(self):
        for mode in ['changed','duplicate','outside','invalid_index']:
            r=copy.deepcopy(self.review)
            if mode=='changed':r['wall_face_examples'][0]['points_pt'][1][0]+=1
            elif mode=='duplicate':r['wall_face_examples'][1]=r['wall_face_examples'][0]
            elif mode=='outside':r['view_bounds_pt']=[25,25,400,400]
            else:r['wall_face_examples'][0]['path']=999
            self.save(r)
            with self.assertRaises(ValueError):read_wall_view_review(self.job,1)

    def test_changed_review_changes_hash(self):
        self.save(self.review);before=read_wall_view_review(self.job,1)
        self.review['view_bounds_pt'][2]=410;self.save(self.review)
        self.assertNotEqual(before['review_sha256'],read_wall_view_review(self.job,1)['review_sha256'])


if __name__=='__main__':unittest.main()
