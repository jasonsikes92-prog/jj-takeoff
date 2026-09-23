import copy
import unittest
from test_wall_run_candidates import line,state
from wall_run_candidates import from_state
from wall_gap_labels import match_labels
from wall_alignment_breaks import apply_review,source_binding


class AlignmentBreaks(unittest.TestCase):
    def setUp(self):
        self.state=state(line('a',[0,100],[10,100]),line('b',[20,100],[30,100]),line('c',[40,100],[50,100]))
        self.runs=from_state(self.state)
        self.gaps=match_labels(self.runs,[])
        gap=self.gaps['gaps'][0]
        self.review={'plan_sha256':self.state['plan_sha256'],'reviewer':'Source reviewer',
            'breaks':[{'gap_id':gap['id'],'source_sha256':source_binding(self.state,self.runs['run_candidates'][0],gap),
                'basis':'Drawing shows separate walls across open space'}]}

    def test_break_splits_alignment_without_adding_gap_length_or_duplicating_pieces(self):
        result=apply_review(self.state,self.runs,self.gaps,self.review)
        sections=result['candidate_sections']
        self.assertEqual([s['source_measurement_ids'] for s in sections],[['a'],['b','c']])
        self.assertEqual([s['interval_pt'] for s in sections],[[0,10],[20,50]])
        self.assertEqual(sum(s['visible_union_lf'] for s in sections),30)
        self.assertEqual([g['status'] for g in self.gaps['gaps']],['separate_wall_runs','no_aligned_tag'])
        self.assertEqual(len(sections[1]['unresolved_gap_ids']),1)
        self.assertIsNone(result['purchase_quantity']);self.assertFalse(result['certified'])

    def test_changed_geometry_withholds_review_and_restore_recovers_it(self):
        changed=copy.deepcopy(self.state);changed['measurements']['a']['points'][1][0]=11
        runs=from_state(changed);gaps=match_labels(runs,[])
        result=apply_review(changed,runs,gaps,self.review)
        self.assertFalse(result['decisions'][0]['current'])
        self.assertEqual(len(result['candidate_sections']),1)
        result=apply_review(self.state,self.runs,self.gaps,self.review)
        self.assertTrue(result['decisions'][0]['current'])

    def test_tagged_gap_cannot_be_silently_removed_by_a_break_review(self):
        labels=[{'id':'door','page':1,'axis':'horizontal','text':'3068','bbox_pt':[14,99,16,101]}]
        gaps=match_labels(self.runs,labels)
        r=copy.deepcopy(self.review)
        r['breaks'][0]['source_sha256']=source_binding(self.state,self.runs['run_candidates'][0],gaps['gaps'][0])
        result=apply_review(self.state,self.runs,gaps,r)
        self.assertFalse(result['decisions'][0]['current'])
        self.assertEqual(gaps['gaps'][0]['status'],'unique_tag_location_candidate')

    def test_missing_gap_stays_visible_as_stale_and_bad_review_is_rejected(self):
        r=copy.deepcopy(self.review);r['breaks'][0]['gap_id']='old-gap'
        self.assertFalse(apply_review(self.state,self.runs,self.gaps,r)['decisions'][0]['current'])
        for key in ('plan','duplicate','basis','reviewer'):
            r=copy.deepcopy(self.review)
            if key=='plan':r['plan_sha256']='another'
            elif key=='duplicate':r['breaks'].append(r['breaks'][0])
            elif key=='basis':r['breaks'][0]['basis']=''
            else:r['reviewer']=''
            with self.assertRaises(ValueError):apply_review(self.state,self.runs,self.gaps,r)

    def test_two_breaks_and_unreviewed_mode_keep_all_visible_material(self):
        r=copy.deepcopy(self.review);gap=self.gaps['gaps'][1]
        r['breaks'].append({'gap_id':gap['id'],'source_sha256':source_binding(self.state,self.runs['run_candidates'][0],gap),
            'basis':'Another separate wall'})
        unreviewed=apply_review(self.state,self.runs,copy.deepcopy(self.gaps),None)
        reviewed=apply_review(self.state,self.runs,self.gaps,r)
        self.assertEqual(len(unreviewed['candidate_sections']),1)
        self.assertEqual(len(reviewed['candidate_sections']),3)
        self.assertEqual(sum(s['visible_union_lf'] for s in reviewed['candidate_sections']),30)
        self.assertEqual(self.state['measurements']['a']['points'],[[0,100],[10,100]])


if __name__=='__main__':unittest.main()
