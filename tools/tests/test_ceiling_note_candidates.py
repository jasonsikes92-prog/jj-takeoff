import copy
import unittest
import fitz
from ceiling_note_candidates import page_notes,attach


class CeilingNotes(unittest.TestCase):
    def setUp(self):
        self.result={'source_sha256':'rooms','regions':[{'id':'one','page':1,
            'points':[[0,0],[100,0],[100,100],[0,100]],'holes':[]}]}

    def note(self,identity,kind,**fields):
        return {'id':identity,'page':1,'text':identity,'bounds_pt':[10,10,50,20],'kind':kind,**fields}

    def test_extracts_explicit_ceiling_notes_not_roof_pitches_or_dimensions(self):
        with fitz.open() as doc:
            p=doc.new_page(width=500,height=500)
            texts=['9\'-1" CLG.','VAULTED','4/12 VAULT','6 : 12','10/12','9\'-1"','0\'-0" CLG.','9\'-12" CLG.']
            for i,text in enumerate(texts):p.insert_text((30,40+i*30),text)
            notes=page_notes(p)
        self.assertEqual([n['kind'] for n in notes],['ceiling_height','vaulted','vault_pitch'])
        self.assertEqual(notes[0]['height_inches'],109);self.assertEqual(notes[2]['rise_inches'],4)

    def test_rotated_vault_text_has_page_coordinates(self):
        with fitz.open() as doc:
            p=doc.new_page();p.insert_text((100,200),'4/12 VAULT',rotate=90)
            note=page_notes(p)[0]
        self.assertLess(note['bounds_pt'][0],note['bounds_pt'][2]);self.assertEqual(note['kind'],'vault_pitch')

    def test_vault_does_not_apply_slope_to_entire_connected_room(self):
        notes=[self.note('height','ceiling_height',height_inches=109),self.note('slope','vault_pitch',rise_inches=4,run_inches=12)]
        result=attach(self.result,notes);r=result['regions'][0]['ceiling_reference']
        self.assertEqual(r['status'],'vault_extent_review_required');self.assertEqual(r['noted_height_inches'],109)
        self.assertEqual(r['noted_pitch'],{'rise_inches':4,'run_inches':12});self.assertIsNone(r['surface_area_sf'])
        self.assertNotIn('ceiling_notes',self.result['regions'][0])

    def test_no_note_is_not_flat_and_multiple_identical_notes_are_not_conflicts(self):
        self.assertEqual(attach(self.result,[])['regions'][0]['ceiling_reference']['status'],'no_explicit_ceiling_note')
        notes=[self.note(str(i),'ceiling_height',height_inches=109) for i in range(2)]
        self.assertEqual(attach(self.result,notes)['regions'][0]['ceiling_reference']['status'],'height_note_only')

    def test_height_and_pitch_conflicts_are_explicit(self):
        for notes in ([self.note(str(h),'ceiling_height',height_inches=h) for h in (108,120)],
                      [self.note(str(r),'vault_pitch',rise_inches=r,run_inches=12) for r in (4,6)]):
            self.assertEqual(attach(self.result,notes)['regions'][0]['ceiling_reference']['status'],'conflicting_notes')

    def test_wrong_page_boundary_hole_or_overlapping_regions_do_not_assign_note(self):
        for kind in ('page','boundary','hole','overlap'):
            result=copy.deepcopy(self.result);note=self.note('height','ceiling_height',height_inches=109)
            if kind=='page':note['page']=2
            elif kind=='boundary':note['bounds_pt']=[90,10,110,20]
            elif kind=='hole':result['regions'][0]['holes']=[[[5,5],[60,5],[60,30],[5,30]]]
            else:
                duplicate=copy.deepcopy(result['regions'][0]);duplicate['id']='two';result['regions'].append(duplicate)
            after=attach(result,[note]);self.assertEqual(len(after['ceiling_note_review']['unresolved_notes']),1)
            self.assertTrue(all(not r['ceiling_notes'] for r in after['regions']))

    def test_changed_note_changes_result_identity(self):
        note=self.note('height','ceiling_height',height_inches=109)
        before=attach(self.result,[note]);note['bounds_pt']=[110,10,150,20]
        self.assertNotEqual(before['source_sha256'],attach(self.result,[note])['source_sha256'])


if __name__=='__main__':unittest.main()
