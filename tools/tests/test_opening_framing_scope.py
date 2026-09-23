import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from opening_framing_scope import build_scope,from_folder,render_markdown
from bid_comparison import compare_quotes,scope_digest


class OpeningFramingScope(unittest.TestCase):
    def setUp(self):
        base={'page':5,'tag':'3068','source_sha256':'source','review_status':'current_source_review',
            'printed_nominal_size':{'width_inches':36,'height_inches':80},'location':'Room',
            'role':'interior_door','door_configuration':'single_hinged'}
        self.schedule={'plan_sha256':'plan','measurement_version':1,'review_sha256':'review',
            'limitations':['Untagged openings remain outside the schedule.'],'stale_or_missing_label_ids':[],
            'openings':[{**base,'opening_id':'door'},
                {**base,'opening_id':'window','role':'window','door_configuration':None,'window_component_count':3},
                {**base,'opening_id':'passage','role':'open_passage','door_configuration':None},
                {**base,'opening_id':'pocket','role':'special_interior_door','door_configuration':'pocket'}]}

    def test_each_physical_opening_is_owned_once_and_passages_are_included(self):
        before=copy.deepcopy(self.schedule);scope=build_scope(self.schedule)
        self.assertEqual(len(scope['openings']),4)
        items={r['id']:r for r in scope['items']}
        self.assertEqual(len(items),18)
        self.assertIn('passage:header',items)
        self.assertIn('window:rough-sill',items);self.assertIn('window:below-window',items)
        self.assertNotIn('door:rough-sill',items);self.assertNotIn('passage:below-window',items)
        self.assertIn('pocket:pocket-frame-interface',items)
        self.assertEqual(sum(i['opening_id']=='window' for i in scope['items'] if 'opening_id' in i),5)
        self.assertTrue(all(i['purchase_quantity'] is None for i in scope['items']))
        self.assertTrue(all(r['lumber_quantity'] is None for r in scope['openings']))
        self.assertFalse(scope['ready_to_order']);self.assertFalse(scope['sent']);self.assertFalse(scope['complete_trade_coverage'])
        self.assertEqual(scope['scope_sha256'],scope_digest(scope));self.assertEqual(before,self.schedule)

    def test_stale_or_missing_openings_never_reuse_roles_or_counts(self):
        self.schedule['openings'][1]['review_status']='stale_source_review'
        self.schedule['stale_or_missing_label_ids']=['printed-tag-lost']
        scope=build_scope(self.schedule);record=scope['openings'][1]
        self.assertIsNone(record['role']);self.assertIsNone(record['reference_assembly_count'])
        self.assertIsNone(record['configuration']);self.assertIsNone(record['location'])
        ids={r['id'] for r in scope['items']}
        self.assertIn('window:source-review',ids);self.assertNotIn('window:rough-sill',ids)
        self.assertIn('opening-lost:source-review',ids)
        self.assertEqual(scope['unresolved_opening_ids'],['window','opening-lost'])
        self.assertFalse(scope['source_enumeration_current'])

    def test_unknown_special_door_requires_kit_interface_review(self):
        self.schedule['openings'][-1]['door_configuration']=None
        scope=build_scope(self.schedule)
        self.assertIn('pocket:special-frame-interface',[i['id'] for i in scope['items']])
        self.assertIn('pocket',scope['unresolved_opening_ids'])

    def test_missing_gable_and_other_unenumerated_scope_is_explicit(self):
        self.schedule['openings']=[]
        scope=build_scope(self.schedule)
        self.assertFalse(scope['source_enumeration_current']);self.assertEqual(len(scope['items']),3)
        self.assertIn('gable windows',scope['items'][0]['label'])

    def test_invalid_revision_and_duplicate_physical_ids_fail(self):
        for version in (0,True,None):
            with self.subTest(version=version),self.assertRaises(ValueError):
                build_scope({**self.schedule,'measurement_version':version})
        for identity in ('door','',None):
            changed=copy.deepcopy(self.schedule);changed['openings'][1]['opening_id']=identity
            with self.subTest(identity=identity),self.assertRaises(ValueError):build_scope(changed)
        changed=copy.deepcopy(self.schedule);changed['openings'][0]['opening_id']='opening-lost'
        changed['stale_or_missing_label_ids']=['printed-tag-lost']
        with self.assertRaises(ValueError):build_scope(changed)

    def test_supplier_excluded_sill_cannot_compare_as_complete(self):
        scope=build_scope(self.schedule)
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'quote.txt';path.write_text('Synthetic framing quote for test only')
            quote={'id':'test','supplier':'Synthetic fixture','source_file':path.name,
                'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewed_scope_sha256':scope['scope_sha256'],
                'reviewed':True,'evidence_kind':'current_subcontractor_quote','date':'2026-09-19',
                'valid_through':'2026-09-20','currency':'USD','total':'100',
                'scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'fixture'} for i in scope['items']]}
            compare=lambda s,q:compare_quotes(s,[q],'2026-09-19',root)['quotes'][0]
            self.assertTrue(compare(scope,quote)['same_scope_current_quote'])
            for status in ('missing','excluded','unknown','allowance'):
                changed=copy.deepcopy(quote)
                if status=='missing':changed['scope_items']=[i for i in changed['scope_items'] if i['scope_id']!='window:rough-sill']
                else:next(i for i in changed['scope_items'] if i['scope_id']=='window:rough-sill')['status']=status
                with self.subTest(status=status):
                    result=compare(scope,changed)
                    self.assertFalse(result['same_scope_current_quote']);self.assertIsNone(result['adjusted_total'])
                    self.assertEqual(result['quoted_total'],'100');self.assertFalse(result['purchase_authorized'])
            for field,value in [('source_sha256','edited'),('role','open_passage')]:
                changed=copy.deepcopy(self.schedule);changed['openings'][1][field]=value
                self.assertFalse(compare(build_scope(changed),quote)['same_scope_current_quote'])

    def test_render_carries_every_scope_id_and_no_private_prices(self):
        self.schedule['openings'][0]['location']='Hall | Bath\nentry'
        scope=build_scope(self.schedule);text=render_markdown(scope)
        self.assertIn('Hall \\| Bath entry',text);self.assertIn(scope['scope_sha256'],text)
        self.assertTrue(all('`'+i['id']+'`' in text for i in scope['items']))
        self.assertNotIn('$',text)

    def test_folder_reader_uses_current_geometry_without_door_core_policy(self):
        with patch('opening_framing_scope.opening_schedule',return_value=self.schedule) as reader:
            scope=from_folder('job',{'version':1})
        reader.assert_called_once_with('job',{'version':1},include_company_policy=False)
        self.assertEqual(scope,build_scope(self.schedule))


if __name__=='__main__':unittest.main()
