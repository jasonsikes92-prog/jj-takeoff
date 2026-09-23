import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from framing_material_allowances import import_allowances


class FramingMaterialOwnership(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.config={'plan_sha256':'plan','template_row':'100','pdf_directory':'.',
            'mappings':[],'excluded_scope':[],
            'kit_purchase_references':[{'component_id':'frames','owner_row_id':'kit-owner',
                'basis':'Same two opening locations; frame supply belongs to the door purchase.'}]}
        for key,value in [('ledger',{}),('authorization',{'answer':'Use saved rates as dated allowances'})]:
            raw=json.dumps(value).encode();(self.folder/(key+'.json')).write_bytes(raw)
            self.config[key]={'path':key+'.json','sha256':hashlib.sha256(raw).hexdigest()}
        self.component={'id':'frames','label':'Pocket frames','quantity':2,'unit':'EA',
            'component_ids':['O05','O06']}
        reference={'id':'door-frame-input','quantity':2,'unit':'EA','measurement_ids':['O05','O06']}
        self.owner={'row_id':'kit-owner','pricing_role':'cost_line','cost_type':'MATERIAL',
            'source_assembly_input_id':'door-frame-input','draft_quantity':2,'unit':'kit',
            'line_cost':146.88,'line_price':168.91,'price_status':'Dated allowance; current price unverified',
            'current_price_certified':False,'quantity_sources':[{'kind':'reviewed_kit_purchase',
                'count_reference':reference,'quantity':2,'unit':'kit','model':'25045','product_id':'206971123'}]}
        self.draft={'plan_sha256':'plan','rows':[{'excel_row':'100','cost_type':'MATERIAL',
            'line_cost':None,'assembly_inputs':[self.component]}], 'additional_cost_rows':[self.owner]}
        self.catalog={'rates':[],'ledger_sha256':'ledger','source_pdf_hashes':{}}

    def result(self):
        with patch('framing_material_allowances.checked_catalog',return_value=self.catalog):
            return import_allowances(self.draft,self.folder,self.config,'2026-09-19')

    def test_existing_kit_charge_is_referenced_without_pricing_it_again(self):
        original=copy.deepcopy(self.draft);result=self.result();study=result['framing_material_allowance_review']
        self.assertEqual(study['unpriced_components'],[])
        self.assertEqual(study['priced_components'],[])
        self.assertEqual(study['priced_component_subtotal_before_tax_delivery_markup'],'0.00')
        ref=study['separately_owned_components'][0]
        self.assertEqual((ref['owner_row_id'],ref['owner_line_cost'],ref['quantity']),('kit-owner',146.88,2))
        self.assertFalse(ref['current_price_certified']);self.assertIsNone(study['full_framing_total'])
        result.pop('framing_material_allowance_review');self.assertEqual(result,original)
        self.assertEqual(self.draft,original)

    def test_equal_counts_at_different_openings_do_not_establish_same_scope(self):
        self.owner['quantity_sources'][0]['count_reference']['measurement_ids']=['O05','OTHER']
        study=self.result()['framing_material_allowance_review']
        self.assertEqual(study['separately_owned_components'],[])
        self.assertIn('locations',study['unpriced_components'][0]['reason'])

    def test_stale_count_missing_owner_and_changed_units_stay_unresolved(self):
        original=copy.deepcopy(self.draft)
        for change in ['quantity','owner','unit','source_count','source_unit','source_id']:
            with self.subTest(change=change):
                self.draft=copy.deepcopy(original);owner=self.draft['additional_cost_rows'][0]
                if change=='quantity':self.draft['rows'][0]['assembly_inputs'][0]['quantity']=3
                elif change=='owner':self.draft['additional_cost_rows']=[]
                elif change=='unit':owner['unit']='LF'
                elif change=='source_count':owner['quantity_sources'][0]['count_reference']['quantity']=3
                elif change=='source_unit':owner['quantity_sources'][0]['count_reference']['unit']='LF'
                else:owner['source_assembly_input_id']='another-component'
                study=self.result()['framing_material_allowance_review']
                self.assertFalse(study['separately_owned_components']);self.assertEqual(len(study['unpriced_components']),1)

    def test_unpriced_existing_owner_remains_owned_but_explicitly_unpriced(self):
        self.owner.update(line_cost=None,line_price=None,price_status='Product rate unavailable')
        study=self.result()['framing_material_allowance_review']
        self.assertIsNone(study['separately_owned_components'][0]['owner_line_cost'])
        self.assertEqual(study['separately_owned_components'][0]['owner_price_status'],'Product rate unavailable')

    def test_count_edit_and_restoration_follow_both_current_sources(self):
        original=self.result()
        for count,ids in [(0,[]),(3,['O05','O06','O07'])]:
            self.component.update(quantity=count,component_ids=ids)
            self.owner.update(draft_quantity=count,line_cost=round(count*73.44,2))
            source=self.owner['quantity_sources'][0];source['quantity']=count
            source['count_reference'].update(quantity=count,measurement_ids=ids)
            study=self.result()['framing_material_allowance_review']
            self.assertEqual(study['separately_owned_components'][0]['quantity'],count)
        self.component.update(quantity=2,component_ids=['O05','O06'])
        self.owner.update(draft_quantity=2,line_cost=146.88)
        self.owner['quantity_sources'][0]['quantity']=2
        self.owner['quantity_sources'][0]['count_reference'].update(quantity=2,measurement_ids=['O05','O06'])
        self.assertEqual(self.result(),original)

    def test_invalid_double_assignment_is_rejected(self):
        self.config['kit_purchase_references']*=2
        with self.assertRaisesRegex(ValueError,'one purchase reference'):self.result()
        self.config['kit_purchase_references']=self.config['kit_purchase_references'][:1]
        self.config['mappings']=[{'component_id':'frames'}]
        with self.assertRaisesRegex(ValueError,'both a framing rate and'):self.result()

    def test_duplicate_or_missing_location_ids_do_not_hide_quantity_work(self):
        for locations in [['O05','O05'],[],['O05']]:
            self.component['component_ids']=locations
            study=self.result()['framing_material_allowance_review']
            self.assertFalse(study['separately_owned_components'])
            self.assertEqual(len(study['unpriced_components']),1)


if __name__=='__main__':unittest.main()
