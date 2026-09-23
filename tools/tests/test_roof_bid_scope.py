import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from roof_bid_scope import build_scope,render_markdown,write_draft
from roof_partition_review import audit_faces
from bid_comparison import required_scope_items,scope_digest,compare_quotes


class RoofBidScope(unittest.TestCase):
    def setUp(self):
        self.roof={'id':'main','kind':'area','page':1,'width_pt':500,'height_pt':500,'points_per_foot':1,
            'points':[[10,10],[110,10],[110,110],[10,110]],'surface_factor':1.25,'label':'Main | roof'}
        cut={**self.roof,'id':'cut','points':[[30,30],[50,30],[50,50],[30,50]]}
        dormer={**cut,'id':'dormer','surface_factor':1.5,'source_pitch_evidence':{'pitch_is_inferred':True}}
        terms=[{'measurement_id':i,'kind':'area','operation':'add'} for i in ('main','dormer')]
        terms.append({'measurement_id':'cut','kind':'area','operation':'deduct','cutout_of':'main'})
        self.audit={'plan_sha256':'plan','measurement_version':1,'measurements_sha256':'geometry',
            'coverage_review_sha256':'coverage',**audit_faces([self.roof,cut,dormer],self.roof['points'],terms)}

    def test_net_parent_area_and_dormer_are_separate_without_buying_cutout_twice(self):
        scope=build_scope(self.audit)
        self.assertEqual(len(scope['items']),2)
        main,dormer=scope['items']
        self.assertEqual(main['reference_quantity'],12000)
        self.assertEqual(main['reference_roofing_squares'],120)
        self.assertEqual(main['deducted_cutout_ids'],['cut'])
        self.assertEqual(dormer['reference_quantity'],600)
        self.assertTrue(dormer['pitch_is_inferred'])
        self.assertEqual(scope_digest(scope),scope['scope_sha256'])

    def test_specs_waste_purchase_units_and_prices_are_not_invented(self):
        scope=build_scope(self.audit)
        for item in scope['items']:
            for field in ('roofing_system','manufacturer_product','waste_percent','purchase_unit',
                          'coverage_per_purchase_unit','purchase_quantity','unit_price'):
                self.assertIsNone(item[field])
        self.assertIsNone(scope['whole_roof_order_quantity']);self.assertFalse(scope['sent'])
        self.assertFalse(scope['ready_to_order'])

    def test_all_material_and_pricing_requirements_enter_quote_comparison(self):
        scope=build_scope(self.audit);required=required_scope_items(scope)
        self.assertEqual(len(required),10)
        self.assertIn('requirement:waste-and-purchase-units',{i['id'] for i in required})
        self.assertIn('requirement:billing-basis',{i['id'] for i in required})

    def test_changed_geometry_or_coverage_changes_bid_fingerprint(self):
        scope=build_scope(self.audit)
        for field,value in (('measurements_sha256','changed'),('measurement_version',2),
                            ('coverage_review_sha256','new-contour')):
            changed={**self.audit,field:value}
            self.assertNotEqual(scope['scope_sha256'],build_scope(changed)['scope_sha256'])

    def test_invalid_or_duplicate_face_quantities_are_rejected(self):
        for change in (None,float('nan'),0):
            audit=copy.deepcopy(self.audit);audit['face_references'][0]['surface_area_sf']=change
            with self.assertRaises(ValueError):build_scope(audit)
        audit=copy.deepcopy(self.audit);audit['face_references'].append(audit['face_references'][0])
        with self.assertRaises(ValueError):build_scope(audit)

    def test_markdown_retains_units_questions_and_inferred_pitch_warning(self):
        text=render_markdown(build_scope(self.audit))
        self.assertIn('Main \\| roof',text);self.assertIn('Inferred; review required',text)
        self.assertIn('One roofing square is 100 SF',text)
        self.assertIn('not a panel cut list',text)
        self.assertIn('Overlapping projected roof area:',text)
        scope=build_scope(self.audit);scope['source_exceptions']['overlap_excess_sf']=-1e-12
        self.assertIn('Overlapping projected roof area: 0.000000 SF',render_markdown(scope))

    def test_export_preserves_scope_and_existing_bid_revision(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'bid';scope=build_scope(self.audit);before=copy.deepcopy(scope)
            names=write_draft(scope,folder)
            self.assertEqual(names,['roofing_DRAFT.md','roofing.json'])
            self.assertEqual(json.loads((folder/'roofing.json').read_text()),scope)
            self.assertEqual((folder/'roofing_DRAFT.md').read_text(),render_markdown(scope))
            self.assertEqual(scope,before)
            with self.assertRaises(FileExistsError):write_draft(scope,folder)
            self.assertEqual(json.loads((folder/'roofing.json').read_text()),before)

    def test_changed_bid_contents_cannot_be_exported_as_reviewed_source(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name)/'bid';scope=build_scope(self.audit)
            scope['items'][0]['reference_quantity']+=1
            with self.assertRaisesRegex(ValueError,'fingerprint'):write_draft(scope,folder)
            self.assertFalse(folder.exists())

    def test_overlapping_roofs_require_a_separate_coverage_answer(self):
        lower={**self.roof,'id':'lower','points':[[50,10],[150,10],[150,110],[50,110]]}
        audit={**self.audit,**audit_faces([self.roof,lower])}
        scope=build_scope(audit);region,=scope['source_exceptions']['overlap_regions']
        identity='requirement:'+region['id']
        self.assertEqual(region['area_sf'],6000)
        self.assertEqual(scope['source_exceptions']['overlapped_footprint_sf'],6000)
        self.assertIn(identity,{i['id'] for i in required_scope_items(scope)})
        self.assertIn(region['id'],render_markdown(scope))
        self.assertEqual(sum(i['reference_quantity'] for i in scope['items']),25000)
        self.assertFalse(scope['ready_to_order'])
        with tempfile.TemporaryDirectory() as name:
            evidence=Path(name)/'quote.txt';evidence.write_text('Illustrative test quote; all roof faces priced.')
            quote={'id':'q','supplier':'Test roofer','source_file':evidence.name,
                'source_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),
                'reviewed_scope_sha256':scope['scope_sha256'],'reviewed':True,
                'date':'2026-09-21','valid_through':'2026-10-21','currency':'USD','total':100,
                'evidence_kind':'current_subcontractor_quote',
                'scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'test page 1'}
                    for i in required_scope_items(scope) if i['id']!=identity]}
            result=compare_quotes(scope,[quote],'2026-09-21',name)['quotes'][0]
            row=next(r for r in result['scope_matrix'] if r['scope_id']==identity)
            self.assertEqual(row['status'],'unknown')
            self.assertFalse(result['same_scope_current_quote'])
            quote['scope_items'].append({'scope_id':identity,'status':'included','source_ref':'test clarification 2'})
            result=compare_quotes(scope,[quote],'2026-09-21',name)['quotes'][0]
            self.assertEqual(next(r for r in result['scope_matrix'] if r['scope_id']==identity)['status'],'included')
            self.assertFalse(result['purchase_authorized'])

    def test_overlap_cannot_reference_absent_faces_or_duplicate_regions(self):
        lower={**self.roof,'id':'lower'}
        audit={**self.audit,**audit_faces([self.roof,lower])}
        duplicate=copy.deepcopy(audit);duplicate['overlap_cells']*=2
        missing=copy.deepcopy(audit);missing['overlap_cells'][0]['source_ids']=['main','absent']
        for invalid in (duplicate,missing):
            with self.assertRaises(ValueError):build_scope(invalid)


if __name__=='__main__':unittest.main()
