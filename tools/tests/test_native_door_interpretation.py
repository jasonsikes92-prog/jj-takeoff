import copy
import unittest
from native_door_interpretation import interpret
from door_room_associations import associate
from door_hardware_specifications import apply_hardware_policy
from door_policy_revision import apply_policy
from hardware_quantity_review import apply_hardware_quantities
from opening_bid_scope import build_scope,render_markdown
from wall_enclosure_candidates import candidates
from opening_quantity_review import apply_quantities
import test_opening_quantity_review as opening_fixtures
import test_door_room_associations as room_fixtures
import test_hardware_quantity_review as quantity_fixtures
import test_wall_enclosure_candidates as wall_fixtures


class NativeDoorInterpretation(unittest.TestCase):
    def setUp(self):
        f=room_fixtures.DoorRoomAssociations();f.setUp()
        self.schedule,self.rooms,self.policy=f.schedule,f.rooms,f.policy
        self.schedule.update(unresolved_opening_ids=['door'],reviewed_role_counts={'interior_door':0},enumerated_window_unit_count=None,
            limitations=[],coverage_certified=False)
        self.schedule['openings'][0].update(role=None,door_configuration=None,review_status='role_unreviewed',points_per_foot=12,
            source_sha256='gap',tag='2868',printed_nominal_size={'height_inches':80,'width_inches':32},drawn_panel_count=None)
        self.schedule['door_symbol_candidates']={'candidates':[{'opening_id':'door','status':'candidate_requires_review',
            'configuration_candidate':'single_hinged','opening_source_sha256':'gap','source_sha256':'symbol'}]}

    def result(self):return associate(interpret(self.schedule,self.rooms),self.rooms)

    def test_supported_geometry_and_named_regions_resolve_policy_and_bid(self):
        before=copy.deepcopy(self.schedule);r=self.result();o=r['openings'][0]
        self.assertEqual(o['review_status'],'native_symbol_inference');self.assertEqual(o['role'],'interior_door')
        self.assertEqual(o['room_class'],'bedroom');self.assertEqual(r['reviewed_role_counts']['interior_door'],0)
        self.assertEqual(r['inferred_role_counts']['interior_door'],1)
        r['door_hardware_review']=apply_hardware_policy(r,self.policy);r['door_core_review']=apply_policy(r,self.policy)
        self.assertEqual(r['door_hardware_review']['openings'][0]['hardware_function'],'privacy')
        self.assertEqual(r['door_core_review']['openings'][0]['core'],'solid')
        scope=build_scope(r)
        self.assertIn('inferred',render_markdown(scope));self.assertIn('door',scope['unresolved_opening_ids'])
        self.assertIsNone(scope['openings'][0]['purchase_quantity']);self.assertEqual(self.schedule,before)

    def test_inferred_hardware_can_flow_into_draft_without_claiming_review(self):
        r=self.result();r['door_hardware_review']=apply_hardware_policy(r,self.policy)
        f=quantity_fixtures.HardwareQuantityTests();f.setUp()
        draft=apply_hardware_quantities(f.draft,r,f.target)
        self.assertEqual([g['quantity'] for g in draft['hardware_quantity_review']['groups']],[1,0,None,None])
        source=draft['rows'][-1]['assembly_inputs'][0]
        self.assertEqual(source['kind'],'inferred_hardware_set_reference')
        self.assertTrue(source['interpretation_requires_review']);self.assertFalse(source['purchase_released'])
        zero=draft['rows'][-1]['assembly_inputs'][1]
        self.assertEqual(zero['quantity'],0);self.assertTrue(zero['interpretation_requires_review'])

    def test_does_not_replace_current_stale_or_conflicting_decisions(self):
        for status in ('current_source_review','stale_source_review','symbol_conflict_requires_review'):
            self.schedule['openings'][0]['review_status']=status
            self.assertEqual(interpret(self.schedule,self.rooms)['inferred_opening_ids'],[])

    def test_ordinary_door_draft_count_retains_inferred_basis(self):
        r=self.result();r['door_core_review']=apply_policy(r,self.policy)
        f=opening_fixtures.OpeningQuantities();f.setUp()
        draft=apply_quantities(f.draft,r,f.config)
        solid=next(row for row in draft['rows'] if row['row_id']=='solid')
        self.assertEqual(solid['draft_quantity'],1)
        self.assertEqual(solid['quantity_sources'][0]['inferred_opening_ids'],['door'])
        self.assertTrue(solid['quantity_sources'][0]['interpretation_requires_review'])
        self.assertFalse(solid['quantity_sources'][0]['purchase_released'])
        self.assertEqual(solid['markup_pct'],'15')

    def test_unknown_garage_wrong_page_changed_geometry_and_symbol_are_not_inferred(self):
        for change in ('missing_room','garage','wrong_page','geometry','symbol','external','ambiguous_symbol'):
            s=copy.deepcopy(self.schedule);rooms=copy.deepcopy(self.rooms)
            if change=='missing_room':rooms['regions'][0]['room_use_confirmed']=False
            elif change=='garage':rooms['regions'][0]['room_use_review']['room_use']='garage'
            elif change=='wrong_page':rooms['regions'][0]['page']=2
            elif change=='geometry':rooms['regions'][0]['points'][0][0]+=1
            elif change=='symbol':s['door_symbol_candidates']['candidates'][0]['opening_source_sha256']='old'
            elif change=='external':rooms['opening_connections'][0]['status']='region_and_exterior_boundary'
            else:s['door_symbol_candidates']['candidates'][0]['status']='ambiguous_symbols'
            self.assertEqual(interpret(s,rooms)['inferred_opening_ids'],[],change)

    def test_different_room_classes_do_not_guess_hardware(self):
        self.rooms['regions'][1]['room_use_review']['room_use']='closet'
        r=self.result();self.assertEqual(r['inferred_opening_ids'],['door'])
        self.assertIsNone(r['openings'][0]['room_class'])
        self.assertIsNone(apply_hardware_policy(r,self.policy)['openings'][0]['hardware_function'])

    def test_exterior_symbol_and_boundary_flow_to_bid_without_interior_defaults(self):
        link=self.rooms['opening_connections'][0]
        link.update(status='region_and_exterior_boundary')
        link['sides'][1]={'status':'exterior_boundary','region_id':None,
            'candidate_region_ids':[],'exterior_enclosure_ids':['enclosure']}
        self.schedule['reviewed_role_counts']['exterior_door']=0
        symbol=self.schedule['door_symbol_candidates']['candidates'][0]
        for kind,configuration,count in [('single_hinged','single_hinged',1),('double_hinged','double_hinged',2),('sliding_pair','sliding',2)]:
            symbol.update(configuration_candidate=kind,drawn_panel_count_candidate=count)
            r=self.result();o=r['openings'][0]
            self.assertEqual(o['role'],'exterior_door');self.assertEqual(o['door_configuration'],configuration)
            self.assertEqual(r['inferred_role_counts']['exterior_door'],1)
            self.assertEqual(r['reviewed_role_counts']['exterior_door'],0)
            r['door_core_review']=apply_policy(r,self.policy)
            r['door_hardware_review']=apply_hardware_policy(r,self.policy)
            self.assertFalse(any(x.get('core') for x in r['door_core_review']['openings']))
            self.assertFalse(any(x.get('hardware_function') for x in r['door_hardware_review']['openings']))
            scope=build_scope(r);items={i['id']:i for i in scope['items']}
            self.assertEqual(items['door:exterior-trim']['reference_quantity'],1)
            self.assertEqual(items['door:supply']['reference_quantity'],1)
            self.assertFalse(scope['ready_to_order']);self.assertIn('door',scope['unresolved_opening_ids'])
        symbol['configuration_candidate']='pocket'
        self.assertEqual(interpret(self.schedule,self.rooms)['inferred_opening_ids'],[])
        symbol['configuration_candidate']='single_hinged'
        link['sides'][1]['exterior_enclosure_ids']=['a','b']
        self.assertEqual(interpret(self.schedule,self.rooms)['inferred_opening_ids'],[])

    def test_double_interior_door_is_one_special_assembly_without_ordinary_hardware(self):
        symbol=self.schedule['door_symbol_candidates']['candidates'][0]
        symbol.update(configuration_candidate='double_hinged',drawn_panel_count_candidate=2)
        r=self.result();o=r['openings'][0]
        self.assertEqual(o['role'],'special_interior_door');self.assertEqual(o['drawn_panel_count'],2)
        self.assertEqual(o['door_configuration'],'double_hinged')
        r['door_hardware_review']=apply_hardware_policy(r,self.policy)
        self.assertIsNone(r['door_hardware_review']['openings'][0]['hardware_function'])
        scope=build_scope(r)
        self.assertEqual(scope['openings'][0]['assembly_count'],1)
        self.assertEqual(scope['openings'][0]['drawn_panel_count'],2)
        self.assertIsNone(scope['openings'][0]['purchase_quantity'])
        self.assertEqual(scope['hardware_references'][0]['ordinary_hinged_set_reference'],0)
        self.assertIn('double hinged (inferred)',render_markdown(scope))
        for count in (None,1,3):
            symbol['drawn_panel_count_candidate']=count
            self.assertEqual(interpret(self.schedule,self.rooms)['inferred_opening_ids'],[])

    def test_native_symbol_closes_boundary_but_stale_or_mismatched_symbol_does_not(self):
        f=wall_fixtures.WallEnclosures();f.setUp()
        f.state['measurements']['top']['points'][1][0]=48;f.add('top2',[[72,2],[116,2]])
        runs,gaps,openings=f.sources(True)
        opening=openings['openings'][0];opening.update(review_status='role_unreviewed',source_sha256='gap')
        symbol={'opening_id':'door','status':'candidate_requires_review','configuration_candidate':'pocket','opening_source_sha256':'gap'}
        openings['door_symbol_candidates']={'candidates':[symbol]}
        r=candidates(f.state,runs,gaps,openings)
        self.assertEqual(r['candidate_enclosures'][0]['gross_boundary_sf'],100)
        self.assertIn('Native door',r['gap_closures'][0]['basis'])
        symbol['opening_source_sha256']='old'
        self.assertEqual(candidates(f.state,runs,gaps,openings)['candidate_enclosures'],[])
        symbol['opening_source_sha256']='gap';opening['review_status']='stale_source_review'
        self.assertEqual(candidates(f.state,runs,gaps,openings)['candidate_enclosures'],[])

    def test_wrong_revision_and_duplicate_topology_rejected(self):
        with self.assertRaises(ValueError):interpret(self.schedule,{**self.rooms,'measurement_version':2})
        self.rooms['opening_connections']*=2
        with self.assertRaises(ValueError):self.result()

    def test_unlocated_tag_survives_interpretation_and_bid(self):
        self.schedule['unlocated_opening_tags']=[{'opening_id':'missing','tag':'2868','page':1,'reason':'No unique current gap'}]
        r=self.result();self.assertIn('missing',r['unresolved_opening_ids'])
        scope=build_scope(r);self.assertIn('missing',scope['unresolved_opening_ids'])
        self.assertIn('Opening tags needing a wall location',render_markdown(scope))


if __name__=='__main__':unittest.main()
