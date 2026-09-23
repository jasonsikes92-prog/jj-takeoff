import copy
import unittest
from floor_trim_reference import floating_floor_wall_runs


def sample():
    room=lambda name,n:{'room_id':name,'finish_perimeter_lf':n+5,'door_gap_lf':3,
        'fixed_footprint_lf':2,'remaining_wall_run_lf':n,'segments':[{'length_lf':n,'points':[[0,0],[n,0]]}]}
    return {'plan_sha256':'plan','measurement_version':3,
        'floor_finish_review':{'plan_sha256':'plan','measurement_version':3,
            'remaining_measurement_ids':['wood'],'measurement_ids':['carpet']},
        'baseboard_review':{'room_measurement_version':3,'obstruction_measurement_version':{'cabinets':2},
            'rooms':[room('wood',30),room('carpet',40),room('tile',20)],
            'source_file':'source.json','source_sha256':'hash','dependencies':[{'job':'cabinets','measurement_version':2}]}}


class FloorTrimReferenceTests(unittest.TestCase):
    def test_only_selected_finish_and_no_order_quantity(self):
        draft=sample();before=copy.deepcopy(draft);result=floating_floor_wall_runs(draft)
        self.assertEqual(result['quantity'],30)
        self.assertEqual(result['measurement_ids'],['wood'])
        self.assertIsNone(result['final_installed_quantity']);self.assertIsNone(result['purchase_quantity'])
        self.assertFalse(result['certified']);self.assertFalse(result['order_released'])
        result['rooms'][0]['segments'][0]['length_lf']=999
        self.assertEqual(draft,before)

    def test_excluded_room_changes_do_not_affect_trim(self):
        draft=sample();draft['baseboard_review']['rooms'][1]['remaining_wall_run_lf']=999
        self.assertEqual(floating_floor_wall_runs(draft)['quantity'],30)

    def test_finish_changes_reselect_rooms(self):
        draft=sample();draft['floor_finish_review'].update(remaining_measurement_ids=['carpet'],measurement_ids=['wood'])
        self.assertEqual(floating_floor_wall_runs(draft)['quantity'],40)

    def test_stale_duplicate_missing_and_conflicting_rooms_rejected(self):
        for action in (lambda d:d.update(measurement_version=4),
                       lambda d:d['floor_finish_review'].update(plan_sha256='other'),
                       lambda d:d['floor_finish_review'].update(remaining_measurement_ids=['wood','wood']),
                       lambda d:d['floor_finish_review'].update(remaining_measurement_ids=['missing']),
                       lambda d:d['floor_finish_review'].update(remaining_measurement_ids=['carpet'])):
            draft=sample();action(draft)
            with self.assertRaises(ValueError):floating_floor_wall_runs(draft)

    def test_bad_segment_or_deduction_rejected(self):
        for value in (29,-1,float('nan')):
            draft=sample();draft['baseboard_review']['rooms'][0]['segments'][0]['length_lf']=value
            with self.assertRaises(ValueError):floating_floor_wall_runs(draft)
        draft=sample();draft['baseboard_review']['rooms'][0]['door_gap_lf']=4
        with self.assertRaises(ValueError):floating_floor_wall_runs(draft)


if __name__=='__main__':unittest.main()
