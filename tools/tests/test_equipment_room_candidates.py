import copy
import unittest
import fitz
from equipment_room_candidates import apply


class EquipmentRooms(unittest.TestCase):
    def setUp(self):
        self.rooms={'plan_sha256':'plan','measurement_version':1,'source_sha256':'rooms','regions':[
            {'id':'utility','page':1,'points_per_foot':12,'points':[[10,10],[70,10],[70,70],[10,70]],'holes':[],
             'printed_labels':[],'room_use_confirmed':False}],
            'opening_connections':[{'opening_id':'door','page':1,'points_per_foot':12,'status':'two_region_boundaries',
                'sides':[{'region_id':'utility','status':'region_boundary'},{'region_id':'laundry','status':'region_boundary'}]}]}

    def run_case(self,circle=True,text='WH',rooms=None,center=(40,40),text_point=(32,43),second=False):
        with fitz.open() as document:
            page=document.new_page(width=200,height=200)
            if circle:page.draw_circle(center,15,width=.6)
            page.insert_text(text_point,text,fontsize=9)
            if second:page.insert_text((32,55),'WH',fontsize=7)
            return apply(rooms or self.rooms,document)

    def test_wh_and_circular_tank_in_dedicated_enclosure_are_an_explicit_assumption(self):
        before=copy.deepcopy(self.rooms);r=self.run_case()
        c=r['regions'][0]['room_use_inference']
        self.assertEqual(c['room_use'],'utility');self.assertEqual(c['status'],'equipment_symbol_inference')
        self.assertFalse(c['owner_approved']);self.assertTrue(c['requires_review'])
        self.assertFalse(r['equipment_room_candidates']['equipment_quantity_released'])
        self.assertNotEqual(r['source_sha256'],before['source_sha256']);self.assertEqual(self.rooms,before)

    def test_text_alone_circle_alone_or_offcenter_label_do_not_establish_equipment_room(self):
        for kwargs in ({'circle':False},{'text':'WC'},{'text':'WH NOTES'},{'text_point':(53,62)},{'second':True}):
            self.assertNotIn('equipment_room_candidates',self.run_case(**kwargs))

    def test_named_confirmed_and_stale_rooms_are_preserved(self):
        for change in ('name','confirmed','stale'):
            rooms=copy.deepcopy(self.rooms)
            if change=='name':rooms['regions'][0]['printed_labels']=[{'text':'GARAGE'}]
            elif change=='confirmed':rooms['regions'][0]['room_use_confirmed']=True
            else:rooms['room_use_review']={'unresolved_decisions':[{'region_id':'utility'}]}
            self.assertNotIn('equipment_room_candidates',self.run_case(rooms=rooms))

    def test_large_multiple_entry_or_external_spaces_stay_unknown(self):
        for change in ('large','entries','external','no_entry'):
            rooms=copy.deepcopy(self.rooms)
            if change=='large':rooms['regions'][0]['points']=[[0,0],[150,0],[150,150],[0,150]]
            elif change=='entries':rooms['opening_connections']*=2
            elif change=='external':rooms['opening_connections'][0]['status']='region_and_exterior_boundary'
            else:rooms['opening_connections']=[]
            self.assertNotIn('equipment_room_candidates',self.run_case(rooms=rooms))

    def test_body_crossing_region_or_hole_is_rejected(self):
        self.assertNotIn('equipment_room_candidates',self.run_case(center=(15,40)))
        self.rooms['regions'][0]['holes']=[[[35,35],[45,35],[45,45],[35,45]]]
        self.assertNotIn('equipment_room_candidates',self.run_case())

    def test_changed_label_position_changes_evidence(self):
        a=self.run_case()['regions'][0]['room_use_inference']['equipment_evidence']
        b=self.run_case(text_point=(33,43))['regions'][0]['room_use_inference']['equipment_evidence']
        self.assertNotEqual(a['source_sha256'],b['source_sha256'])

    def test_boundary_with_unresolved_wall_evidence_cannot_infer_use(self):
        self.rooms['regions'][0]['boundary_source_issues']=[{'measurement_id':'stale-wall'}]
        self.assertNotIn('equipment_room_candidates',self.run_case())


if __name__=='__main__':unittest.main()
