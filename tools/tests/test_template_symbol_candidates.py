import copy
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import numpy as np
import cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from template_symbol_candidates import plan_template_candidates, matches


class TemplateSymbols(unittest.TestCase):
    def setup_page(self,ink=(1,0,0)):
        doc=fitz.open();self.addCleanup(doc.close);p=doc.new_page(width=400,height=400)
        def symbol(x,y,scale):
            p.draw_circle((x,y),12*scale,color=ink,width=scale)
            for angle in (0,60,120):
                dx=16*scale*math.cos(math.radians(angle));dy=16*scale*math.sin(math.radians(angle))
                p.draw_line((x-dx,y-dy),(x+dx,y+dy),color=ink,width=scale)
        symbol(30,30,1);symbol(150,150,1);symbol(280,160,1.5)
        p.draw_circle((150,290),12,color=ink,width=1)
        definition={'plan_sha256':'plan','pages':[{'page':1,'exclusions':[],
            'templates':[{'id':'fan','label':'Fan candidate','meaning_source':'Synthetic legend',
                          'bbox_pt':[10,10,50,50],'ink':'red','scales':[1,1.45,1.5,1.55],
                          'minimum_score':.85}]}]}
        return doc,definition

    def test_reference_excluded_scales_deduplicated_and_circle_rejected(self):
        doc,config=self.setup_page();result=plan_template_candidates(doc,config,'plan')
        points=result['measurements'][0]['points']
        self.assertEqual(len(points),2)
        self.assertLess(math.dist(points[0],[150,150]),2)
        self.assertLess(math.dist(points[1],[280,160]),2)
        self.assertTrue(result['measurements'][0]['engine_line_ids'])
        self.assertFalse(result['coverage_certified']);self.assertFalse(result['estimate_released'])

    def test_dark_ink_and_explicit_exclusion(self):
        doc,config=self.setup_page((0,0,0));page=config['pages'][0]
        page['templates'][0]['ink']='dark'
        page['exclusions']=[{'bbox_pt':[240,120,320,200],'source':'Excluded detail view'}]
        result=plan_template_candidates(doc,config,'plan')
        self.assertEqual(len(result['measurements'][0]['points']),1)

    def test_vector_frame_requirement_is_applied_to_pdf_candidates(self):
        with fitz.open() as doc:
            p=doc.new_page(width=300,height=200)
            for x,y in ((10,10),(130,100)):
                p.draw_rect((x,y,x+20,y+40),color=(1,0,0))
                p.draw_circle((x+10,y+20),7,color=(1,0,0))
            config={'plan_sha256':'plan','pages':[{'page':1,'templates':[{'id':'floor','label':'Floor outlet',
                'meaning_source':'Synthetic legend','bbox_pt':[5,5,35,55],'ink':'red','scales':[1],
                'minimum_score':.9,'require_vector_frame':True}]}]}
            result=plan_template_candidates(doc,config,'plan')
            self.assertEqual(len(result['measurements'][0]['points']),1)
            self.assertIn('vector_frame',result['measurements'][0]['source_matches'][0])
            self.assertIsNotNone(result['searches'][0]['vector_reference_frame'])
        doc,config=self.setup_page();config['pages'][0]['templates'][0]['require_vector_frame']=True
        with self.assertRaisesRegex(ValueError,'No closed vector rectangle'):plan_template_candidates(doc,config,'plan')
        config['pages'][0]['templates'][0]['require_vector_frame']='yes'
        with self.assertRaisesRegex(ValueError,'true or false'):plan_template_candidates(doc,config,'plan')

    def test_higher_resolution_preserves_pdf_coordinates_and_exclusions(self):
        doc,config=self.setup_page();config['raster_pixels_per_point']=2
        config['pages'][0]['exclusions']=[{'bbox_pt':[240,120,320,200],'source':'Excluded detail'}]
        result=plan_template_candidates(doc,config,'plan')
        points=result['measurements'][0]['points']
        self.assertEqual(len(points),1);self.assertLess(math.dist(points[0],[150,150]),2)
        self.assertEqual(result['raster_pixels_per_point'],2)
        self.assertEqual(result['measurements'][0]['width_pt'],400)
        for invalid in (0,4,True,1.5):
            config['raster_pixels_per_point']=invalid
            with self.assertRaises(ValueError):plan_template_candidates(doc,config,'plan')

    def test_no_matches_are_unresolved_not_zero_devices(self):
        doc,config=self.setup_page();config['pages'][0]['exclusions']=[{'bbox_pt':[100,100,350,350],'source':'Non-plan region'}]
        result=plan_template_candidates(doc,config,'plan')
        self.assertEqual(result['measurements'],[])
        self.assertEqual(result['searches'][0]['status'],'no_match_scope_unresolved')

    def test_invalid_definitions_and_changed_drawing_are_rejected(self):
        doc,config=self.setup_page()
        with self.assertRaisesRegex(ValueError,'another drawing'):plan_template_candidates(doc,config,'other')
        for update in ({'scales':[0]},{'scales':[1,1]},{'scales':[[1]]},{'minimum_score':float('nan')},
                       {'rotations_degrees':[]},{'rotations_degrees':[45]},
                       {'rotations_degrees':[0,0]},{'rotations_degrees':[True]},
                       {'stroke_dilations_pixels':[]},{'stroke_dilations_pixels':[4]},
                       {'stroke_dilations_pixels':[True]},{'stroke_dilations_pixels':[0,0]},
                       {'bbox_pt':[1,1,450,450]},{'meaning_source':''},{'ink':'unknown'},
                       {'bbox_pt':[60,60,90,90]}):
            candidate=copy.deepcopy(config);candidate['pages'][0]['templates'][0].update(update)
            with self.subTest(update=update),self.assertRaises(ValueError):plan_template_candidates(doc,candidate,'plan')

    def test_candidate_limit_raises_instead_of_truncating(self):
        doc,config=self.setup_page()
        with patch('template_symbol_candidates.MAX_CANDIDATES',1):
            with self.assertRaisesRegex(ValueError,'Too many'):plan_template_candidates(doc,config,'plan')

    def test_quarter_turns_find_rotated_asymmetric_symbol_without_duplicates(self):
        template=np.zeros((28,18),dtype=np.uint8)
        template[3:24,3:6]=255;template[21:24,3:15]=255;template[5:9,11:15]=255
        mask=np.zeros((160,160),dtype=np.uint8);mask[5:33,5:23]=template
        rotated=np.rot90(template);mask[80:98,85:113]=rotated
        unrotated,_=matches(mask,[5,5,23,33],[1],.97,[])
        self.assertEqual(unrotated,[])
        found,searched=matches(mask,[5,5,23,33],[1],.97,[],[0,90,180,270])
        self.assertEqual(searched,4);self.assertEqual(len(found),1)
        self.assertEqual(found[0]['rotation_degrees'],90)
        self.assertLess(math.dist(found[0]['point_pt'],[99,89]),1)

    def test_stroke_adjustment_matches_scaled_symbol_with_heavier_lines(self):
        template=np.zeros((60,40),dtype=np.uint8)
        cv2.rectangle(template,(6,6),(33,53),255,1)
        cv2.circle(template,(20,30),10,255,1)
        cv2.line(template,(14,10),(14,49),255,1)
        cv2.line(template,(26,10),(26,49),255,1)
        mask=np.zeros((180,180),dtype=np.uint8);mask[5:65,5:45]=template
        small=cv2.dilate(cv2.resize(template,(20,30)),np.ones((3,3),np.uint8))
        mask[100:130,110:130]=small
        baseline,_=matches(mask,[5,5,45,65],[.5],.97,[])
        self.assertEqual(baseline,[])
        found,variants=matches(mask,[5,5,45,65],[.5],.97,[],[0],[0,1])
        self.assertEqual(variants,2);self.assertEqual(len(found),1)
        self.assertEqual(found[0]['stroke_dilation_pixels'],1)
        self.assertLess(math.dist(found[0]['point_pt'],[120,115]),1)

if __name__=='__main__':unittest.main()
