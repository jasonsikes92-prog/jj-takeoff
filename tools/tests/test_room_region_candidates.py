import copy
import unittest
import fitz
from room_region_candidates import page_labels,associate


class RoomRegions(unittest.TestCase):
    def setUp(self):
        self.enclosures={'plan_sha256':'plan','measurement_version':1,'source_sha256':'source',
            'interior_region_candidates':[{'id':'one','parent_enclosure_id':'house','page':1,
                'points_per_foot':10,'points':[[0,0],[100,0],[100,100],[0,100]],'holes':[],
                'boundary_area_sf':100,'floor_finish_quantity':None,'certified':False}]}

    def label(self,identity,text,bounds,page=1):
        return {'id':identity,'text':text,'bounds_pt':bounds,'page':page}

    def test_native_lines_recognize_rooms_and_skip_dimensions_notes_and_equipment(self):
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=500)
            for i,text in enumerate(['Bedroom 2','MASTER BATH','Kitchen','3068','VAULTED','WH','WOOD ATTIC LADDER','OFFICE FRAMING']):
                p.insert_text((30,40+i*30),text)
            labels=page_labels(p)
        self.assertEqual([l['text'] for l in labels],['Bedroom 2','MASTER BATH','Kitchen'])
        self.assertEqual(len({l['id'] for l in labels}),3)

    def test_open_plan_labels_share_one_region_and_one_area(self):
        labels=[self.label('living','LIVING',[10,10,40,20]),self.label('kitchen','KITCHEN',[50,50,80,60])]
        before=copy.deepcopy(self.enclosures);result=associate(self.enclosures,labels)
        self.assertEqual(len(result['regions']),1)
        r=result['regions'][0];self.assertEqual(r['boundary_area_sf'],100)
        self.assertEqual(r['association_status'],'multiple_labels_one_region')
        self.assertEqual(len(r['printed_labels']),2);self.assertIsNone(r['finish_selection'])
        self.assertIsNone(result['whole_floor_finish_quantity']);self.assertFalse(r['room_use_confirmed'])
        self.assertEqual(self.enclosures,before)

    def test_unlabeled_spaces_remain_and_repeated_bedroom_names_stay_distinct(self):
        r=copy.deepcopy(self.enclosures['interior_region_candidates'][0]);r.update(id='two',points=[[120,0],[220,0],[220,100],[120,100]])
        self.enclosures['interior_region_candidates'].append(r)
        one=self.label('bed1','BEDROOM',[10,10,50,20]);two=self.label('bed2','BEDROOM',[130,10,170,20])
        result=associate(self.enclosures,[one])
        self.assertEqual(result['regions'][1]['association_status'],'no_printed_room_label')
        result=associate(self.enclosures,[one,two])
        self.assertEqual([r['printed_labels'][0]['id'] for r in result['regions']],['bed1','bed2'])

    def test_boundary_crossing_hole_and_other_page_do_not_receive_labels(self):
        self.enclosures['interior_region_candidates'][0]['holes']=[[[40,40],[60,40],[60,60],[40,60]]]
        labels=[self.label('cross','LIVING',[90,30,110,40]),self.label('hole','BATH',[45,45,55,55]),
            self.label('other','KITCHEN',[10,10,40,20],2)]
        result=associate(self.enclosures,labels)
        self.assertEqual(len(result['unresolved_labels']),3)
        self.assertEqual(result['regions'][0]['printed_labels'],[])

    def test_overlap_ambiguity_is_not_arbitrarily_assigned_and_duplicate_ids_reject(self):
        r=copy.deepcopy(self.enclosures['interior_region_candidates'][0]);r['id']='overlap'
        self.enclosures['interior_region_candidates'].append(r)
        label=self.label('label','OFFICE',[10,10,40,20])
        result=associate(self.enclosures,[label])
        self.assertEqual(len(result['unresolved_labels']),1)
        self.assertTrue(all(not r['printed_labels'] for r in result['regions']))
        with self.assertRaises(ValueError):associate(self.enclosures,[label,label])

    def test_changed_source_or_label_position_changes_result_identity(self):
        label=self.label('label','OFFICE',[10,10,40,20]);first=associate(self.enclosures,[label])
        label['bounds_pt']=[110,10,140,20]
        self.assertNotEqual(first['source_sha256'],associate(self.enclosures,[label])['source_sha256'])
        label['bounds_pt']=[10,10,40,20];self.enclosures['source_sha256']='changed'
        self.assertNotEqual(first['source_sha256'],associate(self.enclosures,[label])['source_sha256'])


if __name__=='__main__':unittest.main()
