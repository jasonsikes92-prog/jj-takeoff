import copy
import math
import hashlib
import tempfile
import unittest
from pathlib import Path
import fitz
from diagonal_wall_analysis import from_state
from wall_classification_review import source_digest
from test_wall_run_candidates import line,state


def point(along,across=0):
    return [(along-across)/math.sqrt(2),(along+across)/math.sqrt(2)]


def piece(identity,start,end,across=0,**changes):
    return {**line(identity,point(start,across),point(end,across),ppf=12),
        'source_method':'native_parallel_diagonal_wall_strokes_v1',
        'drawn_thickness_inches':3.5,**changes}


def review(s):
    return {'plan_sha256':s['plan_sha256'],'reviewer':'test source review','decisions':[
        {'measurement_id':m['id'],'source_sha256':source_digest(m),'decision':'wall_faces',
         'basis':'Reviewed wall faces in test fixture'} for m in s['measurements'].values()]}


def tag(identity='tag',along=125,across=0):
    x,y=point(along,across)
    return {'id':identity,'page':1,'text':'3068','axis':None,
        'direction':[1/math.sqrt(2),1/math.sqrt(2)],'bbox_pt':[x-1,y-1,x+1,y+1]}


class DiagonalWallAnalysis(unittest.TestCase):
    def setUp(self):
        self.s=state(piece('left',0,100),piece('right',150,200))

    def test_review_required_and_stale_geometry_rejected(self):
        self.assertEqual(from_state(self.s,[tag()])['run_candidates'],[])
        r=review(self.s)
        edited=copy.deepcopy(self.s);edited['measurements']['left']['points'][1]=point(110)
        result=from_state(edited,[tag()],r)
        self.assertEqual(len(result['unresolved_measurements']),1)
        self.assertEqual(result['gaps'],[])

    def test_projected_gap_length_and_tag_preserve_original_coordinates(self):
        original=copy.deepcopy(self.s)
        result=from_state(self.s,[tag()],review(self.s))
        run=result['run_candidates'][0];gap=result['gaps'][0]
        self.assertAlmostEqual(run['visible_union_lf'],150/12)
        self.assertAlmostEqual(gap['drawn_gap_lf'],50/12)
        self.assertEqual(gap['candidate_label_ids'],['tag'])
        self.assertEqual(gap['status'],'tag_location_requires_junction_review')
        for actual,expected in zip(gap['points_pt'],[point(100),point(150)]):
            self.assertAlmostEqual(math.dist(actual,expected),0)
        self.assertIsNone(result['purchase_quantity']);self.assertFalse(result['certified'])
        self.assertEqual(self.s,original)

    def test_overlap_is_unioned_and_reversed_lines_are_deterministic(self):
        self.s['measurements']['overlap']=piece('overlap',80,120)
        first=from_state(self.s,[],review(self.s))
        reverse=copy.deepcopy(self.s)
        for m in reverse['measurements'].values():m['points'].reverse()
        other=from_state(reverse,[],review(reverse))
        self.assertEqual(first['run_candidates'],other['run_candidates'])
        self.assertAlmostEqual(first['run_candidates'][0]['overlapping_piece_lf'],20/12)

    def test_oblique_crossing_uses_current_polygon_not_axis_aligned_bounds(self):
        cross=piece('cross',125,125)
        cross['points']=[point(125,-10),point(125,10)]
        self.s['measurements']['cross']=cross
        result=from_state(self.s,[tag()],review(self.s))
        self.assertEqual(result['gaps'][0]['status'],'drawn_piece_obstructs_gap')
        self.assertEqual(result['gaps'][0]['obstructions'][0]['measurement_id'],'cross')
        cross['points']=[point(125,5),point(125,15)]
        result=from_state(self.s,[tag()],review(self.s))
        self.assertEqual(result['gaps'][0]['status'],'tag_location_requires_junction_review')

    def test_rotated_short_polygon_obstructs_but_has_no_invented_direction(self):
        self.s['measurements']['short']=piece('short',120,130,kind='area',
            points=[point(120,-2),point(130,-2),point(130,2),point(120,2)])
        result=from_state(self.s,[tag()],review(self.s))
        self.assertEqual(result['gaps'][0]['status'],'drawn_piece_obstructs_gap')
        self.assertEqual(result['unresolved_measurements'][0]['measurement_id'],'short')

    def test_missing_footprint_and_duplicate_tags_do_not_claim_clear_opening(self):
        self.s['measurements']['unknown']=piece('unknown',300,350,drawn_thickness_inches=None)
        result=from_state(self.s,[tag()],review(self.s))
        self.assertEqual(result['gaps'][0]['status'],'unassessed_wall_footprints')
        del self.s['measurements']['unknown']
        result=from_state(self.s,[tag(),tag('second')],review(self.s))
        self.assertEqual(result['gaps'][0]['status'],'multiple_tags_require_review')

    def test_page_scale_direction_and_tag_offset_separate(self):
        for changes in ({'page':2},{'direction':[1,0]},{'bbox_pt':[0,0,2,2]}):
            result=from_state(self.s,[{**tag(),**changes}],review(self.s))
            self.assertEqual(result['gaps'][0]['candidate_label_ids'],[])
        for changes in ({'page':2},{'points_per_foot':24}):
            other=copy.deepcopy(self.s);other['measurements']['right'].update(changes)
            self.assertEqual(from_state(other,[],review(other))['gaps'],[])

    def test_alignment_does_not_chain_and_shared_tag_is_not_unique(self):
        for name,offset in [('a',.2),('b',.4)]:
            self.s['measurements'][name+'left']=piece(name+'left',0,100,offset)
            self.s['measurements'][name+'right']=piece(name+'right',150,200,offset)
        result=from_state(self.s,[tag()],review(self.s))
        self.assertEqual(len(result['run_candidates']),2)
        self.assertEqual(result['shared_label_ids'],['tag'])
        self.assertTrue(all(g['status']=='tag_shared_by_multiple_gaps' for g in result['gaps']))

    def test_explicit_nonwall_does_not_obstruct(self):
        self.s['measurements']['symbol']=piece('symbol',120,130)
        r=review(self.s);r['decisions'][-1]['decision']='not_wall_faces'
        result=from_state(self.s,[tag()],r)
        self.assertEqual(result['gaps'][0]['status'],'tag_location_requires_junction_review')

    def test_diagonal_only_pdf_page_keeps_text_direction_and_runs_analysis(self):
        from wall_gap_labels import from_plan_state,page_labels
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'plan.pdf'
            with fitz.open() as doc:
                page=doc.new_page(width=400,height=400)
                origin=fitz.Point(200,200)
                page.insert_text(origin,'3068',fontsize=8,morph=(origin,fitz.Matrix(-45)))
                doc.save(path)
            with fitz.open(path) as doc:label=page_labels(doc[0])[0]
            self.assertIsNone(label['axis'])
            u=label['direction'];bounds=label['bbox_pt']
            center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]
            for name,start,end in [('left',-100,-25),('right',25,100)]:
                self.s['measurements'][name]['points']=[
                    [center[k]+distance*u[k] for k in (0,1)] for distance in (start,end)]
            self.s['plan_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            result=from_plan_state(path,self.s,review(self.s))
            self.assertEqual(result['gaps'],[])
            self.assertEqual(result['diagonal_analysis']['gaps'][0]['candidate_label_ids'],[label['id']])
            self.assertEqual(result['diagonal_analysis']['gaps'][0]['status'],'tag_location_requires_junction_review')

    def junction_state(self):
        return state(piece('left',0,100),piece('right',103.5,200),
            piece('branch',0,1,points=[point(101.75,1.75),point(101.75,35)]))

    def test_reviewed_branch_end_covers_diagonal_junction_not_opening(self):
        s=self.junction_state();result=from_state(s,[],review(s));gap=result['gaps'][0]
        self.assertEqual(gap['status'],'wall_junction_candidate')
        self.assertTrue(gap['junction_review']['covers_gap'])
        self.assertEqual(gap['junction_review']['contacts'][0]['measurement_id'],'branch')
        result=from_state(s,[tag(along=101.75)],review(s))
        self.assertEqual(result['gaps'][0]['status'],'junction_tag_conflict')
        self.assertIsNone(result['purchase_quantity'])

    def test_partial_contact_does_not_close_gap(self):
        s=self.junction_state();s['measurements']['right']['points'][0]=point(108)
        gap=from_state(s,[tag(along=105)],review(s))['gaps'][0]
        self.assertFalse(gap['junction_review']['covers_gap'])
        self.assertEqual(gap['status'],'partial_wall_contact_requires_review')

    def test_stale_or_unreviewed_branch_does_not_establish_junction(self):
        s=self.junction_state();r=review(s)
        r['decisions']=[d for d in r['decisions'] if d['measurement_id']!='branch']
        self.assertEqual(from_state(s,[],r)['gaps'][0]['junction_review']['contacts'],[])
        r=review(s);s['measurements']['branch']['points'][1]=point(101.75,40)
        self.assertEqual(from_state(s,[],r)['gaps'][0]['junction_review']['contacts'],[])

    def test_nearby_branch_gap_or_inconsistent_host_faces_are_not_junction(self):
        s=self.junction_state();s['measurements']['branch']['points'][0]=point(101.75,3)
        self.assertEqual(from_state(s,[],review(s))['gaps'][0]['junction_review']['contacts'],[])
        s=self.junction_state();s['measurements']['right']['drawn_thickness_inches']=5.5
        self.assertEqual(from_state(s,[],review(s))['gaps'][0]['junction_review']['contacts'],[])

    def test_opposite_side_and_reversed_branch_are_recognized(self):
        s=self.junction_state()
        s['measurements']['branch']['points']=[point(101.75,-35),point(101.75,-1.75)]
        gap=from_state(s,[],review(s))['gaps'][0]
        self.assertEqual(gap['status'],'wall_junction_candidate')
        self.assertEqual(gap['junction_review']['contacts'][0]['host_face'],'lower')

    def test_offset_branches_cover_together_but_internal_hole_stays_open(self):
        s=self.junction_state();s['measurements']['right']['points'][0]=point(107)
        s['measurements']['opposite']=piece('opposite',0,1,
            points=[point(105.25,-1.75),point(105.25,-35)])
        gap=from_state(s,[],review(s))['gaps'][0]
        self.assertEqual(gap['status'],'wall_junction_candidate')
        self.assertEqual(len(gap['junction_review']['contacts']),2)
        s['measurements']['right']['points'][0]=point(108)
        s['measurements']['opposite']['points']=[point(106.25,-1.75),point(106.25,-35)]
        gap=from_state(s,[],review(s))['gaps'][0]
        self.assertFalse(gap['junction_review']['covers_gap'])
        self.assertEqual(gap['status'],'partial_wall_contact_requires_review')

    def test_branch_crossing_host_is_obstruction_not_end_contact(self):
        s=self.junction_state();s['measurements']['branch']['points'][0]=point(101.75,-10)
        gap=from_state(s,[],review(s))['gaps'][0]
        self.assertEqual(gap['status'],'drawn_piece_obstructs_gap')
        self.assertFalse(gap['junction_review']['covers_gap'])


if __name__=='__main__':unittest.main()
