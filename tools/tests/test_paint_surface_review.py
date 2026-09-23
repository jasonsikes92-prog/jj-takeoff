import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from paint_surface_review import calculate_review, checked_json, read_gross_rules, attach_references
from measurement_store import encode


class PaintSurfaceReview(unittest.TestCase):
    def setUp(self):
        room={'kind':'area','page':1,'points_per_foot':1,'width_pt':100,'height_pt':100,
              'points':[[10,10],[30,10],[30,30],[10,30]]}
        garage={**room,'points':[[40,10],[50,10],[50,20],[40,20]]}
        self.state={'plan_sha256':'plan','version':1,'measurements':{'room':room,'garage':garage}}
        terms=[]
        for identity in ('room','garage'):
            terms.extend([{'id':identity+'-walls','measurement_id':identity,'kind':'perimeter_wall',
                           'height_ft':9,'height_source':'plan','operation':'add'},
                          {'id':identity+'-ceiling','measurement_id':identity,'kind':'area','operation':'add'}])
        self.rules={'plan_sha256':'plan','rules':[{'id':'gross','surface_components':terms}]}
        self.config={'plan_sha256':'plan','gross_rule_id':'gross','garage_measurement_id':'garage',
                     'remaining':['Other finishes and paint specification']}
        self.finish_state={'plan_sha256':'plan','version':2,'measurements':{'shower':{
            **room,'points':[[10,10],[14,10],[14,15],[10,15]]}}}
        finish_rule={'id':'tile','measurement_ids':['shower'],'surface_components':[{
            'id':'tile-faces','kind':'rectangular_wall_faces','measurement_id':'shower','faces':['min_x','min_y'],
            'height_ft':9,'height_source':'owner','scope_source':'plan'}]}
        self.finish_rules={'plan_sha256':'plan','rules':[finish_rule]}
        self.mapping={'room_wall_component_id':'room-walls','finish_rule_id':'tile','tolerance_ft':0}

    def review(self):
        return calculate_review(self.state,self.rules,self.config,[(self.mapping,self.finish_state,self.finish_rules)])

    def test_live_independent_garage_edit_recalculates_without_price_or_order(self):
        before=self.review()
        self.state['version']=2
        self.state['measurements']['garage']['points']=[[40,10],[45,10],[45,15],[40,15]]
        after=self.review()
        self.assertEqual([r['quantity'] for r in before['gross_references']],[1120,460])
        self.assertEqual([r['quantity'] for r in after['gross_references']],[1120,205])
        self.assertNotEqual(before['geometry_sha256'],after['geometry_sha256'])
        self.assertEqual(after['measurement_version'],2)
        self.assertEqual(before['partial_finish_allocations'],after['partial_finish_allocations'])
        self.assertIsNone(after['final_paint_quantity'])
        self.assertIsNone(after['purchase_quantity'])
        self.assertFalse(after['paint_quantity_certified'])

    def test_finish_edit_recalculates_separate_version(self):
        before=self.review()
        self.finish_state['measurements']['shower']['points']=[[10,10],[16,10],[16,15],[10,15]]
        self.finish_state['version']=3
        after=self.review()
        self.assertEqual(before['partial_finish_allocations'][0]['result']['excluded_wall_sf'],81)
        self.assertEqual(after['partial_finish_allocations'][0]['result']['excluded_wall_sf'],99)
        self.assertEqual(after['partial_finish_allocations'][0]['finish_measurement_version'],3)
        self.assertEqual(before['gross_references'],after['gross_references'])

    def test_disconnected_finish_does_not_return_old_deduction(self):
        self.finish_state['measurements']['shower']['points']=[[12,12],[16,12],[16,17],[12,17]]
        with self.assertRaises(ValueError):self.review()

    def test_wrong_plan_missing_rule_and_unreviewed_candidate_fail(self):
        original=copy.deepcopy(self.state)
        self.state['plan_sha256']='other'
        with self.assertRaises(ValueError):self.review()
        self.state=original
        self.state['measurements']['room']['engine_line_ids']=['unreviewed']
        with self.assertRaises(ValueError):self.review()
        del self.state['measurements']['room']['engine_line_ids']
        self.finish_rules['rules']=[]
        with self.assertRaises(ValueError):self.review()

    def test_rule_binding_ignores_unrelated_changes_but_rejects_changed_paint_rule(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/'quantity_rules.json'
            rules = copy.deepcopy(self.rules)
            config = {**self.config, 'gross_rule_sha256':hashlib.sha256(encode(rules['rules'][0]).encode()).hexdigest()}
            rules['rules'].append({'id':'unrelated-hardware','quantity':2})
            path.write_text(json.dumps(rules),encoding='utf-8')
            self.assertEqual(read_gross_rules(root,config),rules)
            rules['rules'][1]['quantity'] = 4
            path.write_text(json.dumps(rules),encoding='utf-8')
            self.assertEqual(read_gross_rules(root,config),rules)
            rules['rules'][0]['surface_components'][0]['height_ft'] = 10
            path.write_text(json.dumps(rules),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'gross source rule changed'):
                read_gross_rules(root,config)
            rules['rules'].append(copy.deepcopy(rules['rules'][0]))
            path.write_text(json.dumps(rules),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'present and unique'):
                read_gross_rules(root,config)
            with self.assertRaisesRegex(ValueError,'one paint gross-rule'):
                read_gross_rules(root,{**config,'quantity_rules_sha256':'ambiguous'})

    def test_surface_references_preserve_billing_quantities_and_prices(self):
        draft={'rows':[{'row_id':zone,'excel_row':str(n),'cost_type':'SUBCONTRACTOR',
                      'draft_quantity':None,'line_cost':100,'line_price':107}
                     for n,zone in enumerate(('house','garage'),1)]}
        original=copy.deepcopy(draft)
        review={**self.review(),'mapping_sha256':'mapping'}
        result=attach_references(draft,review,{'house':'house','garage':'garage'})
        self.assertEqual(draft,original)
        self.assertEqual([r['assembly_inputs'][0]['quantity'] for r in result['rows']],[1039,460])
        for row in result['rows']:
            self.assertIsNone(row['draft_quantity'])
            self.assertEqual(row['line_cost'],100)
            self.assertEqual(row['line_price'],107)
            self.assertFalse(row['assembly_inputs'][0]['certified'])
        with self.assertRaisesRegex(ValueError,'Duplicate paint'):
            attach_references(result,review,{'house':'house','garage':'garage'})
        draft['rows'][1]['completion_status']='not_applicable_source_reviewed'
        with self.assertRaisesRegex(ValueError,'active cost row'):
            attach_references(draft,review,{'house':'house','garage':'garage'})

    def test_changed_source_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'rules.json';path.write_text(json.dumps(self.rules))
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(checked_json(path,digest),self.rules)
            path.write_text('{}')
            with self.assertRaises(ValueError):checked_json(path,digest)

    def test_enclosed_cavity_removed_without_changing_room_side_finishes(self):
        from measurement_quantities import geometry_digest
        cavity={**self.state['measurements']['room'],'points':[[60,10],[62,10],[62,14],[60,14]]}
        self.state['measurements']['cavity']=cavity
        terms=[{'id':'cavity-walls','measurement_id':'cavity','kind':'perimeter_wall',
                'height_ft':9,'height_source':'plan','operation':'add'},
               {'id':'cavity-ceiling','measurement_id':'cavity','kind':'area','operation':'add'}]
        self.rules['rules'][0]['surface_components'].extend(terms)
        before=self.review()
        self.config['excluded_components']=[{'component_id':t['id'],
            'geometry_sha256':geometry_digest(cavity),'reason':'Enclosed fireplace cavity',
            'source_files':[{'file':'plan-review.json','sha256':'reviewed'}]} for t in terms]
        after=self.review()
        self.assertEqual(before['gross_references'][0]['quantity']-after['gross_references'][0]['quantity'],116)
        self.assertEqual(after['gross_references'][0]['quantity'],1120)
        self.assertEqual(before['gross_references'][1],after['gross_references'][1])
        self.assertEqual(before['partial_finish_allocations'],after['partial_finish_allocations'])
        self.assertEqual(len(after['excluded_components']),2)
        self.state['measurements']['cavity']['points'][1][0]+=1
        with self.assertRaisesRegex(ValueError,'geometry changed'):self.review()

    def test_exclusion_rejects_unknown_duplicate_or_already_mapped_surface(self):
        from measurement_quantities import geometry_digest
        exclusion={'component_id':'room-walls','geometry_sha256':geometry_digest(self.state['measurements']['room']),
                   'reason':'Source review','source_files':[{'file':'evidence','sha256':'proof'}]}
        self.config['excluded_components']=[exclusion]
        with self.assertRaisesRegex(ValueError,'cannot target'):self.review()
        self.config['excluded_components']=[exclusion,exclusion]
        with self.assertRaisesRegex(ValueError,'distinct'):self.review()
        self.config['excluded_components']=[{**exclusion,'component_id':'missing'}]
        with self.assertRaisesRegex(ValueError,'distinct'):self.review()
        self.config['excluded_components']=[{**exclusion,'source_files':[]}]
        with self.assertRaisesRegex(ValueError,'source evidence'):self.review()

    def test_selected_product_rejects_resized_outline_and_invalid_tolerance(self):
        product={'measurement_id':'shower','width_ft':4,'depth_ft':5,'tolerance_ft':0.5/12}
        self.mapping['product_footprint']=product
        self.assertEqual(self.review()['partial_finish_allocations'][0]['result']['excluded_wall_sf'],81)
        for bad in (float('nan'),True,-1,1):
            product['tolerance_ft']=bad
            with self.assertRaises(ValueError):self.review()
        product['tolerance_ft']=0.5/12
        self.finish_state['measurements']['shower']['points']=[[10,10],[16,10],[16,15],[10,15]]
        with self.assertRaisesRegex(ValueError,'selected product'):self.review()

    def test_elevation_mapping_matches_source_and_rejects_duplicate_partition(self):
        from measurement_quantities import geometry_digest
        self.finish_state['measurements']['shower']['points']=[[10,4],[14,4],[14,6],[10,6]]
        self.finish_rules['rules']=[{'id':'tile','measurement_ids':['shower'],'label':'Tile',
            'unit':'SF','use':'assembly_input','rounding':'none','template_rows':[],
            'basis':'Test elevation','remaining':[],'footprint':{'include':['shower'],'exclude':[]}}]
        field={'id':'wall','room_edge_index':0,'anchor_end':'start','direction':1,
            'elevation_anchor_x_pt':10,'elevation_floor_y_pt':10,'include':['shower'],'exclude':[],
            'datum_source':'Test elevation floor line'}
        self.mapping.update(elevation_fields=[field],room_geometry_sha256=geometry_digest(self.state['measurements']['room']))
        self.assertEqual(self.review()['partial_finish_allocations'][0]['result']['excluded_wall_sf'],8)
        self.mapping['elevation_fields'].append({**field,'id':'duplicate'})
        with self.assertRaisesRegex(ValueError,'partition'):self.review()
        self.mapping['elevation_fields']=[field]
        self.state['measurements']['room']['points'].insert(1,[20,10])
        with self.assertRaisesRegex(ValueError,'anchors'):self.review()

    def test_duplicate_finish_does_not_double_zone_deduction(self):
        source=(self.mapping,self.finish_state,self.finish_rules)
        review=calculate_review(self.state,self.rules,self.config,[source,source])
        room=review['combined_room_references'][0]
        self.assertEqual(room['known_finish_exclusion_sf'],81)
        self.assertEqual(room['overlap_between_allocations_sf'],81)
        self.assertEqual(review['partial_zone_references'][0]['remaining_surface_reference_sf'],1039)
        self.assertEqual(review['partial_zone_references'][1]['remaining_surface_reference_sf'],460)
        self.assertIsNone(room['final_paint_quantity'])

    def test_rectangular_and_elevation_masks_union_on_one_wall_only(self):
        from paint_surface_review import combine_room_allocations
        from shapely.geometry import box,mapping
        a={'room_id':'a','result':{'gross_wall_sf':180,'excluded_wall_sf':50,
            'mapped_faces':[{'room_edge_index':0,'start_ft':0,'end_ft':10,'height_ft':5}]}}
        b={'room_id':'a','result':{'gross_wall_sf':180,'excluded_wall_sf':50,
            'mapped_elevation_fields':[{'room_edge_index':0,'wall_plane_geometry_ft':mapping(box(5,3,15,8))}]}}
        room=combine_room_allocations([a,b])[0]
        self.assertEqual(room['known_finish_exclusion_sf'],90)
        self.assertEqual(room['overlap_between_allocations_sf'],10)
        separate=combine_room_allocations([a,{**b,'room_id':'b'}])
        self.assertEqual([r['known_finish_exclusion_sf'] for r in separate],[50,50])
        inconsistent=copy.deepcopy(b);inconsistent['result']['gross_wall_sf']=200
        with self.assertRaisesRegex(ValueError,'disagree'):combine_room_allocations([a,inconsistent])


if __name__=='__main__':unittest.main()
