import copy
import unittest
import fitz
from closet_room_candidates import apply
from native_door_interpretation import interpret
from door_room_associations import associate
from door_hardware_specifications import apply_hardware_policy
from door_policy_revision import apply_policy
from opening_bid_scope import build_scope
import test_native_door_interpretation as fixtures


class ClosetRooms(unittest.TestCase):
    def setUp(self):
        self.rooms={'plan_sha256':'plan','measurement_version':1,'source_sha256':'rooms','regions':[
            {'id':'closet','page':1,'points_per_foot':12,'points':[[10,10],[36,10],[36,70],[10,70]],
             'holes':[],'printed_labels':[],'room_use_confirmed':False}],
            'opening_connections':[{'opening_id':'door','page':1,'points_per_foot':12,'status':'two_region_boundaries',
                'sides':[{'region_id':'closet','status':'region_boundary','face_points_pt':[[10,20],[10,60]]},
                         {'region_id':'living','status':'region_boundary'}]}]}
        self.segments=[[[23.5,10.5],[35.5,10.5]],[[35.5,10.5],[35.5,69.5]],
            [[35.5,69.5],[23.5,69.5]],[[23.5,69.5],[23.5,10.5]],
            [[25,10.5],[25,69.5]],[[26.25,10.5],[26.25,69.5]]]

    def run_case(self,rooms=None,segments=None,**style):
        with fitz.open() as doc:
            page=doc.new_page(width=200,height=200)
            for a,b in self.segments if segments is None else segments:page.draw_line(a,b,**style)
            return apply(self.rooms if rooms is None else rooms,doc)

    def test_shelf_and_two_rod_lines_infer_explicit_unapproved_closet(self):
        before=copy.deepcopy(self.rooms);r=self.run_case();c=r['regions'][0]['room_use_inference']
        self.assertEqual(c['room_use'],'closet');self.assertTrue(c['requires_review'])
        self.assertFalse(c['owner_approved']);self.assertFalse(c['certified'])
        self.assertEqual(c['shelf_evidence']['symbol']['shelf_depth_inches'],12)
        self.assertFalse(r['closet_room_candidates']['shelving_quantity_released'])
        self.assertEqual(before,self.rooms);self.assertNotEqual(r['source_sha256'],before['source_sha256'])

    def test_missing_caps_or_rod_lines_do_not_guess_closet_from_size(self):
        for index in range(6):
            with self.subTest(index=index):
                self.assertNotIn('closet_room_candidates',self.run_case(segments=self.segments[:index]+self.segments[index+1:]))

    def test_invisible_dashed_white_symbols_are_ignored(self):
        for style in ({'color':(1,1,1)},{'stroke_opacity':0},{'dashes':'[3 2] 0'}):
            self.assertNotIn('closet_room_candidates',self.run_case(**style))

    def test_geometry_changes_and_unresolved_boundaries_withhold_use(self):
        for change in ('hole','shape','back','source'):
            r=copy.deepcopy(self.rooms);room=r['regions'][0]
            if change=='hole':room['holes']=[[[24,20],[27,20],[27,30],[24,30]]]
            elif change=='shape':room['points'][1][1]+=3
            elif change=='back':room['points'][1][0]+=5;room['points'][2][0]+=5
            else:room['boundary_source_issues']=[{'measurement_id':'wall'}]
            self.assertNotIn('closet_room_candidates',self.run_case(rooms=r))

    def test_named_confirmed_and_stale_rooms_take_precedence(self):
        for change in ('named','confirmed','stale','inferred'):
            r=copy.deepcopy(self.rooms);room=r['regions'][0]
            if change=='named':room['printed_labels']=[{'text':'PANTRY'}]
            elif change=='confirmed':room['room_use_confirmed']=True
            elif change=='stale':r['room_use_review']={'unresolved_decisions':[{'region_id':'closet'}]}
            else:room['room_use_inference']={'room_use':'utility'}
            self.assertNotIn('closet_room_candidates',self.run_case(rooms=r))

    def test_wrong_entry_page_scale_multiple_or_exterior_connections_rejected(self):
        for change in ('entry','page','scale','multiple','exterior'):
            r=copy.deepcopy(self.rooms);link=r['opening_connections'][0]
            if change=='entry':link['sides'][0]['face_points_pt']=[[36,20],[36,60]]
            elif change=='page':link['page']=2
            elif change=='scale':link['points_per_foot']=24
            elif change=='multiple':r['opening_connections']*=2
            else:link['status']='region_and_exterior_boundary'
            self.assertNotIn('closet_room_candidates',self.run_case(rooms=r))

    def test_rotation_reflection_and_scale_preserve_symbol(self):
        for transform,factor in ((lambda p:[p[1],p[0]],1),(lambda p:[100-p[0],p[1]],1),
                                 (lambda p:[2*p[0],2*p[1]],2)):
            r=copy.deepcopy(self.rooms);room=r['regions'][0]
            room['points']=[transform(p) for p in room['points']];room['points_per_foot']*=factor
            link=r['opening_connections'][0];link['points_per_foot']*=factor
            link['sides'][0]['face_points_pt']=[transform(p) for p in link['sides'][0]['face_points_pt']]
            out=self.run_case(rooms=r,segments=[[transform(a),transform(b)] for a,b in self.segments])
            self.assertEqual(out['regions'][0]['room_use_inference']['room_use'],'closet')

    def test_repeated_paths_are_not_multiple_symbols_but_competing_rods_are(self):
        self.assertIn('closet_room_candidates',self.run_case(segments=self.segments*2))
        self.assertNotIn('closet_room_candidates',self.run_case(segments=self.segments+[[[25.5,10.5],[25.5,69.5]]]))

    def test_changed_symbol_changes_evidence(self):
        a=self.run_case();changed=copy.deepcopy(self.segments)
        changed[-1][0][0]+=.1;changed[-1][1][0]+=.1;b=self.run_case(segments=changed)
        self.assertNotEqual(a['source_sha256'],b['source_sha256'])

    def policy_case(self,kind):
        f=fixtures.NativeDoorInterpretation();f.setUp()
        r=self.run_case();closet=r['regions'][0]
        f.rooms['regions'][0]['room_use_review']['room_use']='office'
        f.rooms['regions'][1]=closet
        f.rooms['opening_connections']=r['opening_connections']
        f.rooms['opening_connections'][0]['sides'][1]['region_id']='a'
        # The inference must be bound to this same opening connection.
        closet['room_use_inference']['shelf_evidence']['connection']=copy.deepcopy(f.rooms['opening_connections'][0])
        f.schedule['door_symbol_candidates']['candidates'][0].update(configuration_candidate=kind,drawn_panel_count_candidate=2)
        result=associate(interpret(f.schedule,f.rooms),f.rooms)
        result['door_core_review']=apply_policy(result,f.policy)
        result['door_hardware_review']=apply_hardware_policy(result,f.policy)
        return f,result

    def test_closet_entry_gets_hollow_passage_with_evidence_in_bid(self):
        f,r=self.policy_case('single_hinged');o=r['openings'][0]
        self.assertEqual(o['role'],'interior_door');self.assertEqual(o['room_class'],'closet')
        self.assertTrue(o['room_association']['closet_evidence'])
        self.assertEqual(r['door_core_review']['openings'][0]['core'],'hollow')
        self.assertEqual(r['door_hardware_review']['openings'][0]['hardware_function'],'passage')
        bid=build_scope(r)['openings'][0]
        self.assertTrue(bid['automatic_room_assignment']);self.assertIsNone(bid['purchase_quantity'])
        self.assertTrue(bid['unresolved'])

    def test_interior_slider_is_one_special_assembly_two_panels_no_ordinary_hardware(self):
        f,r=self.policy_case('sliding_pair');o=r['openings'][0]
        self.assertEqual(o['role'],'special_interior_door');self.assertEqual(o['door_configuration'],'sliding')
        self.assertEqual(o['drawn_panel_count'],2);self.assertEqual(o['room_class'],'closet')
        self.assertIsNone(r['door_hardware_review']['openings'][0]['hardware_function'])
        self.assertIsNone(build_scope(r)['openings'][0]['purchase_quantity'])
        f.schedule['door_symbol_candidates']['candidates'][0]['drawn_panel_count_candidate']=1
        self.assertEqual(interpret(f.schedule,f.rooms)['inferred_opening_ids'],[])

    def test_changed_room_binding_and_explicit_room_class_preserve_boundaries(self):
        f,_=self.policy_case('single_hinged')
        f.rooms['regions'][1]['points'][0][0]+=1
        self.assertEqual(interpret(f.schedule,f.rooms)['inferred_opening_ids'],[])
        f,r=self.policy_case('single_hinged')
        # An explicit class keeps precedence; no forced closet override in a conflict.
        r['openings'][0]['room_class']='bedroom'
        self.assertEqual(associate(r,f.rooms)['openings'][0]['room_class'],'bedroom')


if __name__=='__main__':unittest.main()
