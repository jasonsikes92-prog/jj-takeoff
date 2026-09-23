import copy
import unittest
import fitz
from wall_gap_continuity import detect,rectangle
from wall_run_candidates import from_state,WALL_METHOD


class WallContinuity(unittest.TestCase):
    def setUp(self):
        edge={'path':0,'item':0,'points_pt':[[0,-2],[100,-2]]}
        self.state={'plan_sha256':'plan','version':1,'measurements':{}}
        for identity,points in [('left',[[0,0],[40,0]]),('right',[[44,0],[100,0]])]:
            self.state['measurements'][identity]={'id':identity,'kind':'length','points':points,
                'page':1,'points_per_foot':12,'drawn_thickness_inches':4,'source_method':WALL_METHOD,
                'source_edges':[copy.deepcopy(edge)]}
        self.drawings={1:[{'items':[('l',fitz.Point(0,-2),fitz.Point(100,-2))],'dashes':'[] 0'},
            {'items':[('re',fitz.Rect(0,-2,100,2),1)],'fill':(1.,1.,1.),'fill_opacity':1}]}

    def run_detector(self,status='no_aligned_tag'):
        runs=from_state(self.state);run=runs['run_candidates'][0]
        return detect(self.state,runs,[{**run['gaps'][0],'id':'gap','run_id':run['id'],'status':status}],self.drawings)

    def test_shared_face_and_exact_wall_body_prove_the_interruption(self):
        result=self.run_detector()
        self.assertEqual(result['gap']['source_measurement_ids'],['left','right'])
        self.assertEqual(result['gap']['native_wall_body_rectangles'],[{'path':1,'bounds_pt':[0,-2,100,2]}])
        self.assertEqual(result['gap']['continuous_face_edges'][0]['path'],0)

    def test_blank_page_rectangle_or_face_alone_cannot_fill_a_gap(self):
        original=copy.deepcopy(self.drawings)
        self.drawings[1][1]['items']=[('re',fitz.Rect(-10,-10,110,10),1)]
        self.assertEqual(self.run_detector(),{})
        self.drawings=copy.deepcopy(original);self.drawings[1].pop()
        self.assertEqual(self.run_detector(),{})
        self.drawings=copy.deepcopy(original);self.state['measurements']['right']['source_edges']=[]
        self.assertEqual(self.run_detector(),{})

    def test_tagged_openings_junctions_and_reviewed_breaks_are_not_overridden(self):
        for status in ('unique_tag_location_candidate','separate_wall_runs','wall_junction_candidate','multiple_tags_require_review'):
            with self.subTest(status=status):self.assertEqual(self.run_detector(status),{})

    def test_changed_native_line_dashed_line_and_shifted_piece_are_rejected(self):
        original=copy.deepcopy(self.drawings)
        self.drawings[1][0]['items']=[('l',fitz.Point(10,-2),fitz.Point(100,-2))]
        self.assertEqual(self.run_detector(),{})
        self.drawings=copy.deepcopy(original);self.drawings[1][0]['dashes']='[4 2] 0'
        self.assertEqual(self.run_detector(),{})
        self.drawings=original
        self.state['measurements']['left']['points']=[[0,.1],[40,.1]]
        self.assertEqual(self.run_detector(),{})

    def test_body_must_cover_both_pieces_with_matching_cross_faces(self):
        for bounds in [(20,-2,80,2),(0,-2,100,3)]:
            self.drawings[1][1]['items']=[('re',fitz.Rect(*bounds),1)]
            with self.subTest(bounds=bounds):self.assertEqual(self.run_detector(),{})

    def test_vertical_wall_uses_the_same_geometric_rule(self):
        for m in self.state['measurements'].values():
            m['points']=[[y,x] for x,y in m['points']]
            m['source_edges'][0]['points_pt']=[[-2,0],[-2,100]]
        self.drawings[1][0]['items']=[('l',fitz.Point(-2,0),fitz.Point(-2,100))]
        self.drawings[1][1]['items']=[('re',fitz.Rect(-2,0,2,100),1)]
        self.assertIn('gap',self.run_detector())

    def test_four_line_wall_body_must_be_closed_rectangular_and_opaque(self):
        points=[fitz.Point(0,-2),fitz.Point(100,-2),fitz.Point(100,2),fitz.Point(0,2)]
        drawing={'fill':(1.,1.,1.),'items':[('l',a,b) for a,b in zip(points,points[1:]+points[:1])]}
        self.assertEqual(rectangle(drawing),[0,-2,100,2])
        drawing['fill_opacity']=.5;self.assertIsNone(rectangle(drawing))
        drawing.pop('fill_opacity');drawing['items'][-1]=('l',points[-1],fitz.Point(5,5))
        self.assertIsNone(rectangle(drawing))


if __name__=='__main__':unittest.main()
