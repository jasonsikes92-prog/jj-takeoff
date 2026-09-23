import copy
import hashlib
import json
import unittest
from window_head_caps import head_cap_takeoff
import test_window_snapshot_bridge as fixtures


class HeadCapTests(unittest.TestCase):
    def setUp(self):
        f = self.fixture = fixtures.WindowSnapshotTests()
        f.setUp(); self.addCleanup(f.doCleanups)
        members = f.saved['material_schedule']['assemblies']
        for a, w, line in zip(members, (108, 72), (100, 200)):
            a.update(rough_opening_width_in=w, supplier_line=line, specification_page=1)
        self.frames = [{'opening_id': a['opening_id'], 'frame_width_in': a['rough_opening_width_in']-.5,
                        'rough_opening_width_in': a['rough_opening_width_in'],
                        'supplier_line': a['supplier_line'], 'specification_page': 1} for a in members]
        self.products = [{'part_number': 'short', 'length_in': 72, 'profile': 'same'},
                         {'part_number': 'long', 'length_in': 120, 'profile': 'same'}]
        self.basis = {'plan_sha256': 'plan', 'status': 'estimating_allowance',
                      'specification_sha256': f.saved['material_schedule']['specification_sha256'],
                      'frames': self.frames, 'products': self.products, 'kerf_in': .125,
                      'assumptions': ['Full frame width'], 'remaining': ['Confirm profile and price'],
                      'documents': [{'file': 'spec.pdf', 'sha256': f.saved['material_schedule']['specification_sha256']}]}
        self.save()

    def save(self):
        p = self.fixture.root/'caps.json'; p.write_text(json.dumps(self.basis))
        self.fixture.mapping['head_caps'] = {'file': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    def run_takeoff(self):
        return head_cap_takeoff(self.fixture.saved['material_schedule']['assemblies'], self.frames, self.products, .125)

    def test_continuous_caps_count_groups_not_panes(self):
        r = self.run_takeoff()
        self.assertEqual(r['new_head_locations'], 2)
        self.assertEqual([p['quantity'] for p in r['purchases']], [1, 1])
        self.assertEqual(r['net_new_length_in'], 179)
        self.assertIsNone(r['complete_cost']); self.assertFalse(r['order_released'])

    def test_included_cap_credited_once_and_changed_count_recalculates(self):
        self.frames[1].update(included_quantity=1, included_part_number='short', inclusion_reference='spec page 1')
        self.assertEqual([p['quantity'] for p in self.run_takeoff()['purchases']], [0, 1])
        self.fixture.saved['material_schedule']['assemblies'][1]['assembly_quantity'] = 2
        self.assertEqual([p['quantity'] for p in self.run_takeoff()['purchases']], [1, 1])
        self.frames[1]['included_quantity'] = 3
        with self.assertRaises(ValueError): self.run_takeoff()

    def test_same_profile_offcuts_shared_and_never_spliced(self):
        for a, frame in zip(self.fixture.saved['material_schedule']['assemblies'], self.frames):
            a['rough_opening_width_in'] = 36; frame.update(rough_opening_width_in=36, frame_width_in=35.5)
        self.assertEqual([p['quantity'] for p in self.run_takeoff()['purchases']], [1, 0])
        self.frames[0].update(frame_width_in=121, rough_opening_width_in=122)
        self.fixture.saved['material_schedule']['assemblies'][0]['rough_opening_width_in'] = 122
        with self.assertRaisesRegex(ValueError, 'continuous'): self.run_takeoff()

    def test_source_schedule_and_inclusion_validation(self):
        for change in ({'frame_width_in': float('nan')}, {'supplier_line': 999},
                       {'rough_opening_width_in': 109}, {'included_quantity': True},
                       {'included_quantity': 1, 'included_part_number': 'short', 'inclusion_reference': 'p1'}):
            original = copy.deepcopy(self.frames[0]); self.frames[0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): self.run_takeoff()
            self.frames[0] = original
        self.frames.pop()
        with self.assertRaises(ValueError): self.run_takeoff()

    def test_bridge_preserves_prices_and_rejects_changed_evidence(self):
        f = self.fixture; before = copy.deepcopy(f.draft)
        r = f.run_import()
        self.assertEqual(r['window_head_cap_review']['head_locations'], 2)
        self.assertEqual(f.draft, before)
        self.assertTrue(all(row['line_cost'] is None for row in r['rows']))
        (f.root/'caps.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'source changed'): f.run_import()
        self.basis['plan_sha256'] = 'other'; self.save()
        with self.assertRaisesRegex(ValueError, 'matching plan'): f.run_import()

    def test_bridge_requires_material_schedule_and_matching_specification(self):
        f = self.fixture
        f.mapping.pop('material_row_id')
        with self.assertRaisesRegex(ValueError, 'verified material'): f.run_import()
        f.mapping['material_row_id'] = '112'
        self.basis['specification_sha256'] = 'other'; self.save()
        with self.assertRaisesRegex(ValueError, 'specification'): f.run_import()


if __name__ == '__main__': unittest.main()
