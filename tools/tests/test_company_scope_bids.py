import copy
import hashlib
import json
import threading
import unittest
import urllib.error
import urllib.request
import test_company_scope_review as fixtures
from company_scope_review import import_scope
from company_scope_bids import build_scopes,render_markdown
from bid_comparison import required_scope_items,scope_digest,compare_quotes
from measurement_review import make_server
from measurement_store import MeasurementStore

class CompanyBidTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.CompanyScopeTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def scope(self,facts=None,overrides=None,name='new'):
        folder,config,draft=self.fixture.job(name,facts,overrides)
        draft=import_scope(draft,folder,config)
        return folder,draft,build_scopes(draft)

    def test_known_scope_retains_counts_and_unknown_dimensions_without_private_prices(self):
        _,draft,result=self.scope({'attic_HVAC':True})
        scopes={s['trade']:s for s in result['scopes']}
        self.assertEqual(scopes['Plumbing']['items'][0]['reference_quantity'],4)
        attic=scopes['Framing']['items'][0]
        self.assertIsNone(attic['reference_quantity']);self.assertIsNone(attic['purchase_quantity'])
        self.assertEqual(attic['applicability'],'included')
        for scope in scopes.values():
            self.assertEqual(scope_digest(scope),scope['scope_sha256'])
            self.assertFalse(scope['sent']);self.assertFalse(scope['scope_coverage_certified'])
            self.assertEqual(len(required_scope_items(scope)),len(scope['items'])+3)
            self.assertNotIn('unit_cost',json.dumps(scope));self.assertNotIn('markup',json.dumps(scope))
            self.assertIn('already included',render_markdown(scope))
        self.assertEqual(draft['whole_house_total'],None)

    def test_unknown_attic_is_a_conditional_trade_question_not_an_exclusion(self):
        _,_,result=self.scope()
        framing=next(s for s in result['scopes'] if s['trade']=='Framing')
        self.assertEqual(framing['items'][0]['id'],'attic-hvac-applicability')
        self.assertEqual(framing['items'][0]['applicability'],'unresolved')
        self.assertIsNone(framing['items'][0]['reference_quantity'])
        self.assertIn('Confirm whether HVAC equipment is in the attic',render_markdown(framing))

    def test_false_exclusion_and_zero_are_respected(self):
        for name,facts,overrides in [('no-attic',{'attic_HVAC':False},{}),
            ('excluded',{'attic_HVAC':True},{'framing.attic_HVAC_walkway_and_platform':'exclude_from_framing_scope'})]:
            _,_,result=self.scope(facts,{**overrides,'plumbing.exterior_hose_bibbs':0},name)
            self.assertEqual([s['trade'] for s in result['scopes']],['Plumbing','Tile'])
            item=result['scopes'][0]['items'][0]
            self.assertEqual(item['reference_quantity'],0)
            self.assertEqual(item['applicability'],'zero_saved_count')
            self.assertIn('Exclude these',item['label'])

    def test_missing_duplicate_and_wrong_source_inputs_refused(self):
        _,original,_=self.scope({'attic_HVAC':True})
        for change in ('missing','duplicate','source','locations','attic-condition'):
            draft=copy.deepcopy(original)
            water=next(r for r in draft['rows'] if r['excel_row']=='195')
            if change=='missing':water['assembly_inputs']=[]
            if change=='duplicate':water['assembly_inputs']*=2
            if change=='source':water['assembly_inputs'][0]['source_snapshot']['intake_sha256']='wrong'
            if change=='locations':water['assembly_inputs'][0]['locations']=[[1,2]]
            if change=='attic-condition':draft['company_scope_review']['unresolved_conditions']=['attic_HVAC']
            with self.subTest(change=change),self.assertRaises(ValueError):build_scopes(draft)

    def test_quantity_revision_invalidates_reviewed_quote(self):
        _,draft,result=self.scope()
        scope=next(s for s in result['scopes'] if s['trade']=='Plumbing')
        evidence=self.fixture.root/'quote.txt';evidence.write_text('Synthetic four hose-bibb quote')
        quote={'id':'test','supplier':'Synthetic supplier','source_file':evidence.name,
            'source_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest(),'date':'2026-09-19',
            'valid_through':'2026-10-19','currency':'USD','total':'100','reviewed':True,
            'reviewed_scope_sha256':scope_digest(scope),'evidence_kind':'current_supplier_quote',
            'scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'page 1'} for i in required_scope_items(scope)]}
        first=compare_quotes(scope,[quote],'2026-09-19',self.fixture.root)['quotes'][0]
        self.assertTrue(first['same_scope_current_quote'])
        item=next(r for r in draft['rows'] if r['excel_row']=='195')['assembly_inputs'][0]
        item['quantity']=5
        changed=next(s for s in build_scopes(draft)['scopes'] if s['trade']=='Plumbing')
        second=compare_quotes(changed,[quote],'2026-09-19',self.fixture.root)['quotes'][0]
        self.assertFalse(second['same_scope_current_quote']);self.assertFalse(second['purchase_authorized'])
        self.assertIsNone(second['adjusted_total'])

    def test_live_endpoint_uses_source_checked_pipeline_and_does_not_change_estimate(self):
        folder,_,expected=self.scope({'attic_HVAC':True})
        server=make_server(MeasurementStore(folder));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        def get(path):
            with urllib.request.urlopen(url+path) as response:return json.load(response)
        try:
            before=get('/api/export-snapshot');bids=get('/api/company-scope-bids')
            self.assertEqual(bids['scopes'],expected['scopes'])
            self.assertEqual(get('/api/export-snapshot'),before)
            path=folder.parent/'estimate_intake.json';raw=path.read_bytes();path.write_bytes(raw+b' ')
            with self.assertRaises(urllib.error.HTTPError) as error:get('/api/company-scope-bids')
            self.assertEqual(error.exception.code,400)
            path.write_bytes(raw);self.assertEqual(get('/api/company-scope-bids'),bids)
        finally:server.shutdown();server.server_close();thread.join()

    def test_tile_defaults_are_conditional_specifications_without_roberts_areas_or_prices(self):
        _,draft,result=self.scope()
        tile=next(s for s in result['scopes'] if s['trade']=='Tile')
        items={i['id']:i for i in tile['items']}
        floor,shower,bed,trim=[items[k] for k in ('tile-floor-underlayment','tile-shower-wall-backer','tile-shower-floor','tile-edge-finish')]
        self.assertEqual(floor['specification'],{'concrete_slab':'none_direct_to_slab','wood_floor':'cement_board','wood_floor_board_thickness_inches':0.25})
        self.assertEqual(items['tile-material-waste']['specification'],10)
        self.assertIn('whole purchase units',items['tile-material-waste']['label'])
        self.assertIsNone(shower['specification']['exact_product'])
        self.assertIn('exact product: unconfirmed',render_markdown(tile))
        self.assertEqual(bed['specification'],'mortar_bed')
        self.assertEqual(trim['specification'],'Schluter_trim')
        self.assertIn('mortar bed',render_markdown(tile))
        self.assertIn('Schluter trim',render_markdown(tile))
        for item in tile['items']:
            self.assertEqual(item['applicability'],'conditional_on_project_tile_scope')
            self.assertIsNone(item['reference_quantity']);self.assertIsNone(item['purchase_quantity'])
        self.assertNotIn('cabinet',render_markdown(tile).lower())
        self.assertTrue(all(r.get('line_cost') is None for r in draft['rows']))

    def test_tile_project_override_and_unknown_do_not_revert_to_company_default(self):
        for value in ({'wood_floor':'specified_uncoupling_membrane'},None):
            _,_,result=self.scope(overrides={'tile.floor_underlayment_by_substrate':value},name=str(value is None))
            tile=next(s for s in result['scopes'] if s['trade']=='Tile')
            floor=next(i for i in tile['items'] if i['id']=='tile-floor-underlayment')
            self.assertEqual(floor['specification'],value)
            self.assertEqual(floor['provenance'],{'basis':'project_override'})
            self.assertNotIn('cement board',floor['label'])

    def test_tile_duplicate_and_foreign_provenance_rejected(self):
        _,original,_=self.scope()
        for change in ('duplicate','source','provenance'):
            draft=copy.deepcopy(original);specs=draft['company_scope_review']['specifications']
            if change=='duplicate':specs.append(copy.deepcopy(specs[0]))
            if change=='source':specs[0]['intake_sha256']='other'
            if change=='provenance':specs[0]['provenance']=None
            with self.subTest(change=change),self.assertRaises(ValueError):build_scopes(draft)

    def test_shower_floor_and_edge_overrides_replace_defaults_in_bid(self):
        for key,identity,default in [('tile.shower_floor','tile-shower-floor','mortar bed'),
                                     ('tile.edge_finish','tile-edge-finish','Schluter trim')]:
            for value in ('project_specified_alternative',None):
                _,_,result=self.scope(overrides={key:value},name=identity+str(value))
                tile=next(s for s in result['scopes'] if s['trade']=='Tile')
                item=next(i for i in tile['items'] if i['id']==identity)
                self.assertEqual(item['specification'],value)
                self.assertEqual(item['provenance'],{'basis':'project_override'})
                self.assertNotIn(default,item['label'])
                self.assertIsNone(item['purchase_quantity'])

    def test_older_frozen_intake_does_not_gain_newer_tile_rules(self):
        folder,config,draft=self.fixture.job()
        profile_path=folder.parent/'company_profile_snapshot.json'
        profile=json.loads(profile_path.read_bytes())
        profile['rules']=[r for r in profile['rules'] if not r['key'].startswith('tile.')]
        profile_path.write_text(json.dumps(profile),encoding='utf-8')
        intake_path=folder.parent/'estimate_intake.json';intake=json.loads(intake_path.read_bytes())
        intake.update(fixtures.resolve(profile,intake['project_facts'],intake['project_overrides']))
        intake['company_profile_sha256']=hashlib.sha256(profile_path.read_bytes()).hexdigest()
        intake_path.write_text(json.dumps(intake),encoding='utf-8')
        config['intake_sha256']=hashlib.sha256(intake_path.read_bytes()).hexdigest()
        result=build_scopes(import_scope(draft,folder,config))
        self.assertNotIn('Tile',[s['trade'] for s in result['scopes']])

    def test_tile_specification_change_invalidates_quote_scope(self):
        _,draft,result=self.scope()
        scope=next(s for s in result['scopes'] if s['trade']=='Tile')
        source=self.fixture.root/'tile-quote.txt';source.write_text('Synthetic tile scope quote')
        quote={'id':'tile','supplier':'Synthetic supplier','source_file':source.name,
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'date':'2026-09-21',
            'valid_through':'2026-10-21','currency':'USD','total':'100','reviewed':True,
            'reviewed_scope_sha256':scope_digest(scope),'evidence_kind':'current_supplier_quote',
            'scope_items':[{'scope_id':i['id'],'status':'included','source_ref':'page 1'} for i in required_scope_items(scope)]}
        self.assertTrue(compare_quotes(scope,[quote],'2026-09-21',self.fixture.root)['quotes'][0]['same_scope_current_quote'])
        for index,value in [(0,{'wood_floor':'specified_membrane'}),(2,'specified_shower_pan'),(3,'specified_edge_profile')]:
            changed_draft=copy.deepcopy(draft)
            changed_draft['company_scope_review']['specifications'][index]['value']=value
            changed=next(s for s in build_scopes(changed_draft)['scopes'] if s['trade']=='Tile')
            checked=compare_quotes(changed,[quote],'2026-09-21',self.fixture.root)['quotes'][0]
            self.assertFalse(checked['same_scope_current_quote']);self.assertFalse(checked['purchase_authorized'])

    def test_building_areas_travel_with_framing_scope_without_becoming_prices(self):
        _,draft,_=self.scope({'attic_HVAC':False})
        rule={'id':'candidate-building-area-total','measurement_ids':['floor','garage'],
              'template_rows':['10'],'quantity':None}
        row=next(r for r in draft['rows'] if str(r['excel_row'])=='10')
        row['quantity_sources']=[];row['draft_quantity']=None
        draft.setdefault('pending_quantities',[]).append(rule)
        original=copy.deepcopy(draft)
        first=next(s for s in build_scopes(draft)['scopes'] if s['trade']=='Framing')
        self.assertIsNone(first['items'][0]['reference_quantity'])
        self.assertIn('Pending boundary and scope review',render_markdown(first))
        self.assertEqual(draft,original)
        draft['pending_quantities'].remove(rule)
        row['quantity_sources']=[rule];row['draft_quantity']=1200
        row['line_cost']=12345
        second=next(s for s in build_scopes(draft)['scopes'] if s['trade']=='Framing')
        self.assertEqual(second['items'][0]['reference_quantity'],1200)
        self.assertIn('do not add the total to its components',render_markdown(second))
        self.assertNotIn('12345',json.dumps(second))
        self.assertNotEqual(first['scope_sha256'],second['scope_sha256'])
        self.assertFalse(second['purchase_authorized'])

    def test_cmu_scope_uses_frozen_defaults_and_project_override_without_quantities(self):
        key='foundation.cmu_vertical_core_reinforcement'
        _,draft,result=self.scope({'foundation_wall_material':'CMU'},name='cmu')
        foundation=next(s for s in result['scopes'] if s['trade']=='Foundation')
        self.assertEqual(len(foundation['items']),3)
        self.assertEqual(foundation['items'][0]['specification']['bars_per_filled_core'],2)
        self.assertTrue(all(i['reference_quantity'] is None and i['purchase_quantity'] is None for i in foundation['items']))
        self.assertIn('fill product and yield',render_markdown(foundation))
        override={'filled_core_interval':2,'bars_per_filled_core':1,'bar_size':'#5'}
        _,_,changed=self.scope({'foundation_wall_material':'CMU'},{key:override},name='changed-cmu')
        revised=next(s for s in changed['scopes'] if s['trade']=='Foundation')
        self.assertEqual(revised['items'][0]['specification'],override)
        self.assertNotEqual(revised['scope_sha256'],foundation['scope_sha256'])
        self.assertFalse(revised['purchase_authorized'])
        for material in (None,'poured_concrete'):
            _,_,other=self.scope({'foundation_wall_material':material},name=str(material))
            self.assertNotIn('Foundation',[s['trade'] for s in other['scopes']])

if __name__=='__main__':unittest.main()
