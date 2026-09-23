"""Prove saved edits update physical quantities, template rows and draft outputs."""
import csv
import io
import json
import math
import sqlite3
import threading
import unittest
import urllib.request
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP

import test_slab_review as review_tests
from slab_review import ReviewStore, Conflict, make_server, trade_draft
from slab_outputs import estimate_csv, material_notes


class OutputTests(unittest.TestCase):
    def test_historical_mesh_confirmation_is_not_republished(self):
        self.profile['material_specs']={'welded_wire_mesh':'Remesh roll','mesh_lap_inches':6}
        self.write_profile()
        saved=self.save_blue(self.config['initial_points'])
        saved['construction']['outputs']['material_notes']=[
            'Reinforcement: Remesh roll, confirmed by Jason. 6-inch overlaps confirmed by Jason.']
        before=json.dumps(saved,sort_keys=True)
        text=trade_draft(self.config,saved)
        self.assertIn('not a verified code splice',text)
        self.assertNotIn('6-inch overlaps confirmed',text)
        self.assertEqual(before,json.dumps(saved,sort_keys=True))

    def test_mesh_overlap_is_an_allowance_not_code_confirmation(self):
        notes=material_notes({'material_specs':{'welded_wire_mesh':'Remesh roll',
            'mesh_lap_inches':6}})
        mesh=next(n for n in notes if n.startswith('Reinforcement:'))
        self.assertIn('6-inch sheet-edge overlap used for the provisional roll calculation',mesh)
        self.assertIn('not a verified code splice',mesh)
        self.assertIn('cross-wire end overhangs',mesh)
        self.assertNotIn('overlaps confirmed',mesh)

    setUpBase=review_tests.ReviewTests.setUp
    tearDown=review_tests.ReviewTests.tearDown
    payload=review_tests.ReviewTests.payload

    def setUp(self):
        self.setUpBase()
        self.legacy=self.store.read()
        self.profile={'schema':'jnj.slab-construction.v1','plan_sha256':self.config['plan_sha256'],
            'outline':'blue','reference_points':self.config['initial_points'],'edge_roles':['bearing','bearing','thickened','thickened'],
            'slab_inches':4,'waste_percent':10,'exterior':{'total_depth_inches':24,'bottom_width_inches':16,
            'vertical_inches_above_bottom':8,'angle_degrees':45},
            'interior_grade_beam':{'eligible_wall_lf':0,'total_depth_inches':8,'bottom_width_inches':12,'angle_degrees':45},
            'concrete_item_id':'concrete','pricing_as_of':'2026-09-09','prices':{},'required_information':['TEST ONLY: resolve project specifications']}
        self.write_profile()

    def write_profile(self):
        (self.folder/'construction_profile.json').write_text(json.dumps(self.profile))
        self.store=ReviewStore(self.folder)

    def save_blue(self,points=None,version=1):return self.store.save(dict(self.payload(points,version),outline='blue'))

    def test_pump_is_one_charge_and_second_charge_only_for_separate_pour(self):
        from slab_outputs import calculate_outputs
        config=json.loads(json.dumps(self.config))
        config['assembly']['lines'].append({'estimate_item_id':'pump','name':'Pump','unit':'hours','markup_value':10})
        self.profile['pump']={'estimate_item_id':'pump','separate_footer_mobilizations':0}
        self.profile['prices']['pump']={'unit':'mobilization','unit_price':1500,'currency':'USD','source':'TEST builder rate',
            'date':'2026-09-09','valid_through':'2026-09-09'}
        def calculate():return calculate_outputs(config,config['initial_points'],self.profile)['estimate_rows'][-1]
        row=calculate();self.assertEqual((row['quantity'],row['cost'],row['sell_amount']),(1,1500,1650))
        self.profile['pump']['separate_footer_mobilizations']=1
        row=calculate();self.assertEqual((row['quantity'],row['cost'],row['sell_amount']),(2,3000,3300))
        self.profile['pump']['separate_footer_mobilizations']=True
        with self.assertRaises(ValueError):calculate()

    def test_unmapped_material_cost_bulk_break_and_expired_price(self):
        from slab_outputs import apply_price
        def row():return {'quantity':8,'unit':'stick','unit_price':None,'cost':None,'sell_amount':None,'markup_percent':None}
        price={'unit_price':14.33,'bulk_unit_price':12.18,'bulk_minimum':50,'unit':'stick','currency':'USD',
            'date':'2026-09-09','valid_through':'2026-09-09','source':'TEST retailer'}
        for qty,expected in [(49,114.64),(50,97.44),(87,97.44)]:
            r=row();apply_price(r,price,'2026-09-09',bulk_quantity=qty)
            self.assertEqual(r['cost'],expected);self.assertIsNone(r['sell_amount']);self.assertIsNone(r['markup_percent'])
        for changed in ({'unit':'box'},{'valid_through':'2026-09-08'}):
            r=row();apply_price(r,dict(price,**changed),'2026-09-09',bulk_quantity=87)
            self.assertIsNone(r['unit_price']);self.assertIsNone(r['cost'])

    def test_concrete_finish_and_joint_preferences_preserve_quantity_and_history(self):
        old=self.save_blue();old_csv=estimate_csv(old);old_draft=trade_draft(self.config,old)
        self.profile['concrete_mix']={'strength_psi':3000,'target_slump_inches':5,'grade':'interior','finish':'smooth_trowel'}
        self.profile['saw_cut_preferences']={'spacing_min_ft':12,'spacing_max_ft':15,'symmetrical':True}
        self.write_profile();new=self.save_blue(points=old['points'],version=2)
        self.assertEqual(new['construction']['outputs']['concrete'],old['construction']['outputs']['concrete'])
        self.assertEqual(new['construction']['profile']['slab_inches'],4)
        row=new['construction']['outputs']['estimate_rows'][0];prior=old['construction']['outputs']['estimate_rows'][0]
        for key in ('quantity','unit','estimate_item_id','markup_percent'):self.assertEqual(row[key],prior[key])
        self.assertIn('3000 PSI interior grade, 5-inch slump',estimate_csv(new))
        self.assertIn('smooth trowel finish',trade_draft(self.config,new))
        self.assertIn('symmetrical cuts',trade_draft(self.config,new))
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        self.assertFalse(new['construction']['outputs']['verification_valid'])
        for invalid in (0,-1,True,float('nan')):
            self.profile['concrete_mix']['target_slump_inches']=invalid
            with self.assertRaisesRegex(ValueError,'target slump'):self.write_profile()
        self.profile['concrete_mix']['target_slump_inches']=5
        self.profile['saw_cut_preferences']['spacing_min_ft']=16
        with self.assertRaisesRegex(ValueError,'ordered positive spacing'):self.write_profile()

    def test_edit_updates_quantity_csv_draft_and_reload_without_changing_red(self):
        first=self.save_blue(self.config['initial_points'])
        second=self.save_blue(version=2)
        a=first['construction']['outputs']; b=second['construction']['outputs']
        self.assertGreater(b['concrete']['with_waste_cy'],a['concrete']['with_waste_cy'])
        self.assertEqual(b['estimate_rows'][0]['quantity'],round(b['concrete']['with_waste_cy'],9))
        text=trade_draft(self.config,second)
        self.assertIn(f"Concrete allowance including waste: {b['concrete']['with_waste_cy']:.2f} CY",text)
        row=list(csv.DictReader(io.StringIO(estimate_csv(second))))[0]
        self.assertEqual(row['measurement_version'],'3')
        self.assertAlmostEqual(float(row['quantity']),b['estimate_rows'][0]['quantity'])
        reopened=ReviewStore(self.folder)
        self.assertEqual(reopened.read(2),first)
        self.assertEqual(reopened.read(3),second)
        self.assertEqual(reopened.read(1),self.legacy)
        self.assertFalse(b['verification_valid'])
        self.assertIsNone(b['current_total'])

    def test_dated_fixture_price_updates_cost_to_cent_and_preserves_old_price_version(self):
        # Synthetic price checks arithmetic only; it is never installed in the Roberts profile.
        self.profile['prices']={'concrete':{'source':'TEST ONLY synthetic quote','unit':'CY','currency':'USD',
            'date':'2026-09-09','valid_through':'2026-10-09','unit_price':'200.01'}}
        self.write_profile(); first=self.save_blue(self.config['initial_points'])
        second=self.save_blue(version=2)
        row=second['construction']['outputs']['estimate_rows'][0]
        expected=(Decimal(str(row['quantity']))*Decimal('200.01')).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        self.assertEqual(Decimal(str(row['cost'])),expected)
        self.assertGreater(row['cost'],first['construction']['outputs']['estimate_rows'][0]['cost'])
        self.profile['prices']['concrete']['unit_price']='210.01';self.write_profile()
        self.assertEqual(self.store.read(2),first)
        self.assertIn(f"{expected:.2f}",trade_draft(self.config,second))

    def test_expired_price_does_not_become_current(self):
        self.profile['prices']={'concrete':{'source':'TEST ONLY expired quote','unit':'CY','currency':'USD',
            'date':'2026-01-01','valid_through':'2026-08-01','unit_price':'100'}}
        self.write_profile()
        r=self.save_blue()['construction']['outputs']
        self.assertIsNone(r['estimate_rows'][0]['cost']);self.assertIsNone(r['current_total'])

    def test_material_answers_preserve_units_previous_versions_and_concrete(self):
        before=self.save_blue()
        self.profile['material_specs']={'gravel_depth_inches':4,'vapor_barrier_reported':'6 millimeter plastic sheet'}
        self.write_profile(); after=self.save_blue(version=2)
        result=after['construction']['outputs']
        self.assertEqual(result['concrete'],before['construction']['outputs']['concrete'])
        self.assertIn('4 inches thick',result['material_notes'][0])
        self.assertIn('6 millimeter plastic sheet',result['material_notes'][1])
        self.assertIn('Confirm 6 mil',trade_draft(self.config,after))
        self.assertEqual(ReviewStore(self.folder).read(2),before)
        self.assertEqual(ReviewStore(self.folder).read(3),after)
        self.assertIsNone(result['current_total'])

    def test_invalid_gravel_depth_is_rejected(self):
        for depth in (0,-4,True,float('nan'),float('inf')):
            self.profile['material_specs']={'gravel_depth_inches':depth}
            with self.subTest(depth=depth),self.assertRaises(ValueError):self.write_profile()

    def test_confirmed_plastic_and_added_grid_survive_export_without_rewriting_history(self):
        self.profile['material_specs']={'vapor_barrier_reported':'6 millimeter plastic sheet'}
        self.write_profile();before=self.save_blue()
        self.profile['material_specs'].update(vapor_barrier_mil=6,vapor_roll_coverage_sf=2000,welded_wire_mesh='4x4 welded wire mesh rolls',rebar_grid_included=True)
        self.write_profile();after=self.save_blue(version=2)
        text=trade_draft(self.config,after)
        self.assertIn('6 mil plastic (0.1524 mm)',text)
        self.assertIn('2000 SF per roll',text)
        self.assertNotIn('Confirm 6 mil',text)
        self.assertIn('4x4 welded wire mesh rolls',text)
        self.assertIn('Additional #4 rebar grid included',text)
        row=list(csv.DictReader(io.StringIO(estimate_csv(after))))[-1]
        self.assertEqual(row['name'],'Additional #4 rebar grid')
        self.assertEqual(row['quantity'],'');self.assertEqual(row['estimate_item_id'],'')
        self.assertIn('mapping required',row['quantity_status'])
        self.assertEqual(ReviewStore(self.folder).read(2),before)
        self.assertEqual(after['construction']['outputs']['concrete'],before['construction']['outputs']['concrete'])
        self.profile['material_specs']['vapor_roll_coverage_sf']=0
        with self.assertRaises(ValueError):self.write_profile()

    def test_product_confirmation_reaches_draft_and_preserves_prior_material_notes(self):
        self.profile['material_specs']={'vapor_barrier_mil':6,'vapor_roll_coverage_sf':2000,
                                       'welded_wire_mesh':'4x4 welded wire mesh rolls'}
        self.write_profile();before=self.save_blue()
        self.profile['material_specs'].update(vapor_product_name='HDX CFHD0620C, 20 ft x 100 ft clear sheeting',
            welded_wire_mesh='Home Depot concrete remesh model 75011, 5 ft x 150 ft rolls (750 gross SF)',
            mesh_product_confirmed=True)
        self.write_profile();after=self.save_blue(version=2)
        text=trade_draft(self.config,after)
        self.assertIn('HDX CFHD0620C, 20 ft x 100 ft',text)
        self.assertIn('model 75011, 5 ft x 150 ft rolls (750 gross SF)',text)
        self.assertIn('Cutting layout and laps remain unresolved.',text)
        self.assertNotIn('Wire gauge, roll dimensions',text)
        self.assertEqual(ReviewStore(self.folder).read(2),before)
        self.assertEqual(after['construction']['outputs']['concrete'],before['construction']['outputs']['concrete'])
        self.assertEqual(after['construction']['outputs']['estimate_rows'],before['construction']['outputs']['estimate_rows'])
        self.assertIsNone(after['construction']['outputs']['current_total'])

    def test_backfill_does_not_automatically_add_rebar(self):
        for included in (None,False,True):
            with self.subTest(included=included):
                self.profile['material_specs']={'backfilled':True,'rebar_grid_included':included}
                self.write_profile()
                from slab_outputs import calculate_outputs
                result=calculate_outputs(self.config,self.config['initial_points'],self.profile)
                self.assertEqual(any(r['name']=='Additional #4 rebar grid' for r in result['estimate_rows']),included is True)
                self.assertIsNone(result['current_total'])
        self.profile['material_specs']['rebar_grid_included']='yes'
        with self.assertRaises(ValueError):self.write_profile()

    def test_grid_spacing_is_recorded_but_missing_clearances_do_not_become_bar_counts(self):
        self.profile['material_specs']={'rebar_grid_included':True,'rebar_grid_spacing_inches':[12,12]}
        self.write_profile();snap=self.save_blue()
        self.assertIn('12 by 12 inches on center',trade_draft(self.config,snap))
        self.assertIsNone(snap['construction']['outputs']['estimate_rows'][-1]['quantity'])
        for spacing in ([12,0],[12],True,[12,float('nan')]):
            self.profile['material_specs']['rebar_grid_spacing_inches']=spacing
            with self.subTest(spacing=spacing),self.assertRaises(ValueError):self.write_profile()

    def test_grid_edit_updates_cut_quantity_and_preserves_saved_version(self):
        before=self.save_blue(self.config['initial_points'])
        self.profile['material_specs']={'rebar_grid_included':True,'rebar_grid_spacing_inches':[12,12],
            'rebar_grid_setback_inches':6,'rebar_grid_lap_inches':6,'rebar_stock_length_ft':20}
        self.write_profile();first=self.save_blue(self.config['initial_points'],version=2)
        second=self.save_blue(version=3)
        a=first['construction']['outputs'];b=second['construction']['outputs']
        self.assertGreater(b['rebar_grid']['cut_lf'],a['rebar_grid']['cut_lf'])
        row=list(csv.DictReader(io.StringIO(estimate_csv(second))))[-1]
        self.assertAlmostEqual(float(row['quantity']),b['rebar_grid']['cut_lf'])
        self.assertEqual(row['estimate_item_id'],'');self.assertEqual(row['unit_price'],'')
        self.assertIn('6-inch edge setback and 6-inch bar overlap',trade_draft(self.config,second))
        self.assertIn('| Stock stick |',trade_draft(self.config,second))
        self.assertEqual(ReviewStore(self.folder).read(2),before)
        self.assertEqual(ReviewStore(self.folder).read(3),first)
        self.assertFalse(b['verification_valid']);self.assertIsNone(b['current_total'])

    def test_roll_counts_follow_edits_and_keep_old_versions_and_markup(self):
        # Rebuild only this disposable fixture with the two existing material rows.
        self.config['assembly']['lines'] += [
            {'estimate_item_id':'plastic','name':'Vapor Barrier','unit':'each','formula':'round({QTY}/2000)','markup_value':17},
            {'estimate_item_id':'mesh','name':'Wire Mesh','unit':'roll','formula':'round({QTY}/750)','markup_value':19}]
        (self.folder/'review_config.json').write_text(json.dumps(self.config))
        self.store.database.unlink();self.write_profile()
        before=self.save_blue(self.config['initial_points'])
        self.profile['roll_item_ids']={'plastic':'plastic','mesh':'mesh'}
        self.profile['material_specs']={'vapor_barrier_mil':6,'vapor_roll_coverage_sf':2000,'vapor_lap_inches':6,
            'vapor_product':{'width_ft':20,'length_ft':100},'welded_wire_mesh':'Confirmed mesh','mesh_lap_inches':6,
            'mesh_product':{'width_ft':5,'length_ft':150}}
        self.write_profile();first=self.save_blue(self.config['initial_points'],version=2)
        second=self.save_blue([[100,100],[600,100],[600,500],[100,500]],version=3)
        rows=list(csv.DictReader(io.StringIO(estimate_csv(second))))
        self.assertEqual([r['quantity'] for r in rows[1:]],['2','3'])
        self.assertEqual([r['unit'] for r in rows[1:]],['roll','roll'])
        self.assertEqual([r['markup_percent'] for r in rows[1:]],['17.0','19.0'])
        self.assertTrue(all(r['unit_price']=='' for r in rows))
        self.assertIn('6-inch overlaps confirmed',trade_draft(self.config,second))
        self.assertIn('| Strip | Roll |',trade_draft(self.config,second))
        self.assertEqual(ReviewStore(self.folder).read(2),before)
        self.assertEqual(ReviewStore(self.folder).read(3),first)
        self.assertIsNone(second['construction']['outputs']['current_total'])

    def test_whole_purchase_rows_preserve_measurements_prices_and_history(self):
        before=self.save_blue(self.config['initial_points'])
        old_csv=estimate_csv(before);old_draft=trade_draft(self.config,before)
        self.profile['purchase_rounding']='whole_units'
        self.profile['material_specs']={'rebar_grid_included':True,'rebar_grid_spacing_inches':[12,12],
            'rebar_grid_setback_inches':6,'rebar_grid_lap_inches':6,'rebar_stock_length_ft':20}
        self.profile['prices']={'concrete':{'source':'TEST ONLY synthetic quote','unit':'CY','currency':'USD',
            'date':'2026-09-09','valid_through':'2026-10-09','unit_price':'200'}}
        self.write_profile();after=self.save_blue(self.config['initial_points'],version=2)
        r=after['construction']['outputs'];row=r['estimate_rows'][0]
        from slab_materials import whole_units
        self.assertEqual(row['quantity'],whole_units(r['concrete']['with_waste_cy']))
        self.assertEqual(row['cost'],row['quantity']*200)
        self.assertEqual(row['measured_quantity'],r['concrete']['with_waste_cy'])
        self.assertEqual(r['estimate_rows'][-1]['quantity'],r['rebar_grid']['stock_count'])
        self.assertEqual(r['estimate_rows'][-1]['unit'],'stick')
        self.assertIn('measured_quantity',estimate_csv(after))
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        self.assertEqual(ReviewStore(self.folder).read(3),after)
        edited=self.save_blue(version=3)['construction']['outputs']
        self.assertGreater(edited['estimate_rows'][0]['quantity'],row['quantity'])
        self.assertFalse(edited['verification_valid'])

    def test_roll_mapping_cannot_replace_concrete_or_unknown_rows(self):
        for mapping in ({'plastic':'concrete'},{'mesh':'missing'},{'plastic':'a','mesh':'a'}):
            self.profile['roll_item_ids']=mapping
            with self.subTest(mapping=mapping),self.assertRaises(ValueError):self.write_profile()

    def test_confirmed_lap_without_product_dimensions_withholds_roll_quantity(self):
        self.profile['material_specs']={'vapor_barrier_mil':6,'vapor_lap_inches':6}
        self.write_profile();r=self.save_blue()['construction']['outputs']
        self.assertNotIn('roll_layouts',r)
        self.assertIn('plastic',r['roll_layout_errors'])
        self.assertIn('Plastic quantity withheld',' '.join(r['material_notes']))

    def test_changed_topology_withholds_material_quantities(self):
        points=[[100,100],[200,100],[300,100],[300,200],[100,200]]
        snap=self.save_blue(points)
        r=snap['construction']['outputs']
        self.assertFalse(r['calculation_valid'])
        self.assertIsNone(r['estimate_rows'][0]['quantity'])
        self.assertIn('withheld',trade_draft(self.config,snap))

    def test_rule_changes_require_restart_and_tampered_saved_outputs_are_refused(self):
        snap=self.save_blue()
        snap['construction']['outputs']['concrete']['with_waste_cy']=999
        with closing(sqlite3.connect(self.store.database)) as db,db:
            db.execute('UPDATE versions SET snapshot=? WHERE version=2',(json.dumps(snap),))
        with self.assertRaises(Conflict):self.store.read(2)
        self.profile['waste_percent']=15
        (self.folder/'construction_profile.json').write_text(json.dumps(self.profile))
        with self.assertRaises(Conflict):self.store.save(dict(self.payload(version=2),outline='blue'))

    def test_http_preview_and_saved_export_use_same_quantities(self):
        server=make_server(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        def post(path,payload):
            request=urllib.request.Request(url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':url})
            with urllib.request.urlopen(request) as response:return json.load(response)
        try:
            payload=dict(self.payload(),outline='blue')
            preview=post('/api/preview',{'points':payload['points'],'outline':'blue'})['construction']
            saved=post('/api/save',payload)
            self.assertEqual(saved['construction']['outputs'],preview)
            with urllib.request.urlopen(url+'/estimate/2.csv') as response:
                row=list(csv.DictReader(io.StringIO(response.read().decode('utf-8-sig'))))[0]
            self.assertAlmostEqual(float(row['quantity']),preview['estimate_rows'][0]['quantity'])
            with urllib.request.urlopen(url+'/draft/2.md') as response:
                self.assertIn(f"{preview['concrete']['with_waste_cy']:.2f} CY",response.read().decode())
        finally:server.shutdown();server.server_close();thread.join()


    def test_revised_laps_update_cuts_exports_and_preserve_history(self):
        self.profile['purchase_rounding']='whole_units'
        self.profile['material_specs']={'rebar_grid_included':True,'rebar_grid_spacing_inches':[12,12],
            'rebar_grid_setback_inches':6,'rebar_grid_lap_inches':6,'rebar_stock_length_ft':20,
            'footer_rebar_runs':2,'footer_rebar_size':'#4'}
        self.write_profile();before=self.save_blue();old_csv=estimate_csv(before);old_draft=trade_draft(self.config,before)
        self.profile['material_specs'].update(rebar_lap_rule='irc2024_no4_grade60',rebar_grade=60,
            rebar_grid_lap_inches=30,footer_rebar_lap_inches=30)
        self.write_profile();after=self.save_blue(version=2)
        old=before['construction']['outputs'];new=after['construction']['outputs'];grid=new['rebar_grid']
        self.assertEqual(grid['lap_inches'],30)
        self.assertEqual(grid['net_lf'],old['rebar_grid']['net_lf'])
        self.assertGreater(grid['cut_lf'],old['rebar_grid']['cut_lf'])
        for run in grid['segments']:
            self.assertAlmostEqual(sum(run['cuts_ft'])-run['splice_count']*2.5,run['net_lf'])
        self.assertEqual(new['footer_rebar']['lap_inches'],30)
        self.assertIsNone(new['purchase_materials']['footer_rebar']['quantity'])
        self.assertIn('30-inch laps',estimate_csv(after));self.assertIn('30-inch laps',trade_draft(self.config,after))
        self.assertNotIn('6-inch bar overlap',trade_draft(self.config,after))
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        self.assertEqual(new['concrete'],old['concrete'])
        self.assertFalse(new['verification_valid'])

    def test_revised_lap_rule_rejects_short_or_unsupported_rebar(self):
        from slab_outputs import material_notes
        specs={'rebar_lap_rule':'irc2024_no4_grade60','rebar_grade':60,'rebar_grid_included':True,
            'rebar_grid_lap_inches':30,'footer_rebar_runs':2,'footer_rebar_size':'#4','footer_rebar_lap_inches':30}
        for key,value in [('rebar_grid_lap_inches',6),('footer_rebar_lap_inches',6),('footer_rebar_lap_inches',None),
            ('rebar_grid_lap_inches',float('nan')),('rebar_grade',40),('footer_rebar_size','#5')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                material_notes({'material_specs':dict(specs,**{key:value})})
        material_notes({'material_specs':dict(specs,rebar_grid_lap_inches=36,footer_rebar_lap_inches=36)})

    def test_wall_connection_budget_exports_without_rewriting_old_pending_count(self):
        self.profile['purchase_rounding']='whole_units'
        self.profile['material_specs']={'footer_rebar_runs':2,'footer_rebar_size':'#4','rebar_stock_length_ft':20,
            'rebar_lap_rule':'irc2024_no4_grade60','rebar_grade':60,'footer_rebar_lap_inches':30}
        self.write_profile();old=self.save_blue();old_csv=estimate_csv(old);old_draft=trade_draft(self.config,old)
        self.profile['material_specs'].update(footer_end_connection='lap_to_projecting_wall_rebar',footer_stock_basis='gross_boundary_budget')
        self.write_profile();new=self.save_blue(version=2);r=new['construction']['outputs'];f=r['footer_rebar']
        self.assertEqual(r['purchase_materials']['footer_rebar']['quantity'],f['budget_sticks'])
        self.assertIsNone(f['purchase_sticks']);self.assertFalse(r['verification_valid'])
        self.assertIn('Footer #4 rebar (budget allowance)',estimate_csv(new))
        self.assertIn('confirmed by Jason',trade_draft(self.config,new))
        self.assertIn('wall-bar lap connections',trade_draft(self.config,new))
        self.assertIsNone(old['construction']['outputs']['purchase_materials']['footer_rebar']['quantity'])
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        self.assertEqual(r['concrete'],old['construction']['outputs']['concrete'])

    def test_mesh_span_history_and_exports_keep_grid_support_request(self):
        self.profile.update(purchase_rounding='whole_units',support_rules={
            'grid':{'model':'911','pack_size':50,'source':'TEST'},
            'mesh':{'model':'944','pack_size':100,'spacing_inches':24,'source':'TEST'}})
        self.profile['material_specs']={'substrate_extent':'footer_haunch_junction','bearing_overlap_inches':4,
            'gravel_thickness_direction':'perpendicular','gravel_depth_inches':4,'rebar_grid_included':True,
            'rebar_grid_spacing_inches':[12,12],'rebar_grid_setback_inches':6,'rebar_grid_lap_inches':30,'rebar_stock_length_ft':20}
        self.write_profile();old=self.save_blue();old_csv=estimate_csv(old);old_draft=trade_draft(self.config,old)
        self.profile['material_specs']['deep_edge_support']={'mesh':'mesh_spans_slope','grid':'chairs'}
        self.write_profile();new=self.save_blue(version=2);r=new['construction']['outputs']
        text=estimate_csv(new)
        self.assertNotIn('Mesh supports at thickened edges',text)
        self.assertIn('Grid supports at thickened edges',text)
        self.assertIn('Mesh itself spans the slope',trade_draft(self.config,new))
        self.assertFalse(r['verification_valid'])
        self.assertEqual(r['rebar_grid'],old['construction']['outputs']['rebar_grid'])
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        prior_csv=estimate_csv(new);prior_draft=trade_draft(self.config,new)
        self.profile['material_specs']['grid_edge_chair_height_inches']=2
        self.profile['support_rules']['grid_edge']={'model':'GRPROLK42B','pack_size':40,'height_inches':2}
        self.write_profile();height_version=self.save_blue(version=3)
        updated=height_version['construction']['outputs']
        edge=updated['purchase_materials']['grid_edge_chairs']
        self.assertEqual(edge['quantity'],math.ceil(r['chair_allowances']['grid']['special_height_count']/40))
        self.assertNotIn('Grid supports at thickened edges',estimate_csv(height_version))
        self.assertIn('2-inch rebar chairs at thickened edges',estimate_csv(height_version))
        self.assertIn('Jason confirmed 2-inch rebar chairs',trade_draft(self.config,height_version))
        self.assertEqual(updated['purchase_materials']['grid_chairs'],r['purchase_materials']['grid_chairs'])
        self.assertEqual(updated['rebar_grid'],r['rebar_grid'])
        self.assertEqual(estimate_csv(self.store.read(3)),prior_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(3)),prior_draft)
        self.assertFalse(updated['verification_valid'])
        for invalid in (0,-1,True,float('nan')):
            self.profile['material_specs']['grid_edge_chair_height_inches']=invalid
            with self.assertRaisesRegex(ValueError,'positive edge chair height'):self.write_profile()
        self.profile['material_specs']['grid_edge_chair_height_inches']=2
        self.profile['material_specs']['deep_edge_support']={'grid':'mesh_spans_slope'}
        with self.assertRaisesRegex(ValueError,'separately'):self.write_profile()


class LaborScopeTests(unittest.TestCase):
    setUpBase=review_tests.ReviewTests.setUp
    tearDown=review_tests.ReviewTests.tearDown
    write_profile=OutputTests.write_profile

    def setUp(self):
        OutputTests.setUp(self)
        config=json.loads(json.dumps(self.config))
        config['assembly']['lines'].append({'estimate_item_id':'labor','name':'Labor','type':'LABOR',
            'unit':'sq ft','formula':'round({QTY}*0.9)','markup_value':12,'markup_unit':'PERCENT'})
        folder=self.folder/'labor';folder.mkdir()
        for name in ('plan.pdf','sheet-4.png'):(folder/name).write_bytes((self.folder/name).read_bytes())
        (folder/'review_config.json').write_text(json.dumps(config),encoding='utf-8')
        (folder/'construction_profile.json').write_text(json.dumps(self.profile),encoding='utf-8')
        self.store=ReviewStore(folder);self.config=config
        self.labor={'estimate_item_id':'labor','bulk_grading_by':'separate_grader',
            'included_scopes':['touch-up grading','steel placement','finishing','saw cuts'],'bobcat_budget_usd':300}

    def test_labor_scope_and_one_budget_preserve_prices_quantities_and_saved_history(self):
        payload={'base_version':1,'plan_sha256':self.config['plan_sha256'],'points':self.config['initial_points'],'outline':'blue','note':'test'}
        old=self.store.save(payload);old_csv=estimate_csv(old);old_draft=trade_draft(self.config,old)
        self.profile['slab_labor']=self.labor
        path=self.store.folder/'construction_profile.json';path.read_text(encoding='utf-8')
        path.write_text(json.dumps(self.profile),encoding='utf-8');self.store=ReviewStore(self.store.folder)
        new=self.store.save(dict(payload,base_version=2));result=new['construction']['outputs']
        rows=result['estimate_rows'];self.assertEqual(len(rows),3)
        labor=next(r for r in rows if r['estimate_item_id']=='labor');budget=rows[-1]
        self.assertEqual(labor['markup_percent'],12);self.assertEqual(labor['unit'],'sq ft')
        self.assertIsNone(labor['quantity']);self.assertIn('saw cuts included',labor['name'])
        self.assertEqual((budget['scope'],budget['quantity'],budget['budget_cost']),('bobcat_use',1,300))
        for key in ('unit_price','cost','sell_amount','markup_percent'):self.assertIsNone(budget[key])
        self.assertIsNone(result['priced_subtotal']);self.assertIsNone(result['current_total'])
        self.assertEqual(result['concrete'],old['construction']['outputs']['concrete'])
        exported=list(csv.DictReader(io.StringIO(estimate_csv(new))))
        self.assertEqual([r['budget_cost'] for r in exported],['','','300'])
        self.assertIn('~$300.00 budget',trade_draft(self.config,new))
        self.assertIn('Bulk grading is priced separately',trade_draft(self.config,new))
        self.assertEqual(estimate_csv(self.store.read(2)),old_csv)
        self.assertEqual(trade_draft(self.config,self.store.read(2)),old_draft)
        self.assertEqual(self.store.read(3),new)

    def test_labor_rate_follows_net_area_and_preserves_history(self):
        from slab_outputs import calculate_outputs
        payload={'base_version':1,'plan_sha256':self.config['plan_sha256'],'points':self.config['initial_points'],'outline':'blue','note':'test'}
        before=self.store.save(payload);before_csv=estimate_csv(before)
        self.profile['slab_labor']=dict(self.labor,billing_basis='measured_net_sf')
        self.profile['purchase_rounding']='whole_units'
        self.profile['pricing_notes']=['TEST ONLY']
        self.profile['prices']['labor']={'unit_price':1.75,'unit':'sq ft','source':'TEST builder rate','currency':'USD',
            'date':'2026-09-09','valid_through':'2026-09-09'}
        path=self.store.folder/'construction_profile.json';path.read_text(encoding='utf-8')
        path.write_text(json.dumps(self.profile),encoding='utf-8');self.store=ReviewStore(self.store.folder)
        snapshots=[]
        for version,right,expected_sf,cost,sell in [(2,300,200,350,392),(3,400,300,525,588),(4,300.125,200.125,350.22,392.25)]:
            points=[[100,100],[right,100],[right,200],[100,200]]
            snap=self.store.save(dict(payload,base_version=version,points=points));snapshots.append(snap)
            result=snap['construction']['outputs'];labor=next(r for r in result['estimate_rows'] if r['estimate_item_id']=='labor')
            self.assertEqual((labor['quantity'],labor['cost'],labor['sell_amount']),(expected_sf,cost,sell))
            self.assertEqual(labor['quantity'],snap['results']['net_sf'])
            self.assertEqual(result['estimate_rows'][-1]['budget_cost'],300)
            self.assertEqual(result['priced_cost_subtotal'],cost)
            self.assertNotIn('Slab labor, tax',trade_draft(self.config,snap))
            self.assertIsNone(result['current_total'])
        reopened=ReviewStore(self.store.folder)
        self.assertEqual(estimate_csv(reopened.read(2)),before_csv)
        for snap in snapshots:
            self.assertEqual(reopened.read(snap['version']),snap)
            self.assertIn('1.75',estimate_csv(snap))
        invalid=calculate_outputs(self.config,[[100,100],[300,101],[300,200],[100,200]],self.profile)
        labor=next(r for r in invalid['estimate_rows'] if r['estimate_item_id']=='labor')
        self.assertIsNone(labor['quantity']);self.assertIsNone(labor['cost'])
        self.assertIn('Slab labor, tax',' '.join(invalid['material_notes']))
        self.profile['slab_labor']['billing_basis']='unknown'
        with self.assertRaisesRegex(ValueError,'billing basis'):
            calculate_outputs(self.config,self.config['initial_points'],self.profile)

    def test_invalid_budgets_and_material_or_missing_labor_mapping_are_rejected(self):
        from slab_outputs import calculate_outputs
        for bad in (-1,True,float('nan'),float('inf'),None):
            self.profile['slab_labor']=dict(self.labor,bobcat_budget_usd=bad)
            with self.subTest(budget=bad),self.assertRaisesRegex(ValueError,'Bobcat budget'):
                calculate_outputs(self.config,self.config['initial_points'],self.profile)
        for bad in ('concrete','missing'):
            self.profile['slab_labor']=dict(self.labor,estimate_item_id=bad)
            with self.subTest(mapping=bad),self.assertRaisesRegex(ValueError,'separate existing labor row'):
                calculate_outputs(self.config,self.config['initial_points'],self.profile)
        self.profile['slab_labor']=dict(self.labor,bobcat_budget_usd=0)
        result=calculate_outputs(self.config,self.config['initial_points'],self.profile)
        self.assertEqual(result['estimate_rows'][-1]['budget_cost'],0)


class PricingPolicyTests(unittest.TestCase):
    setUp=LaborScopeTests.setUp
    tearDown=LaborScopeTests.tearDown
    setUpBase=review_tests.ReviewTests.setUp
    write_profile=OutputTests.write_profile

    def policy(self,keys):
        return {'material_markup_percent':15,'labor_markup_percent':7,'source':'TEST approval',
            'delivery':{'cost':79,'source':'TEST delivery'},
            'retail_tax':{'percent':8,'source':'TEST tax','effective_from':'2026-07-01','effective_through':'2026-09-30'},
            'row_mapping':{k:{'row_id':'TEST-'+k,'origin':'test fixture'} for k in keys}}

    def test_purchase_tax_delivery_and_markup_are_applied_once(self):
        from slab_outputs import apply_estimate_policy
        self.profile['pricing_as_of']='2026-09-10';self.profile['slab_labor']=self.labor
        self.profile['pricing_policy']=self.policy(['concrete','plastic','labor','bobcat_use','retail_delivery'])
        def rows():return [
            {'estimate_item_id':'concrete','cost':100,'sell_amount':100,'price_source':'TEST inclusive','price_status':'tax included'},
            {'estimate_item_id':'plastic','cost':100,'sell_amount':100,'price_source':'https://www.homedepot.com/p/TEST','price_status':'TEST'},
            {'estimate_item_id':'labor','cost':200,'sell_amount':200,'price_status':'TEST'},
            {'estimate_item_id':None,'scope':'bobcat_use','cost':None,'sell_amount':None,'budget_cost':300,'price_status':'TEST'}]
        result=rows();apply_estimate_policy(result,self.profile)
        self.assertEqual([r['purchase_tax'] for r in result],[0,8,0,None,6.32])
        self.assertEqual([r['sell_amount'] for r in result],[115,124.2,214,None,98.12])
        self.assertEqual(result[3]['budget_sell_amount'],321)
        self.assertEqual(sum(Decimal(str(r['cost'] if r['cost'] is not None else r['budget_cost'])) for r in result),Decimal('793.32'))
        self.profile['prices']['plastic']={'tax_included':True}
        result=rows();apply_estimate_policy(result,self.profile)
        self.assertEqual(result[1]['purchase_tax'],0);self.assertEqual(result[1]['sell_amount'],115)
        self.profile['pricing_policy']['row_mapping']['plastic']['row_id']='TEST-concrete'
        with self.assertRaisesRegex(ValueError,'cannot be shared'):apply_estimate_policy(rows(),self.profile)
        self.profile['pricing_policy']=self.policy(['concrete','plastic','labor','bobcat_use','retail_delivery'])
        self.profile['pricing_policy']['retail_tax']['effective_through']='2026-09-09'
        with self.assertRaisesRegex(ValueError,'not effective'):apply_estimate_policy(rows(),self.profile)

    def test_policy_updates_edited_prices_exports_and_preserves_prior_snapshot(self):
        payload={'base_version':1,'plan_sha256':self.config['plan_sha256'],'points':self.config['initial_points'],'outline':'blue','note':'test'}
        old=self.store.save(payload);old_csv=estimate_csv(old);old_draft=trade_draft(self.config,old)
        self.profile.update(pricing_as_of='2026-09-10',pricing_notes=['TEST'],purchase_rounding='whole_units',
            slab_labor=dict(self.labor,billing_basis='measured_net_sf'),pricing_policy=self.policy(['concrete','labor','bobcat_use','retail_delivery']))
        self.profile['prices']={key:{'unit_price':rate,'unit':unit,'currency':'USD','date':'2026-09-10','valid_through':'2026-09-10','source':'TEST'} for key,rate,unit in [('concrete',190,'CY'),('labor',1.75,'sq ft')]}
        path=self.store.folder/'construction_profile.json';path.read_text(encoding='utf-8')
        path.write_text(json.dumps(self.profile),encoding='utf-8');self.store=ReviewStore(self.store.folder)
        first=self.store.save(dict(payload,base_version=2));second=self.store.save(dict(payload,base_version=3,points=[[100,100],[400,100],[400,200],[100,200]]))
        a=first['construction']['outputs'];b=second['construction']['outputs']
        self.assertGreater(b['budget_sell_total'],a['budget_sell_total'])
        self.assertEqual(a['purchase_tax_total'],b['purchase_tax_total']);self.assertEqual(b['purchase_tax_total'],6.32)
        self.assertEqual(next(r for r in b['estimate_rows'] if r['estimate_item_id']=='labor')['sell_amount'],561.75)
        self.assertIsNone(b['current_total']);self.assertFalse(b['verification_valid'])
        self.assertIn('budget_sell_amount',estimate_csv(second));self.assertIn('~$321.00 budget',trade_draft(self.config,second))
        reopened=ReviewStore(self.store.folder)
        self.assertEqual(reopened.read(first['version']),first);self.assertEqual(reopened.read(second['version']),second)
        self.assertEqual(estimate_csv(reopened.read(2)),old_csv);self.assertEqual(trade_draft(self.config,reopened.read(2)),old_draft)


if __name__=='__main__':unittest.main()
