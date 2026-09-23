"""Geometry recognition must not silently certify role, quantity or stale reviews."""
import copy
import hashlib
import math
from pathlib import Path
import tempfile
import unittest

import fitz
from door_symbol_candidates import recognize,from_plan


def fixture(rotation=0,reflection=1,scale=12):
    def point(p):
        x,y=p[0]*scale/12,p[1]*reflection*scale/12
        return [100+x*math.cos(rotation)-y*math.sin(rotation),200+x*math.sin(rotation)+y*math.cos(rotation)]
    curve=[point([32*math.cos(i*math.pi/72),32*math.sin(i*math.pi/72)]) for i in range(11)]
    drawings=[{'type':'s','items':[('l',a,b) for a,b in zip(curve,curve[1:])]},
              {'type':'s','items':[('l',point([0,0]),curve[-1])]}]
    opening={'opening_id':'door-1','page':1,'tag':'2868','points':[point([0,0]),point([32,0])],
        'points_per_foot':scale,'source_sha256':'gap-source','review_status':'role_unreviewed',
        'printed_nominal_size':{'width_inches':32,'height_inches':80,'type_code':None}}
    return opening,drawings


class DoorSymbols(unittest.TestCase):
    def test_rotated_reflected_scaled_symbols_remain_unapproved(self):
        for angle in (0,.7,math.pi,4.8):
            for reflection in (-1,1):
                for scale in (6,18,36):
                    opening,drawings=fixture(angle,reflection,scale)
                    before=copy.deepcopy(opening)
                    result=recognize([opening],{1:drawings},'plan')
                    self.assertEqual(len(result['candidates']),1)
                    candidate=result['candidates'][0]
                    self.assertEqual(candidate['configuration_candidate'],'single_hinged')
                    self.assertEqual(candidate['status'],'candidate_requires_review')
                    self.assertFalse(candidate['role_confirmed']);self.assertFalse(result['coverage_certified'])
                    self.assertFalse(candidate['purchase_released']);self.assertEqual(opening,before)

    def test_tag_leaf_arc_and_gap_all_required(self):
        for change in ('no_leaf','no_arc','straight','wrong_width','window_suffix','wrong_gap','wrong_page','fill_only'):
            opening,drawings=fixture()
            if change=='no_leaf':drawings=drawings[:1]
            elif change=='no_arc':drawings=drawings[1:]
            elif change=='straight':drawings[0]['items']=[('l',[100+i,200],[101+i,200]) for i in range(10)]
            elif change=='wrong_width':opening['printed_nominal_size']['width_inches']=24
            elif change=='window_suffix':opening['printed_nominal_size']['type_code']='SH'
            elif change=='wrong_gap':opening['points'][1][0]+=10
            elif change=='wrong_page':opening['page']=2
            elif change=='fill_only':drawings[0]['type']='f'
            self.assertEqual(recognize([opening],{1:drawings},'plan')['candidates'],[],change)

    def test_separate_symbols_ambiguous_but_duplicate_strokes_are_not(self):
        opening,drawings=fixture()
        self.assertEqual(len(recognize([opening],{1:drawings+copy.deepcopy(drawings)},'plan')['candidates'][0]['matches']),1)
        _,other=fixture(reflection=-1)
        candidate=recognize([opening],{1:drawings+other},'plan')['candidates'][0]
        self.assertEqual(candidate['status'],'ambiguous_symbols')
        self.assertIsNone(candidate['configuration_candidate'])

    def test_current_conflicting_and_stale_reviews_are_preserved(self):
        opening,drawings=fixture()
        opening.update(review_status='current_source_review',role='interior_door',door_configuration='single_hinged',drawn_panel_count=1)
        def candidate():return recognize([opening],{1:drawings},'plan')['candidates'][0]
        self.assertEqual(candidate()['status'],'corroborates_review')
        opening['role']='window'
        self.assertEqual(candidate()['status'],'conflicts_with_review');self.assertIsNone(candidate()['configuration_candidate'])
        opening.update(review_status='stale_source_review',role=None,door_configuration=None,drawn_panel_count=None)
        self.assertEqual(candidate()['status'],'stale_review_requires_reconciliation')

    def test_evidence_binds_plan_gap_and_drawing(self):
        opening,drawings=fixture()
        def signature(plan='plan'):return recognize([opening],{1:drawings},plan)['candidates'][0]['source_sha256']
        before=signature();self.assertNotEqual(before,signature('changed-plan'))
        opening['source_sha256']='changed-gap';self.assertNotEqual(before,signature())
        before=signature();drawings[0]['items'][3]=('l',drawings[0]['items'][3][1],[drawings[0]['items'][3][2][0]+.01,drawings[0]['items'][3][2][1]])
        self.assertNotEqual(before,signature())

    def test_actual_pdf_and_changed_source_rejection(self):
        opening,drawings=fixture()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plan.pdf'
            with fitz.open() as pdf:
                page=pdf.new_page()
                for drawing in drawings:
                    shape=page.new_shape()
                    for _,a,b in drawing['items']:shape.draw_line(a,b)
                    shape.finish(closePath=False);shape.commit()
                pdf.save(path)
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(len(from_plan(path,[opening],sha)['candidates']),1)
            with self.assertRaisesRegex(ValueError,'source changed'):from_plan(path,[opening],'wrong')


if __name__=='__main__':unittest.main()
