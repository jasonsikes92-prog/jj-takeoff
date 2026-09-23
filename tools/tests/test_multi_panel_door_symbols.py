"""Paired-symbol evidence must not infer products or count incomplete drawings."""
import copy
import hashlib
import math
from pathlib import Path
import tempfile
import unittest
import fitz
from door_symbol_candidates import recognize,from_plan


def fixture(kind,rotation=0,reflection=1,scale=12,width=60):
    def point(p):
        x,y=p[0]*scale/12,p[1]*reflection*scale/12
        return [100+x*math.cos(rotation)-y*math.sin(rotation),200+x*math.sin(rotation)+y*math.cos(rotation)]
    drawings=[]
    def path(points):
        ps=[point(p) for p in points]
        drawings.append({'type':'s','color':(0,0,0),'stroke_opacity':1,'dashes':'[] 0',
            'items':[('l',a,b) for a,b in zip(ps,ps[1:])]})
    if kind=='double_hinged':
        for hinge,direction in ((0,1),(width,-1)):
            arc=[[hinge+direction*width/2*math.cos(i*math.pi/72),width/2*math.sin(i*math.pi/72)] for i in range(11)]
            path(arc);path([[hinge,0],arc[-1]])
    else:
        path([[0,0],[31,0],[31,1.5],[0,1.5],[0,0]])
        path([[15,1.75],[46,1.75],[46,3.25],[15,3.25],[15,1.75]])
        path([[0,-.5],[0,3.5]]);path([[60,-.5],[60,3.5]])
    return {'opening_id':'door','page':1,'tag':f'{width//12}{width%12}68','points':[point([0,0]),point([width,0])],
        'points_per_foot':scale,'source_sha256':'opening-source','review_status':'role_unreviewed',
        'printed_nominal_size':{'width_inches':width,'height_inches':80,'type_code':None}},drawings


class MultiPanelSymbols(unittest.TestCase):
    def candidate(self,o,ds):return recognize([o],{1:ds},'plan')['candidates']

    def test_narrow_paired_swings_are_not_mistaken_for_a_bifold(self):
        from opening_schedule import withhold_symbol_conflicts
        for width in (24,30,36,42,48,96):
            o,ds=fixture('double_hinged',rotation=.4,scale=18,width=width)
            c,=self.candidate(o,ds);self.assertEqual(c['configuration_candidate'],'double_hinged')
            o.update(review_status='current_source_review',role='special_interior_door',door_configuration='double_hinged',drawn_panel_count=2)
            self.assertEqual(self.candidate(o,ds)[0]['status'],'corroborates_review')
            o['door_configuration']='bifold'
            symbols=recognize([o],{1:ds},'plan')
            self.assertEqual(symbols['candidates'][0]['status'],'conflicts_with_review')
            result=withhold_symbol_conflicts({'openings':[o],'door_symbol_candidates':symbols,
                'unresolved_opening_ids':[],'reviewed_role_counts':{'special_interior_door':1}})
            self.assertIsNone(result['openings'][0]['role'])
            self.assertEqual(result['openings'][0]['conflicting_source_review']['door_configuration'],'bifold')

    def test_rotation_reflection_and_scale_preserve_two_panel_candidate_only(self):
        for kind in ('double_hinged','sliding_pair'):
            for rotation in (0,.8,math.pi,4.7):
                for reflection in (-1,1):
                    for scale in (6,18,36):
                        o,ds=fixture(kind,rotation,reflection,scale)
                        c,=self.candidate(o,ds)
                        self.assertEqual(c['configuration_candidate'],kind)
                        self.assertEqual(c['drawn_panel_count_candidate'],2)
                        self.assertFalse(c['role_confirmed']);self.assertFalse(c['purchase_released'])

    def test_missing_leaf_arc_panel_cap_or_outer_jamb_prevents_candidate(self):
        for kind in ('double_hinged','sliding_pair'):
            o,ds=fixture(kind)
            for index in range(len(ds)):
                self.assertEqual(self.candidate(o,ds[:index]+ds[index+1:]),[],(kind,index))
        o,ds=fixture('sliding_pair');ds[0]['items']=ds[0]['items'][:-1]
        self.assertEqual(self.candidate(o,ds),[])

    def test_duplicate_geometry_is_one_candidate_but_competing_swings_are_ambiguous(self):
        for kind in ('double_hinged','sliding_pair'):
            o,ds=fixture(kind)
            c,=self.candidate(o,ds+copy.deepcopy(ds));self.assertEqual(len(c['matches']),1)
        o,ds=fixture('double_hinged');_,other=fixture('double_hinged',reflection=-1)
        c,=self.candidate(o,ds+other)
        self.assertEqual(c['status'],'ambiguous_symbols');self.assertIsNone(c['configuration_candidate'])

    def test_opposite_swing_sides_and_nonmeeting_arcs_do_not_make_double_door(self):
        o,ds=fixture('double_hinged');_,other=fixture('double_hinged',reflection=-1)
        self.assertEqual(self.candidate(o,ds[:2]+other[2:]),[])
        o,ds=fixture('double_hinged')
        # Shift one full leaf/swing one inch: each half matches its local tolerance,
        # but the two closed swing tips no longer meet.
        for drawing in ds[2:]:
            drawing['items']=[('l',[a[0]+1,a[1]],[b[0]+1,b[1]]) for _,a,b in drawing['items']]
        self.assertEqual(self.candidate(o,ds),[])

    def test_parallel_nonoverlapping_panels_and_no_jamb_anchor_are_rejected(self):
        for shift in (25,-20):
            o,ds=fixture('sliding_pair')
            ds[1]['items']=[('l',[a[0]+shift,a[1]],[b[0]+shift,b[1]]) for _,a,b in ds[1]['items']]
            self.assertEqual(self.candidate(o,ds),[])
        o,ds=fixture('sliding_pair')
        for drawing in ds[:2]:
            drawing['items']=[('l',[a[0]+5,a[1]],[b[0]+5,b[1]]) for _,a,b in drawing['items']]
        self.assertEqual(self.candidate(o,ds),[])

    def test_hidden_dashed_white_wrong_tag_size_page_and_gap_are_rejected(self):
        for kind in ('double_hinged','sliding_pair'):
            for changes in ({'type':'f'},{'stroke_opacity':0},{'color':(1,1,1)},{'dashes':'[3 2] 0'}):
                o,ds=fixture(kind)
                self.assertEqual(self.candidate(o,[{**d,**changes} for d in ds]),[])
            for issue in ('tag','width','gap','page'):
                o,ds=fixture(kind)
                if issue=='tag':o['printed_nominal_size']['type_code']='SH'
                elif issue=='width':o['printed_nominal_size']['width_inches']=72
                elif issue=='gap':o['points'][1][0]+=5
                else:o['page']=2
                self.assertEqual(self.candidate(o,ds),[])

    def test_reviewed_configurations_counts_conflicts_and_stale_status(self):
        for kind,role,configs in (('double_hinged','exterior_door',('double_hinged',)),
                                 ('sliding_pair','special_interior_door',('bypass','sliding'))):
            for config in configs:
                o,ds=fixture(kind);o.update(review_status='current_source_review',role=role,
                    door_configuration=config,drawn_panel_count=2)
                before=copy.deepcopy(o)
                self.assertEqual(self.candidate(o,ds)[0]['status'],'corroborates_review');self.assertEqual(o,before)
                o['drawn_panel_count']=1
                c,=self.candidate(o,ds);self.assertEqual(c['status'],'conflicts_with_review')
                self.assertIsNone(c['drawn_panel_count_candidate'])
                o.update(review_status='stale_source_review',role=None,door_configuration=None,drawn_panel_count=None)
                self.assertEqual(self.candidate(o,ds)[0]['status'],'stale_review_requires_reconciliation')

    def test_actual_pdfs_keep_evidence_bound_to_plan_and_gap(self):
        for kind in ('double_hinged','sliding_pair'):
            o,ds=fixture(kind)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'plan.pdf'
                with fitz.open() as doc:
                    page=doc.new_page()
                    for d in ds:
                        shape=page.new_shape()
                        for _,a,b in d['items']:shape.draw_line(a,b)
                        shape.finish(closePath=False);shape.commit()
                    doc.save(path)
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                c,=from_plan(path,[o],digest)['candidates']
                self.assertEqual(c['configuration_candidate'],kind)
                o['source_sha256']='changed'
                self.assertNotEqual(from_plan(path,[o],digest)['candidates'][0]['source_sha256'],c['source_sha256'])
                with self.assertRaises(ValueError):from_plan(path,[o],'old-plan')


if __name__=='__main__':unittest.main()
