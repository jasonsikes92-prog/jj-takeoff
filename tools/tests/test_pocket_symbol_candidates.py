"""Pocket geometry, contradictory review withholding and non-pocket rejection."""
import copy
import math
import unittest
from door_symbol_candidates import recognize
from opening_schedule import withhold_symbol_conflicts
import test_door_symbol_candidates as hinged


def fixture(angle=0,reflection=1,scale=12,side=0):
    def point(p):
        x=(p[0] if side==0 else 32-p[0])*scale/12;y=p[1]*reflection*scale/12
        return [100+x*math.cos(angle)-y*math.sin(angle),200+x*math.sin(angle)+y*math.cos(angle)]
    cavity=[[-32,-1], [0,-1], [0,1], [-32,1]]
    leaf=[[-16,-.625],[16,-.625],[16,.625],[-16,.625]]
    segments=[(cavity[0],cavity[1]),(cavity[2],cavity[3]),(cavity[3],cavity[0])]
    segments.extend(zip(leaf,leaf[1:]+leaf[:1]))
    drawings=[{'type':'s','items':[('l',point(a),point(b))]} for a,b in segments]
    opening={'opening_id':'pocket-1','page':1,'tag':'2868','points':[point([0,0]),point([32,0])],
        'points_per_foot':scale,'source_sha256':'gap-source','review_status':'role_unreviewed',
        'printed_nominal_size':{'width_inches':32,'height_inches':80,'type_code':None}}
    return opening,drawings


class PocketSymbols(unittest.TestCase):
    def test_rotated_reflected_scaled_pocket_is_a_candidate_only(self):
        for angle in (0,.7,math.pi,4.8):
            for reflection in (-1,1):
                for scale in (6,18,36):
                    for side in (0,1):
                        opening,drawings=fixture(angle,reflection,scale,side)
                        r=recognize([opening],{1:drawings},'plan')
                        self.assertEqual(len(r['candidates']),1)
                        c=r['candidates'][0]
                        self.assertEqual(c['configuration_candidate'],'pocket')
                        self.assertEqual(c['status'],'candidate_requires_review');self.assertFalse(c['purchase_released'])

    def test_bare_leaf_or_cavity_or_parallel_walls_are_not_pockets(self):
        for indexes in ([0,1,2],[3,4,5,6],[0,1,3,4,5,6],[0,1,2,3,4,5],[0,1,3,5]):
            opening,drawings=fixture()
            self.assertEqual(recognize([opening],{1:[drawings[i] for i in indexes]},'plan')['candidates'],[])
        opening,drawings=fixture()
        for drawing in drawings:
            drawing['items']=[(kind,[a[0],a[1]+12],[b[0],b[1]+12]) for kind,a,b in drawing['items']]
        self.assertEqual(recognize([opening],{1:drawings},'plan')['candidates'],[])

    def test_duplicates_and_both_swing_and_pocket_are_not_extra_doors(self):
        opening,drawings=fixture()
        self.assertEqual(len(recognize([opening],{1:drawings+copy.deepcopy(drawings)},'plan')['candidates'][0]['matches']),1)
        _,swing=hinged.fixture()
        c=recognize([opening],{1:drawings+swing},'plan')['candidates'][0]
        self.assertEqual(c['status'],'ambiguous_symbols');self.assertIsNone(c['configuration_candidate'])

    def test_conflicting_review_is_visible_but_withheld_from_counts(self):
        opening,drawings=fixture()
        opening.update(review_status='current_source_review',role='interior_door',door_configuration='single_hinged',drawn_panel_count=1)
        candidate=recognize([opening],{1:drawings},'plan')
        self.assertEqual(candidate['candidates'][0]['status'],'conflicts_with_review')
        result=withhold_symbol_conflicts({'openings':[opening],'door_symbol_candidates':candidate,
            'unresolved_opening_ids':[],'reviewed_role_counts':{'interior_door':1},'enumerated_window_unit_count':4})
        self.assertEqual(opening['review_status'],'symbol_conflict_requires_review')
        self.assertIsNone(opening['role']);self.assertIsNone(result['enumerated_window_unit_count'])
        self.assertEqual(result['reviewed_role_counts']['interior_door'],0)
        self.assertEqual(opening['conflicting_source_review']['door_configuration'],'single_hinged')
        self.assertEqual(result['unresolved_opening_ids'],['pocket-1'])

    def test_distinct_overlapping_leaf_rectangles_remain_ambiguous(self):
        opening,drawings=fixture()
        extra=copy.deepcopy(drawings[3:])
        for drawing in extra:
            drawing['items']=[(kind,[a[0],200+(a[1]-200)*.88],[b[0],200+(b[1]-200)*.88]) for kind,a,b in drawing['items']]
        c=recognize([opening],{1:drawings+extra},'plan')['candidates'][0]
        self.assertGreater(len(c['matches']),1)
        self.assertEqual(c['status'],'ambiguous_symbols')

    def test_corrected_review_corroborates_and_stale_review_stays_stale(self):
        opening,drawings=fixture()
        opening.update(review_status='current_source_review',role='special_interior_door',door_configuration='pocket',drawn_panel_count=1)
        self.assertEqual(recognize([opening],{1:drawings},'plan')['candidates'][0]['status'],'corroborates_review')
        opening['review_status']='stale_source_review'
        self.assertEqual(recognize([opening],{1:drawings},'plan')['candidates'][0]['status'],'stale_review_requires_reconciliation')


if __name__=='__main__':unittest.main()
