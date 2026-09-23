import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_short_piece_directions import propose
from test_wall_run_candidates import line,state


def square(identity,x,y):
    return {**line(identity,[x,y],[x+3.5,y],ppf=12),'kind':'area',
        'points':[[x,y],[x+3.5,y],[x+3.5,y+3.5],[x,y+3.5]]}


def tag(identity,x,y,axis='horizontal'):
    return {'id':identity,'page':1,'axis':axis,'bbox_pt':[x-1,y-1,x+1,y+1],'text':'3068'}


class ShortPieceDirections(unittest.TestCase):
    def setUp(self):
        self.square=square('short',150,98.25)
        self.wall=line('long',[10,100],[100,100],ppf=12)
        self.tag=tag('door',125,100)

    def test_unique_direction_is_derived_without_changing_source_outline(self):
        source=state(self.square,self.wall);original=copy.deepcopy(source)
        review,projected=propose(source,[self.tag])
        self.assertEqual(review['pieces'][0]['axis'],'horizontal')
        self.assertEqual(projected['measurements']['short']['points'],[[150,100],[153.5,100]])
        self.assertEqual(source,original)
        self.assertFalse(review['certified'])

    def test_two_short_pieces_can_support_each_other_across_tagged_gap(self):
        review,_=propose(state(square('a',100,98.25),self.square),[self.tag])
        self.assertTrue(all(p['axis']=='horizontal' for p in review['pieces']))

    def test_missing_tag_multiple_tags_and_intervening_geometry_withhold_direction(self):
        for labels,extra in (([],[]),([self.tag,{**self.tag,'id':'other'}],[]),
                ([self.tag],[line('blocker',[120,100],[135,100],ppf=12)])):
            review,projected=propose(state(self.square,self.wall,*extra),labels)
            self.assertIsNone(review['pieces'][0]['axis'])
            self.assertEqual(projected['measurements']['short']['kind'],'area')

    def test_both_axis_evidence_does_not_choose_a_direction(self):
        vertical=line('vertical',[151.75,30],[151.75,50],ppf=12)
        review,_=propose(state(self.square,self.wall,vertical),[self.tag,tag('v',151.75,75,'vertical')])
        self.assertEqual(review['pieces'][0]['status'],'ambiguous_axes')
        self.assertIsNone(review['pieces'][0]['axis'])

    def test_changed_outline_and_changed_alignment_remove_prior_inference(self):
        altered=copy.deepcopy(self.square);altered['points'][1][0]+=1
        review,_=propose(state(altered,self.wall),[self.tag])
        self.assertEqual(review['pieces'][0]['status'],'edited_outline_outside_short_rectangle_scope')
        shifted=square('short',150,108.25)
        review,_=propose(state(shifted,self.wall),[self.tag])
        self.assertIsNone(review['pieces'][0]['axis'])

    def test_other_page_or_scale_and_ambiguous_peer_cannot_supply_direction(self):
        for change in ({'page':2},{'points_per_foot':24}):
            review,_=propose(state(self.square,{**self.wall,**change}),[self.tag])
            self.assertIsNone(review['pieces'][0]['axis'])
        peer=square('peer',100,98.25)
        vertical=line('vertical',[101.75,30],[101.75,50],ppf=12)
        review,_=propose(state(self.square,peer,vertical),[self.tag,tag('v',101.75,75,'vertical')])
        self.assertTrue(all(p['axis'] is None for p in review['pieces']))


if __name__=='__main__':unittest.main()
