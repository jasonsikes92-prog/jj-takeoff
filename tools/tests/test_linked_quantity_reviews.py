import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'viewer'))
from measurement_store import MeasurementStore
from linked_quantity_reviews import import_linked_quantities
from measurement_quantities import geometry_digest


class LinkedQuantityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name);self.job=self.folder/'cladding';self.job.mkdir()
        raw=b'fixed plan';self.sha=hashlib.sha256(raw).hexdigest()
        (self.job/'plan.pdf').write_bytes(raw)
        config={'plan_sha256':self.sha,'measurements':[{'id':'wall','page':1,
            'kind':'area','points':[[0,0],[100,0],[100,100],[0,100]],
            'width_pt':500,'height_pt':500,'points_per_foot':10,'dependent_rows':['226']}]}
        self.rules={'plan_sha256':self.sha,'rules':[{'id':'cladding',
            'label':'Partial cladding','measurement_ids':['wall'],'unit':'SF',
            'rounding':'none','template_rows':['226'],'use':'assembly_input',
            'basis':'Gross wall','remaining':['Returns still unresolved']}]}
        (self.job/'measurements.json').write_text(json.dumps(config))
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        self.store=MeasurementStore(self.job)
        self.links=[{'job':'cladding','config_sha256':self.digest('measurements.json'),
                     'rules_sha256':self.digest('quantity_rules.json'),'template_rows':['226']}]
        self.draft={'plan_sha256':self.sha,'rows':[{'excel_row':'226','cost_type':'MATERIAL',
            'completion_status':'pending','draft_quantity':None,'line_cost':None,'line_price':None}]}

    def digest(self,name):
        return hashlib.sha256((self.job/name).read_bytes()).hexdigest()

    def test_source_geometry_edit_withholds_derived_layout_until_restored(self):
        upstream=self.folder/'roof';upstream.mkdir()
        for name in ('plan.pdf','measurements.json'):
            (upstream/name).write_bytes((self.job/name).read_bytes())
        source=MeasurementStore(upstream);state=source.read()
        self.links[0]['source_measurements']=[{'job':'roof','geometry_sha256':{
            'wall':geometry_digest(state['measurements']['wall'])}}]
        first=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(first['rows'][0]['assembly_inputs'][0]['quantity'],100)
        moved=[[0,0],[110,0],[110,100],[0,100]]
        source.save('wall',moved,1,self.sha,'Changed source roof')
        with self.assertRaisesRegex(ValueError,'Source measurement geometry changed'):
            import_linked_quantities(self.draft,self.links,self.folder)
        source.save('wall',state['measurements']['wall']['points'],2,self.sha,'Restore source roof')
        self.assertEqual(import_linked_quantities(self.draft,self.links,self.folder),first)
        self.links[0]['source_measurements'][0]['geometry_sha256']={}
        with self.assertRaisesRegex(ValueError,'matching plan and geometry'):
            import_linked_quantities(self.draft,self.links,self.folder)

    def test_derived_contour_cannot_survive_a_source_room_revision(self):
        self.draft['measurement_version']=3
        self.links[0]['derived_from_measurement_version']=3
        self.assertEqual(import_linked_quantities(self.draft,self.links,self.folder)
                         ['rows'][0]['assembly_inputs'][0]['quantity'],100)
        for revision in (4,None):
            self.draft['measurement_version']=revision
            with self.assertRaisesRegex(ValueError,'recalculation'):
                import_linked_quantities(self.draft,self.links,self.folder)

    def test_saved_step_updates_combined_quantity_and_retains_partial_scope(self):
        before=copy.deepcopy(self.draft)
        first=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(first['rows'][0]['assembly_inputs'][0]['quantity'],100)
        self.assertNotIn('latest_edit',first['rows'][0]['assembly_inputs'][0]['linked_review'])
        stepped=[[0,0],[100,0],[100,100],[70,100],[70,120],[30,120],[30,100],[0,100]]
        self.store.save('wall',stepped,1,self.sha,'Porch step')
        updated=import_linked_quantities(self.draft,self.links,self.folder)
        row=updated['rows'][0];value=row['assembly_inputs'][0]
        self.assertEqual(value['quantity'],108)
        self.assertEqual(value['linked_review']['measurement_version'],2)
        self.assertEqual(value['linked_review']['latest_edit'],
                         {'measurement_id':'wall','note':'Porch step'})
        self.assertEqual(value['remaining'],['Returns still unresolved'])
        self.assertIsNone(row['draft_quantity']);self.assertIsNone(row['line_cost'])
        self.assertIsNone(row['line_price']);self.assertEqual(self.draft,before)

    def test_live_derivation_requires_current_matching_source_and_single_method(self):
        self.links[0]['derived_floor_field']={'source_file':'recipe.json','source_sha256':'unset'}
        self.draft['measurement_version']=3
        for state in (None,{'version':2,'plan_sha256':self.sha},{'version':3,'plan_sha256':'other'}):
            with self.assertRaisesRegex(ValueError,'current draft source state'):
                import_linked_quantities(self.draft,self.links,self.folder,source_state=state)
        self.links[0]['derived_from_measurement_version']=3
        with self.assertRaisesRegex(ValueError,'one derivation method'):
            import_linked_quantities(self.draft,self.links,self.folder,
                                     source_state={'version':3,'plan_sha256':self.sha})

    def test_changed_rules_or_configuration_are_rejected(self):
        for name in ('measurements.json','quantity_rules.json'):
            with self.subTest(name=name):
                original=(self.job/name).read_bytes()
                (self.job/name).write_bytes(original+b' ')
                with self.assertRaisesRegex(ValueError,'configuration changed'):
                    import_linked_quantities(self.draft,self.links,self.folder)
                (self.job/name).write_bytes(original)

    def test_explicit_partial_append_preserves_existing_inputs_and_rejects_duplicates(self):
        existing={'id':'rectangular-walls','quantity':900,'unit':'SF'}
        self.draft['rows'][0]['assembly_inputs']=[existing]
        self.links[0]['append_assembly_inputs']=True
        result=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(result['rows'][0]['assembly_inputs'][0],existing)
        self.assertEqual(result['rows'][0]['assembly_inputs'][1]['quantity'],100)
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            import_linked_quantities(result,self.links,self.folder)
        for update in ({'draft_quantity':1},{'line_cost':1},{'covered_by_package':'quote'}):
            draft=copy.deepcopy(self.draft);draft['rows'][0].update(update)
            with self.assertRaisesRegex(ValueError,'already assigned'):
                import_linked_quantities(draft,self.links,self.folder)

    def test_wrong_plan_unapproved_target_and_missing_history_are_rejected(self):
        wrong=copy.deepcopy(self.draft);wrong['plan_sha256']='other'
        with self.assertRaisesRegex(ValueError,'another drawing'):
            import_linked_quantities(wrong,self.links,self.folder)
        links=copy.deepcopy(self.links);links[0]['template_rows']=[]
        with self.assertRaisesRegex(ValueError,'Unapproved'):
            import_linked_quantities(self.draft,links,self.folder)
        (self.job/'measurement_edits.sqlite3').unlink()
        with self.assertRaisesRegex(ValueError,'no saved measurement history'):
            import_linked_quantities(self.draft,self.links,self.folder)

    def test_multiple_partial_inputs_share_explicit_package_target(self):
        self.rules['rules'].append({**self.rules['rules'][0],'id':'second-scope','label':'Second scope'})
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        self.links[0]['rules_sha256']=self.digest('quantity_rules.json')
        with self.assertRaisesRegex(ValueError,'duplicate'):
            import_linked_quantities(self.draft,self.links,self.folder)
        self.links[0]['append_assembly_inputs']=True
        result=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual([q['id'] for q in result['rows'][0]['assembly_inputs']],['cladding','second-scope'])
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertIsNone(result['rows'][0]['line_price'])
        with self.assertRaisesRegex(ValueError,'[Dd]uplicate'):
            import_linked_quantities(self.draft,self.links*2,self.folder)

    def test_pending_partial_input_keeps_other_package_inputs(self):
        second={**self.rules['rules'][0],'id':'unreviewed-scope','label':'Unreviewed scope',
                'defer_pending_scope':True,'geometry_reviews':{'wall':{'decision':'not_suitable_for_estimate'}}}
        self.rules['rules'].append(second)
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        self.links[0].update(rules_sha256=self.digest('quantity_rules.json'),append_assembly_inputs=True)
        result=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual([q['id'] for q in result['rows'][0]['assembly_inputs']],['cladding'])
        self.assertEqual([q['id'] for q in result['pending_quantities']],['unreviewed-scope'])
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertIsNone(result['rows'][0]['line_price'])

    def test_existing_ownership_and_exclusions_cannot_be_overwritten(self):
        for update in ({'draft_quantity':10},{'line_cost':1},{'covered_by_package':'quote'},
                       {'assembly_inputs':[{'id':'existing'}]}, {'cost_type':'GROUP'},
                       {'cost_type':'ASSEMBLY'}, {'completion_status':'not_applicable_owner'}):
            with self.subTest(update=update):
                draft=copy.deepcopy(self.draft);draft['rows'][0].update(update)
                with self.assertRaisesRegex(ValueError,'excluded or already assigned'):
                    import_linked_quantities(draft,self.links,self.folder)

    def test_duplicate_link_and_purchase_quantity_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            import_linked_quantities(self.draft,self.links*2,self.folder)
        self.rules['rules'][0]['use']='template_quantity'
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        self.links[0]['rules_sha256']=self.digest('quantity_rules.json')
        with self.assertRaisesRegex(ValueError,'purchase quantity'):
            import_linked_quantities(self.draft,self.links,self.folder)


    def test_selected_direct_quantity_updates_without_importing_unselected_rules(self):
        self.rules['rules'][0]['use']='template_quantity'
        self.rules['rules'].append({**self.rules['rules'][0],'id':'unselected','template_rows':['999']})
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        link=self.links[0];link.update(rules_sha256=self.digest('quantity_rules.json'),
            quantity_rule_ids=['cladding'],template_quantity_rows=['226'])
        self.draft['rows'][0]['unit']='ft2'
        before=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(before['rows'][0]['draft_quantity'],100)
        original=copy.deepcopy(self.store.read()['measurements']['wall']['points'])
        self.store.save('wall',[[0,0],[120,0],[120,100],[0,100]],1,self.sha,'Widen')
        after=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(after['rows'][0]['draft_quantity'],120)
        self.assertNotEqual(before['linked_quantity_reviews'][0]['geometry_sha256'],after['linked_quantity_reviews'][0]['geometry_sha256'])
        self.store.save('wall',original,2,self.sha,'Restore')
        restored=import_linked_quantities(self.draft,self.links,self.folder)
        self.assertEqual(before['linked_quantity_reviews'][0]['geometry_sha256'],restored['linked_quantity_reviews'][0]['geometry_sha256'])
        self.draft['rows'][0]['unit']='each'
        with self.assertRaisesRegex(ValueError,'matching unit'):
            import_linked_quantities(self.draft,self.links,self.folder)
        for ids in ([],['missing'],['cladding','cladding']):
            link['quantity_rule_ids']=ids
            with self.assertRaisesRegex(ValueError,'selection'):
                import_linked_quantities(self.draft,self.links,self.folder)

    def test_area_unit_aliases_preserve_template_units_and_reject_other_dimensions(self):
        self.rules['rules'][0]['use']='template_quantity'
        (self.job/'quantity_rules.json').write_text(json.dumps(self.rules))
        self.links[0].update(rules_sha256=self.digest('quantity_rules.json'),template_quantity_rows=['226'])
        for unit in ('SF','ft2','sq ft'):
            with self.subTest(unit=unit):
                self.draft['rows'][0]['unit']=unit
                original=copy.deepcopy(self.draft)
                row=import_linked_quantities(self.draft,self.links,self.folder)['rows'][0]
                self.assertEqual(row['draft_quantity'],100)
                self.assertEqual(row['unit'],unit)
                self.assertEqual(row['quantity_sources'][0]['remaining'],['Returns still unresolved'])
                self.assertEqual(self.draft,original)
        for unit in ('LF','feet','each','CY','',None):
            with self.subTest(unit=unit):
                self.draft['rows'][0]['unit']=unit
                with self.assertRaisesRegex(ValueError,'matching unit'):
                    import_linked_quantities(self.draft,self.links,self.folder)

    def test_measured_lf_populates_original_feet_unit_and_rejects_area_or_count(self):
        job=self.folder/'beams';job.mkdir()
        (job/'plan.pdf').write_bytes((self.job/'plan.pdf').read_bytes())
        m={'id':'beam','page':1,'kind':'length','points':[[0,0],[101,0]],
            'width_pt':500,'height_pt':500,'points_per_foot':10,'dependent_rows':['226']}
        (job/'measurements.json').write_text(json.dumps({'plan_sha256':self.sha,'measurements':[m]}))
        rules={'plan_sha256':self.sha,'rules':[{'id':'beam-length','label':'Beam length',
            'measurement_ids':['beam'],'unit':'LF','rounding':'whole_up','template_rows':['226'],
            'use':'template_quantity','basis':'Measured run','remaining':['Stock cuts separate']}]}
        (job/'quantity_rules.json').write_text(json.dumps(rules));store=MeasurementStore(job)
        link={'job':'beams','config_sha256':hashlib.sha256((job/'measurements.json').read_bytes()).hexdigest(),
            'rules_sha256':hashlib.sha256((job/'quantity_rules.json').read_bytes()).hexdigest(),
            'template_rows':['226'],'template_quantity_rows':['226']}
        self.draft['rows'][0].update(unit='feet',markup_pct='7')
        before=copy.deepcopy(self.draft)
        first=import_linked_quantities(self.draft,[link],self.folder)
        self.assertEqual(first['rows'][0]['draft_quantity'],11)
        self.assertEqual(first['rows'][0]['unit'],'feet')
        self.assertEqual(first['rows'][0]['markup_pct'],'7')
        self.assertEqual(first['rows'][0]['quantity_sources'][0]['unit'],'LF')
        self.assertIsNone(first['rows'][0]['line_cost']);self.assertEqual(self.draft,before)
        store.save('beam',[[0,0],[121,0]],1,self.sha,'Extend beam')
        changed=import_linked_quantities(self.draft,[link],self.folder)
        self.assertEqual(changed['rows'][0]['draft_quantity'],13)
        for unit in ['ft2','each']:
            self.draft['rows'][0]['unit']=unit
            with self.assertRaisesRegex(ValueError,'matching unit'):
                import_linked_quantities(self.draft,[link],self.folder)

    def test_explicit_row_mapping_preserves_source_and_live_measurements(self):
        self.draft['rows'][0]['excel_row']='214'
        self.links[0].update(template_rows=['214'],template_row_mapping={'226':'214'})
        original=copy.deepcopy(self.rules)
        first=import_linked_quantities(self.draft,self.links,self.folder)
        part=first['rows'][0]['assembly_inputs'][0]
        self.assertEqual(part['template_rows'],['214'])
        self.assertEqual(part['source_template_rows'],['226'])
        self.assertEqual(part['quantity'],100)
        self.assertEqual(part['linked_review']['template_row_mapping'],{'226':'214'})
        self.store.save('wall',[[0,0],[110,0],[110,100],[0,100]],1,self.sha,'Change mapped source')
        self.assertEqual(import_linked_quantities(self.draft,self.links,self.folder)['rows'][0]['assembly_inputs'][0]['quantity'],110)
        self.assertEqual(json.loads((self.job/'quantity_rules.json').read_bytes()),original)
        for mapping in ({},{'wrong':'214'},{'226':'missing'},{'226':214},[]):
            self.links[0]['template_row_mapping']=mapping
            with self.assertRaisesRegex(ValueError,'row mapping'):
                import_linked_quantities(self.draft,self.links,self.folder)

if __name__=='__main__':unittest.main()
