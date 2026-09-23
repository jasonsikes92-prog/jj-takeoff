import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'levelground'))
from opening_references import references


def fixture():
    base={'page':2,'review_status':'current_source_review','tag':'3068','location':'Source room',
        'printed_nominal_size':{'width_inches':36,'height_inches':80},'door_configuration':'single_hinged',
        'drawn_panel_count':1,'project_core':'private-core','project_core_source':'private-source',
        'role_source':'private-reviewer', 'supplier_cost':98765}
    rows=[{**base,'opening_id':role,'role':role} for role in
        ('window','interior_door','special_interior_door','exterior_door','open_passage')]
    rows[0]['window_component_count']=3
    return {'plan_sha256':'plan','measurement_version':1,'review_sha256':'review','openings':rows,
        'unresolved_opening_ids':[],'stale_or_missing_label_ids':[],
        'door_core_review':{'settings':'private-defaults','markup_pct':15,'price':98765}}


class OpeningReferences(unittest.TestCase):
    def test_count_units_and_whitelisted_details_omit_company_information(self):
        source=fixture();before=copy.deepcopy(source);result=references(source)
        self.assertEqual([q['qty'] for q in result['quantities']],[3,1,1,1])
        self.assertEqual(result['open_passage_count'],1)
        self.assertFalse(result['coverage_certified']);self.assertFalse(result['purchase_released'])
        for private in ('private-core','private-source','private-reviewer','private-defaults','98765','markup_pct','supplier_cost','door_core_review'):
            self.assertNotIn(private,json.dumps(result))
        self.assertEqual(source,before)

    def test_stale_or_missing_source_withholds_counts_and_changes_identity(self):
        source=fixture();before=references(source)
        for field,value in [('stale_or_missing_label_ids',['missing']),('unresolved_opening_ids',['window'])]:
            changed=copy.deepcopy(source);changed[field]=value;result=references(changed)
            self.assertEqual(result['quantities'],[]);self.assertFalse(result['source_enumeration_current'])
            self.assertNotEqual(result['source_sha256'],before['source_sha256'])
        source['openings'][0]['review_status']='stale_source_review';result=references(source)
        self.assertIsNone(result['details'][0]['role']);self.assertIsNone(result['details'][0]['individual_window_units'])
        self.assertEqual(result['quantities'],[])

    def test_unknown_window_components_do_not_infer_mull_units(self):
        source=fixture();source['openings'][0]['window_component_count']=None
        result=references(source)
        self.assertEqual([q['qty'] for q in result['quantities']],[1,1,1])
        self.assertTrue(any('window quantity is withheld' in u for u in result['unknowns']))

    def test_private_policy_change_does_not_change_public_reference(self):
        source=fixture();before=references(source)
        source['door_core_review']={'private_updated_supplier_price':321}
        self.assertEqual(references(source),before)


if __name__=='__main__':unittest.main()
