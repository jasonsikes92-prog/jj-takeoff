import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from opening_header_review import review,from_folder


class OpeningHeaderReview(unittest.TestCase):
    def setUp(self):
        self.state={'version':1,'plan_sha256':'plan','measurements':{'EO1':{'kind':'length','page':5,
            'points':[[0,0],[60,0]],'points_per_foot':12}}}
        self.bindings=[{'opening_id':'EO1','measurement_id':'EO1','measurement_page':5,'header_id':'H1','source':'plan mapping'}]
        self.headers=[{'id':'H1','length_inches':63}]
        self.products=[{'opening_id':'EO1','rough_opening_width_in':60,'source':'supplier'}]
        self.supplier=[{'opening_id':'EO1','header_id':'H1','plan_cut_length_inches':63,
            'member_id':'BM1','stock_length_inches':58,'product':'Printed supplier LVL',
            'source':'Supplier layout, page 2'}]

    def test_supplier_short_stock_remains_separate_from_plan_header(self):
        result=review(self.state,self.bindings,self.headers,self.products,self.supplier)
        row=result['openings'][0];alternative=row['supplier_alternative']
        self.assertEqual(row['header_cut_length_inches'],63)
        self.assertEqual(row['status'],'end_support_length_unverified')
        self.assertEqual(alternative['stock_minus_plan_cut_inches'],-5)
        self.assertEqual(alternative['length_remaining_for_both_supports_inches'],-2)
        self.assertEqual(alternative['flags'],['supplier_stock_shorter_than_plan_cut',
                                              'supplier_stock_has_no_end_support_length'])
        self.assertFalse(alternative['adopted_as_replacement'])
        self.assertIsNone(row['king_stud_count'])

    def test_supplier_comparison_follows_edits_and_zero_remaining_is_flagged(self):
        self.supplier[0]['stock_length_inches']=72
        first=review(self.state,self.bindings,self.headers,self.products,self.supplier)
        self.assertEqual(first['openings'][0]['supplier_alternative']['flags'],[])
        self.state['measurements']['EO1']['points'][1][0]=72
        edited=review(self.state,self.bindings,self.headers,self.products,self.supplier)
        alternative=edited['openings'][0]['supplier_alternative']
        self.assertEqual(alternative['length_remaining_for_both_supports_inches'],0)
        self.assertIn('supplier_stock_has_no_end_support_length',alternative['flags'])
        self.assertFalse(alternative['structural_adequacy_verified'])
        self.assertFalse(alternative['revision_matches_plan_verified'])

    def test_supplier_missing_opening_width_does_not_invent_end_support(self):
        self.bindings[0]['measurement_id']=None
        row=review(self.state,self.bindings,self.headers,[],self.supplier)['openings'][0]
        self.assertIsNone(row['supplier_alternative']['length_remaining_for_both_supports_inches'])
        self.assertIn('supplier_stock_shorter_than_plan_cut',row['supplier_alternative']['flags'])

    def test_supplier_duplicate_unknown_or_stale_mapping_rejected(self):
        with self.assertRaises(ValueError):review(self.state,self.bindings,self.headers,self.products,self.supplier*2)
        for key,value in [('opening_id','unknown'),('header_id','H2'),('plan_cut_length_inches',64),
                          ('source',''),('stock_length_inches',True),('stock_length_inches',float('nan'))]:
            bad=copy.deepcopy(self.supplier);bad[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                review(self.state,self.bindings,self.headers,self.products,bad)

    def test_supplier_document_and_plan_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);config={'plan_sha256':'plan','bindings':self.bindings}
            document=b'Original supplier layout test fixture'
            (folder/'layout.pdf').write_bytes(document)
            supplier={'plan_sha256':'plan','openings':self.supplier,
                      'documents':[{'path':'layout.pdf','sha256':hashlib.sha256(document).hexdigest()}]}
            values={'headers':{'sha256':'plan','headers':self.headers},
                    'products':{'openings':self.products},'supplier_headers':supplier}
            def save():
                for key,value in values.items():
                    data=json.dumps(value).encode();(folder/(key+'.json')).write_bytes(data)
                    config[key]={'path':key+'.json','sha256':hashlib.sha256(data).hexdigest()}
                (folder/'opening_header_review.json').write_text(json.dumps(config))
            save()
            self.assertEqual(from_folder(folder,self.state)['openings'][0]['supplier_alternative']['stock_length_inches'],58)
            (folder/'layout.pdf').write_bytes(b'Changed layout')
            with self.assertRaisesRegex(ValueError,'evidence changed'):from_folder(folder,self.state)
            (folder/'layout.pdf').write_bytes(document)
            supplier['plan_sha256']='other';save()
            with self.assertRaisesRegex(ValueError,'matching plan'):from_folder(folder,self.state)
            supplier['plan_sha256']='plan';supplier['documents'][0]['path']='../outside.pdf';save()
            with self.assertRaisesRegex(ValueError,'inside the job'):from_folder(folder,self.state)

    def test_positive_length_is_not_support_certification(self):
        result=review(self.state,self.bindings,self.headers,self.products)
        row=result['openings'][0]
        self.assertEqual(row['length_remaining_for_both_supports_inches'],3)
        self.assertEqual(row['status'],'end_support_length_unverified')
        self.assertIsNone(row['jack_stud_count'])
        self.assertFalse(result['structural_adequacy_verified'])

    def test_edit_recalculates_and_does_not_use_stale_supplier_width(self):
        first=review(self.state,self.bindings,self.headers,self.products)
        self.state['measurements']['EO1']['points'][1][0]=66
        self.state['version']=2
        edited=review(self.state,self.bindings,self.headers,self.products)
        self.assertEqual(edited['openings'][0]['status'],'header_shorter_than_opening_reference')
        self.assertEqual(edited['openings'][0]['length_remaining_for_both_supports_inches'],-3)
        self.assertIn('drawn_width_differs_from_product_reference',edited['openings'][0]['flags'])
        self.assertNotEqual(first['measurement_inputs_sha256'],edited['measurement_inputs_sha256'])

    def test_product_can_expose_short_header_without_linked_geometry(self):
        self.bindings[0]['measurement_id']=None
        self.headers[0]['length_inches']=45;self.products[0]['rough_opening_width_in']=48
        result=review(self.state,self.bindings,self.headers,self.products)['openings'][0]
        self.assertEqual(result['length_remaining_for_both_supports_inches'],-3)
        self.assertIn('opening_geometry_not_linked',result['flags'])
        self.bindings[0]['header_id']=None
        self.assertEqual(review(self.state,self.bindings,self.headers,self.products)['openings'][0]['status'],'header_not_documented')

    def test_missing_product_does_not_claim_rough_opening_approval(self):
        row=review(self.state,self.bindings,self.headers,[])['openings'][0]
        self.assertIsNone(row['product_rough_opening_width_inches'])
        self.assertIn('product_rough_opening_unverified',row['flags'])

    def test_pocket_header_checks_door_and_cavity_once_and_tracks_cavity_edits(self):
        self.state['measurements']['PC1']={'kind':'length','page':5,
            'points':[[60,0],[90,0]],'points_per_foot':12}
        self.bindings[0]['span_measurement_ids']=['EO1','PC1']
        self.headers[0]['length_inches']=93
        first=review(self.state,self.bindings,self.headers,[])
        row=first['openings'][0]
        self.assertEqual(row['measurement_id'],'EO1')
        self.assertEqual(row['span_measurement_ids'],['EO1','PC1'])
        self.assertEqual(row['drawn_width_inches'],90)
        self.assertEqual(row['length_remaining_for_both_supports_inches'],3)
        self.state['measurements']['PC1']['points'][1][0]=96
        after=review(self.state,self.bindings,self.headers,[])
        self.assertEqual(after['openings'][0]['status'],'header_shorter_than_opening_reference')
        self.assertNotEqual(after['measurement_inputs_sha256'],first['measurement_inputs_sha256'])

    def test_combined_header_span_rejects_gaps_overlap_scale_and_line_mismatches(self):
        self.bindings[0]['span_measurement_ids']=['EO1','PC1']
        for points,scale in [([[61,0],[90,0]],12),([[59,0],[90,0]],12),
                             ([[60,1],[90,1]],12),([[60,0],[90,2]],12),
                             ([[60,0],[90,0]],24),([[60,0],[60,0]],12),
                             ([[60,float('nan')],[90,float('nan')]],12)]:
            self.state['measurements']['PC1']={'kind':'length','page':5,
                'points':points,'points_per_foot':scale}
            with self.subTest(points=points,scale=scale),self.assertRaises(ValueError):
                review(self.state,self.bindings,self.headers,[])
        self.bindings[0]['span_measurement_ids']=['EO1','EO1']
        with self.assertRaisesRegex(ValueError,'unique'):review(self.state,self.bindings,self.headers,[])

    def test_linked_span_can_be_checked_without_incorrect_main_editor_selection(self):
        self.bindings[0].update(measurement_id=None,span_measurement_ids=['EO1'])
        row=review(self.state,self.bindings,self.headers,[])['openings'][0]
        self.assertEqual(row['drawn_width_inches'],60)
        self.assertIsNone(row['measurement_id'])
        self.assertNotIn('opening_geometry_not_linked',row['flags'])

    def test_invalid_or_bent_width_and_duplicate_opening_rejected(self):
        with self.assertRaises(ValueError):review(self.state,self.bindings*2,self.headers,self.products)
        for bad in (0,-1,True,float('nan')):
            with self.assertRaises(ValueError):review(self.state,self.bindings,[{'id':'H1','length_inches':bad}],self.products)
        self.state['measurements']['EO1']['points'].append([65,5])
        with self.assertRaises(ValueError):review(self.state,self.bindings,self.headers,self.products)

    def test_file_sources_plan_identity_and_job_boundary_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);config={'plan_sha256':'plan','bindings':self.bindings}
            for key,value in [('headers',{'sha256':'plan','headers':self.headers}),('products',{'openings':self.products})]:
                data=json.dumps(value).encode();(folder/(key+'.json')).write_bytes(data)
                config[key]={'path':key+'.json','sha256':hashlib.sha256(data).hexdigest()}
            path=folder/'opening_header_review.json';path.write_text(json.dumps(config))
            self.assertEqual(len(from_folder(folder,self.state)['openings']),1)
            bad=copy.deepcopy(self.state);bad['plan_sha256']='other'
            with self.assertRaisesRegex(ValueError,'plan changed'):from_folder(folder,bad)
            (folder/'headers.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'evidence changed'):from_folder(folder,self.state)
            config['headers']['path']='../outside.json';path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'inside the job'):from_folder(folder,self.state)


if __name__=='__main__':unittest.main()
