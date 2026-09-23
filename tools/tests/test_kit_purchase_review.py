import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from kit_purchase_review import import_kit_purchases
from estimate_readiness import readiness


class KitPurchases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.row={'row_id':'area','excel_row':'445','name':'Surround','parent':'Tub walls','cost_type':'ALLOWANCE',
          'unit':'ft2','markup_pct':'8','completion_status':'evidence_in_progress','draft_quantity':None,
          'unit_cost':None,'line_cost':None,'line_price':None,
          'assembly_inputs':[{'id':'count','quantity':1,'unit':'EA','use':'assembly_input'}]}
        self.parent={'row_id':'parent','excel_row':'444','name':'Tub walls','parent':'Bath','cost_type':'GROUP',
          'unit':'each','markup_pct':'0','completion_status':'evidence_in_progress','line_cost':None}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[copy.deepcopy(self.parent),copy.deepcopy(self.row)]}
        self.purchase={'plan_sha256':'plan','row_id':'kit','replaces_row_id':'area','parent_row_id':'parent',
          'name':'Three-piece surround kit','unit':'kit','assembly_input_id':'count','product_id':'product',
          'model':'model','basis':'One kit per measured tub count','source':'Selected product schedule'}
        self.save()

    def save(self):
        raw=json.dumps(self.purchase).encode();(self.root/'purchase.json').write_bytes(raw)
        self.config={'plan_sha256':'plan','purchases':[{'file':'purchase.json','sha256':hashlib.sha256(raw).hexdigest()}]}

    def test_single_cost_owner_preserves_template_unit_and_markup(self):
        before=copy.deepcopy(self.draft);result=import_kit_purchases(self.draft,self.config,self.root)
        self.assertEqual(self.draft,before)
        reference=result['rows'][1];kit=result['additional_cost_rows'][0]
        self.assertEqual((reference['unit'],reference['draft_quantity'],reference['cost_owner_row_id']),('ft2',None,'kit'))
        self.assertEqual((kit['draft_quantity'],kit['unit'],kit['markup_pct']),(1,'kit','8'))
        report=readiness(result,{'rows':self.draft['rows']})
        self.assertEqual(report['rows'][1]['role'],'cost_reference')
        self.assertNotIn('Supplemental parent ownership is unresolved or already priced',report['additional_cost_rows'][0]['issues'])
        self.assertIn('Current line pricing unresolved',report['additional_cost_rows'][0]['issues'])
        self.assertFalse(result['estimate_released'])

    def test_changed_count_and_zero_recalculate_without_area_conversion(self):
        for count in (0,2,5):
            self.draft['rows'][1]['assembly_inputs'][0]['quantity']=count
            result=import_kit_purchases(self.draft,self.config,self.root)
            self.assertEqual(result['additional_cost_rows'][0]['draft_quantity'],count)

    def test_pending_scope_withholds_purchase_quantity(self):
        self.draft['rows'][1]['assembly_inputs']=[]
        self.draft['pending_quantities']=[{'id':'count','template_rows':['445'],'label':'Needs review'}]
        result=import_kit_purchases(self.draft,self.config,self.root)
        self.assertIsNone(result['additional_cost_rows'][0]['draft_quantity'])
        self.assertIn('Quantity unresolved',readiness(result,{'rows':self.draft['rows']})['additional_cost_rows'][0]['issues'])

    def test_invalid_count_units_missing_source_and_duplicate_inputs_rejected(self):
        for change in ('negative','fraction','boolean','nan','area','missing','duplicate'):
            with self.subTest(change=change):
                draft=copy.deepcopy(self.draft);values=draft['rows'][1]['assembly_inputs']
                if change in ('negative','fraction','boolean','nan'):values[0]['quantity']={'negative':-1,'fraction':1.5,'boolean':True,'nan':float('nan')}[change]
                if change=='area':values[0]['unit']='SF'
                if change=='missing':values.clear()
                if change=='duplicate':values.append(copy.deepcopy(values[0]))
                with self.assertRaises(ValueError):import_kit_purchases(draft,self.config,self.root)

    def test_cost_conflicts_and_wrong_parent_rejected(self):
        for change in ('price','quantity','package','excluded','parent','duplicate'):
            with self.subTest(change=change):
                draft=copy.deepcopy(self.draft);row=draft['rows'][1]
                if change=='price':row['line_cost']=1
                if change=='quantity':row['draft_quantity']=12
                if change=='package':row['covered_by_package']='other'
                if change=='excluded':row['completion_status']='not_applicable_source_reviewed'
                if change=='parent':draft['rows'][0]['name']='Other scope'
                if change=='duplicate':draft=import_kit_purchases(draft,self.config,self.root)
                with self.assertRaises(ValueError):import_kit_purchases(draft,self.config,self.root)

    def test_drawing_and_evidence_changes_rejected(self):
        config=copy.deepcopy(self.config);config['plan_sha256']='other'
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,config,self.root)
        self.purchase['plan_sha256']='other';self.save()
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)
        (self.root/'purchase.json').write_text('{}')
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def test_readiness_rejects_unrelated_group_owner(self):
        result=import_kit_purchases(self.draft,self.config,self.root)
        result['rows'][0]['name']='Other scope'
        report=readiness(result,{'rows':self.draft['rows']})
        self.assertIn('Supplemental parent ownership is unresolved or already priced',report['additional_cost_rows'][0]['issues'])

    def test_one_input_purchase_keeps_other_scope_unresolved(self):
        self.purchase['ownership']='assembly_input';self.save()
        self.draft['rows'][1]['assembly_inputs'].append({'id':'leaf','quantity':1,'unit':'EA','use':'assembly_input'})
        result=import_kit_purchases(self.draft,self.config,self.root)
        row=result['rows'][1];extra=result['additional_cost_rows'][0]
        self.assertNotIn('cost_owner_row_id',row)
        self.assertEqual(row['assembly_input_cost_owners'],{'count':'kit'})
        self.assertEqual(row['pricing_role'],'input_only')
        self.assertEqual(extra['source_row_id'],'area')
        self.assertNotIn('replaces_row_id',extra)
        report=readiness(result,{'rows':self.draft['rows']})
        self.assertIn('Assembly input has no purchase owner: leaf',report['rows'][1]['issues'])
        self.assertNotIn('Supplemental parent ownership is unresolved or already priced',report['additional_cost_rows'][0]['issues'])
        result['rows'][1]['assembly_input_cost_owners']['count']='wrong'
        self.assertIn('Supplemental assembly input reference is missing or mismatched',readiness(result,{'rows':self.draft['rows']})['additional_cost_rows'][0]['issues'])

    def test_whole_row_purchase_cannot_hide_other_inputs(self):
        self.draft['rows'][1]['assembly_inputs'].append({'id':'leaf','quantity':1,'unit':'EA'})
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def test_duplicate_input_owner_and_invalid_mode_rejected(self):
        self.purchase['ownership']='assembly_input';self.save()
        draft=import_kit_purchases(self.draft,self.config,self.root)
        self.purchase['row_id']='another-kit';self.save()
        with self.assertRaises(ValueError):import_kit_purchases(draft,self.config,self.root)
        self.purchase['ownership']='unknown';self.save()
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def test_pending_input_purchase_withholds_only_its_count(self):
        self.purchase['ownership']='assembly_input';self.save()
        self.draft['rows'][1]['assembly_inputs']=[{'id':'leaf','quantity':1,'unit':'EA'}]
        self.draft['pending_quantities']=[{'id':'count','template_rows':['445'],'label':'Needs review'}]
        result=import_kit_purchases(self.draft,self.config,self.root)
        self.assertIsNone(result['additional_cost_rows'][0]['draft_quantity'])
        self.assertEqual(result['rows'][1]['assembly_inputs'][0]['id'],'leaf')

    def test_individual_leaf_gets_each_owner_without_inventing_a_product(self):
        self.purchase.update(ownership='assembly_input',unit='each',product_status='specification_pending',
                             product_id=None,model=None,name='Hollow-core pocket leaf')
        self.save()
        for count in (0,1,3):
            self.draft['rows'][1]['assembly_inputs'][0]['quantity']=count
            result=import_kit_purchases(self.draft,self.config,self.root)
            extra=result['additional_cost_rows'][0]
            self.assertEqual((extra['draft_quantity'],extra['unit'],extra['markup_pct']),(count,'each','8'))
            self.assertIsNone(extra['unit_cost'])
            self.assertIsNone(extra['quantity_sources'][0]['model'])
            self.assertEqual(extra['quantity_sources'][0]['kind'],'reviewed_count_purchase')
            self.assertIn('Product specification',extra['quantity_sources'][0]['remaining'][-1])
            self.assertEqual(result['rows'][1]['assembly_input_cost_owners'],{'count':'kit'})

    def test_identified_item_preserves_count_selection_and_cost_ownership(self):
        for selection in ('selected','estimating_candidate'):
            self.purchase.update(ownership='assembly_input',unit='each',product_status='identified',selection_status=selection)
            self.save()
            for count in (0,4,5):
                self.draft['rows'][1]['assembly_inputs'][0]['quantity']=count
                result=import_kit_purchases(self.draft,self.config,self.root)
                row=result['additional_cost_rows'][0];source=row['quantity_sources'][0]
                self.assertEqual((row['draft_quantity'],row['markup_pct'],row['unit_cost']),(count,'8',None))
                self.assertEqual((source['kind'],source['selection_status'],source['product_id']),('reviewed_item_purchase',selection,'product'))
                self.assertFalse(row['certified']);self.assertFalse(row['current_price_certified'])
                self.assertEqual(result['rows'][1]['assembly_input_cost_owners'],{'count':'kit'})
            self.draft['rows'][1]['assembly_inputs']=[]
            self.draft['pending_quantities']=[{'id':'count','template_rows':['445']}]
            self.assertIsNone(import_kit_purchases(self.draft,self.config,self.root)['additional_cost_rows'][0]['draft_quantity'])
            self.draft['rows'][1]['assembly_inputs']=[{'id':'count','quantity':1,'unit':'EA'}]
            self.draft.pop('pending_quantities')

    def test_identified_item_rejects_missing_identity_status_and_whole_row_ownership(self):
        self.purchase.update(ownership='assembly_input',unit='each',product_status='identified',selection_status='selected')
        good=copy.deepcopy(self.purchase)
        for change in ({'product_id':None},{'model':None},{'selection_status':None},{'selection_status':'approved'},{'ownership':'row'}):
            self.purchase={**good,**change};self.save()
            with self.subTest(change=change),self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def test_installed_scope_keeps_subcontract_markup_and_live_count(self):
        raw=b'original supplier scope';(self.root/'invoice.pdf').write_bytes(raw)
        self.draft['rows'][1].update(cost_type='SUBCONTRACTOR',markup_pct='7')
        self.purchase.update(ownership='assembly_input',unit='each',product_status='installed_scope',
            installed_scope='8 x 8 cedar column wrap, installed',product_id=None,model=None,
            evidence_files=[{'file':'invoice.pdf','sha256':hashlib.sha256(raw).hexdigest()}])
        self.save()
        for count in (0,4,5):
            self.draft['rows'][1]['assembly_inputs'][0]['quantity']=count
            extra=import_kit_purchases(self.draft,self.config,self.root)['additional_cost_rows'][0]
            self.assertEqual((extra['draft_quantity'],extra['cost_type'],extra['markup_pct']),(count,'SUBCONTRACTOR','7'))
            self.assertEqual(extra['quantity_sources'][0]['kind'],'reviewed_installed_scope')
        good=copy.deepcopy(self.purchase)
        for change in ({'installed_scope':''},{'evidence_files':[]},{'ownership':'row'},{'model':'invented'}):
            self.purchase={**good,**change};self.save()
            with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)
        self.purchase=good;self.save();(self.root/'invoice.pdf').write_bytes(b'changed')
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def assortment(self):
        raw=b'original invoice';(self.root/'invoice.pdf').write_bytes(raw)
        self.purchase.update(ownership='assembly_input',unit='each',product_status='reviewed_assortment',
            selection_status='estimating_candidate',product_id=None,model=None,
            evidence_files=[{'file':'invoice.pdf','sha256':hashlib.sha256(raw).hexdigest()}],
            items=[{'id':'line-1','model':'A','quantity':1,'source_ref':'Invoice line 1'},
                   {'id':'line-2','model':'B','quantity':2,'source_ref':'Invoice line 2'}])
        self.draft['rows'][1]['assembly_inputs'][0]['quantity']=3
        self.save()

    def test_assortment_preserves_each_count_models_markup_and_other_scope(self):
        self.assortment()
        self.draft['rows'][1]['assembly_inputs'].append({'id':'other','quantity':1,'unit':'EA'})
        result=import_kit_purchases(self.draft,self.config,self.root)
        row=result['additional_cost_rows'][0];source=row['quantity_sources'][0]
        self.assertEqual((row['draft_quantity'],row['unit'],row['markup_pct']),(3,'each','8'))
        self.assertEqual(source['kind'],'reviewed_assortment_purchase')
        self.assertEqual(source['items'],self.purchase['items'])
        self.assertEqual(result['rows'][1]['unit'],'ft2')
        self.assertIsNone(result['rows'][1]['draft_quantity'])
        self.assertIn('Assembly input has no purchase owner: other',readiness(result,{'rows':self.draft['rows']})['rows'][1]['issues'])

    def test_assortment_changed_or_pending_count_withholds_purchase(self):
        self.assortment()
        for count in (0,2,4):
            self.draft['rows'][1]['assembly_inputs'][0]['quantity']=count
            extra=import_kit_purchases(self.draft,self.config,self.root)['additional_cost_rows'][0]
            self.assertIsNone(extra['draft_quantity'])
            self.assertIn('differs',extra['quantity_sources'][0]['remaining'][-1])
        self.draft['rows'][1]['assembly_inputs']=[]
        self.draft['pending_quantities']=[{'id':'count','template_rows':['445']}]
        self.assertIsNone(import_kit_purchases(self.draft,self.config,self.root)['additional_cost_rows'][0]['draft_quantity'])

    def test_assortment_rejects_untraceable_or_invalid_members(self):
        self.assortment();good=copy.deepcopy(self.purchase)
        changes=[{'items':[]},{'evidence_files':[]},{'ownership':'row'},{'model':'invented'},
                 {'selection_status':'approved'},{'items':good['items']+[good['items'][0]]}]
        for field,value in [('quantity',True),('quantity',0),('quantity',1.5),('model',''),('source_ref','')]:
            members=copy.deepcopy(good['items']);members[0][field]=value;changes.append({'items':members})
        for change in changes:
            self.purchase={**good,**change};self.save()
            with self.subTest(change=change),self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)
        self.purchase=good;self.save();(self.root/'invoice.pdf').write_bytes(b'changed')
        with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)

    def test_unspecified_item_cannot_replace_whole_row_or_claim_known_product(self):
        self.purchase.update(ownership='assembly_input',unit='each',product_status='specification_pending',
                             product_id=None,model=None)
        good=copy.deepcopy(self.purchase)
        for change in ({'ownership':'row'},{'model':'invented'},{'product_id':'invented'},
                       {'product_status':'approved'},{'source':None},{'unit':'box'}):
            with self.subTest(change=change):
                self.purchase={**good,**change};self.save()
                with self.assertRaises(ValueError):import_kit_purchases(self.draft,self.config,self.root)


    def prepare_pack(self):
        path=self.root/'pack.txt';path.write_text('24 items per package')
        self.purchase.update(unit='pack',product_status='identified',ownership='assembly_input',
            selection_status='estimating_candidate',units_per_pack=24,
            evidence_files=[{'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}])
        self.save()

    def test_pack_rounding_preserves_required_count_and_template_unit(self):
        self.prepare_pack()
        for required,expected in ((0,0),(24,1),(25,2),(48,2),(49,3)):
            self.draft['rows'][1]['assembly_inputs'][0]['quantity']=required
            result=import_kit_purchases(self.draft,self.config,self.root)
            row=result['additional_cost_rows'][0];source=row['quantity_sources'][0]
            self.assertEqual((row['draft_quantity'],row['unit'],row['markup_pct']),(expected,'pack','8'))
            self.assertEqual(source['count_reference']['quantity'],required)
            self.assertEqual(source['purchase_pack']['surplus_units'],expected*24-required)
            self.assertEqual(result['rows'][1]['unit'],'ft2')
            self.assertIsNone(row['line_cost'])

    def test_pack_pending_count_withholds_quantity(self):
        self.prepare_pack();self.draft['rows'][1]['assembly_inputs']=[]
        self.draft['pending_quantities']=[{'id':'count','template_rows':['445'],'label':'Needs review'}]
        row=import_kit_purchases(self.draft,self.config,self.root)['additional_cost_rows'][0]
        self.assertIsNone(row['draft_quantity'])
        self.assertIsNone(row['quantity_sources'][0]['purchase_pack']['purchased_units'])

    def test_pack_quantity_survives_trade_export(self):
        from export_trade_scopes import packages,render
        self.prepare_pack();self.draft['rows'][1]['assembly_inputs'][0]['quantity']=49
        result=import_kit_purchases(self.draft,self.config,self.root)
        snapshot={'snapshot_sha256':'trial','draft':result,
            'readiness':readiness(result,{'rows':self.draft['rows']})}
        coverage={'rows':[{'excel_row':'445','status':'draft_scope_routed',
            'draft_file':'trade.md','draft_owner':'test'}],
            'supplemental_cost_routes':[{'row_id':'kit','draft_file':'trade.md','draft_owner':'test'}]}
        trade=packages(Path('index.json'),{'files':['trade.md']},coverage,snapshot)[0]
        pack=trade['items'][1]['quantity_basis'][0]['purchase_pack']
        self.assertEqual((pack['quantity'],pack['unit'],pack['required_quantity'],pack['coverage_unit']),(3,'pack',49,'EA'))
        self.assertIn('24 items per pack',pack['product'])
        self.assertIn('3 pack',render(trade))
        self.assertFalse(trade['ready_to_order'])

    def test_pack_size_and_source_must_be_valid(self):
        self.prepare_pack()
        for value in (0,-1,True,24.5,'24',None):
            self.purchase['units_per_pack']=value;self.save()
            with self.assertRaisesRegex(ValueError,'pack size'):import_kit_purchases(self.draft,self.config,self.root)
        self.purchase['units_per_pack']=24;self.save()
        (self.root/'pack.txt').write_text('12 items per package')
        with self.assertRaisesRegex(ValueError,'missing or changed'):import_kit_purchases(self.draft,self.config,self.root)

if __name__=='__main__':unittest.main()
