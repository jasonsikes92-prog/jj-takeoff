import copy
import hashlib
import json
import unittest
import tempfile
from pathlib import Path
from opening_quantity_review import apply_quantities,window_basis,default_mapping
import test_door_policy_revision as policy_fixtures


class OpeningQuantities(unittest.TestCase):
    def setUp(self):
        self.draft={'plan_sha256':'plan','measurement_version':1,'mapped_quantity_rows':0,'rows':[],
            'whole_house_total':None,'estimate_released':False}
        self.config={'plan_sha256':'plan','reviewer':'Reviewer','basis':'Source-reviewed enumeration','mappings':[]}
        for identity,kind,core in [('window','window_installation',None),('solid','ordinary_single_hinged_door','solid'),
                ('hollow','ordinary_single_hinged_door','hollow')]:
            row={'row_id':identity,'excel_row':str(len(self.draft['rows'])+1),'name':identity,'parent':'test',
                'unit':'each','cost_type':'LABOR' if core is None else 'MATERIAL','markup_pct':'7' if core is None else '15',
                'draft_quantity':None,'quantity_sources':[],'assembly_inputs':[],'line_cost':None,'line_price':None,
                'certified':False,'completion_status':'not_yet_reconciled'}
            self.draft['rows'].append(row)
            self.config['mappings'].append({'row_id':identity,'name':identity,'parent':'test','kind':kind,
                'core':core,'nominal_height_inches':80})
        base={'review_status':'current_source_review','source_sha256':'geometry','printed_nominal_size':{'height_inches':80}}
        self.schedule={'plan_sha256':'plan','measurement_version':1,'review_sha256':'review',
            'unresolved_opening_ids':[],'stale_or_missing_label_ids':[],'enumerated_window_unit_count':3,'limitations':['Incomplete coverage'],
            'openings':[{**base,'opening_id':'w','role':'window','window_component_count':3},
                {**base,'opening_id':'d1','role':'interior_door','door_configuration':'single_hinged'},
                {**base,'opening_id':'d2','role':'interior_door','door_configuration':'single_hinged'},
                {**base,'opening_id':'s','role':'special_interior_door'},
                {**base,'opening_id':'e','role':'exterior_door'},
                {**base,'opening_id':'p','role':'open_passage'}],
            'door_core_review':{'openings':[{'opening_id':'d1','core':'solid'},{'opening_id':'d2','core':'hollow'},
                {'opening_id':'s','core':'solid'}]}}
        self.policy={'value':'individual_window_unit','provenance':{'basis':'company_default'}}
    def run_mapping(self):return apply_quantities(self.draft,self.schedule,self.config,self.policy)

    def test_units_core_and_special_scope_without_prices_or_source_mutation(self):
        before=copy.deepcopy(self.draft);result=self.run_mapping()
        self.assertEqual([r['draft_quantity'] for r in result['rows']],[3,1,1])
        self.assertEqual(result['opening_quantity_review']['unmapped_opening_ids'],['s','e'])
        self.assertEqual([r['markup_pct'] for r in result['rows']],['7','15','15'])
        self.assertTrue(all(r['line_cost'] is None and not r['certified'] for r in result['rows']))
        self.assertFalse(result['estimate_released']);self.assertIsNone(result['whole_house_total'])
        self.assertEqual(self.draft,before)

    def test_stale_missing_or_unreviewed_openings_withhold_all_counts(self):
        for field,value in [('unresolved_opening_ids',['d1']),('stale_or_missing_label_ids',['lost'])]:
            with self.subTest(field=field):
                s=copy.deepcopy(self.schedule);s[field]=value
                result=apply_quantities(self.draft,s,self.config,self.policy)
                self.assertTrue(all(r['draft_quantity'] is None for r in result['rows']))
                self.assertEqual(len(result['pending_quantities']),3)
        self.schedule['openings'][1]['review_status']='stale_source_review'
        self.assertTrue(all(r['draft_quantity'] is None for r in self.run_mapping()['rows']))

    def test_unknown_height_configuration_or_core_does_not_create_partial_door_total(self):
        for field,value in [('printed_nominal_size',None),('door_configuration',None)]:
            s=copy.deepcopy(self.schedule);s['openings'][1][field]=value
            result=apply_quantities(self.draft,s,self.config,self.policy)
            self.assertEqual([r['draft_quantity'] for r in result['rows']],[3,None,None])
        self.schedule['door_core_review']=None
        self.assertEqual([r['draft_quantity'] for r in self.run_mapping()['rows']],[3,None,None])

    def test_selected_core_override_and_height_remap_counts(self):
        self.schedule['door_core_review']['openings'][0]['core']='hollow'
        self.assertEqual([r['draft_quantity'] for r in self.run_mapping()['rows']],[3,0,2])
        self.schedule['openings'][1]['printed_nominal_size']={'height_inches':96}
        result=self.run_mapping()
        self.assertEqual([r['draft_quantity'] for r in result['rows']],[3,0,1])
        self.assertIn('d1',result['opening_quantity_review']['unmapped_opening_ids'])

    def test_unknown_window_policy_or_components_withhold_window_labor(self):
        self.policy['value']='framed_opening'
        self.assertEqual([r['draft_quantity'] for r in self.run_mapping()['rows']],[None,1,1])
        self.policy['value']='individual_window_unit';self.schedule['enumerated_window_unit_count']=None
        self.assertIsNone(self.run_mapping()['rows'][0]['draft_quantity'])

    def test_window_material_counts_assemblies_not_units_or_panels(self):
        row=copy.deepcopy(self.draft['rows'][0]);row.update(row_id='material',excel_row='4',name='Windows',cost_type='ALLOWANCE')
        self.draft['rows'].append(row)
        self.config['mappings'].append({'row_id':'material','name':'Windows','parent':'test','kind':'window_assemblies'})
        result=self.run_mapping()
        self.assertEqual([r['draft_quantity'] for r in result['rows']],[3,1,1,1])
        source=result['rows'][-1]['quantity_sources'][0]
        self.assertEqual(source['quantity_basis'],'complete window assembly')
        self.assertEqual(source['opening_details'][0]['window_component_count'],3)
        self.assertEqual(source['opening_ids'],['w'])
        self.schedule['enumerated_window_unit_count']=None;self.policy=None
        self.assertEqual([r['draft_quantity'] for r in self.run_mapping()['rows']],[None,1,1,1])
        self.schedule['stale_or_missing_label_ids']=['lost']
        self.assertIsNone(self.run_mapping()['rows'][-1]['draft_quantity'])

    def test_window_cleaning_counts_units_independent_of_installation_billing(self):
        row=copy.deepcopy(self.draft['rows'][0]);row.update(row_id='cleaning',excel_row='700',
            name='Cleaning - Final window cleaning',parent='Cleaning',cost_type='SUBCONTRACTOR')
        self.draft['rows'].append(row)
        self.config['mappings'].append({'row_id':'cleaning','name':row['name'],'parent':'Cleaning','kind':'window_cleaning'})
        self.policy['value']='framed_opening'
        result=self.run_mapping();cleaning=result['rows'][-1]
        self.assertEqual(cleaning['draft_quantity'],3)
        self.assertIsNone(cleaning['line_cost'])
        self.assertIn('interior/exterior faces counted together',cleaning['quantity_sources'][0]['quantity_basis'])
        self.assertIn('historical invoice',cleaning['quantity_sources'][0]['remaining'][-1])
        self.schedule['enumerated_window_unit_count']=None
        self.assertIsNone(self.run_mapping()['rows'][-1]['draft_quantity'])
        self.schedule['enumerated_window_unit_count']=3
        self.schedule['stale_or_missing_label_ids']=['w']
        self.assertIsNone(self.run_mapping()['rows'][-1]['draft_quantity'])

    def test_unmapped_specialties_keep_source_dimensions_without_inventing_a_template_match(self):
        self.schedule['openings'][3].update(door_configuration='bypass',drawn_panel_count=2,
            location='Closet',printed_nominal_size={'width_inches':60,'height_inches':80})
        self.schedule['openings'][4].update(door_configuration='sliding',drawn_panel_count=2,
            location='Rear exterior',printed_nominal_size={'width_inches':72,'height_inches':80})
        review=self.run_mapping()['opening_quantity_review']
        self.assertEqual([o['opening_id'] for o in review['unmapped_openings']],['s','e'])
        slider=review['unmapped_openings'][1]
        self.assertEqual(slider['printed_nominal_size']['width_inches'],72)
        self.assertEqual(slider['door_configuration'],'sliding')
        self.assertEqual(slider['reference_assembly_count'],1)
        self.assertIsNone(slider['purchase_quantity'])
        self.assertIn('template',slider['reason'])
        self.schedule['openings'][4]['review_status']='stale_source_review'
        stale=next(o for o in self.run_mapping()['opening_quantity_review']['unmapped_openings'] if o['opening_id']=='e')
        self.assertIsNone(stale['reference_assembly_count'])
        self.assertIsNone(stale['door_configuration'])

    def test_claimed_rows_wrong_units_and_duplicate_scopes_are_rejected(self):
        for key,value in [('draft_quantity',0),('line_cost',0),('unit','LF'),('covered_by_package','quote'),
                ('cost_owner_row_id','owner'),('cost_type','MATERIAL'),('assembly_inputs',[{}]),('completion_status','not_applicable')]:
            draft=copy.deepcopy(self.draft);draft['rows'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):apply_quantities(draft,self.schedule,self.config,self.policy)
        self.config['mappings'].append(copy.deepcopy(self.config['mappings'][0]))
        with self.assertRaises(ValueError):self.run_mapping()
        self.config['mappings'].pop()
        self.config['mappings'][2]['core']='solid'
        with self.assertRaisesRegex(ValueError,'multiple template rows'):self.run_mapping()

    def test_unresolved_neighbor_does_not_erase_known_assembly_references(self):
        self.schedule['unresolved_opening_ids']=['d1']
        self.schedule['openings'][1].update(role=None,review_status='role_unreviewed')
        self.schedule['openings'][4].update(review_status='native_symbol_inference',
            door_configuration='double_hinged',drawn_panel_count=2)
        result=self.run_mapping()
        self.assertTrue(all(r['draft_quantity'] is None for r in result['rows']))
        refs={o['opening_id']:o for o in result['opening_quantity_review']['unmapped_openings']}
        self.assertEqual(refs['e']['reference_assembly_count'],1)
        self.assertEqual(refs['e']['drawn_panel_count'],2)
        self.assertTrue(refs['e']['interpretation_requires_review'])
        self.assertIsNone(refs['e']['purchase_quantity'])
        self.assertIsNone(refs['d1']['reference_assembly_count'])
        self.assertFalse(result['estimate_released'])

    def test_drawing_revision_and_template_scope_are_checked(self):
        for key,value in [('plan_sha256','different'),('measurement_version',2)]:
            s=copy.deepcopy(self.schedule);s[key]=value
            with self.assertRaises(ValueError):apply_quantities(self.draft,s,self.config,self.policy)
        self.config['mappings'][0]['parent']='other'
        with self.assertRaisesRegex(ValueError,'scope changed'):self.run_mapping()


class WindowPolicy(unittest.TestCase):
    def test_frozen_policy_replay_override_and_hash_checks(self):
        fixture=policy_fixtures.DoorPolicyRevision();fixture.setUp();self.addCleanup(fixture.doCleanups)
        key='windows.installation_quantity_basis'
        fixture.base['rules'].append({'key':key,'value':'individual_window_unit','source':'Owner answer'})
        fixture.write_base();path=fixture.job/'estimate_intake.json'
        ref={'path':'../estimate_intake.json','sha256':fixture.sha(path)}
        self.assertEqual(window_basis(fixture.folder,ref,'plan')['value'],'individual_window_unit')
        fixture.overrides={key:'framed_opening'};fixture.write_base();ref['sha256']=fixture.sha(path)
        self.assertEqual(window_basis(fixture.folder,ref,'plan')['value'],'framed_opening')
        data=json.loads(path.read_bytes());data['settings'][key]='individual_window_unit';path.write_text(json.dumps(data))
        ref['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'saved source decisions'):window_basis(fixture.folder,ref,'plan')
        with self.assertRaises(ValueError):window_basis(fixture.folder,{**ref,'path':'../../outside'},'plan')


class DefaultOpeningMapping(unittest.TestCase):
    def test_row_identity_is_found_by_scope_not_position_and_other_options_are_not_claimed(self):
        from new_plan_template import read_template
        template=read_template();template['rows'].reverse()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'draft_takeoff';folder.mkdir()
            path=folder/'template_rows.json';path.write_text(json.dumps(template))
            mapping=default_mapping(folder,template,'plan')
            self.assertEqual(len(mapping['mappings']),7)
            self.assertEqual({m['row_id'].rsplit('R',1)[-1] for m in mapping['mappings']},{'0112','0114','0139','0141','0146','0148','0700'})
            self.assertEqual(mapping['unresolved_template_scopes'],[])
            self.assertEqual(mapping['hardware_target']['row_id'].rsplit('R',1)[-1], '0156')
            self.assertNotIn('installation_policy',mapping)
            (folder.parent/'estimate_intake.json').write_text('saved intake fixture')
            self.assertIn('installation_policy',default_mapping(folder,template,'plan'))

    def test_ambiguous_or_wrong_unit_template_rows_are_reported_not_guessed(self):
        from new_plan_template import read_template
        template=read_template()
        window=next(r for r in template['rows'] if r['excel_row']=='114')
        template['rows'].append(copy.deepcopy(window))
        next(r for r in template['rows'] if r['excel_row']=='139')['unit']='LF'
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'template_rows.json').write_text(json.dumps(template))
            mapping=default_mapping(folder,template,'plan')
        self.assertEqual(len(mapping['mappings']),5)
        self.assertEqual(len(mapping['unresolved_template_scopes']),2)


if __name__=='__main__':unittest.main()
