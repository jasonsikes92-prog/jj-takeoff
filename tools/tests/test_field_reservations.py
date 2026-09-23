import copy
import unittest
from tools.field_reservations import resolve, junction_points
from tools.field_stud_layout import layout


class FieldReservations(unittest.TestCase):
    def setUp(self):
        self.runs = [{'id':'W','orientation':'horizontal','coordinate_pt':20,
                      'start_pt':0,'end_pt':160,'source':'wall'}]
        self.bindings = [dict(id=name,assembly=name,run='W',source='reviewed fixture',
                            kind='run_end',endpoint=end,allowance_inches=4)
                         for name,end in [('start','start_pt'),('end','end_pt')]]
        self.bindings += [dict(id='door',assembly='door',run='W',source='reviewed fixture',
            kind='opening',opening='O',normal_offset_inches=1.75,allowance_inches=3.75)]
        self.openings = {'O':[[50,21.75],[70,21.75]]}
        self.branches = {}

    def zones(self):
        return resolve(self.runs,self.bindings,self.openings,self.branches,points_per_foot=12)

    def count(self):
        return layout(self.runs,self.zones(),points_per_foot=12,spacing_inches=16,first_center_inches=.75)['field_count']

    def test_opening_edit_recalculates_reserved_stations(self):
        before = self.count()
        self.openings['O'][1][0] += 16
        self.assertEqual(self.count(),before-1)

    def test_end_reservations_follow_extended_wall(self):
        self.runs[0]['end_pt'] += 16
        self.assertEqual(self.zones()[1]['interval'],[172,180])

    def test_detached_or_outside_opening_refused(self):
        for points in [[[50,22],[70,22]],[[-5,21.75],[70,21.75]],[[50,21.75],[50,21.75]]]:
            self.openings['O'] = points
            with self.assertRaises(ValueError):self.zones()

    def add_branch(self):
        self.branches['I'] = {'id':'I','orientation':'vertical','coordinate_pt':100,
                              'start_pt':21.75,'end_pt':80,'source':'branch'}
        self.bindings.append(dict(id='T',assembly='T',run='W',source='reviewed fixture',
            kind='intersection',branch='I',branch_endpoint='start_pt',signed_gap_inches=1.75,allowance_inches=4.25))

    def test_intersection_follows_branch_position(self):
        self.add_branch();self.assertEqual(self.zones()[-1]['interval'],[95.75,104.25])
        self.branches['I']['coordinate_pt'] += 16
        self.assertEqual(self.zones()[-1]['interval'],[111.75,120.25])

    def test_disconnected_parallel_or_outside_branch_refused(self):
        self.add_branch();original = copy.deepcopy(self.branches['I'])
        for change in [{'start_pt':40},{'orientation':'horizontal'},{'coordinate_pt':200}]:
            self.branches['I'] = {**original,**change}
            with self.assertRaises(ValueError):self.zones()

    def test_duplicate_and_invalid_allowance_refused(self):
        self.bindings.append(self.bindings[0])
        with self.assertRaises(ValueError):self.zones()
        self.bindings.pop()
        for amount in [-1,True,float('nan')]:
            self.bindings[0]['allowance_inches'] = amount
            with self.assertRaises(ValueError):self.zones()


class JunctionAnchors(unittest.TestCase):
    def setUp(self):
        self.runs=[{'id':'H','orientation':'horizontal','coordinate_pt':20,'start_pt':0,'end_pt':100},
                   {'id':'V','orientation':'vertical','coordinate_pt':50,'start_pt':21.75,'end_pt':80}]
        self.definitions=[{'id':'J','x_run':'V','y_run':'H','x_offset_inches':0,'y_offset_inches':0,
            'attachments':[{'run':'H','endpoint':'through','normal_offset_inches':0},
                           {'run':'V','endpoint':'start_pt','normal_offset_inches':0,'signed_gap_inches':-1.75}]}]

    def calculate(self):return junction_points(self.runs,self.definitions,points_per_foot=12)

    def test_intersection_tracks_branch_move_on_host(self):
        self.assertEqual(self.calculate(),{'J':[50,20]})
        self.runs[1]['coordinate_pt']=66
        self.assertEqual(self.calculate(),{'J':[66,20]})

    def test_disconnected_end_and_outside_host_are_rejected(self):
        self.runs[1]['start_pt']=25
        with self.assertRaisesRegex(ValueError,'no longer meets'):self.calculate()
        self.runs[1]['start_pt']=21.75;self.runs[1]['coordinate_pt']=120
        with self.assertRaisesRegex(ValueError,'beyond'):self.calculate()

    def test_opposed_branch_keeps_reviewed_drawing_offset(self):
        self.runs.append({'id':'H2','orientation':'horizontal','coordinate_pt':20.5,'start_pt':51.75,'end_pt':100})
        self.definitions[0]['attachments'].append({'run':'H2','endpoint':'start_pt',
            'normal_offset_inches':-.5,'signed_gap_inches':-1.75})
        self.assertEqual(self.calculate(),{'J':[50,20]})
        self.runs[2]['coordinate_pt']+=1
        with self.assertRaisesRegex(ValueError,'no longer aligns'):self.calculate()

    def test_junction_reservation_tracks_live_point(self):
        bindings=[{'id':'zone','run':'H','kind':'junction','junction':'J','assembly':'J',
                   'allowance_inches':3.5,'source':'fixture'}]
        zones=resolve(self.runs,bindings,{}, {},points_per_foot=12,junctions=self.calculate())
        self.assertEqual(zones[0]['interval'],[46.5,53.5])

    def test_duplicate_or_nonfinite_definition_rejected(self):
        self.definitions.append(self.definitions[0])
        with self.assertRaises(ValueError):self.calculate()
        self.definitions.pop();self.definitions[0]['x_offset_inches']=float('nan')
        with self.assertRaises(ValueError):self.calculate()
