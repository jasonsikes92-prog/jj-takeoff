import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from floor_obstructions import net_floor_area,split_room_at_boundary
from floor_finish_review import allocate_floor_costs,apply_floor_billing


class FloorCostAllocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'mapping.json';self.source.write_text('reviewed mapping')
        self.config={'displaced_assembly_id':'pooled','fixed_obstructions':{'remaining':['Waste and billing basis']},
            'cost_allocation':{'source_file':'mapping.json','source_sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'groups':[{'id':'kitchen','label':'Kitchen','measurement_ids':['kitchen'],'cost_rows':['km','kl'],'basis':'Kitchen label'},
                      {'id':'other','label':'Other rooms','measurement_ids':['hall'],'cost_rows':['gm','gl'],'basis':'Remaining field'}]}}
        def row(identity,markup,pooled=False):return {'row_id':identity,'excel_row':identity,'markup_pct':markup,
            'pricing_role':'cost_line','unit':'each' if identity=='kl' else 'ft2',
            'unit_cost':1.5 if identity=='gl' else None,'draft_quantity':None,'line_cost':None,'line_price':None,
            'assembly_inputs':[{'id':'pooled','quantity':180}] if pooled else []}
        self.draft={'rows':[row('km',8),row('kl',7),row('gm',8,True),row('gl',15,True)],
            'floor_finish_review':{'remaining_measurement_ids':['kitchen','hall'],'remaining_finish_area_sf':180,
            'obstructions':{'rooms':[{'measurement_id':'kitchen','gross_sf':100,'deducted_sf':16,'net_sf':84},
                                     {'measurement_id':'hall','gross_sf':100,'deducted_sf':4,'net_sf':96}]}}}
    def apply(self):allocate_floor_costs(self.draft,self.config,self.root)
    def test_disjoint_owners_preserve_prices_units_and_markups(self):
        before=copy.deepcopy(self.draft);self.apply()
        self.assertEqual([r['assembly_inputs'][0]['quantity'] for r in self.draft['rows']],[84,84,96,96])
        for old,new in zip(before['rows'],self.draft['rows']):
            self.assertEqual({k:v for k,v in old.items() if k!='assembly_inputs'},
                             {k:v for k,v in new.items() if k!='assembly_inputs'})
        self.assertEqual(sum(g['net_sf'] for g in self.draft['floor_finish_review']['cost_allocation']['groups']),180)
    def test_missing_duplicate_or_unknown_room_rejected(self):
        original=copy.deepcopy(self.config)
        for ids in ([],['hall','kitchen'],['unknown']):
            self.config=copy.deepcopy(original);self.config['cost_allocation']['groups'][1]['measurement_ids']=ids
            with self.assertRaises(ValueError):self.apply()
    def test_shared_owner_or_abandoned_pool_rejected(self):
        self.config['cost_allocation']['groups'][0]['cost_rows']=['km','gl']
        with self.assertRaises(ValueError):self.apply()
    def test_existing_priced_or_other_scope_cannot_be_overwritten(self):
        original=copy.deepcopy(self.draft)
        for key,value in [('line_cost',100),('draft_quantity',10),('covered_by_package',True),
                          ('assembly_inputs',[{'id':'other-scope'}]),('quantity_sources',[{'id':'source'}])]:
            self.draft=copy.deepcopy(original);self.draft['rows'][0][key]=value;before=copy.deepcopy(self.draft)
            with self.assertRaises(ValueError):self.apply()
            self.assertEqual(self.draft,before)
    def test_source_changes_and_wrong_total_rejected(self):
        self.draft['floor_finish_review']['remaining_finish_area_sf']=181
        with self.assertRaises(ValueError):self.apply()
        self.draft['floor_finish_review']['remaining_finish_area_sf']=180;self.source.write_text('changed')
        with self.assertRaises(ValueError):self.apply()
    def test_shared_footprint_is_split_and_overlap_counted_once(self):
        def m(x,w):return {'kind':'area','page':1,'points_per_foot':1,'width_pt':100,'height_pt':100,
                          'points':[[x,0],[x+w,0],[x+w,10],[x,10]]}
        rooms={'plan_sha256':'p','version':1,'measurements':{'a':m(0,10),'b':m(10,10)}}
        cuts={'plan_sha256':'p','version':1,'measurements':{'one':m(8,4),'overlap':m(9,2)}}
        result=net_floor_area(rooms,['a','b'],cuts,['one','overlap'],include_rooms=True)
        self.assertEqual([r['net_sf'] for r in result['rooms']],[80,80])
        self.assertEqual(sum(r['net_sf'] for r in result['rooms']),result['net_sf'])
        cuts['measurements']['one']=m(8,5)
        changed=net_floor_area(rooms,['a','b'],cuts,['one','overlap'],include_rooms=True)
        self.assertEqual([r['net_sf'] for r in changed['rooms']],[80,70])

    def test_open_room_division_moves_area_without_adding_or_losing_floor(self):
        room={'kind':'area','page':1,'points_per_foot':1,'width_pt':100,'height_pt':100,
              'points':[[0,0],[20,0],[20,20],[0,20]]}
        state={'plan_sha256':'p','version':1,'measurements':{'open':room}}
        line={**room,'kind':'length','points':[[0,8],[20,8]]}
        boundary={'plan_sha256':'p','version':1,'measurements':{'division':line}}
        config={'room_id':'open','above_id':'k','below_id':'f','measurement_id':'division'}
        from measurement_store import calculate
        result,ids=split_room_at_boundary(state,['open'],boundary,config)
        self.assertEqual([calculate(result['measurements'][i])['quantity'] for i in ids],[160,240])
        line['points']=[[0,9],[20,9]]
        result,ids=split_room_at_boundary(state,['open'],boundary,config)
        self.assertEqual([calculate(result['measurements'][i])['quantity'] for i in ids],[180,220])
        self.assertEqual(list(state['measurements']),['open'])
        line['points']=[[0,9],[20,10]]
        with self.assertRaises(ValueError):split_room_at_boundary(state,['open'],boundary,config)

    def billing_fixture(self):
        self.apply();self.draft['plan_sha256']='plan'
        for row in self.draft['rows']:
            row.update(cost_type='LABOR' if row['row_id'].endswith('l') else 'MATERIAL',unit='ft2')
        source=self.root/'billing.json'
        source.write_text(json.dumps({'plan_sha256':'plan','labor_basis':'measured_installed_floor_area','material_waste_pct':10,'labor_cost_owner_ids':['kl','gl']}))
        return {'source_file':'billing.json','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}

    def test_labor_uses_net_area_material_waste_is_separate(self):
        billing=self.billing_fixture();apply_floor_billing(self.draft,billing,self.root)
        self.assertEqual([r['draft_quantity'] for r in self.draft['rows']],[None,84,None,96])
        review=self.draft['floor_finish_review']['billing_review']
        self.assertAlmostEqual(review['material_area_with_waste_sf'],198)
        self.assertIsNone(review['material_purchase_quantity'])
        self.assertEqual(self.draft['rows'][3]['unit_cost'],1.5)

    def test_changed_room_area_updates_labor_without_waste(self):
        billing=self.billing_fixture();group=self.draft['floor_finish_review']['cost_allocation']['groups'][1]
        group['net_sf']=100.25;self.draft['floor_finish_review']['remaining_finish_area_sf']=184.25
        apply_floor_billing(self.draft,billing,self.root)
        self.assertEqual(self.draft['rows'][3]['draft_quantity'],100.25)
        self.assertEqual(self.draft['rows'][3]['quantity_sources'][0]['rounding'],'none')

    def test_wrong_unit_or_price_conflict_does_not_partially_apply(self):
        billing=self.billing_fixture();original=copy.deepcopy(self.draft)
        for change in ({'unit':'each'},{'line_cost':500},{'cost_type':'GROUP'},{'draft_quantity':0}):
            self.draft=copy.deepcopy(original);self.draft['rows'][3].update(change);before=copy.deepcopy(self.draft)
            with self.assertRaises(ValueError):apply_floor_billing(self.draft,billing,self.root)
            self.assertEqual(before,self.draft)

    def test_reviewed_labor_owner_preserves_template_material_class_and_markup(self):
        billing=self.billing_fixture();self.draft['rows'][3]['cost_type']='MATERIAL'
        apply_floor_billing(self.draft,billing,self.root)
        self.assertEqual(self.draft['rows'][3]['cost_type'],'MATERIAL')
        self.assertEqual(self.draft['rows'][3]['markup_pct'],15)
        self.assertEqual(self.draft['rows'][3]['draft_quantity'],96)

    def test_billing_source_change_and_nonfinite_waste_rejected(self):
        billing=self.billing_fixture();source=self.root/'billing.json';source.write_text('changed')
        with self.assertRaises(ValueError):apply_floor_billing(self.draft,billing,self.root)
        for waste in (True,-1,float('nan'),None):
            source.write_text(json.dumps({'plan_sha256':'plan','labor_basis':'measured_installed_floor_area','material_waste_pct':waste}))
            billing['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):apply_floor_billing(self.draft,billing,self.root)


if __name__=='__main__':unittest.main()
