import copy
import unittest
from pathlib import Path
from framing_material_allowances import reference_plate_measurement


class PlateMeasurementReference(unittest.TestCase):
    def setUp(self):
        self.source={'id':'walls','label':'Wall length','quantity':15,'measured_quantity':15,
            'unit':'LF','use':'assembly_input','measurement_ids':['A','B'],
            'linked_review':{'job':str(Path('job').resolve()),'measurement_version':3},
            'remaining':['Opening assemblies remain incomplete']}
        self.owner={'id':'framing-stock-plates-top','unit':'stick','quantity':2,'component_ids':['S1','S2'],
            'sku':'TOP','stock_length_ft':16,'source_snapshot':{'mapping_sha256':'map'}}
        self.review={'runs':[{'id':'A','length_inches':120,'source_kind':'editable_measurement'},
            {'id':'B','length_inches':60,'source_kind':'editable_measurement'},
            {'id':'E','length_inches':500,'source_kind':'editable_exterior_centerline'}],
            'source_version':3,'mapping_sha256':'map','source_geometry_sha256':{'A':'a','B':'b','E':'e'},
            'boards':[{'id':i,'sku':'TOP','length_ft':16} for i in ['S1','S2']],
            'remaining':['Bottom treatment remains unresolved']}
        self.study={'priced_components':[],'separately_owned_components':[],
            'unpriced_components':[{'component_id':'walls'},{'component_id':'bottom'}],
            'priced_component_subtotal_before_tax_delivery_markup':'100.00','full_framing_total':None}

    def result(self):
        result=copy.deepcopy(self.study)
        reference_plate_measurement(result,[self.source,self.owner],self.review,Path('job'),'walls')
        return result

    def test_raw_geometry_stays_visible_without_an_extra_purchase(self):
        result=self.result();ref=result['measurement_references'][0]
        self.assertEqual(ref['quantity'],15);self.assertFalse(ref['is_purchase'])
        self.assertEqual(ref['derived_purchase_component_ids'],[self.owner['id']])
        self.assertEqual(len(ref['remaining']),2)
        self.assertEqual(result['unpriced_components'],[{'component_id':'bottom'}])
        self.assertEqual(result['priced_component_subtotal_before_tax_delivery_markup'],'100.00')
        self.assertIsNone(result['full_framing_total'])

    def test_changed_source_location_version_count_or_units_stays_unresolved(self):
        for change in ['location','version','quantity','measured','unit','job','duplicate']:
            with self.subTest(change=change):
                self.setUp()
                if change=='location':self.source['measurement_ids']=['A','different']
                elif change=='version':self.source['linked_review']['measurement_version']=4
                elif change=='quantity':self.source['quantity']=16
                elif change=='measured':self.source['measured_quantity']=14
                elif change=='unit':self.source['unit']='SF'
                elif change=='job':self.source['linked_review']['job']='different'
                else:self.source['measurement_ids']=['A','B','B']
                self.assertFalse(self.result()['measurement_references'])

    def test_incomplete_or_incompatible_plate_purchases_do_not_hide_scope(self):
        for change in ['board','count','mapping','sku','length','unit']:
            with self.subTest(change=change):
                self.setUp()
                if change=='board':self.owner['component_ids']=['S1']
                elif change=='count':self.owner['quantity']=3
                elif change=='mapping':self.owner['source_snapshot']['mapping_sha256']='other'
                elif change=='sku':self.owner['sku']='other'
                elif change=='length':self.owner['stock_length_ft']=12
                else:self.owner['unit']='LF'
                self.assertEqual(self.result()['unpriced_components'],self.study['unpriced_components'])

    def test_measurement_cannot_also_own_a_charge(self):
        self.study['priced_components']=[{'component_id':'walls'}]
        with self.assertRaisesRegex(ValueError,'also be a material purchase'):self.result()

    def test_joint_source_edit_and_restoration_recalculate_reference(self):
        original=self.result()
        self.review['runs'][0]['length_inches']=132;self.review['source_version']=4
        self.source.update(quantity=16,measured_quantity=16);self.source['linked_review']['measurement_version']=4
        self.assertEqual(self.result()['measurement_references'][0]['quantity'],16)
        self.setUp();self.assertEqual(self.result(),original)


if __name__=='__main__':unittest.main()
