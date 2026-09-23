import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wall_gap_labels import page_labels,match_labels,from_plan_state
from wall_run_candidates import from_state
from test_wall_run_candidates import line,state


class WallGapLabels(unittest.TestCase):
    def setUp(self):
        self.state=state(line('left',[10,100],[100,100],ppf=12),line('right',[150,100],[200,100],ppf=12))
        self.label={'id':'tag','page':1,'axis':'horizontal','text':'3068','bbox_pt':[120,99,130,101]}

    def test_unique_tag_then_saved_point_closes_matching_space(self):
        before=match_labels(from_state(self.state),[self.label])
        self.assertEqual(before['gaps'][0]['status'],'unique_tag_location_candidate')
        revised=copy.deepcopy(self.state);revised['version']=2
        revised['measurements']['left']['points'][1][0]=140
        after=match_labels(from_state(revised),[self.label])
        self.assertEqual(after['gaps'][0]['status'],'no_aligned_tag')
        self.assertEqual(after['unmatched_label_ids'],['tag'])
        self.assertNotEqual(before['measurement_inputs_sha256'],after['measurement_inputs_sha256'])
        self.assertIsNone(after['purchase_quantity'])

    def test_multiple_tags_and_shared_tag_are_explicit(self):
        runs=from_state(self.state)
        result=match_labels(runs,[self.label,{**self.label,'id':'another'}])
        self.assertEqual(result['gaps'][0]['status'],'multiple_tags_require_review')
        runs['run_candidates'].append({**runs['run_candidates'][0],'id':'parallel'})
        result=match_labels(runs,[self.label])
        self.assertEqual(result['shared_label_ids'],['tag'])
        self.assertTrue(all(g['status']=='tag_shared_by_multiple_gaps' for g in result['gaps']))

    def test_page_axis_and_distance_gate_matching(self):
        for changes in ({'page':2},{'axis':'vertical'},{'axis':None},{'bbox_pt':[120,104,130,106]}):
            result=match_labels(from_state(self.state),[{**self.label,**changes}])
            self.assertEqual(result['gaps'][0]['status'],'no_aligned_tag')

    def test_real_pdf_preserves_tags_and_rejects_another_source(self):
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.pdf'
            with fitz.open() as doc:
                p=doc.new_page(width=400,height=400)
                p.insert_text((110,103),'3068',fontsize=8)
                p.insert_text((250,150),'6062MU',fontsize=8,rotate=90)
                p.insert_text((20,200),'ROOM',fontsize=8)
                p.insert_text((20,230),'123',fontsize=8)
                doc.save(plan)
            self.state['plan_sha256']=hashlib.sha256(plan.read_bytes()).hexdigest()
            result=from_plan_state(plan,self.state)
            self.assertEqual({label['text'] for label in result['labels']},{'3068','6062MU'})
            self.assertEqual(result['gaps'][0]['status'],'unique_tag_location_candidate')
            self.assertFalse(result['certified'])
            # A page containing only short pieces still needs its source tags.
            from test_wall_short_piece_directions import square
            short_state=state(square('a',100,98.25),square('b',150,98.25))
            short_state['plan_sha256']=self.state['plan_sha256']
            assisted=from_plan_state(plan,short_state)
            self.assertEqual(assisted['gaps'],[])
            self.assertEqual(len(assisted['direction_assisted']['gaps']),1)
            self.assertEqual(assisted['direction_assisted']['gaps'][0]['status'],'unique_tag_location_candidate')
            self.assertEqual(assisted['direction_assisted']['measurement_inputs_sha256'],assisted['measurement_inputs_sha256'])
            self.assertTrue(all(m['kind']=='area' for m in short_state['measurements'].values()))
            self.state['plan_sha256']='another-source'
            with self.assertRaisesRegex(ValueError,'source drawing'):from_plan_state(plan,self.state)


if __name__=='__main__':unittest.main()
