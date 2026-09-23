import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from export_trade_scopes import packages,render,export


class TradeScopes(unittest.TestCase):
    def setUp(self):
        self.index={'files':['trade.md']}
        self.coverage={'rows':[{'excel_row':'1','status':'draft_scope_routed','draft_file':'trade.md','draft_owner':'trade'},
            {'excel_row':'2','status':'not_applicable_source_reviewed'}],
            'supplemental_cost_routes':[{'row_id':'extra','draft_file':'trade.md','draft_owner':'trade','scope_note':'Already included in package'}]}
        self.snapshot={'snapshot_sha256':'snapshot','draft':{'plan_sha256':'plan','measurement_version':3,
            'rows':[{'excel_row':'1','row_id':'one','name':'Supply','draft_quantity':None,'unit':'EA','unit_cost':9876},
                    {'excel_row':'2','row_id':'excluded','name':'Excluded option','draft_quantity':None}],
            'additional_cost_rows':[{'row_id':'extra','name':'Included work','draft_quantity':2,'unit':'EA','cost_owner_row_id':'one'}]},
            'readiness':{'rows':[{'row_id':'one','issues':['Quantity unresolved']}],
                         'additional_cost_rows':[{'row_id':'extra','issues':[]}]}}

    def test_current_quantities_unknowns_and_ownership_without_prices_or_exclusions(self):
        original=copy.deepcopy(self.snapshot)
        p=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertEqual([r['row_id'] for r in p['items']],['one','extra'])
        self.assertIsNone(p['items'][0]['draft_quantity'])
        self.assertEqual(p['items'][1]['cost_owner_row_id'],'one')
        self.assertIn('Confirm inclusion under Supply',p['items'][1]['quote_action'])
        self.assertIn('no separate charge',p['items'][1]['quote_action'])
        self.assertNotIn('unit_cost',p['items'][0])
        text=render(p);self.assertIn('Unresolved',text);self.assertIn('2 EA',text)
        self.assertNotIn('9876',text);self.assertNotIn('Excluded option',text)
        self.assertEqual(self.snapshot,original)

    def test_waste_rounding_and_pack_basis_preserved_without_prices(self):
        row=self.snapshot['draft']['rows'][0]
        row.update(draft_quantity=121,unit='SF',quantity_sources=[{
            'id':'roof','basis':'Measured roof plus waste, rounded to whole SF.',
            'waste_percent':20,'rounding':'whole_up','unit_cost':4321,
            'purchase_pack':{'quantity':4,'unit':'bundle','product':'Shingles',
                'required_quantity':120.2,'coverage_unit':'SF','source':'Supplier specification',
                'cost':8765,'order_released':True}}])
        before=copy.deepcopy(self.snapshot)
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        item=result['items'][0];text=render(result)
        self.assertEqual(item['draft_quantity'],121)
        self.assertEqual(item['quantity_basis'][0]['purchase_pack']['quantity'],4)
        self.assertIn('Waste already included: 20%; do not add it again.',text)
        self.assertIn('Rounding: whole_up',text)
        self.assertIn('4 bundle of Shingles',text)
        self.assertIn('Not additional work or purchase authorization',text)
        self.assertNotIn('4321',text);self.assertNotIn('8765',text)
        self.assertNotIn('order_released',item['quantity_basis'][0]['purchase_pack'])
        self.assertEqual(before,self.snapshot)

    def test_package_inclusions_survive_export_without_supplier_prices(self):
        self.snapshot['draft']['rows'][0]['price_evidence']={'quote':{'quoted_total':9876,
            'scope_matrix':[
                {'scope_id':'hardware','label':'Tracks, rollers, guides and pulls',
                 'status':'included','note':'Two closet openings','source_ref':'Owner F55','unit_cost':4321},
                {'scope_id':'pocket-frames','label':'Pocket frames','status':'excluded',
                 'note':'Separate supplier','source_ref':'Owner R01'}]}}
        before=copy.deepcopy(self.snapshot)
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        text=render(result)
        self.assertIn('Tracks, rollers, guides and pulls',text)
        self.assertIn('recorded package status **included**',text)
        self.assertIn('Confirm within this package; no separate charge.',text)
        self.assertIn('Pocket frames: recorded package status **excluded**',text)
        self.assertIn('Source: Owner F55',text)
        self.assertNotIn('9876',text);self.assertNotIn('4321',text)
        self.assertNotIn('unit_cost',result['items'][0]['package_scope'][0])
        self.assertEqual(before,self.snapshot)

    def test_project_duration_is_schedule_reference_not_rental_quantity(self):
        self.snapshot['draft']['rows'].append({'row_id':'duration','excel_row':'3',
            'name':'PROJECT DURATION - # OF MONTHS','parent':'INPUTS','unit':'month','draft_quantity':9})
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertEqual(result['project_duration_reference'],{'months':9,'source_row_id':'duration'})
        self.assertIn('9 months',render(result))
        self.assertIn('not a rental quantity',render(result))
        self.assertEqual(len(result['items']),2)
        for value in (True,-1,0,float('nan'),'9'):
            self.snapshot['draft']['rows'][-1]['draft_quantity']=value
            with self.assertRaisesRegex(ValueError,'positive months'):
                packages(Path('index.json'),self.index,self.coverage,self.snapshot)

    def test_partial_assembly_reference_does_not_become_purchase_quantity(self):
        self.snapshot['draft']['rows'][0]['assembly_inputs']=[{
            'id':'ladder-net','quantity':277.1166,'unit':'LF',
            'basis':'Net length at average course height',
            'remaining':['Laps and stock cuts unresolved'],'unit_cost':4321}]
        before=copy.deepcopy(self.snapshot)
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        text=render(result)
        self.assertIsNone(result['items'][0]['draft_quantity'])
        self.assertIn('277.1166 LF',text)
        self.assertIn('not a purchase quantity or additional charge',text)
        self.assertIn('Laps and stock cuts unresolved',text)
        self.assertNotIn('4321',text)
        self.assertEqual(before,self.snapshot)

    def test_measured_cost_row_keeps_distinct_assembly_references(self):
        row=self.snapshot['draft']['rows'][0]
        row.update(draft_quantity=1200,unit='SF',assembly_inputs=[{
            'id':'wall-field','quantity':900,'unit':'SF','basis':'Walls only',
            'remaining':['Ceilings and board specification remain separate'],'unit_cost':4321}])
        before=copy.deepcopy(self.snapshot)
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        item=result['items'][0]
        self.assertEqual(item['draft_quantity'],1200)
        self.assertEqual(item['assembly_references'][0]['quantity'],900)
        text=render(result)
        self.assertIn('1200 SF',text)
        self.assertIn('assembly reference 900 SF',text)
        self.assertIn('not a purchase quantity or additional charge',text)
        self.assertNotIn('4321',text)
        self.assertEqual(before,self.snapshot)

    def test_owner_selected_exclusion_is_not_a_request_even_when_old_route_remains(self):
        self.snapshot['draft']['rows'][0].update(completion_status='not_applicable_owner_selected_assembly',
            unit_cost=None,next_check='Encapsulation replaces floor batts')
        self.snapshot['draft']['additional_cost_rows'][0].pop('cost_owner_row_id')
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertEqual([i['row_id'] for i in result['items']],['extra'])
        self.assertEqual(result['excluded_items'][0]['row_id'],'one')
        self.assertIn('Excluded options — do not quote',render(result))
        self.snapshot['draft']['rows'][0]['draft_quantity']=10
        with self.assertRaisesRegex(ValueError,'Excluded scope still contains'):
            packages(Path('index.json'),self.index,self.coverage,self.snapshot)

    def test_active_scope_cannot_be_covered_by_an_excluded_owner(self):
        self.snapshot['draft']['rows'][0].update(completion_status='not_applicable_source_reviewed',unit_cost=None)
        with self.assertRaisesRegex(ValueError,'excluded package owner'):
            packages(Path('index.json'),self.index,self.coverage,self.snapshot)

    def test_owner_chain_rejects_cycles_and_nonbillable_owners(self):
        self.snapshot['draft']['rows'][0]['cost_owner_row_id']='extra'
        with self.assertRaisesRegex(ValueError,'Circular package ownership'):
            packages(Path('index.json'),self.index,self.coverage,self.snapshot)
        self.snapshot['draft']['rows'][0].pop('cost_owner_row_id')
        self.snapshot['draft']['rows'][0]['pricing_role']='input_only'
        with self.assertRaisesRegex(ValueError,'nonbillable package owner'):
            packages(Path('index.json'),self.index,self.coverage,self.snapshot)

    def test_valid_package_self_reference_remains_supported(self):
        self.snapshot['draft']['rows'][0]['covered_by_package']='one'
        p=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertIn('no separate charge',p['items'][1]['quote_action'])

    def test_duplicate_cost_owners_across_routes_are_rejected(self):
        self.coverage['rows'].append(copy.deepcopy(self.coverage['rows'][0]))
        with self.assertRaisesRegex(ValueError,'more than one trade'):
            packages(Path('index.json'),self.index,self.coverage,self.snapshot)

    def test_existing_output_and_invalid_routes_are_not_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);output=root/'existing';output.mkdir()
            with patch('export_trade_scopes.validate') as validate,self.assertRaises(FileExistsError):
                export(root/'index.json',output)
            validate.assert_not_called()
            with patch('export_trade_scopes.validate',return_value={'valid':False,'errors':['Stale quantity']}),self.assertRaises(ValueError):
                export(root/'index.json',root/'new')
            self.assertFalse((root/'new').exists())

    def test_empty_alternative_heading_preserves_shared_active_components(self):
        parent=self.snapshot['draft']['rows'][0]
        parent.update(cost_type='ASSEMBLY',unit_cost=None)
        child=self.snapshot['draft']['rows'][1]
        child.update(parent='Supply',completion_status='not_applicable_source_reviewed')
        shared={'excel_row':'3','row_id':'backfill','name':'Shared backfill','parent':'Supply',
                'draft_quantity':None,'cost_owner_row_id':'extra','unit':'truck'}
        self.snapshot['draft']['rows'].append(shared)
        self.snapshot['draft']['additional_cost_rows'][0].pop('cost_owner_row_id')
        self.snapshot['readiness']['rows'].append({'row_id':'backfill','issues':[]})
        self.coverage['rows'].append({'excel_row':'3','status':'draft_scope_routed',
            'draft_file':'trade.md','draft_owner':'trade'})
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertIn('Reference heading only',result['items'][0]['quote_action'])
        self.assertIn('Confirm inclusion under Included work',result['items'][1]['quote_action'])
        child['completion_status']='evidence_in_progress'
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertEqual(result['items'][0]['quote_action'],'Quote this scope or identify its owning package')
        child['completion_status']='not_applicable_source_reviewed'
        parent['assembly_inputs']=[{'id':'unresolved-work','quantity':None,'unit':'LF'}]
        result=packages(Path('index.json'),self.index,self.coverage,self.snapshot)[0]
        self.assertEqual(result['items'][0]['quote_action'],'Quote this scope or identify its owning package')


if __name__=='__main__':unittest.main()
