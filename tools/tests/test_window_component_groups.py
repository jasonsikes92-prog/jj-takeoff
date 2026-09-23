import unittest
from jnj_takeoff import window_count,window_trim_lf,window_cross_view_candidates


class Page:
    def __init__(self,words,number=0):self.words=words;self.number=number
    def get_text(self,mode):return self.words


class WindowComponents(unittest.TestCase):
    def words(self,scale=1,dx=0,dy=0):
        raw=[(90,0,110,6,'6044MU'),(63,6,83,12,'1644FX'),
             (90,6,110,12,'3044SH'),(117,6,137,12,'1644FX'),
             (300,60,320,66,'3062SH')]
        return [(x1*scale+dx,y1*scale+dy,x2*scale+dx,y2*scale+dy,t)
                for x1,y1,x2,y2,t in raw]

    def test_components_count_once_under_parent_at_different_page_scales(self):
        for scale in (0.5,1,3):
            count,rows=window_count(Page(self.words(scale,400,800)))
            self.assertEqual(count,4)
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['multiplier'],3)
            self.assertEqual(rows[0]['basis'],'dimension_matched_components')
            self.assertEqual(rows[0]['component_tags'],['1644FX','3044SH','1644FX'])

    def test_dimension_mismatch_does_not_suppress_separate_labels(self):
        words=self.words();words[2]=(*words[2][:4],'2044SH')
        count,rows=window_count(Page(words))
        self.assertEqual(len(rows),5)
        self.assertEqual(count,6)

    def test_trim_uses_parent_opening_once_not_component_perimeters(self):
        total,rows=window_trim_lf(Page(self.words()))
        self.assertEqual(total,39)
        self.assertEqual([r['tag'] for r in rows],['6044MU','3062SH'])

    def test_double_label_does_not_multiply_a_single_window(self):
        page=Page([(0,0,20,6,'3062SH'),(0,7,20,13,'DOUBLE')])
        self.assertEqual(window_count(page)[0],1)

    def test_shared_component_labels_reject_ambiguous_parent_assignment(self):
        words=self.words();words.append((90,-1,110,5,'6044MU'))
        with self.assertRaisesRegex(ValueError,'multiple assemblies'):
            window_count(Page(words))

    def test_exact_overprinted_tags_count_once_but_distinct_positions_remain(self):
        word=(0,0,20,6,'3050FX')
        self.assertEqual(window_count(Page([word,word]))[0],1)
        self.assertEqual(window_count(Page([word,(40,0,60,6,'3050FX')]))[0],2)

    def test_cross_view_candidates_do_not_assume_size_is_physical_identity(self):
        floor=Page(self.words())
        gable=(150,0,170,6,'3050FX')
        elevation=Page(self.words()+[gable,gable],8)
        result=window_cross_view_candidates([floor],[elevation])
        self.assertEqual(len(result['unrepresented_elevation_tags']),1)
        self.assertEqual(result['unrepresented_elevation_tags'][0]['page'],9)
        self.assertEqual(result['unrepresented_elevation_tags'][0]['tag'],'3050FX')
        self.assertIsNone(result['whole_building_count'])
        self.assertFalse(result['certified'])
        other=Page([gable],9)
        self.assertEqual(len(window_cross_view_candidates([floor],[elevation,other])['unrepresented_elevation_tags']),2)


if __name__=='__main__':unittest.main()
