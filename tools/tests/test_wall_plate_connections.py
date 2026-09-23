import copy
import unittest
from wall_plate_connections import calculate
from wall_run_candidates import from_state
from wall_gap_labels import match_labels
from wall_gap_obstructions import screen
from test_wall_gap_obstructions import wall
from test_wall_run_candidates import state


class PlateConnections(unittest.TestCase):
    def setUp(self):
        self.state=state(wall('left',[10,100],[100,100]),wall('right',[103.5,100],[150,100]),
            wall('branch',[101.75,101.75],[101.75,130]))
        self.counts={'top':2,'bottom':1}

    def sources(self):
        runs=from_state(self.state)
        gaps=match_labels(runs,[],screen(runs,self.state))
        return runs,gaps

    def calculate(self):
        return calculate(self.state,*self.sources(),{'openings':[]},self.counts)

    def test_matching_host_gap_is_counted_once_in_either_orientation(self):
        for transpose in (False,True):
            if transpose:
                for m in self.state['measurements'].values():m['points']=[p[::-1] for p in m['points']]
            r=self.calculate()
            self.assertEqual(len(r['connections']),1)
            self.assertAlmostEqual(r['connection_lf'],3.5/12)
            self.assertAlmostEqual(r['top_plate_reference_lf'],7/12)
            self.assertAlmostEqual(r['bottom_plate_reference_lf'],3.5/12)
            self.assertFalse(r['certified']);self.assertIsNone(r['purchase_quantity'])

    def test_staggered_branch_contacts_do_not_duplicate_host_gap(self):
        self.state=state(wall('left',[10,100],[100,100]),wall('right',[106.5,100],[150,100]),
            wall('upper',[104.75,70],[104.75,98.25]),wall('lower',[101.75,101.75],[101.75,130]))
        result=self.calculate()
        self.assertEqual(len(result['connections']),1)
        self.assertEqual(len(result['connections'][0]['source_evidence']),2)
        self.assertAlmostEqual(result['connection_lf'],6.5/12)

    def test_crossing_host_claims_withhold_both_instead_of_double_counting(self):
        self.state['measurements']['upper']=wall('upper',[101.75,70],[101.75,98.25])
        result=self.calculate()
        self.assertEqual(len(result['connections']),0)
        self.assertEqual(len(result['pending_gaps']),2)
        self.assertTrue(all('single plate owner' in p['reason'] for p in result['pending_gaps']))
        self.assertIsNone(result['connection_lf'])

    def test_edited_branch_and_mismatched_faces_do_not_fill_a_gap(self):
        original=copy.deepcopy(self.state)
        for name,changes in (('branch',{'points':[[101.75,103],[101.75,130]]}),
                ('branch',{'page':2}),('branch',{'points_per_foot':24}),('right',{'drawn_thickness_inches':5.5})):
            self.state=copy.deepcopy(original);self.state['measurements'][name].update(changes)
            self.assertEqual(self.calculate()['connections'],[],changes)
        self.state=original;self.assertEqual(len(self.calculate()['connections']),1)

    def test_separate_walls_and_previously_assigned_opening_stay_out_of_connections(self):
        runs,gaps=self.sources();gap=gaps['gaps'][0]
        gap['status']='separate_wall_runs'
        result=calculate(self.state,runs,gaps,{'openings':[]},self.counts)
        self.assertEqual(result['connections'],[]);self.assertEqual(result['separate_wall_gap_ids'],[gap['id']])
        runs,gaps=self.sources()
        result=calculate(self.state,runs,gaps,{'openings':[{'gap_id':gaps['gaps'][0]['id']}]},self.counts)
        self.assertEqual(result['connections'],[]);self.assertEqual(result['pending_gaps'],[])

    def test_native_continuity_requires_evidence_and_same_revision(self):
        runs,gaps=self.sources();gap=gaps['gaps'][0];gap['status']='continuous_wall_body_candidate'
        self.assertEqual(calculate(self.state,runs,gaps,{'openings':[]},self.counts)['connections'],[])
        gap['continuity_source']={'continuous_face_edges':['verified-native-face'],'native_wall_body_rectangles':['verified-body']}
        self.assertEqual(len(calculate(self.state,runs,gaps,{'openings':[]},self.counts)['connections']),1)
        gaps['measurement_version']+=1
        with self.assertRaises(ValueError):calculate(self.state,runs,gaps,{'openings':[]},self.counts)

    def test_unknown_course_counts_are_not_zero(self):
        self.counts['top']=None
        self.assertIsNone(self.calculate()['top_plate_reference_lf'])
        self.counts['top']=0
        self.assertEqual(self.calculate()['top_plate_reference_lf'],0)

    def test_duplicate_gap_cannot_add_same_connection_twice(self):
        runs,gaps=self.sources();gaps['gaps']*=2
        with self.assertRaises(ValueError):calculate(self.state,runs,gaps,{'openings':[]},self.counts)
