"""Supplier counts must retain opening identity and assembly/component meaning."""
import copy
import json
import unittest
import test_count_reference_reviews as base
from count_reference_reviews import count_digest,current_count_review
from estimate_readiness import readiness


class SupplierCounts(unittest.TestCase):
    def setUp(self):
        base.CountReviews.setUp(self)
        self.row=self.draft['rows'][1]
        self.row.update(cost_type='LABOR',covered_by_package=None,unit_cost=75,line_cost=375,line_price=401.25,
                        draft_quantity=5)
        plan=self.root/'plan.pdf';plan.write_bytes(b'window plan')
        spec=self.root/'spec.pdf';spec.write_bytes(b'supplier specification')
        view=self.root/'view.png';view.write_bytes(b'reviewed source rendering')
        self.schedule={'sources':{'specifications.pdf':self.sha(spec)},'assemblies':[
            {'opening_id':'A','assembly_quantity':1,'component_count':3,'source_plan_sheet':5},
            {'opening_id':'B','assembly_quantity':1,'component_count':2,'source_plan_sheet':9}]}
        path=self.root/'schedule.json';path.write_text(json.dumps(self.schedule))
        self.row['quantity_sources']=[{'kind':'enumerated_window_components','assemblies':copy.deepcopy(self.schedule['assemblies'])}]
        self.draft['plan_sha256']=self.sha(plan);self.config['plan_sha256']=self.sha(plan)
        self.record.update(scope='supplier_schedule_count',plan_sha256=self.sha(plan),source_type='MEASURED',
            plan_source_id='plan',view_source_id='view',sheet='5 and 9',schedule_source_id='schedule',
            specification_source_id='spec',count_basis='component',quantity=5,row_sha256=count_digest(self.row),
            check_components=[{'label':'Two mapped openings','count':5,'source_ids':['plan','schedule','spec']}])
        for identity,p in [('plan',plan),('view',view),('spec',spec),('schedule',path)]:
            self.record['sources'].append({'id':identity,'file':p.name,'sha256':self.sha(p),'reference':'Source count evidence'})
        self.template={'rows':copy.deepcopy(self.draft['rows'])};self.save_record()

    sha=base.CountReviews.sha
    save_record=base.CountReviews.save_record
    apply=base.CountReviews.apply

    def checked(self):return current_count_review(self.apply()['rows'][1],'supplier_schedule_count')
    def rebind(self):
        self.record['row_sha256']=count_digest(self.row);self.save_record()

    def test_components_and_assemblies_are_distinct_and_do_not_certify_prices(self):
        self.assertTrue(self.checked())
        result=self.apply();report=readiness(result,self.template)
        self.assertEqual(report['rows'][1]['issues'],['Price source evidence missing','Current price certification outstanding'])
        self.assertFalse(report['estimate_released']);self.assertFalse(result['rows'][1]['certified'])
        self.row['cost_type']='ALLOWANCE';self.row['draft_quantity']=2
        self.row['quantity_sources'][0]['kind']='enumerated_window_assemblies'
        self.record['count_basis']='assembly';self.record['quantity']=2;self.record['check_components'][0]['count']=2
        self.rebind();self.assertTrue(self.checked())
        self.record['count_basis']='component';self.save_record();self.assertFalse(self.checked())

    def test_duplicate_missing_or_changed_openings_rejected_even_with_equal_total(self):
        baseline=copy.deepcopy(self.row['quantity_sources'])
        for field,value in [('opening_id','A'),('component_count',3),('source_plan_sheet',5)]:
            self.row['quantity_sources']=copy.deepcopy(baseline)
            self.row['quantity_sources'][0]['assemblies'][1][field]=value
            self.rebind();self.assertFalse(self.checked(),field)
        self.row['quantity_sources']=copy.deepcopy(baseline)
        self.row['quantity_sources'][0]['assemblies'].pop();self.rebind();self.assertFalse(self.checked())

    def test_specification_hash_must_match_bound_schedule(self):
        self.schedule['sources']['specifications.pdf']='different'
        path=self.root/'schedule.json';path.write_text(json.dumps(self.schedule))
        self.record['sources'][-1]['sha256']=self.sha(path);self.save_record()
        self.assertFalse(self.checked())

    def test_installed_trim_count_uses_openings_not_components_or_board_lengths(self):
        self.row.update(cost_type='SUBCONTRACTOR',draft_quantity=2,
            price_evidence={'source_unit':'trimmed opening','units_per_source_unit':1},
            assembly_inputs=[{'id':'window-rough-opening-perimeter','use':'assembly_input','quantity':80,'unit':'LF'}])
        self.row['quantity_sources']=[{'kind':'enumerated_window_trim_assemblies','assemblies':[
            {'opening_id':p['opening_id'],'assembly_quantity':p['assembly_quantity']} for p in self.schedule['assemblies']]}]
        self.record.update(count_basis='trim_assembly',quantity=2)
        self.record['remaining_scope']=['Identify extra billed openings']
        self.record['check_components'][0]['count']=2
        self.rebind();self.assertTrue(self.checked())
        report=readiness(self.apply(),self.template)['rows'][1]
        self.assertIn('Identify extra billed openings',report['issues'])
        self.assertNotIn('Quantity and assembly certification outstanding',report['issues'])
        original=copy.deepcopy(self.row)
        for field,value in [('price_evidence',{'source_unit':'LF','units_per_source_unit':1}),
                            ('assembly_inputs',[{'id':'unresolved-other-scope','use':'assembly_input'}]),
                            ('draft_quantity',5)]:
            self.row.clear();self.row.update(copy.deepcopy(original));self.row[field]=value
            self.rebind();self.assertFalse(self.checked(),field)
        self.row.clear();self.row.update(copy.deepcopy(original))
        self.row['quantity_sources'][0]['assemblies'][1]['opening_id']='A'
        self.rebind();self.assertFalse(self.checked())

    def test_changed_quantity_source_revision_and_plan_reopen(self):
        result=self.apply()['rows'][1];result['quantity_sources'][0]['assemblies'][0]['opening_id']='C'
        self.assertFalse(current_count_review(result,'supplier_schedule_count'))
        self.draft['measurement_version']=2;self.assertFalse(self.checked());self.draft['measurement_version']=1
        self.draft['plan_sha256']='changed';self.assertFalse(self.checked());self.draft['plan_sha256']=self.config['plan_sha256']
        self.row['draft_quantity']=6;self.assertFalse(self.checked())

    def test_wrong_unit_package_partial_or_pending_quantity_rejected(self):
        original=copy.deepcopy(self.row)
        for key,value in [('unit','LF'),('covered_by_package','owner'),('assembly_inputs',[{'id':'partial'}]),
                          ('pricing_role','input_only'),('cost_type','SUBCONTRACTOR')]:
            self.row.clear();self.row.update(copy.deepcopy(original));self.row[key]=value
            self.rebind();self.assertFalse(self.checked(),key)
        self.row.clear();self.row.update(original);self.rebind()
        self.draft['pending_quantities']=[{'template_rows':['2']}];self.assertFalse(self.checked())


if __name__=='__main__':unittest.main()
