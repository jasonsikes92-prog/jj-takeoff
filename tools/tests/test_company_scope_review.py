import copy
import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import fitz
from company_profile import initialize,resolve,DEFAULT_PROFILE
from new_plan_template import read_template
from company_scope_review import default_mapping,import_scope
from measurement_estimate import template_draft
from measurement_review import make_server
from measurement_store import MeasurementStore

class CompanyScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.plan=self.root/'source.pdf'
        with fitz.open() as doc:
            doc.new_page(width=500,height=500);doc.save(self.plan)
        self.template=read_template()

    def job(self,name='new',facts=None,overrides=None):
        job=self.root/name;initialize(self.plan,job,facts=facts,project_overrides=overrides)
        folder=job/'draft_takeoff';folder.mkdir();shutil.copyfile(self.plan,folder/'plan.pdf')
        intake=json.loads((job/'estimate_intake.json').read_text());sha=intake['plan_sha256']
        self.rules={'plan_sha256':sha,'rules':[]}
        line={'id':'test-wall','page':1,'kind':'length','width_pt':500,'height_pt':500,
            'points_per_foot':10,'points':[[0,0],[100,0]],'label':'Synthetic wall',
            'color':'#d97706','dependent_rows':[]}
        for file,data in [('measurements.json',{'plan_sha256':sha,'measurements':[line]}),
                          ('quantity_rules.json',self.rules),('template_rows.json',self.template)]:
            (folder/file).write_text(json.dumps(data))
        config=default_mapping(folder,self.template,sha)
        (folder/'company_scope_review.json').write_text(json.dumps(config))
        state=MeasurementStore(folder).read()
        return folder,config,template_draft(state,self.rules,self.template)

    def test_known_attic_scope_and_hose_bibbs_enter_once_without_billable_quantity(self):
        folder,config,draft=self.job(facts={'attic_HVAC':True})
        original=copy.deepcopy(draft);result=import_scope(draft,folder,config)
        water=next(r for r in result['rows'] if r['excel_row']=='195')
        allowance=water['assembly_inputs'][0]
        self.assertEqual((allowance['quantity'],allowance['unit']),(4,'EA'))
        self.assertFalse(allowance['measured_from_plan']);self.assertEqual(allowance['locations'],[])
        self.assertIsNone(water['draft_quantity']);self.assertIsNone(water['line_cost'])
        attic=next(p for p in result['pending_quantities'] if p['id']=='attic-hvac-walkway-platform')
        self.assertIsNone(attic['quantity']);self.assertEqual(attic['template_rows'],['100'])
        self.assertEqual(draft,original)
        with self.assertRaises(ValueError):import_scope(result,folder,config)

    def test_no_attic_or_unknown_does_not_inherit_an_attic_quantity(self):
        profile=json.loads(DEFAULT_PROFILE.read_text())
        for facts in ({},{'attic_HVAC':False},{'attic_HVAC':None}):
            value=resolve(profile,facts)
            self.assertNotIn('attic-hvac-walkway-platform',[a['id'] for a in value['unlocated_scope_allowances']])
        self.assertIn('attic_HVAC',resolve(profile)['facts_to_extract_from_plan'])

    def test_project_exclusion_and_zero_replace_defaults(self):
        folder,config,draft=self.job(facts={'attic_HVAC':True},overrides={
            'framing.attic_HVAC_walkway_and_platform':'exclude_from_framing_scope',
            'plumbing.exterior_hose_bibbs':0})
        result=import_scope(draft,folder,config)
        water=next(r for r in result['rows'] if r['excel_row']=='195')
        self.assertEqual(water['assembly_inputs'][0]['quantity'],0)
        self.assertEqual(water['assembly_inputs'][0]['provenance']['basis'],'project_override')
        self.assertEqual(result['pending_quantities'],[])

    def test_source_tampering_cross_plan_and_mapping_omissions_rejected(self):
        folder,config,draft=self.job()
        for change in ('hash','plan','missing','duplicate','path','wrongrow'):
            changed=copy.deepcopy(config)
            if change=='hash':changed['intake_sha256']='bad'
            if change=='plan':changed['plan_sha256']='other'
            if change=='missing':changed['mappings']=[]
            if change=='duplicate':changed['mappings']*=2
            if change=='path':changed['intake_path']='../../other/estimate_intake.json'
            if change=='wrongrow':changed['mappings'][0]['row_id']=self.template['rows'][0]['row_id']
            with self.subTest(change=change),self.assertRaises(ValueError):import_scope(draft,folder,changed)
        profile=folder.parent/'company_profile_snapshot.json';profile.write_text('{}')
        with self.assertRaises(ValueError):import_scope(draft,folder,config)

    def test_template_ambiguity_and_preexisting_cost_or_input_refused(self):
        folder,config,draft=self.job()
        for field,value in [('draft_quantity',10),('line_cost',100),('completion_status','not_applicable')]:
            changed=copy.deepcopy(draft)
            next(r for r in changed['rows'] if r['excel_row']=='195')[field]=value
            with self.assertRaises(ValueError):import_scope(changed,folder,config)
        template=copy.deepcopy(self.template)
        template['rows'].append(copy.deepcopy(next(r for r in template['rows'] if r['excel_row']=='195')))
        with self.assertRaises(ValueError):default_mapping(folder,template,draft['plan_sha256'])

    def test_actual_http_export_and_changed_intake_rejected(self):
        folder,config,draft=self.job(facts={'attic_HVAC':True})
        server=make_server(MeasurementStore(folder));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}/api/export-snapshot'
        try:
            with urllib.request.urlopen(url) as response:first=json.load(response)
            self.assertEqual(first['draft']['company_scope_review']['scope_ids'],['exterior-hose-bibbs','attic-hvac-walkway-platform'])
            self.assertEqual(len(first['draft']['rows']),711)
            path=folder.parent/'estimate_intake.json';raw=path.read_bytes()
            path.write_bytes(raw+b' ')
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
            self.assertEqual(error.exception.code,400)
            path.write_bytes(raw)
            with urllib.request.urlopen(url) as response:self.assertEqual(json.load(response),first)
        finally:server.shutdown();server.server_close();thread.join()

    def test_existing_pending_attic_scope_cannot_be_added_twice(self):
        folder,config,draft=self.job(facts={'attic_HVAC':True})
        draft['pending_quantities'].append({'id':'attic-hvac-walkway-platform',
            'quantity':None,'unit':'SF','template_rows':['100']})
        with self.assertRaisesRegex(ValueError,'already assigned'):import_scope(draft,folder,config)

if __name__=='__main__':unittest.main()
