import copy
import unittest
from test_wall_run_candidates import line,state
from wall_classification_review import source_digest
from wall_run_candidates import from_state
from wall_gap_obstructions import screen


def stroke(identity,a,b):
    return {**line(identity,a,b,ppf=12),'source_method':'native_parallel_wall_strokes_v2',
        'drawn_thickness_inches':3.5,'source_edges':[{'path':1,'item':0}]}


def review(s,decisions):
    return {'plan_sha256':s['plan_sha256'],'reviewer':'Test source reviewer','decisions':[
        {'measurement_id':identity,'decision':decision,'basis':'Drawing face interpretation',
         'source_sha256':source_digest(s['measurements'][identity])} for identity,decision in decisions]}


class WallClassification(unittest.TestCase):
    def test_filled_objects_can_be_excluded_and_stale_review_is_withheld(self):
        s=state(line('fill',[0,0],[100,0],ppf=12))
        r=review(s,[('fill','not_wall_faces')])
        result=from_state(s,r)
        self.assertEqual(result['run_candidates'],[])
        self.assertEqual(result['excluded_measurements'][0]['measurement_id'],'fill')
        changed=copy.deepcopy(s);changed['measurements']['fill']['points'][1][0]=110
        result=from_state(changed,r)
        self.assertEqual(result['run_candidates'],[])
        self.assertIn('stale',result['unresolved_measurements'][0]['reason'])

    def test_filled_wall_review_preserves_candidate_runs_without_certifying(self):
        s=state(line('fill',[0,0],[100,0],ppf=12))
        r=review(s,[('fill','wall_faces')])
        result=from_state(s,r)
        self.assertEqual(result['run_candidates'][0]['source_measurement_ids'],['fill'])
        self.assertFalse(result['certified'])

    def setUp(self):
        self.s=state(stroke('a',[0,100],[100,100]),stroke('b',[200,100],[250,100]),
            stroke('cross',[130,80],[130,120]))
        self.review=review(self.s,[('a','wall_faces'),('b','wall_faces'),('cross','uncertain')])

    def test_reviewed_faces_enter_runs_but_unknowns_can_obstruct_gaps(self):
        runs=from_state(self.s,self.review)
        self.assertEqual(len(runs['run_candidates']),1)
        self.assertEqual([m['measurement_id'] for m in runs['unresolved_measurements']],['cross'])
        self.assertEqual(next(iter(screen(runs,self.s)['obstructions_by_gap'].values()))[0]['measurement_id'],'cross')
        self.assertIsNone(runs['purchase_quantity']);self.assertFalse(runs['certified'])

    def test_fresh_nonwall_exclusion_is_removed_when_geometry_changes(self):
        r=review(self.s,[('a','wall_faces'),('b','wall_faces'),('cross','not_wall_faces')])
        runs=from_state(self.s,r)
        self.assertEqual(next(iter(screen(runs,self.s)['obstructions_by_gap'].values())),[])
        changed=copy.deepcopy(self.s);changed['measurements']['cross']['points'][0][0]+=1
        after=from_state(changed,r)
        self.assertEqual(after['excluded_measurements'],[])
        self.assertIn('stale',after['unresolved_measurements'][0]['reason'])

    def test_geometry_scale_and_evidence_changes_withhold_only_affected_wall(self):
        for field,value in [('points',[[0,100],[90,100]]),('points_per_foot',24),
                ('source_edges',[{'path':99,'item':0}]),('drawn_thickness_inches',5.5)]:
            changed=copy.deepcopy(self.s);changed['measurements']['a'][field]=value
            result=from_state(changed,self.review)
            self.assertEqual(result['run_candidates'][0]['source_measurement_ids'],['b'])
            self.assertIn('stale',next(m for m in result['unresolved_measurements'] if m['measurement_id']=='a')['reason'])
        restored=from_state(self.s,self.review)
        self.assertEqual(restored['run_candidates'][0]['source_measurement_ids'],['a','b'])

    def test_plan_identity_duplicate_unknown_and_missing_basis_rejected(self):
        for mutation in ('plan','duplicate','unknown','basis','decision','reviewer'):
            r=copy.deepcopy(self.review)
            if mutation=='plan':r['plan_sha256']='other'
            elif mutation=='duplicate':r['decisions'].append(r['decisions'][0])
            elif mutation=='unknown':r['decisions'][0]['measurement_id']='missing'
            elif mutation=='basis':r['decisions'][0]['basis']=' '
            elif mutation=='decision':r['decisions'][0]['decision']='approved'
            else:r['reviewer']=' '
            with self.assertRaises(ValueError):from_state(self.s,r)

    def test_cosmetic_edit_preserves_review_and_classification_change_has_own_digest(self):
        before=from_state(self.s,self.review)
        changed=copy.deepcopy(self.s);changed['measurements']['a'].update(label='Renamed',color='#ffffff')
        self.assertEqual(before,from_state(changed,self.review))
        r=copy.deepcopy(self.review);r['decisions'][0]['decision']='uncertain'
        after=from_state(self.s,r)
        self.assertEqual(before['measurement_inputs_sha256'],after['measurement_inputs_sha256'])
        self.assertNotEqual(before['classification_review_sha256'],after['classification_review_sha256'])
        self.assertEqual(after['run_candidates'][0]['source_measurement_ids'],['b'])

    def test_short_outline_needs_explicit_axis_and_edit_invalidates_it(self):
        s=state({**stroke('stub',[0,0],[3.5,0]),'kind':'area',
            'points':[[0,0],[3.5,0],[3.5,3.5],[0,3.5]]})
        r=review(s,[('stub','wall_faces')])
        self.assertEqual(from_state(s,r)['run_candidates'],[])
        r['decisions'][0]['axis']='horizontal'
        result=from_state(s,r)
        self.assertEqual(result['run_candidates'][0]['axis'],'horizontal')
        self.assertEqual(result['run_candidates'][0]['visible_union_lf'],3.5/12)
        self.assertEqual(s['measurements']['stub']['kind'],'area')
        changed=copy.deepcopy(s);changed['measurements']['stub']['points'][1][0]=4
        self.assertEqual(from_state(changed,r)['run_candidates'],[])
        r['decisions'][0]['axis']='diagonal'
        with self.assertRaises(ValueError):from_state(s,r)


if __name__=='__main__':unittest.main()
