import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measured_surface_costs import import_surfaces
from measurement_store import MeasurementStore
from estimate_readiness import readiness


class MeasuredSurfaceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.job=self.root/'drawing';self.job.mkdir()
        raw=b'plan';self.plan=hashlib.sha256(raw).hexdigest();(self.job/'plan.pdf').write_bytes(raw)
        self.ms=[{'id':name,'kind':'area','page':1,'points':points,'points_per_foot':10,
                  'width_pt':500,'height_pt':500,'dependent_rows':[]} for name,points in [
                  ('left',[[0,0],[20,0],[20,55],[0,55]]),('right',[[100,0],[120,0],[120,55],[100,55]])]]
        self.write(self.job/'measurements.json',{'plan_sha256':self.plan,'measurements':self.ms})
        self.store=MeasurementStore(self.job)
        self.write(self.root/'owner.json',{'answer':'Granite'})
        proof={'plan_sha256':self.plan,'row_id':'JJ-LIVING','basis':'Owner selected granite.',
               'documents':[{'file':'owner.json','sha256':self.sha(self.root/'owner.json')}]}
        self.write(self.root/'scope.json',proof)
        self.item={'row_id':'JJ-LIVING','parent_row_id':'R1','markup_source_row_id':'R2',
                   'name':'Living tops','job':'drawing','config_sha256':self.sha(self.job/'measurements.json'),
                   'scope_source':{'file':'scope.json','sha256':self.sha(self.root/'scope.json')},
                   'measurement_ids':['left','right'],'basis':'Gross surfaces, round sum once; not slabs.',
                   'remaining':['Granite specification, yield and price unresolved']}
        self.config={'plan_sha256':self.plan,'surfaces':[self.item]}
        self.draft={'plan_sha256':self.plan,'measurement_version':1,'rows':[
            {'row_id':'R1','excel_row':'1','name':'Living room','parent':'','cost_type':'GROUP','unit':'','markup_pct':'0','completion_status':'pending','line_cost':None},
            {'row_id':'R2','excel_row':'2','name':'Comparable top','parent':'Other room','cost_type':'MATERIAL','unit':'sq ft','markup_pct':'15',
             'completion_status':'pending','draft_quantity':None,'line_cost':None,'line_price':None}]}

    def write(self,path,value):path.write_text(json.dumps(value))
    def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def run_import(self):return import_surfaces(self.draft,self.config,self.root)

    def test_live_area_rounding_and_unpriced_scope_are_preserved(self):
        result=self.run_import();row=result['additional_cost_rows'][0]
        self.assertEqual(row['draft_quantity'],22);self.assertEqual(row['markup_pct'],'15')
        self.assertIsNone(row['line_cost']);self.assertEqual(result['rows'],self.draft['rows'])
        state=self.store.read();points=copy.deepcopy(state['measurements']['right']['points'])
        points[1][0]+=1;points[2][0]+=1
        self.store.save('right',points,state['version'],self.plan,'Widen surface')
        row=self.run_import()['additional_cost_rows'][0]
        self.assertAlmostEqual(row['quantity_sources'][0]['measured_quantity'],22.55)
        self.assertEqual(row['draft_quantity'],23)
        audit=readiness(self.run_import(),{'rows':self.draft['rows']})['additional_cost_rows'][0]
        self.assertNotIn('Supplemental parent ownership is unresolved or already priced',audit['issues'])
        self.assertIn('Current line pricing unresolved',audit['issues'])
        self.assertIn('Quantity and assembly certification outstanding',audit['issues'])
        row['markup_pct']='8'
        changed=self.run_import();changed['additional_cost_rows'][0]=row
        self.assertIn('Supplemental parent ownership is unresolved or already priced',readiness(changed,{'rows':self.draft['rows']})['additional_cost_rows'][0]['issues'])

    def test_overlaps_withhold_quantity_and_do_not_create_free_material(self):
        state=self.store.read()
        self.store.save('right',self.ms[0]['points'],state['version'],self.plan,'Duplicate location')
        row=self.run_import()['additional_cost_rows'][0]
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
        self.assertEqual(row['quantity_sources'][0]['overlapping_measurement_ids'],[['left','right']])
        self.item.update(measurement_ids=['left'],other_surface_ids=['right'])
        self.assertIsNone(self.run_import()['additional_cost_rows'][0]['draft_quantity'])

    def test_existing_claims_and_repeated_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):import_surfaces(self.run_import(),self.config,self.root)
        self.config['surfaces'].append({**self.item,'row_id':'JJ-SECOND'})
        proof=json.loads((self.root/'scope.json').read_bytes());proof['row_id']='JJ-SECOND'
        self.write(self.root/'second.json',proof)
        self.config['surfaces'][1]['scope_source']={'file':'second.json','sha256':self.sha(self.root/'second.json')}
        with self.assertRaisesRegex(ValueError,'already has'):self.run_import()
        self.config['surfaces'].pop()
        self.draft['rows'][1]['assembly_inputs']=[{'measurement_ids':['left'],'linked_review':{'job':str(self.job)}}]
        with self.assertRaisesRegex(ValueError,'already has'):self.run_import()

    def test_source_changes_exclusions_and_wrong_units_fail(self):
        for path in [self.root/'scope.json',self.root/'owner.json',self.job/'measurements.json',self.job/'plan.pdf']:
            raw=path.read_bytes();path.write_bytes(raw+b' ')
            try:
                with self.assertRaises(ValueError):self.run_import()
            finally:path.write_bytes(raw)
        for update in [{'unit':'each'},{'cost_type':'LABOR'}]:
            old=copy.deepcopy(self.draft['rows'][1]);self.draft['rows'][1].update(update)
            with self.assertRaisesRegex(ValueError,'markup source'):self.run_import()
            self.draft['rows'][1]=old
        self.draft['rows'][0]['line_cost']=100
        with self.assertRaisesRegex(ValueError,'unpriced parent'):self.run_import()


if __name__=='__main__':unittest.main()
