import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from owner_item_quantities import import_counts


class OwnerCounts(unittest.TestCase):
    def test_combined_count_waits_for_an_explicit_pending_measurement(self):
        self.draft['rows'][0]['excel_row']='214'
        self.config['items'][0]['include_assembly_input_ids']=['floods']
        self.draft['pending_quantities']=[{'id':'floods','template_rows':['214'],'label':'Floods need review'}]
        result=import_counts(self.draft,self.config,self.root)
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(result['rows'][0]['quantity_sources'],[])
        self.assertEqual(result['pending_quantities'][-1]['id'],'mirrors')
        self.assertEqual(result['pending_quantities'][-1]['missing_assembly_input_ids'],['floods'])
        self.draft['pending_quantities'][0]['template_rows']=['999']
        with self.assertRaisesRegex(ValueError,'missing or duplicated'):
            import_counts(self.draft,self.config,self.root)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.path=self.root/'answer.json'
        self.path.write_text(json.dumps({'source_kind':'owner_confirmation','plan_sha256':'p','counts':{'mirrors':3,'rear':0}}))
        source={'file':'answer.json','sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'field':'counts.mirrors'}
        self.config={'plan_sha256':'p','reviewed':True,'items':[{'id':'mirrors','label':'Primary bath mirrors','row_ids':['r'],
            'source':source,'use':'template_quantity','basis':'Owner R05: two decorative and one LED'}]}
        self.draft={'plan_sha256':'p','rows':[{'row_id':'r','unit':'each','cost_type':'ALLOWANCE','completion_status':'evidence_in_progress',
            'draft_quantity':None,'quantity_sources':[],'assembly_inputs':[],'line_cost':None}]}

    def test_source_count_has_no_invented_geometry_or_price(self):
        before=copy.deepcopy(self.draft);r=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(r['draft_quantity'],3);self.assertIsNone(r['line_cost'])
        self.assertEqual(r['quantity_sources'][0]['measurement_ids'],[])
        self.assertFalse(r['quantity_sources'][0]['certified']);self.assertEqual(self.draft,before)

    def duration_input(self):
        record={'source_kind':'owner_confirmation','plan_sha256':'p','unit':'month','months':9}
        self.path.write_text(json.dumps(record))
        self.config['items'][0].update(use='project_input',unit='month',label='Construction duration',basis='Owner confirms nine months')
        self.config['items'][0]['source'].update(field='months',sha256=hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.draft['rows'][0].update(parent='INPUTS',pricing_role='input_only',unit='month')

    def test_duration_preserves_costs_and_rejects_changed_evidence(self):
        self.duration_input();before=copy.deepcopy(self.draft)
        row=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(row['draft_quantity'],9)
        self.assertEqual(row['quantity_sources'][0]['unit'],'month')
        self.assertEqual(row['quantity_sources'][0]['measurement_ids'],[])
        self.assertIsNone(row['line_cost']);self.assertEqual(self.draft,before)
        self.path.write_text(self.path.read_text().replace('9','8'))
        with self.assertRaisesRegex(ValueError,'evidence missing or changed'):
            import_counts(self.draft,self.config,self.root)

    def test_duration_cannot_replace_cost_scope_or_existing_input(self):
        self.duration_input()
        for change in ({'parent':'General Requirements'},{'pricing_role':'cost_line'},
                       {'unit':'each'},{'draft_quantity':0},{'line_cost':150},
                       {'quantity_sources':[{'id':'other'}]}, {'assembly_inputs':[{'id':'other'}]}):
            draft=copy.deepcopy(self.draft);draft['rows'][0].update(change)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'Project duration'):
                import_counts(draft,self.config,self.root)
        config=copy.deepcopy(self.config);config['items'][0]['unit']='each'
        with self.assertRaisesRegex(ValueError,'Project duration'):import_counts(self.draft,config,self.root)

    def test_duration_rejects_zero_fractional_boolean_and_wrong_plan(self):
        self.duration_input()
        for value in (0,-1,1.5,True):
            record=json.loads(self.path.read_bytes());record['months']=value
            self.path.write_text(json.dumps(record))
            self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.subTest(value=value),self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.duration_input();self.config['plan_sha256']='other'
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_other_owner_input_survives_explicit_partial_purchase_ownership(self):
        row=self.draft['rows'][0]
        row.update(pricing_role='input_only',assembly_input_cost_owners={'fans':'fan-purchase'})
        self.config['items'][0]['use']='assembly_input'
        result=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertIsNone(result['draft_quantity']);self.assertIsNone(result['line_cost'])
        self.assertEqual(result['assembly_inputs'][0]['quantity'],3)
        self.assertEqual(result['assembly_input_cost_owners'],{'fans':'fan-purchase'})
        for change in ('direct','no-owner','same-owner','inputs-parent'):
            draft=copy.deepcopy(self.draft);config=copy.deepcopy(self.config)
            if change=='direct':config['items'][0]['use']='template_quantity'
            if change=='no-owner':draft['rows'][0]['assembly_input_cost_owners']={}
            if change=='same-owner':draft['rows'][0]['assembly_input_cost_owners']['mirrors']='other'
            if change=='inputs-parent':draft['rows'][0]['parent']='INPUTS'
            with self.subTest(change=change),self.assertRaises(ValueError):import_counts(draft,config,self.root)

    def supplemental_purchase(self):
        self.draft['rows'][0].update(parent='Bath accessories',markup_pct='8')
        self.draft['rows'].append({'row_id':'parent','name':'Bath accessories','cost_type':'ASSEMBLY'})
        purchase={'row_id':'paper-holder','parent_row_id':'parent','name':'Toilet-paper holder',
            'product_id':'product','model':'model','selection_status':'selected'}
        record=json.loads(self.path.read_bytes());record['purchase']=purchase
        self.path.write_text(json.dumps(record))
        self.config['items'][0].update(use='supplemental_purchase',purchase=purchase)
        self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_supplemental_product_preserves_unresolved_template_scope(self):
        self.supplemental_purchase();before=copy.deepcopy(self.draft)
        result=import_counts(self.draft,self.config,self.root)
        self.assertEqual(result['rows'],before['rows']);self.assertEqual(self.draft,before)
        extra=result['additional_cost_rows'][0]
        self.assertEqual((extra['draft_quantity'],extra['markup_pct'],extra['unit']),(3,'8','each'))
        self.assertEqual(extra['quantity_sources'][0]['kind'],'reviewed_item_purchase')
        self.assertIsNone(extra['line_cost']);self.assertFalse(extra['certified'])

    def test_supplemental_product_requires_matching_product_parent_and_unique_owner(self):
        self.supplemental_purchase()
        for change in ('model','parent','duplicate','markup'):
            draft=copy.deepcopy(self.draft);config=copy.deepcopy(self.config)
            if change=='model':config['items'][0]['purchase']['model']='other'
            if change=='parent':draft['rows'][1]['cost_type']='MATERIAL'
            if change=='duplicate':draft['additional_cost_rows']=[{'row_id':'paper-holder'}]
            if change=='markup':draft['rows'][0]['markup_pct']='NaN'
            with self.assertRaises(ValueError):import_counts(draft,config,self.root)

    def document_count(self):
        original=self.root/'original.txt';original.write_text('One 400-amp service and one generator prewire')
        document={'file':original.name,'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'page':1,'source_ref':'Electrical extras, original invoice'}
        record={'source_kind':'documented_scope_count','plan_sha256':'p','counts':{'mirrors':1},
            'review_basis':'One installation in the original scope; rough and trim are installments.',
            'documents':[document]}
        self.path.write_text(json.dumps(record))
        self.config['items'][0].update(source_kind='documented_scope_count')
        self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        return original,record

    def test_document_count_retains_original_evidence_without_owner_attribution(self):
        self.document_count();row=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(row['draft_quantity'],1)
        self.assertEqual(row['quantity_sources'][0]['source_kind'],'documented_scope_count')
        self.assertEqual(len(row['quantity_sources'][0]['documents']),1)
        self.assertEqual(row['quantity_sources'][0]['measurement_ids'],[])
        self.assertIsNone(row['line_cost']);self.assertFalse(row['quantity_sources'][0]['certified'])

    def test_changed_original_source_rejected_without_editing_review_record(self):
        original,_=self.document_count();original.write_text('Different installation scope')
        with self.assertRaisesRegex(ValueError,'original source'):import_counts(self.draft,self.config,self.root)

    def test_document_count_requires_explicit_source_kind_original_and_location(self):
        _,record=self.document_count()
        self.config['items'][0].pop('source_kind')
        with self.assertRaisesRegex(ValueError,'source type'):import_counts(self.draft,self.config,self.root)
        self.config['items'][0]['source_kind']='documented_scope_count'
        for docs in ([],[{**record['documents'][0],'page':0}],[{**record['documents'][0],'file':'../original.txt'}],
                     [record['documents'][0],record['documents'][0]]):
            self.path.write_text(json.dumps({**record,'documents':docs}))
            self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_owner_count_and_measured_items_sum_without_invented_positions(self):
        self.config['items'][0]['include_assembly_input_ids']=['appliances']
        self.draft['rows'][0]['assembly_inputs']=[{'id':'appliances','quantity':2,'unit':'EA','measurement_ids':['a','b']}]
        r=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(r['draft_quantity'],5)
        self.assertEqual(r['quantity_sources'][0]['owner_confirmed_count'],3)
        self.assertEqual(r['quantity_sources'][0]['measurement_ids'],['a','b'])
        self.assertIsNone(r['line_cost'])
        self.draft['rows'][0]['assembly_inputs'][0]['quantity']=3
        self.assertEqual(import_counts(self.draft,self.config,self.root)['rows'][0]['draft_quantity'],6)

    def test_original_json_count_pointer_is_checked_and_retained(self):
        original,record=self.document_count()
        original.write_text(json.dumps({'items':[{'quantity':1}]}))
        doc=record['documents'][0];doc.pop('page');doc.update(json_pointer='/items/0/quantity',sha256=hashlib.sha256(original.read_bytes()).hexdigest())
        self.path.write_text(json.dumps(record));self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        row=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(row['draft_quantity'],1)
        self.assertEqual(row['quantity_sources'][0]['documents'][0]['json_pointer'],'/items/0/quantity')
        record['counts']['mirrors']=2
        self.path.write_text(json.dumps(record));self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'differs'):import_counts(self.draft,self.config,self.root)

    def test_json_count_rejects_missing_location_noncounts_and_ambiguous_page(self):
        original,record=self.document_count();doc=record['documents'][0];doc.pop('page')
        for value,pointer,extra in [(1,'/missing',{}),(True,'/items/0/quantity',{}),(1.5,'/items/0/quantity',{}),(1,'/items/-1/quantity',{}),(1,'/items/0/quantity',{'page':1})]:
            original.write_text(json.dumps({'items':[{'quantity':value}]}))
            record['documents']=[{**doc,'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'json_pointer':pointer,**extra}]
            self.path.write_text(json.dumps(record));self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_combined_count_refuses_missing_fractional_and_duplicate_inputs(self):
        self.config['items'][0]['include_assembly_input_ids']=['appliances']
        for value,unit in [(None,'EA'),(1.5,'EA'),(True,'EA'),(2,'SF')]:
            self.draft['rows'][0]['assembly_inputs']=[{'id':'appliances','quantity':value,'unit':unit}]
            with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.draft['rows'][0]['assembly_inputs']=[]
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.draft['rows'][0]['assembly_inputs']=[{'id':i,'quantity':1,'unit':'EA','measurement_ids':['same']} for i in ['a','b']]
        self.config['items'][0]['include_assembly_input_ids']=['a','b']
        with self.assertRaisesRegex(ValueError,'repeats'):import_counts(self.draft,self.config,self.root)
        self.config['items'][0]['include_assembly_input_ids']=['a','a']
        with self.assertRaisesRegex(ValueError,'unique'):import_counts(self.draft,self.config,self.root)

    def test_zero_is_explicit_and_assembly_keeps_existing_inputs(self):
        self.config['items'][0].update(use='assembly_input')
        self.config['items'][0]['source']['field']='counts.rear'
        self.draft['rows'][0]['assembly_inputs']=[{'id':'other','quantity':1}]
        r=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual([q['quantity'] for q in r['assembly_inputs']],[1,0]);self.assertIsNone(r['draft_quantity'])

    def test_changed_source_and_wrong_plan_rejected(self):
        self.config['plan_sha256']='other'
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.config['plan_sha256']='p';self.path.write_text('{}')
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_missing_invalid_count_and_unreviewed_mapping_rejected(self):
        for value in (True,-1,1.5,'3',None):
            data={'source_kind':'owner_confirmation','plan_sha256':'p','counts':{'mirrors':value}}
            self.path.write_text(json.dumps(data));self.config['items'][0]['source']['sha256']=hashlib.sha256(self.path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.config['reviewed']=False
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_existing_quantity_package_or_excluded_row_rejected(self):
        for field,value in [('draft_quantity',2),('covered_by_package','p'),('completion_status','not_applicable_owner'),('cost_type','GROUP')]:
            draft=copy.deepcopy(self.draft);draft['rows'][0][field]=value
            with self.assertRaises(ValueError):import_counts(draft,self.config,self.root)

    def test_duplicates_missing_field_and_traversal_rejected(self):
        self.config['items'].append(copy.deepcopy(self.config['items'][0]))
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.config['items'].pop();self.config['items'][0]['source']['field']='counts.missing'
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)
        self.config['items'][0]['source']['file']='../answer.json'
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_same_source_cannot_be_added_twice_under_different_ids(self):
        self.config['items'][0]['use']='assembly_input'
        other=copy.deepcopy(self.config['items'][0]);other['id']='duplicate-source'
        self.config['items'].append(other)
        with self.assertRaises(ValueError):import_counts(self.draft,self.config,self.root)

    def test_historical_reference_preserves_saved_trade_quantity_without_id(self):
        self.config['items'][0]['use']='assembly_input'
        row=self.draft['rows'][0];row['draft_quantity']=1
        row['quantity_sources']=[{'kind':'saved_slab_snapshot','source':{'file':'slab.json'}}]
        result=import_counts(self.draft,self.config,self.root)['rows'][0]
        self.assertEqual(result['draft_quantity'],1)
        self.assertEqual(result['quantity_sources'],row['quantity_sources'])
        self.assertEqual(result['assembly_inputs'][0]['quantity'],3)
        self.assertIsNone(result['line_cost'])


if __name__=='__main__':unittest.main()
