import copy
import unittest
from room_use_review import binding
from door_room_associations import associate
from door_symbol_candidates import recognize
from door_policy_revision import apply_policy
from door_hardware_specifications import apply_hardware_policy
from opening_bid_scope import build_scope,render_markdown
from hardware_quantity_review import apply_hardware_quantities
from opening_quantity_review import apply_quantities
import test_door_room_associations as room_fixtures
import test_door_symbol_candidates as symbol_fixtures
import test_hardware_quantity_review as hardware_fixtures
import test_opening_quantity_review as quantity_fixtures


class SwingRoom(unittest.TestCase):
    def setUp(self):
        f=room_fixtures.DoorRoomAssociations();f.setUp()
        self.schedule,self.rooms,self.policy=f.schedule,f.rooms,f.policy
        o,ds=symbol_fixtures.fixture()
        self.schedule['openings'][0].update(o,opening_id='door',review_status='current_source_review',
            role='interior_door',door_configuration='single_hinged',drawn_panel_count=1)
        self.schedule.update(unresolved_opening_ids=[],limitations=[],coverage_certified=False)
        self.rooms['regions'][0]['points']=[[90,200],[150,200],[150,260],[90,260]]
        self.rooms['regions'][1]['points']=[[90,140],[150,140],[150,200],[90,200]]
        self.rooms['regions'][1]['room_use_review']['room_use']='living'
        for r in self.rooms['regions']:r['room_use_review']['source_sha256']=binding('plan',r)
        self.schedule['door_symbol_candidates']=recognize(self.schedule['openings'],{1:ds},'plan')

    def result(self):return associate(self.schedule,self.rooms)

    def test_swing_into_private_room_corroborates_class_and_flags_policies_and_bid(self):
        original=copy.deepcopy(self.schedule);result=self.result();row=result['openings'][0]
        self.assertEqual(row['room_class'],'bedroom');self.assertTrue(row['room_assignment_requires_review'])
        self.assertEqual(row['room_association']['status'],'resolved_from_native_swing_and_room_evidence')
        self.assertIn('swing_evidence',row['room_association']);self.assertEqual(self.schedule,original)
        result['door_core_review']=apply_policy(result,self.policy)
        result['door_hardware_review']=apply_hardware_policy(result,self.policy)
        core=result['door_core_review']['openings'][0];hardware=result['door_hardware_review']['openings'][0]
        self.assertEqual(core['core'],'solid');self.assertEqual(hardware['hardware_function'],'privacy')
        for r in (core,hardware):
            self.assertTrue(r['interpretation_requires_review']);self.assertIn('automatic_room_assignment',r)
        scope=build_scope(result)
        self.assertIn('room inferred',render_markdown(scope));self.assertIn('door',scope['unresolved_opening_ids'])
        self.assertIsNone(scope['openings'][0]['purchase_quantity'])

    def test_reviewed_role_with_inferred_room_keeps_quantity_provenance(self):
        result=self.result();result['door_core_review']=apply_policy(result,self.policy)
        result['door_hardware_review']=apply_hardware_policy(result,self.policy)
        h=hardware_fixtures.HardwareQuantityTests();h.setUp()
        draft=apply_hardware_quantities(h.draft,result,h.target)
        inputs=draft['rows'][-1]['assembly_inputs']
        self.assertEqual([i['quantity'] for i in inputs],[1,0])
        for i in inputs:
            self.assertTrue(i['interpretation_requires_review']);self.assertIn('door',i['automatic_room_assignments'])
        q=quantity_fixtures.OpeningQuantities();q.setUp()
        draft=apply_quantities(q.draft,result,q.config)
        row=next(r for r in draft['rows'] if r['row_id']=='solid')
        self.assertEqual(row['draft_quantity'],1);self.assertTrue(row['quantity_sources'][0]['interpretation_requires_review'])

    def test_no_class_is_assigned_from_outswing_or_special_assembly(self):
        _,ds=symbol_fixtures.fixture(reflection=-1)
        self.schedule['door_symbol_candidates']=recognize(self.schedule['openings'],{1:ds},'plan')
        self.assertIsNone(self.result()['openings'][0]['room_class'])
        self.setUp();self.schedule['openings'][0].update(role='special_interior_door',door_configuration='pocket')
        self.assertIsNone(self.result()['openings'][0]['room_class'])

    def test_private_to_private_connection_is_not_ranked_by_swing(self):
        self.rooms['regions'][1]['room_use_review']['room_use']='closet'
        self.assertIsNone(self.result()['openings'][0]['room_class'])
        self.rooms['regions'][1]['room_use_review']['room_use']='bathroom'
        self.assertIsNone(self.result()['openings'][0]['room_class'])

    def test_stale_ambiguous_or_missing_symbol_evidence_is_not_used(self):
        for field,value in [('opening_source_sha256','old'),('status','ambiguous_symbols'),('matches',[])]:
            s=copy.deepcopy(self.schedule);s['door_symbol_candidates']['candidates'][0][field]=value
            self.assertIsNone(associate(s,self.rooms)['openings'][0]['room_class'])
        r=copy.deepcopy(self.rooms);r['regions'][0]['points'][0][0]+=1
        self.assertIsNone(associate(self.schedule,r)['openings'][0]['room_class'])

    def test_swing_crossing_a_region_hole_or_overlapping_rooms_is_not_unique(self):
        r=self.rooms['regions'][0]
        r['holes']=[[[120,202],[133,202],[133,216],[120,216]]]
        r['room_use_review']['source_sha256']=binding('plan',r)
        self.assertIsNone(self.result()['openings'][0]['room_class'])
        self.setUp();r=self.rooms['regions'][1]
        r['points']=copy.deepcopy(self.rooms['regions'][0]['points']);r['room_use_review']['source_sha256']=binding('plan',r)
        self.assertIsNone(self.result()['openings'][0]['room_class'])

    def test_explicit_class_and_project_specification_keep_precedence(self):
        self.schedule['openings'][0]['room_class']='other_interior'
        result=self.result();self.assertEqual(result['openings'][0]['room_class'],'other_interior')
        self.assertNotIn('swing_evidence',result['openings'][0]['room_association'])
        self.schedule['openings'][0].update(room_class=None,project_core='hollow',project_core_source='Explicit project selection')
        core=apply_policy(self.result(),self.policy)['openings'][0]
        self.assertEqual(core['core'],'hollow');self.assertEqual(core['basis'],'project_specification')


if __name__=='__main__':unittest.main()
