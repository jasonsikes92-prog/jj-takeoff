import unittest
import fitz
from native_hatch_regions import area_drawings
from native_area_candidates import filled_regions


class NativeHatchRegions(unittest.TestCase):
    def setUp(self):
        self.doc=fitz.open();self.page=self.doc.new_page()
        self.addCleanup(self.doc.close)

    def backing(self):
        shape=self.page.new_shape()
        shape.draw_polyline([(20,20),(120,20),(120,120),(20,120),(20,20)])
        shape.finish(fill=(1,1,1),color=None);shape.commit()

    def hatch(self,ys,end=120):
        for y in ys:self.page.draw_line((20,y),(end,y),color=(1,0,0))

    def test_hatch_preserves_backing_geometry_and_records_source(self):
        self.backing();self.hatch(range(22,120,4))
        drawings=area_drawings(self.page)
        self.assertEqual(drawings[0]['fill'],(1,0,0))
        self.assertEqual(self.page.get_drawings()[0]['fill'],(1,1,1))
        measurements=filled_regions(self.page,[0,0,140,140],
            [{'fill':[1,0,0],'label':'Heated'}],{'points_per_foot':10})
        self.assertEqual(len(measurements),1)
        self.assertEqual(measurements[0]['source_cad_paths'],[0])
        self.assertEqual(len(measurements[0]['source_hatch_paths']),25)
        self.assertIn([20.,20.],measurements[0]['points'])

    def test_short_details_do_not_fill_a_large_backing(self):
        self.backing();self.hatch(range(22,120,4),end=35)
        self.assertNotIn('hatch_source_paths',area_drawings(self.page)[0])

    def test_crossing_outside_backing_is_rejected(self):
        self.backing();self.hatch(range(22,120,4),end=150)
        self.assertNotIn('hatch_source_paths',area_drawings(self.page)[0])

    def test_nonparallel_colored_linework_is_rejected(self):
        self.backing();self.hatch(range(22,120,4))
        self.page.draw_line((30,20),(30,120),color=(1,0,0))
        self.assertNotIn('hatch_source_paths',area_drawings(self.page)[0])
