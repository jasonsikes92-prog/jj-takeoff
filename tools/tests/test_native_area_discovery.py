import unittest
import fitz
from native_area_discovery import discover_view,automatic_registration,view_story_caption
from native_area_candidates import filled_regions


class NativeAreaDiscovery(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.doc.new_page(width=1000,height=1000);self.doc.new_page(width=1000,height=1000)
        self.addCleanup(self.doc.close)

    def region(self,page,rect,color,label=None):
        a,b,c,d=rect;shape=page.new_shape()
        shape.draw_polyline([(a,b),(c,b),(c,d),(a,d),(a,b)])
        shape.finish(fill=color,color=None);shape.commit()
        if label:page.insert_text((a+10,b+30),label,fontsize=10)

    def test_labels_identify_polygons_without_fixed_colors_or_area_totals(self):
        page=self.doc[1]
        self.region(page,[200,200,480,450],(1,0,1),'HEATED')
        self.region(page,[490,200,750,450],(0,1,0),'GARAGE')
        self.region(page,[20,200,40,220],(1,0,1))
        page.insert_text((45,215),'HEATED 999999 SF')
        result=discover_view(page)
        self.assertEqual(result['view_bounds_pt'],[200,200,750,450])
        self.assertEqual(len(result['fills']),2)
        self.assertEqual(result['fills'][0]['fill'],[1,0,1])
        self.assertFalse(result['printed_schedule_used'])
        self.assertEqual(len(result['source_cad_paths']),2)

    def test_unlabeled_and_grayscale_fills_are_not_area_candidates(self):
        page=self.doc[1]
        self.region(page,[200,200,480,450],(.5,.5,.5),'HEATED')
        self.region(page,[490,200,750,450],(0,1,0))
        self.assertIsNone(discover_view(page))

    def test_story_caption_requires_adjacent_scale_and_unique_view(self):
        page=self.doc[1];bounds=[100,100,700,400]
        page.insert_text((400,430),'1st Floor',fontsize=10)
        self.assertIsNone(view_story_caption(page,bounds))
        page.insert_text((390,443),'1/4 in = 1 ft',fontsize=10)
        self.assertEqual(view_story_caption(page,bounds)['story'],'FIRST FLOOR')
        page.insert_text((200,430),'2nd Floor',fontsize=10)
        page.insert_text((190,443),'1/4 in = 1 ft',fontsize=10)
        self.assertIsNone(view_story_caption(page,bounds))

    def test_qualified_patio_labels_in_pale_regions(self):
        page=self.doc[1]
        self.region(page,[50,50,350,250],(.68,1,1),'BACK COVERED PATIO')
        self.region(page,[400,50,700,250],(1,.75,.75),'UNCOVERED PATIO LEFT')
        result=discover_view(page)
        self.assertIsNotNone(result)
        self.assertEqual({f['source_label'] for f in result['fills']},
                         {'BACK COVERED PATIO','UNCOVERED PATIO LEFT'})
        self.assertFalse(result['printed_schedule_used'])

    def test_pale_fill_with_schedule_text_does_not_become_measured_region(self):
        page=self.doc[1]
        self.region(page,[50,50,350,250],(.68,1,1),'BACK COVERED PATIO 337.32')
        self.assertIsNone(discover_view(page))

    def test_conflicting_labels_and_repeated_color_are_rejected(self):
        page=self.doc[1];self.region(page,[200,200,480,450],(1,0,1),'HEATED')
        page.insert_text((220,280),'GARAGE',fontsize=10)
        with self.assertRaisesRegex(ValueError,'Multiple area labels'):discover_view(page)
        other=self.doc[0]
        self.region(other,[200,200,480,450],(1,0,1),'HEATED')
        self.region(other,[490,200,750,450],(1,0,1),'GARAGE')
        result=discover_view(other)
        self.assertEqual(len(result['fills']),2)
        measures=filled_regions(other,result['view_bounds_pt'],result['fills'],{'points_per_foot':10})
        self.assertEqual(len(measures),2)
        self.assertEqual({m['label'] for m in measures},{f['label'] for f in result['fills']})
        paths=[p for m in measures for p in m['source_cad_paths']]
        self.assertEqual(len(paths),len(set(paths)))
        duplicate=[dict(result['fills'][0]),dict(result['fills'][1])]
        duplicate[1]['source_paths']=duplicate[0]['source_paths']
        with self.assertRaisesRegex(ValueError,'multiple owners'):
            filled_regions(other,result['view_bounds_pt'],duplicate,{'points_per_foot':10})

    def test_unlabeled_same_color_in_view_is_not_silently_included(self):
        page=self.doc[1]
        self.region(page,[200,200,400,450],(1,0,1),'HEATED')
        self.region(page,[550,200,750,450],(0,1,0),'GARAGE')
        self.region(page,[460,200,480,220],(1,0,1))
        with self.assertRaisesRegex(ValueError,'Unlabeled same-color'):discover_view(page)

    def pattern(self,offset=(100,200),ratio=(.5,.5),reference=True):
        lines=[[(30+i*7,40+i*35),(400-i*3,40+i*35)] for i in range(11)]
        lines += [[(45+i*35,80+i*5),(45+i*35,450-i*7)] for i in range(11)]
        for a,b in lines:
            if reference:self.doc[0].draw_line(a,b)
            self.doc[1].draw_line(tuple(v*r+t for v,r,t in zip(a,ratio,offset)),tuple(v*r+t for v,r,t in zip(b,ratio,offset)))
        self.cal={'points_per_foot':18,'usable_candidate':True,'controls':[{'axis':'horizontal'},{'axis':'vertical'}]}

    def registration(self):
        return automatic_registration(self.doc[0],self.doc[1],self.cal,[0,0,500,500],[0,0,1000,1000])

    def test_registration_discovers_both_anchors_from_native_lines(self):
        self.pattern();result=self.registration()
        self.assertAlmostEqual(result['points_per_foot'],9)
        self.assertEqual(len(result['matched_segments']),22)
        self.assertEqual(len(result['discovered_anchors']),2)
        self.assertFalse(result['certified'])

    def test_duplicate_views_are_ambiguous(self):
        self.pattern();self.pattern(offset=(500,600),reference=False)
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.registration()

    def test_nonuniform_scale_is_rejected(self):
        self.pattern(ratio=(.5,.6))
        with self.assertRaises(ValueError):self.registration()

    def test_uncalibrated_source_is_rejected(self):
        self.pattern()
        self.cal['usable_candidate']=False
        with self.assertRaises(ValueError):self.registration()


if __name__=='__main__':unittest.main()
