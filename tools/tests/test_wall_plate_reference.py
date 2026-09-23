import copy
import unittest
from wall_plate_reference import calculate,import_reference,opening_references


class WallPlateReference(unittest.TestCase):
    def setUp(self):
        self.runs={'plan_sha256':'drawing','measurement_version':1,'run_candidates':[
            {'id':'wall','page':1,'points_per_foot':10,'source_measurement_ids':['a','b','c'],
                'visible_intervals_pt':[[0,100],[50,150],[200,250]],'visible_union_lf':999,
                'gaps':[{'from_pt':150,'to_pt':200}]}],
            'unresolved_measurements':[{'measurement_id':'uncertain'}],'excluded_measurements':[]}
        self.decisions={'settings':{'framing.top_plates':2,'framing.bottom_plates':1},
            'provenance':{'framing.top_plates':{'basis':'company_default'},'framing.bottom_plates':{'basis':'company_default'}}}

    def test_union_avoids_overlap_and_keeps_gaps_outside_partial_allowance(self):
        r=calculate(self.runs,self.decisions)
        self.assertEqual((r['visible_wall_lf'],r['top_plate_reference_lf'],r['bottom_plate_reference_lf']),(20,40,20))
        self.assertEqual(r['unassigned_gap_count'],1)
        self.assertEqual(r['unresolved_measurements'],self.runs['unresolved_measurements'])
        self.assertIsNone(r['complete_wall_plate_quantity']);self.assertIsNone(r['purchase_quantity'])
        self.assertFalse(r['certified'])

    def test_absent_geometry_or_practice_is_unknown_but_explicit_zero_is_zero(self):
        del self.decisions['settings']['framing.top_plates']
        r=calculate(self.runs,self.decisions)
        self.assertIsNone(r['top_plate_reference_lf']);self.assertEqual(r['bottom_plate_reference_lf'],20)
        self.decisions['settings']['framing.top_plates']=0
        self.assertEqual(calculate(self.runs,self.decisions)['top_plate_reference_lf'],0)
        self.runs['run_candidates']=[]
        self.assertIsNone(calculate(self.runs,self.decisions)['bottom_plate_reference_lf'])

    def test_scale_and_course_change_recalculate_without_rounding_to_stock(self):
        self.runs['run_candidates'][0]['points_per_foot']=12
        self.decisions['settings']['framing.top_plates']=3
        result=calculate(self.runs,self.decisions)
        self.assertAlmostEqual(result['top_plate_reference_lf'],50)
        self.assertAlmostEqual(result['bottom_plate_reference_lf'],200/12)

    def test_invalid_counts_scale_and_duplicate_runs_reject(self):
        for value in (True,-1,2.5):
            d=copy.deepcopy(self.decisions);d['settings']['framing.top_plates']=value
            with self.assertRaises(ValueError):calculate(self.runs,d)
        for scale in (0,True,float('nan')):
            r=copy.deepcopy(self.runs);r['run_candidates'][0]['points_per_foot']=scale
            with self.assertRaises(ValueError):calculate(r,self.decisions)
        self.runs['run_candidates']*=2
        with self.assertRaises(ValueError):calculate(self.runs,self.decisions)

    def test_import_is_partial_unpriced_and_cannot_repeat_or_cross_revisions(self):
        reference=calculate(self.runs,self.decisions);reference['source_sha256']='source'
        row={'name':'Framing Lumber','parent':'Framing','cost_type':'MATERIAL','excel_row':'100',
            'draft_quantity':None,'line_cost':None,'completion_status':'pending','assembly_inputs':[]}
        draft={'plan_sha256':'drawing','measurement_version':1,'rows':[row]}
        result=import_reference(draft,reference)
        self.assertEqual([i['quantity'] for i in result['rows'][0]['assembly_inputs']],[40,20])
        self.assertIsNone(result['rows'][0]['draft_quantity']);self.assertIsNone(result['rows'][0]['line_cost'])
        self.assertEqual(draft['rows'][0]['assembly_inputs'],[])
        with self.assertRaises(ValueError):import_reference(result,reference)
        with self.assertRaises(ValueError):import_reference({**draft,'measurement_version':2},reference)
        row['draft_quantity']=1
        with self.assertRaises(ValueError):import_reference(draft,reference)


class OpeningPlateReference(unittest.TestCase):
    def setUp(self):
        self.runs={'plan_sha256':'drawing','measurement_version':1,'run_candidates':[
            {'id':'wall','page':1,'axis':'horizontal','points_per_foot':10,
             'centerline_coordinate_range_pt':[5,5],
             'gaps':[{'from_pt':a,'to_pt':b} for a,b in ((10,45),(60,100),(110,140),(150,190))]}]}
        self.schedule={'plan_sha256':'drawing','measurement_version':1,'stale_or_missing_label_ids':[],
            'openings':[{'opening_id':str(i),'run_id':'wall','page':1,'points_per_foot':10,
                'gap_id':'wall:gap-'+str(i),'points':[[a,5],[b,5]],'role':role,
                'review_status':status,'source_sha256':'source','role_source':'source drawing',
                'drawn_gap_width_inches':999,'printed_nominal_size':{'width_inches':999}}
                for i,(a,b,role,status) in enumerate(((10,45,'window','current_source_review'),
                    (60,100,'interior_door','current_source_review'),(110,140,'open_passage','current_source_review'),
                    (150,190,'window','stale_source_review')),1)]}
        self.counts={'top':2,'bottom':1}

    def test_drawn_spans_include_top_at_doors_but_bottom_only_under_windows(self):
        r=opening_references(self.runs,self.schedule,self.counts)
        self.assertEqual((r['top_plate_reference_lf'],r['bottom_plate_reference_lf']),(15,3.5))
        self.assertEqual([i['bottom_plate_reference_lf'] for i in r['openings']],[3.5,0])
        self.assertEqual(len(r['pending_openings']),2);self.assertEqual(r['remaining_gap_count'],2)

    def test_duplicate_opening_and_gap_ownership_rejected(self):
        for duplicate_id in (True,False):
            s=copy.deepcopy(self.schedule);extra=copy.deepcopy(s['openings'][0])
            if not duplicate_id:extra['opening_id']='other'
            s['openings'].append(extra)
            with self.assertRaises(ValueError):opening_references(self.runs,s,self.counts)

    def test_different_source_scale_page_and_endpoints_rejected(self):
        for key,value in (('plan_sha256','other'),('measurement_version',2)):
            s={**self.schedule,key:value}
            with self.assertRaises(ValueError):opening_references(self.runs,s,self.counts)
        for key,value in (('points_per_foot',20),('page',2),('run_id','missing'),('gap_id','wall:gap-3'),
                ('points',[[10,6],[45,6]]),('points',[[10,5],[44,5]]),('points',[[10,5],[float('nan'),5]])):
            s=copy.deepcopy(self.schedule);s['openings'][0][key]=value
            with self.assertRaises(ValueError):opening_references(self.runs,s,self.counts)

    def test_no_reviewed_openings_and_unknown_practice_do_not_become_zero(self):
        self.counts['top']=None
        self.assertIsNone(opening_references(self.runs,self.schedule,self.counts)['top_plate_reference_lf'])
        self.counts['top']=0
        self.assertEqual(opening_references(self.runs,self.schedule,self.counts)['top_plate_reference_lf'],0)
        self.schedule['openings']=[]
        self.assertIsNone(opening_references(self.runs,self.schedule,self.counts)['bottom_plate_reference_lf'])

    def test_import_preserves_visible_lengths_and_adds_separate_unpriced_opening_inputs(self):
        reference={'plan_sha256':'drawing','measurement_version':1,'source_sha256':'source',
            'top_plate_reference_lf':40,'bottom_plate_reference_lf':20,'visible_wall_lf':20,
            'basis':'visible only','remaining':['junctions and stock cuts'],'unassigned_gap_count':4,'unresolved_measurements':[],
            'opening_plate_reference':opening_references(self.runs,self.schedule,self.counts)}
        draft={'plan_sha256':'drawing','measurement_version':1,'rows':[{'name':'Framing Lumber','parent':'Framing',
            'cost_type':'MATERIAL','excel_row':'100','draft_quantity':None,'line_cost':None,'completion_status':'pending'}]}
        row=import_reference(draft,reference)['rows'][0]
        self.assertEqual([a['quantity'] for a in row['assembly_inputs']],[40,20,15,3.5])
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
