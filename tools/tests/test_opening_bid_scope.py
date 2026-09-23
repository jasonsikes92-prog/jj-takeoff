import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from opening_bid_scope import build_scope,render_markdown,attach_cross_view
from bid_comparison import scope_digest,compare_quotes


class OpeningBidScope(unittest.TestCase):
    def test_elevation_candidate_requires_response_without_adding_quantities(self):
        scope=build_scope(self.schedule,self.policy)
        before=copy.deepcopy(scope)
        review={'plan_sha256':'plan','certified':False,'whole_building_count':None,
            'unrepresented_elevation_tags':[{'page':9,'tag':'3050FX','bbox':[10,20,30,40]}]}
        result=attach_cross_view(scope,review)
        self.assertEqual(result['openings'],before['openings'])
        self.assertEqual(result['hardware_references'],before['hardware_references'])
        self.assertFalse(result['source_enumeration_current'])
        added=result['items'][-1]
        self.assertIsNone(added['reference_quantity']);self.assertIsNone(added['purchase_quantity'])
        self.assertIn('3050FX on PDF page 9',render_markdown(result))
        self.assertIn('already listed assembly',render_markdown(result))
        self.assertEqual(attach_cross_view(build_scope(self.schedule,self.policy),review)['items'][-1]['id'],added['id'])
        with self.assertRaisesRegex(ValueError,'another drawing'):
            attach_cross_view(build_scope(self.schedule,self.policy),{**review,'plan_sha256':'other'})

    def setUp(self):
        base={'page':5,'printed_nominal_size':{'width_inches':60,'height_inches':80},
            'source_sha256':'source','review_status':'current_source_review','location':'Rear door','tag':'5068',
            'role':'exterior_door','door_configuration':'double_hinged','drawn_panel_count':2}
        self.schedule={'plan_sha256':'plan','measurement_version':1,'review_sha256':'review','limitations':['Incomplete plan coverage'],
            'stale_or_missing_label_ids':[],'door_core_review':{'openings':[]},
            'openings':[{**base,'opening_id':'door'},
                {**base,'opening_id':'window','role':'window','door_configuration':None,'window_component_count':3},
                {**base,'opening_id':'passage','role':'open_passage','door_configuration':None}]}
        self.policy={'value':'individual_window_unit','provenance':{'basis':'company_default'}}

    def test_assemblies_panels_units_and_passages_have_distinct_quantities(self):
        original=copy.deepcopy(self.schedule);scope=build_scope(self.schedule,self.policy)
        self.assertEqual(len(scope['openings']),2);self.assertEqual(len(scope['items']),11)
        items={i['id']:i for i in scope['items']}
        self.assertEqual(items['door:supply']['reference_quantity'],1)
        self.assertEqual(scope['openings'][0]['drawn_panel_count'],2)
        self.assertEqual(items['window:supply']['reference_quantity'],1)
        self.assertEqual(items['window:installation']['reference_quantity'],3)
        self.assertEqual(items['window:installation']['reference_unit'],'individual window unit')
        self.assertEqual(scope['excluded_open_passage_ids'],['passage'])
        self.assertFalse(scope['ready_to_order']);self.assertFalse(scope['sent'])
        self.assertTrue(all(i['purchase_quantity'] is None for i in scope['items']))
        self.assertEqual(self.schedule,original)

    def test_unlocated_tags_require_quote_response_and_prevent_current_enumeration(self):
        self.schedule['unlocated_opening_tags']=[{'opening_id':'unlocated-1','tag':'3068','page':5,
            'reason':'No matching wall gap'}]
        scope=build_scope(self.schedule,self.policy)
        self.assertFalse(scope['source_enumeration_current'])
        self.assertIn('unlocated-1',scope['unresolved_opening_ids'])
        item=next(i for i in scope['items'] if i['id']=='unlocated-1:source-review')
        self.assertIsNone(item['reference_assembly_count']);self.assertIsNone(item['purchase_quantity'])
        self.assertIn('unlocated-1:source-review',render_markdown(scope))
        self.schedule['unlocated_opening_tags'][0]['opening_id']='window'
        with self.assertRaises(ValueError):build_scope(self.schedule,self.policy)

    def test_stale_and_missing_openings_remain_visible_without_old_counts(self):
        self.schedule['openings'][0]['review_status']='stale_source_review'
        self.schedule['stale_or_missing_label_ids']=['printed-tag-lost']
        scope=build_scope(self.schedule,self.policy)
        self.assertIsNone(scope['openings'][0]['assembly_count'])
        self.assertIsNone(scope['openings'][0]['drawn_panel_count'])
        self.assertIsNone(scope['openings'][0]['door_configuration'])
        self.assertEqual(scope['unresolved_opening_ids'],['door','opening-lost'])
        self.assertFalse(scope['source_enumeration_current'])
        self.assertIn('opening-lost:source-review',[i['id'] for i in scope['items']])

    def test_unconfirmed_window_policy_withholds_installation_reference(self):
        scope=build_scope(self.schedule)
        item=next(i for i in scope['items'] if i['id']=='window:installation')
        self.assertIsNone(item['reference_quantity']);self.assertIn('window',scope['unresolved_opening_ids'])

    def test_changed_configuration_invalidates_existing_quote_scope_review(self):
        scope=build_scope(self.schedule,self.policy)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'synthetic_quote.txt';path.write_text('Synthetic test quote only')
            quote={'id':'test','supplier':'Synthetic fixture','source_file':path.name,
                'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed_scope_sha256':scope_digest(scope),
                'reviewed':True,'evidence_kind':'current_supplier_quote','date':'2026-09-19','valid_through':'2026-09-20',
                'currency':'USD','total':'100','scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'fixture'} for i in scope['items']]}
            result=compare_quotes(scope,[quote],'2026-09-19',root)
            self.assertTrue(result['quotes'][0]['same_scope_current_quote'])
            self.schedule['openings'][0]['door_configuration']='sliding'
            changed=build_scope(self.schedule,self.policy)
            result=compare_quotes(changed,[quote],'2026-09-19',root)
            self.assertFalse(result['quotes'][0]['same_scope_current_quote'])
            self.assertIsNone(result['winner']);self.assertFalse(result['estimate_released'])

    def test_rendering_contains_every_scope_id_and_escapes_location(self):
        self.schedule['openings'][0]['location']='Rear | door\nlabel'
        scope=build_scope(self.schedule,self.policy);text=render_markdown(scope)
        self.assertIn('Rear \\| door label',text)
        self.assertTrue(all('`'+i['id']+'`' in text for i in scope['items']))
        self.assertIn('Unsent draft',text)

    def test_hardware_distinguishes_ordinary_special_exterior_and_passage(self):
        base=self.schedule['openings'][0]
        self.schedule['openings'] += [
            {**base,'opening_id':kind,'role':role,'door_configuration':kind,'drawn_panel_count':panels}
            for kind,role,panels in [('single_hinged','interior_door',1),('pocket','special_interior_door',1),
                ('bypass','special_interior_door',2),('bifold','special_interior_door',2)]]
        scope=build_scope(self.schedule,self.policy)
        self.assertEqual(scope['enumerated_ordinary_hinged_set_reference'],1)
        refs={r['opening_id']:r for r in scope['hardware_references']}
        self.assertEqual(set(refs),{'door','single_hinged','pocket','bypass','bifold'})
        self.assertEqual(refs['single_hinged']['ordinary_hinged_set_reference'],1)
        self.assertTrue(all(refs[k]['ordinary_hinged_set_reference']==0 for k in ('door','pocket','bypass','bifold')))
        self.assertTrue(all(r['hardware_function'] is None and r['purchase_quantity'] is None for r in refs.values()))
        responses=[i for i in scope['items'] if i['work']=='hardware_scope_confirmation']
        self.assertEqual(len(responses),5)
        self.assertTrue(all(i['reference_quantity'] is None for i in responses))

    def test_hardware_does_not_infer_privacy_from_core(self):
        self.schedule['openings'][0].update(role='interior_door',door_configuration='single_hinged',drawn_panel_count=1)
        self.schedule['door_core_review']['openings']=[{'opening_id':'door','core':'solid'}]
        scope=build_scope(self.schedule,self.policy)
        self.assertEqual(scope['enumerated_ordinary_hinged_set_reference'],1)
        self.assertIsNone(scope['hardware_references'][0]['hardware_function'])
        self.assertIn('Door core does not determine privacy',render_markdown(scope))

    def test_conflicting_single_door_panel_count_is_withheld(self):
        self.schedule['openings'][0].update(role='interior_door',door_configuration='single_hinged',drawn_panel_count=2)
        scope=build_scope(self.schedule,self.policy)
        self.assertIsNone(scope['enumerated_ordinary_hinged_set_reference'])
        self.assertIsNone(scope['hardware_references'][0]['ordinary_hinged_set_reference'])
        self.assertIn('door',scope['unresolved_opening_ids'])
        self.assertIn('conflicts',scope['openings'][0]['unresolved'][0])

    def test_stale_unknown_and_missing_sources_withhold_hardware_total(self):
        for changes in ({'review_status':'stale_source_review'},{'door_configuration':None}):
            schedule=copy.deepcopy(self.schedule);schedule['openings'][0].update(changes)
            result=build_scope(schedule,self.policy)
            self.assertIsNone(result['enumerated_ordinary_hinged_set_reference'])
            self.assertIsNone(result['hardware_references'][0]['ordinary_hinged_set_reference'])
        self.schedule['stale_or_missing_label_ids']=['printed-tag-lost']
        self.assertIsNone(build_scope(self.schedule,self.policy)['enumerated_ordinary_hinged_set_reference'])

    def test_hardware_omission_is_not_hidden_by_general_accessory_inclusion(self):
        scope=build_scope(self.schedule,self.policy)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'quote.txt';path.write_text('Synthetic inclusion test')
            quote={'id':'test','supplier':'Fixture','source_file':path.name,
                'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed_scope_sha256':scope_digest(scope),
                'reviewed':True,'evidence_kind':'current_supplier_quote','date':'2026-09-19','valid_through':'2026-09-20',
                'currency':'USD','total':'100','scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'fixture'}
                    for i in scope['items'] if i['id']!='door:hardware']}
            result=compare_quotes(scope,[quote],'2026-09-19',root)
            self.assertIsNone(result['winner'])
            self.assertFalse(result['quotes'][0]['same_scope_current_quote'])

    def test_exterior_trim_is_per_surround_and_omissions_prevent_complete_bid(self):
        scope=build_scope(self.schedule,self.policy)
        trim=[i for i in scope['items'] if i['work']=='exterior_trim_scope_confirmation']
        self.assertEqual({i['opening_id'] for i in trim},{'door','window'})
        self.assertTrue(all(i['reference_quantity']==1 and i['purchase_quantity'] is None for i in trim))
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'quote.txt';path.write_text('Synthetic exterior trim scope test')
            quote={'id':'test','supplier':'Fixture','source_file':path.name,
                'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed_scope_sha256':scope_digest(scope),
                'reviewed':True,'evidence_kind':'current_supplier_quote','date':'2026-09-19','valid_through':'2026-09-20',
                'currency':'USD','total':'100','scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'fixture'}
                    for i in scope['items'] if i['id']!='door:exterior-trim']}
            result=compare_quotes(scope,[quote],'2026-09-19',root)
            self.assertFalse(result['quotes'][0]['same_scope_current_quote'])
            self.assertIsNone(result['winner'])
            quote['scope_items'].append({'scope_id':'door:exterior-trim','status':'included','source_ref':'fixture trim material and installation'})
            self.assertTrue(compare_quotes(scope,[quote],'2026-09-19',root)['quotes'][0]['same_scope_current_quote'])
        self.schedule['openings'][0].update(role='interior_door',door_configuration='single_hinged',drawn_panel_count=1)
        ids={i['id'] for i in build_scope(self.schedule,self.policy)['items']}
        self.assertNotIn('door:exterior-trim',ids)
        self.schedule['openings'][1]['review_status']='stale_source_review'
        changed=build_scope(self.schedule,self.policy)
        self.assertNotIn('window:exterior-trim',{i['id'] for i in changed['items']})
        self.assertFalse(changed['source_enumeration_current'])


if __name__=='__main__':unittest.main()
