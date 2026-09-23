import copy
import unittest
from enclosure_quantity_review import apply_quantities,binding
import test_wall_enclosure_candidates as enclosure_fixtures


class EnclosureQuantities(unittest.TestCase):
    def setUp(self):
        fixture=enclosure_fixtures.WallEnclosures();fixture.setUp();self.enclosures=fixture.calculate()
        row={'row_id':'first','excel_row':'5','name':'SF FIRST FLOOR','parent':'INPUTS','unit':'ft2',
            'cost_type':'MATERIAL','pricing_role':'input_only','markup_pct':'0','draft_quantity':None,
            'quantity_sources':[],'assembly_inputs':[],'unit_cost':None,'line_cost':None,'line_price':None,
            'completion_status':'not_yet_reconciled','certified':False}
        self.draft={'plan_sha256':'plan','measurement_version':1,'rows':[row],
            'mapped_quantity_rows':0,'whole_house_total':None,'estimate_released':False}
        enclosure=self.enclosures['candidate_enclosures'][0]
        self.review={'plan_sha256':'plan','reviewer':'Source reviewer','basis':'First-floor gross wall-face boundary; exclude patios',
            'mappings':[{'row_id':'first','name':'SF FIRST FLOOR','enclosures':[{'id':enclosure['id'],'sha256':binding(enclosure)}]}]}

    def calculate(self):return apply_quantities(self.draft,self.enclosures,self.review)

    def test_current_scope_populates_only_nonbillable_input_and_preserves_sources(self):
        before=copy.deepcopy(self.draft);result=self.calculate();row=result['rows'][0]
        self.assertEqual(row['draft_quantity'],100);self.assertEqual(row['markup_pct'],'0')
        self.assertEqual(row['quantity_sources'][0]['source_pages'],[1])
        self.assertEqual(len(row['quantity_sources'][0]['measurement_ids']),4)
        self.assertIn('gross wall-face',row['quantity_sources'][0]['quantity_basis'])
        self.assertIsNone(row['line_cost']);self.assertIsNone(result['whole_house_total'])
        self.assertFalse(result['estimate_released']);self.assertFalse(row['certified'])
        self.assertEqual(self.draft,before)

    def test_missing_changed_and_restored_enclosure_review(self):
        original=copy.deepcopy(self.enclosures)
        self.enclosures['candidate_enclosures'][0]['gross_boundary_sf']=110
        self.assertIsNone(self.calculate()['rows'][0]['draft_quantity'])
        self.assertEqual(len(self.calculate()['pending_quantities']),1)
        self.enclosures['candidate_enclosures']=[]
        self.assertIsNone(self.calculate()['rows'][0]['draft_quantity'])
        self.enclosures=original
        self.enclosures['measurement_version']=2;self.draft['measurement_version']=2
        self.assertEqual(self.calculate()['rows'][0]['draft_quantity'],100)

    def test_duplicate_floor_ownership_and_overlapping_outer_rings_are_rejected(self):
        mapping=self.review['mappings'][0]
        mapping['enclosures'].append(copy.deepcopy(mapping['enclosures'][0]))
        with self.assertRaisesRegex(ValueError,'multiple floor'):self.calculate()
        mapping['enclosures'].pop()
        other=copy.deepcopy(self.enclosures['candidate_enclosures'][0]);other['id']='other'
        self.enclosures['candidate_enclosures'].append(other)
        mapping['enclosures'].append({'id':'other','sha256':binding(other)})
        with self.assertRaisesRegex(ValueError,'overlap'):self.calculate()

    def test_partial_multi_boundary_mapping_withholds_entire_input(self):
        self.review['mappings'][0]['enclosures'].append({'id':'missing','sha256':'0'*64})
        result=self.calculate()
        self.assertIsNone(result['rows'][0]['draft_quantity'])
        self.assertEqual(result['enclosure_quantity_review']['mappings'][0]['missing_or_changed_enclosure_ids'],['missing'])

    def test_cost_rows_flooring_totals_and_preassigned_inputs_cannot_be_claimed(self):
        for key,value in [('parent','Flooring'),('name','SF TOTAL FRAMED'),('name','Covered Porches'),
                ('unit','LF'),('pricing_role','cost_line'),('draft_quantity',0),('line_cost',0),
                ('assembly_inputs',[{}]),('quantity_sources',[{}]),('cost_owner_row_id','other'),
                ('completion_status','not_applicable')]:
            draft=copy.deepcopy(self.draft);draft['rows'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                apply_quantities(draft,self.enclosures,self.review)

    def test_unassigned_enclosures_are_visible_and_source_mismatch_rejected(self):
        other=copy.deepcopy(self.enclosures['candidate_enclosures'][0]);other['id']='second'
        self.enclosures['candidate_enclosures'].append(other)
        self.assertEqual(self.calculate()['enclosure_quantity_review']['unassigned_enclosure_ids'],['second'])
        self.enclosures['measurement_version']=3
        with self.assertRaises(ValueError):self.calculate()
        self.enclosures['measurement_version']=1;self.review['plan_sha256']='other'
        with self.assertRaises(ValueError):self.calculate()

    def test_review_metadata_is_required_and_cannot_be_applied_twice(self):
        result=self.calculate()
        with self.assertRaises(ValueError):apply_quantities(result,self.enclosures,self.review)
        for key in ('reviewer','basis'):
            review=copy.deepcopy(self.review);review[key]=' '
            with self.subTest(key=key),self.assertRaises(ValueError):apply_quantities(self.draft,self.enclosures,review)


if __name__=='__main__':unittest.main()
