import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'viewer')]
from count_reference_reviews import apply_count_reviews,count_digest,current_count_review
from estimate_readiness import readiness


class CountReviews(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.original=self.root/'invoice.txt';self.original.write_text('One service installation')
        child={'row_id':'child','excel_row':'2','name':'Service count','parent':'Electrical','cost_type':'SUBCONTRACTOR',
            'unit':'each','markup_pct':'7','draft_quantity':1,'quantity_sources':[{'source_kind':'documented_scope_count','quantity':1}],
            'assembly_inputs':[],'covered_by_package':'owner','completion_status':'evidence_in_progress',
            'certified':False,'current_price_certified':False,'unit_cost':None,'line_cost':None,'line_price':None}
        owner={**child,'row_id':'owner','excel_row':'1','name':'Installed contract','covered_by_package':'owner',
            'line_cost':100,'line_price':107,'pricing_basis':'dated_package_allowance',
            'price_evidence':{'billing_basis':'fixed_package','covered_row_ids':['owner','child']}}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[owner,child]}
        self.template={'rows':copy.deepcopy(self.draft['rows'])}
        self.record={'scope':'package_count_reference','plan_sha256':'plan','measurement_version':1,'row_id':'child',
            'row_sha256':count_digest(child),'quantity':1,'source_type':'GIVEN','given_by':'Original invoice',
            'reviewer':'Test source reviewer','review_basis':'Original installation, not installment count',
            'sources':[{'id':'invoice','file':'invoice.txt','sha256':self.sha(self.original),'reference':'Page 1 service scope'}],
            'check_components':[{'label':'Service installation','count':1,'source_ids':['invoice']}]}
        self.config={'plan_sha256':'plan','rows':[{'row_id':'child','file':'review.json','sha256':''}]}
        self.save_record()

    def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def save_record(self):
        p=self.root/'review.json';p.write_text(json.dumps(self.record));self.config['rows'][0]['sha256']=self.sha(p)
    def apply(self):return apply_count_reviews(self.draft,self.config,self.root)
    def checked(self):return current_count_review(self.apply()['rows'][1])

    def test_checked_count_clears_only_covered_reference_check(self):
        result=self.apply();self.assertTrue(current_count_review(result['rows'][1]))
        audit=readiness(result,self.template)
        self.assertEqual(audit['rows'][1]['issues'],[])
        self.assertIn('Quantity and assembly certification outstanding',audit['rows'][0]['issues'])
        self.assertIn('Current price certification outstanding',audit['rows'][0]['issues'])
        self.assertFalse(result['rows'][1]['certified']);self.assertFalse(audit['estimate_released'])
        self.assertNotIn('count_reference_review',self.draft['rows'][1])
        self.assertEqual(result['rows'][1]['count_reference_review']['source_type'],'GIVEN')
        self.assertIn('not independently measured',result['rows'][1]['count_reference_review']['core_quantity_check'])

    def test_changed_quantity_geometry_source_or_plan_withdraws_review(self):
        for key,value in [('draft_quantity',2),('quantity_sources',[{'geometry_sha256':'changed'}]),('unit','SF')]:
            old=copy.deepcopy(self.draft);self.draft['rows'][1][key]=value
            self.assertFalse(self.checked());self.draft=old
        self.draft['measurement_version']=2;self.assertFalse(self.checked());self.draft['measurement_version']=1
        self.draft['plan_sha256']='different';self.assertFalse(self.checked());self.draft['plan_sha256']='plan'
        self.original.write_text('Changed scope');self.assertFalse(self.checked())

    def test_review_file_change_missing_proof_and_bad_component_are_not_accepted(self):
        (self.root/'review.json').write_text('{}');self.assertFalse(self.checked());self.save_record()
        for field,value in [('check_components',[]),('sources',[]),('source_type','ASSUMED'),('quantity',2),('reviewer','')]:
            old=copy.deepcopy(self.record);self.record[field]=value;self.save_record()
            self.assertFalse(self.checked());self.record=old
        self.save_record();self.record['check_components'][0]['count']=True;self.save_record();self.assertFalse(self.checked())

    def test_billable_or_unowned_or_pending_scope_cannot_be_cleared(self):
        for key,value in [('line_cost',10),('covered_by_package','child'),('cost_owner_row_id','extra')]:
            old=copy.deepcopy(self.draft);self.draft['rows'][1][key]=value
            self.record['row_sha256']=count_digest(self.draft['rows'][1]);self.save_record()
            self.assertFalse(self.checked());self.draft=old
        self.record['row_sha256']=count_digest(self.draft['rows'][1]);self.save_record()
        self.draft['pending_quantities']=[{'template_rows':['2']}];self.assertFalse(self.checked())

    def test_measured_review_needs_view_and_core_reconciliation(self):
        self.record.update(source_type='MEASURED',sheet='Sheet 5',view_source_id='view')
        self.save_record();self.assertFalse(self.checked())
        view=self.root/'view.png';view.write_bytes(b'test fixture bytes')
        self.record['sources'].append({'id':'view','file':'view.png','sha256':self.sha(view),'reference':'Reviewed fixture drawing'})
        self.save_record();self.assertTrue(self.checked())
        result=self.apply()['rows'][1]['count_reference_review']
        self.assertIn('reconcile',result['core_quantity_check'])
        self.assertEqual(result['independent_accuracy_validation'],'not_established')

    def test_zero_requires_explicit_matching_components(self):
        self.draft['rows'][1]['draft_quantity']=0;self.record['quantity']=0
        self.record['check_components'][0]['count']=0;self.record['row_sha256']=count_digest(self.draft['rows'][1])
        self.save_record();self.assertTrue(self.checked())
        self.record['check_components'][0]['count']=1;self.save_record();self.assertFalse(self.checked())

    def test_duplicate_review_and_outside_source_rejected(self):
        self.config['rows'].append(copy.deepcopy(self.config['rows'][0]))
        with self.assertRaises(ValueError):self.apply()
        self.config['rows'].pop();self.record['sources'][0]['file']='../invoice.txt';self.save_record()
        self.assertFalse(self.checked())


class SelectedFixtureReviews(CountReviews):
    def fixture(self):
        row=self.draft['rows'][1]
        row.update(cost_type='ALLOWANCE',covered_by_package=None,unit_cost=20,line_cost=20,line_price=21.4,
            price_evidence={'product_id':'123','model':'MODEL'})
        plan=self.root/'plan.pdf';plan.write_bytes(b'fixture plan')
        self.draft['plan_sha256']=self.sha(plan);self.config['plan_sha256']=self.sha(plan)
        view=self.root/'view.png';view.write_bytes(b'fixture view')
        self.selection={'items':[{'id':12,'quantity':1,'status':'SELECTED','url':'https://supplier.test/p/model/123'}]}
        path=self.root/'selection.json';path.write_text(json.dumps(self.selection))
        self.record.update(scope='selected_fixture_count',plan_sha256=self.sha(plan),source_type='MEASURED',
            plan_source_id='plan',view_source_id='view',sheet='Sheet 5',row_sha256=count_digest(row),
            selected_item={'source_id':'selection','json_pointer':'/items/0','option_id':12,
                'product_id':'123','model':'MODEL','url':'https://supplier.test/p/model/123'})
        for identity,p in [('plan',plan),('view',view),('selection',path)]:
            self.record['sources'].append({'id':identity,'file':p.name,'sha256':self.sha(p),'reference':'Original fixture evidence'})
        self.record['check_components'][0]['source_ids']=['plan','view','selection']
        self.template={'rows':copy.deepcopy(self.draft['rows'])};self.save_record()
        return row

    def test_selected_fixture_quantity_check_does_not_accept_price_or_installation(self):
        self.fixture();result=self.apply();row=result['rows'][1]
        self.assertTrue(current_count_review(row,'selected_fixture_count'))
        self.assertFalse(current_count_review(row))
        report=readiness(result,self.template)
        self.assertEqual(report['rows'][1]['issues'],['Current price certification outstanding'])
        self.assertFalse(row['certified']);self.assertFalse(report['estimate_released'])

    def test_selected_product_count_option_and_status_must_match_original(self):
        self.fixture();original=copy.deepcopy(self.selection)
        for key,value in [('quantity',2),('id',13),('status','UNSELECTED'),('url','https://supplier.test/p/other/456')]:
            self.selection=copy.deepcopy(original);self.selection['items'][0][key]=value
            path=self.root/'selection.json';path.write_text(json.dumps(self.selection))
            self.record['sources'][-1]['sha256']=self.sha(path);self.save_record()
            self.assertFalse(current_count_review(self.apply()['rows'][1],'selected_fixture_count'),key)

    def test_product_path_ignores_page_fragment_but_not_product_substitution(self):
        self.fixture()
        for url,valid in [('https://supplier.test/p/model/123#overlay',True),
                          ('https://supplier.test/p/model/123?view=details#overlay',True),
                          ('https://supplier.test/p/other/456#123',False),
                          ('https://supplier.test/p/other/456?product=/123',False)]:
            self.selection['items'][0]['url']=url
            path=self.root/'selection.json';path.write_text(json.dumps(self.selection))
            self.record['selected_item']['url']=url
            self.record['sources'][-1]['sha256']=self.sha(path);self.save_record()
            self.assertEqual(current_count_review(self.apply()['rows'][1],'selected_fixture_count'),valid,url)

    def test_selected_count_cannot_clear_labor_area_package_or_missing_plan(self):
        row=self.fixture();original=copy.deepcopy(row)
        for key,value in [('unit','SF'),('cost_type','LABOR'),('covered_by_package','owner'),
                          ('assembly_inputs',[{'id':'unfinished'}]),('quantity_sources',[])]:
            row.clear();row.update(copy.deepcopy(original));row[key]=value
            self.record['row_sha256']=count_digest(row);self.save_record()
            self.assertFalse(current_count_review(self.apply()['rows'][1],'selected_fixture_count'),key)
        row.clear();row.update(original);self.record['row_sha256']=count_digest(row)
        self.record['plan_source_id']='missing';self.save_record()
        self.assertFalse(current_count_review(self.apply()['rows'][1],'selected_fixture_count'))

    def test_selected_count_reopens_on_product_substitution_or_bad_pointer(self):
        row=self.fixture();checked=self.apply()['rows'][1]
        checked['price_evidence']['product_id']='other'
        self.assertFalse(current_count_review(checked,'selected_fixture_count'))
        for pointer in ('/items/-1','/items/00','/items/99','items/0'):
            self.record['selected_item']['json_pointer']=pointer;self.save_record()
            self.assertFalse(current_count_review(self.apply()['rows'][1],'selected_fixture_count'))


class OwnerCountReviews(CountReviews):
    def fixture(self):
        row=self.draft['rows'][1]
        row.update(name='Plan sets',cost_type='MATERIAL',covered_by_package=None,
            quantity_sources=[{'source_kind':'owner_confirmation','quantity':1}],
            unit_cost=100,line_cost=100,line_price=115,price_evidence={'source':'Dated allowance'})
        plan=self.root/'plan.pdf';plan.write_bytes(b'fixture plan')
        workbook=self.root/'answers.xlsx';workbook.write_bytes(b'workbook reader is mocked in unit tests')
        self.answer={'question_id':'F25','sheet':'Roberts questions','cell':'E16',
            'question':'How many billable sets?','context':'One set, not one sheet.','answer':1}
        self.submission={'source_workbook_sha256':self.sha(workbook),'records':[self.answer]}
        self.submission_path=self.root/'submission.json';self.submission_path.write_text(json.dumps(self.submission))
        self.draft['plan_sha256']=self.sha(plan);self.config['plan_sha256']=self.sha(plan)
        self.record.update(scope='owner_confirmed_count',plan_sha256=self.sha(plan),
            source_type='GIVEN',given_by='Jason, returned answers',plan_source_id='plan',row_sha256=count_digest(row),
            owner_answer={k:v for k,v in self.answer.items() if k!='answer'})
        self.record['owner_answer'].update(submission_source_id='submission',workbook_source_id='workbook')
        for identity,p in [('plan',plan),('workbook',workbook),('submission',self.submission_path)]:
            self.record['sources'].append({'id':identity,'file':p.name,'sha256':self.sha(p),'reference':'Original owner evidence'})
        self.record['check_components'][0]['source_ids']=['submission','workbook']
        self.book=MagicMock();self.cell=self.book.__getitem__.return_value.__getitem__.return_value
        self.cell.column=5;self.cell.row=16;self.cell.data_type='n';self.cell.value=1
        self.book.__getitem__.return_value.cell.side_effect=lambda r,c:MagicMock(value={1:'F25',3:self.answer['question'],4:self.answer['context']}[c])
        reader=patch('count_reference_reviews.load_workbook',return_value=self.book)
        reader.start();self.addCleanup(reader.stop)
        self.template={'rows':copy.deepcopy(self.draft['rows'])};self.save_record()
        return row

    def accepted(self):return current_count_review(self.apply()['rows'][1],'owner_confirmed_count')

    def save_submission(self):
        self.submission_path.write_text(json.dumps(self.submission))
        self.record['sources'][-1]['sha256']=self.sha(self.submission_path);self.save_record()

    def test_owner_count_clears_quantity_only_and_preserves_warning(self):
        self.fixture();result=self.apply();self.assertTrue(self.accepted())
        report=readiness(result,self.template)
        self.assertEqual(report['rows'][1]['issues'],['Current price certification outstanding'])
        self.assertIn('Owner-confirmed item count; not independently measured',report['rows'][1]['warnings'])
        self.assertFalse(result['rows'][1]['certified']);self.assertFalse(report['estimate_released'])
        self.book.close.assert_called()

    def test_changed_or_duplicate_answer_rejected_even_with_refreshed_hash(self):
        self.fixture();original=copy.deepcopy(self.submission)
        for value in [True,'1',-1,1.5,2,None]:
            self.submission=copy.deepcopy(original);self.submission['records'][0]['answer']=value
            self.save_submission();self.assertFalse(self.accepted(),repr(value))
        self.submission=copy.deepcopy(original);self.submission['records']*=2
        self.save_submission();self.assertFalse(self.accepted())
        self.submission=copy.deepcopy(original);self.submission['source_workbook_sha256']='wrong'
        self.save_submission();self.assertFalse(self.accepted())

    def test_workbook_cell_and_question_binding_must_agree(self):
        self.fixture()
        for key,value in [('value',2),('data_type','f'),('value',True),('column',4)]:
            old=getattr(self.cell,key);setattr(self.cell,key,value)
            self.assertFalse(self.accepted());setattr(self.cell,key,old)
        self.record['owner_answer']['question']='Different question';self.save_record();self.assertFalse(self.accepted())

    def test_owner_count_cannot_clear_assembly_area_labor_or_pending_scope(self):
        row=self.fixture();original=copy.deepcopy(row)
        for key,value in [('unit','SF'),('cost_type','LABOR'),('covered_by_package','owner'),
                ('assembly_inputs',[{'id':'unfinished'}]),('pricing_role','input_only'),('quantity_sources',[])]:
            row.clear();row.update(copy.deepcopy(original));row[key]=value
            self.record['row_sha256']=count_digest(row);self.save_record();self.assertFalse(self.accepted(),key)
        row.clear();row.update(original);self.record['row_sha256']=count_digest(row);self.save_record()
        self.draft['pending_quantities']=[{'template_rows':['2']}];self.assertFalse(self.accepted())

    def test_owner_review_reopens_when_source_plan_or_count_changes(self):
        self.fixture();self.assertTrue(self.accepted())
        self.draft['measurement_version']=2;self.assertFalse(self.accepted());self.draft['measurement_version']=1
        self.record['plan_source_id']='missing';self.save_record();self.assertFalse(self.accepted())
        self.record['plan_source_id']='plan';self.save_record()
        (self.root/'answers.xlsx').write_bytes(b'changed');self.assertFalse(self.accepted())


if __name__=='__main__':unittest.main()
