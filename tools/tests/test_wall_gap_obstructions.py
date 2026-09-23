import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_gap_obstructions import screen,footprint
from wall_gap_labels import match_labels
from wall_run_candidates import from_state
from test_wall_run_candidates import line,state


def wall(identity,a,b):
    return {**line(identity,a,b,ppf=12),'drawn_thickness_inches':3.5}


class GapObstructions(unittest.TestCase):
    def setUp(self):
        self.left=wall('left',[10,100],[100,100]);self.right=wall('right',[200,100],[250,100])
        self.runs=from_state(state(self.left,self.right))

    def test_parallel_and_crossing_piece_footprints_obstruct_gap(self):
        for obstruction in (wall('parallel',[120,101],[150,101]),wall('crossing',[130,80],[130,120])):
            result=screen(self.runs,state(self.left,self.right,obstruction))
            hits=next(iter(result['obstructions_by_gap'].values()))
            self.assertEqual(len(hits),1)
            self.assertEqual(hits[0]['measurement_id'],obstruction['id'])
            self.assertGreater(hits[0]['overlap_lf'],0)

    def test_endpoint_contact_and_other_page_do_not_block(self):
        touching=wall('touch',[90,101],[100,101])
        elsewhere={**wall('other',[120,101],[150,101]),'page':2}
        result=screen(self.runs,state(self.left,self.right,touching,elsewhere))
        self.assertEqual(next(iter(result['obstructions_by_gap'].values())),[])

    def test_current_points_override_source_bounds_and_missing_thickness_stays_unassessed(self):
        piece={**wall('block',[120,101],[150,101]),'source_bounds_pt':[500,500,600,600]}
        result=screen(self.runs,state(self.left,self.right,piece))
        self.assertEqual(next(iter(result['obstructions_by_gap'].values()))[0]['current_footprint_pt'],[120,99.25,150,102.75])
        piece['points']=[[120,110],[150,110]]
        self.assertEqual(next(iter(screen(self.runs,state(piece))['obstructions_by_gap'].values())),[])
        piece.pop('drawn_thickness_inches')
        self.assertEqual(screen(self.runs,state(piece))['unassessed_measurement_ids'],['block'])

    def test_source_rectangle_retains_both_actual_dimensions(self):
        area={**self.left,'kind':'area','points':[[120,99],[123,99],[123,103],[120,103]]}
        self.assertEqual(footprint(area),[120,99,123,103])
        area['points'][1][0]+=1
        self.assertIsNone(footprint(area))

    def test_obstructed_long_gap_does_not_steal_tag_from_clear_gap(self):
        runs=copy.deepcopy(self.runs)
        clear={**runs['run_candidates'][0],'id':'clear','gaps':[{'from_pt':150,'to_pt':180,'length_lf':2.5}]}
        runs['run_candidates'].append(clear)
        evidence={'method':'fixture','obstructions_by_gap':{
            runs['run_candidates'][0]['id']+':gap-1':[{'measurement_id':'drawn-wall'}]},'unassessed_measurement_ids':[]}
        label={'id':'door','page':1,'axis':'horizontal','text':'3068','bbox_pt':[160,99,170,101]}
        result=match_labels(runs,[label],evidence)
        self.assertEqual([g['status'] for g in result['gaps']],['drawn_piece_obstructs_gap','unique_tag_location_candidate'])
        self.assertEqual(result['shared_label_ids'],[])
        self.assertEqual(result['gaps'][0]['candidate_label_ids'],['door'])
        self.assertFalse(result['certified'])

    def test_perpendicular_end_contact_is_a_junction_not_an_opening(self):
        items=[wall('left',[10,100],[100,100]),wall('right',[103.5,100],[150,100]),
            wall('branch',[101.75,101.75],[101.75,130])]
        for vertical in (False,True):
            current=copy.deepcopy(items)
            if vertical:
                for m in current:m['points']=[p[::-1] for p in m['points']]
            s=state(*current);runs=from_state(s);evidence=screen(runs,s)
            result=match_labels(runs,[],evidence)
            self.assertEqual(result['gaps'][0]['status'],'wall_junction_candidate')
            self.assertEqual(result['gaps'][0]['junction_contacts'][0]['measurement_id'],'branch')
            self.assertEqual(result['gaps'][0]['obstructions'],[])
            self.assertEqual(result['gaps'][0]['drawn_gap_lf'],3.5/12)
            self.assertIsNone(runs['whole_wall_quantity'])

    def test_junction_contact_requires_matching_faces_page_scale_and_current_run(self):
        base=state(wall('left',[10,100],[100,100]),wall('right',[103.5,100],[150,100]),
            wall('branch',[101.75,101.75],[101.75,130]))
        for changes in ({'points':[[101.75,103],[101.75,130]]},
                        {'points':[[103,101.75],[103,130]]},
                        {'page':2},{'points_per_foot':24},
                        {'source_method':'native_parallel_wall_strokes_v3'},
                        {'drawn_thickness_inches':5.5}):
            s=copy.deepcopy(base);s['measurements']['branch'].update(changes)
            evidence=screen(from_state(s),s)
            self.assertFalse(any(evidence['junctions_by_gap'].values()),changes)

    def test_tag_at_junction_is_explicit_conflict_not_unique_opening(self):
        s=state(wall('left',[10,100],[100,100]),wall('right',[103.5,100],[150,100]),
            wall('branch',[101.75,101.75],[101.75,130]))
        runs=from_state(s)
        label={'id':'tag','page':1,'axis':'horizontal','text':'3068','bbox_pt':[100.5,99,102.5,101]}
        result=match_labels(runs,[label],screen(runs,s))
        self.assertEqual(result['gaps'][0]['status'],'junction_tag_conflict')
        self.assertEqual(result['unmatched_label_ids'],['tag'])
        self.assertEqual(result['gaps'][0]['candidate_label_ids'],['tag'])

    def staggered(self):
        return state(wall('left',[10,100],[100,100]),wall('right',[106.5,100],[150,100]),
            wall('upper',[104.75,70],[104.75,98.25]),
            wall('lower',[101.75,101.75],[101.75,130]))

    def test_staggered_contacts_cover_one_gap_in_both_orientations(self):
        for vertical in (False,True):
            s=self.staggered()
            if vertical:
                for m in s['measurements'].values():m['points']=[p[::-1] for p in m['points']]
            runs=from_state(s);result=match_labels(runs,[],screen(runs,s))
            gap=next(g for g in result['gaps'] if g['from_pt']==100)
            self.assertEqual(gap['status'],'wall_junction_candidate')
            self.assertEqual({c['measurement_id'] for c in gap['junction_contacts']},{'upper','lower'})
            self.assertEqual(sorted(c['covered_interval_pt'] for c in gap['junction_contacts']),[[100,103.5],[103,106.5]])
            self.assertIsNone(runs['whole_wall_quantity'])

    def test_staggered_partial_or_disconnected_contacts_remain_unresolved(self):
        for changes in ({'page':2},{'points_per_foot':24},
                        {'source_method':'native_parallel_wall_strokes_v3'},
                        {'points':[[104.75,70],[104.75,97]]},
                        {'drawn_thickness_inches':2}):
            s=self.staggered();s['measurements']['upper'].update(changes)
            self.assertFalse(any(screen(from_state(s),s)['junctions_by_gap'].values()),changes)

    def test_staggered_edit_and_restore_recalculates_contact(self):
        s=self.staggered();before=screen(from_state(s),s)
        original=copy.deepcopy(s['measurements']['upper']['points'])
        s['measurements']['upper']['points'][1][1]-=2
        self.assertFalse(any(screen(from_state(s),s)['junctions_by_gap'].values()))
        s['measurements']['upper']['points']=original
        self.assertEqual(screen(from_state(s),s),before)

    def test_different_host_thicknesses_do_not_imply_one_junction(self):
        s=state(wall('left',[10,100],[100,100]),
            {**wall('right',[103.5,100],[150,100]),'drawn_thickness_inches':5.5},
            wall('branch',[101.75,101.75],[101.75,130]))
        self.assertFalse(any(screen(from_state(s),s)['junctions_by_gap'].values()))


if __name__=='__main__':unittest.main()
