import sys
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vector_symbol_frames import rectangle_frames,corroborate_frames


class VectorFrames(unittest.TestCase):
    def test_closed_frames_and_rotated_frames_exclude_open_edges_and_circles(self):
        with fitz.open() as doc:
            p=doc.new_page(width=300,height=200)
            p.draw_rect((10,10,30,50),color=(1,0,0))
            p.draw_rect((100,90,120,130),color=(1,0,0))
            p.draw_rect((160,100,200,120),color=(1,0,0))
            p.draw_line((230,90),(230,130),color=(1,0,0))
            p.draw_line((230,90),(250,90),color=(1,0,0))
            p.draw_line((250,90),(250,130),color=(1,0,0))
            p.draw_circle((60,110),10,color=(1,0,0))
            frames=rectangle_frames(p,'red');self.assertEqual(len(frames),3)
            candidates=[{'point_pt':[110,110],'bbox_pt':[94,84,126,136],'rotation_degrees':0},
                        {'point_pt':[180,110],'bbox_pt':[154,94,206,126],'rotation_degrees':90},
                        {'point_pt':[240,110],'bbox_pt':[224,84,256,136],'rotation_degrees':0},
                        {'point_pt':[60,110],'bbox_pt':[44,84,76,136],'rotation_degrees':0}]
            kept,rejected,ref=corroborate_frames(candidates,frames,[5,5,35,55])
            self.assertEqual(len(kept),2);self.assertEqual(len(rejected),2)
            self.assertEqual(ref['bbox_pt'],[10,10,30,50])
            self.assertTrue(all(c['vector_frame']['path_sequence_numbers'] for c in kept))

    def test_missing_legend_frame_requires_another_method(self):
        with self.assertRaisesRegex(ValueError,'No closed vector rectangle'):
            corroborate_frames([],[],[5,5,35,55])

    def test_multiple_matching_frames_are_not_silently_assigned(self):
        frames=[{'bbox_pt':[10,10,30,50]}, {'bbox_pt':[100,90,120,130]}, {'bbox_pt':[101,92,119,128]}]
        candidates=[{'point_pt':[110,110],'bbox_pt':[94,84,126,136],'rotation_degrees':0}]
        kept,rejected,_=corroborate_frames(candidates,frames,[5,5,35,55])
        self.assertEqual(kept,[]);self.assertEqual(len(rejected),1)


if __name__=='__main__':unittest.main()
