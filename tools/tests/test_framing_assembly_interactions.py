import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from framing_assembly_interactions import find_interactions,jamb_clearance


def zone(owner, run, start, end):
    return {'assembly': owner, 'run': run, 'interval': [start, end], 'source': 'synthetic fixture'}


class Interactions(unittest.TestCase):
    def test_jamb_screen_is_translation_reflection_and_scale_invariant(self):
        left=jamb_clearance([16,36],0,24,1.5,3.5,1,1)
        shifted=jamb_clearance([116,136],100,24,1.5,3.5,1,1)
        right=jamb_clearance([-36,-16],0,24,1.5,3.5,1,1)
        scaled=jamb_clearance([32,72],0,48,1.5,3.5,1,1)
        for item in (shifted,right,scaled):
            self.assertEqual(item['framing_face_clearance_inches'],left['framing_face_clearance_inches'])
            self.assertEqual(item['screen'],left['screen'])
        self.assertEqual(left['opening_side'],'start');self.assertEqual(right['opening_side'],'end')
        self.assertFalse(left['purchase_order_released']);self.assertEqual(left['quantity_deductions'],[])

    def test_jamb_screen_rejects_topology_and_unit_input_errors(self):
        for args in (([0,20],10,24,1.5,3.5,1,1),([0,20],30,0,1.5,3.5,1,1),
                     ([0,float('nan')],30,24,1.5,3.5,1,1),([0,20],30,24,1.5,3.5,True,1),
                     ([0,20],30,24,1.5,3.5,0,0)):
            with self.subTest(args=args),self.assertRaises(ValueError):jamb_clearance(*args)

    def test_touching_and_overlapping_reserves_group_transitively(self):
        result = find_interactions([zone('jamb', 'wall', 0, 3), zone('corner', 'wall', 2, 5),
                                    zone('backing', 'wall', 5, 7), zone('other', 'wall', 8, 9)])
        self.assertEqual(len(result['interactions']), 2)
        self.assertIn({'assemblies': ['backing', 'corner', 'jamb'], 'requires_combined_layout': True}, result['groups'])
        self.assertEqual(result['quantity_deductions'], [])
        self.assertFalse(result['purchase_order_released'])

    def test_same_coordinates_on_unconnected_walls_do_not_collide(self):
        result = find_interactions([zone('a', 'wall1', 0, 5), zone('b', 'wall2', 0, 5)])
        self.assertEqual(result['interactions'], [])
        self.assertTrue(all(not g['requires_combined_layout'] for g in result['groups']))

    def test_shared_assembly_links_runs_without_counting_it_twice(self):
        zones = [zone('corner', 'wall1', 0, 3), zone('corner', 'wall2', 0, 3),
                 zone('door', 'wall1', 2, 8), zone('pocket', 'wall2', 2, 8)]
        result = find_interactions(zones + zones[:1])
        self.assertEqual(result['assembly_count'], 3)
        self.assertEqual(len(result['interactions']), 2)
        self.assertEqual(result['groups'][0]['assemblies'], ['corner', 'door', 'pocket'])

    def test_same_owner_overlapping_zones_are_not_a_conflict(self):
        result = find_interactions([zone('pocket', 'wall', 0, 5), zone('pocket', 'wall', 4, 8)])
        self.assertEqual(result['interactions'], [])
        self.assertEqual(result['assembly_count'], 1)

    def test_invalid_geometry_and_missing_source_are_rejected(self):
        for interval in ([5, 1], [0, float('nan')], [0, float('inf')], [True, 2]):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                find_interactions([dict(zone('a', 'w', 0, 1), interval=interval)])
        with self.assertRaises(ValueError):
            find_interactions([dict(zone('a', 'w', 0, 1), source='')])


if __name__ == '__main__':
    unittest.main()
