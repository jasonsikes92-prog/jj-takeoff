import copy
import unittest
from stud_stock import calculate


class StudStock(unittest.TestCase):
    def setUp(self):
        self.field={'runs':[{'run':'house'},{'run':'garage'}],
            'field_studs':[{'id':'A','run':'house','assembly_owners':[]},{'id':'B','run':'garage','assembly_owners':[]}],
            'zones':[{'run':'house','assembly':'corner-alias'},{'run':'garage','assembly':'corner'}]}
        self.assemblies={'components':[{'id':'corner','quantities':{'junction_studs':4}}],
            'component_totals':{'jack_studs':2}}
        self.aliases={'corner':['corner-alias']};self.offsets={'house':0,'garage':10.71875}
        self.stocks=[{'sku':'precut','length_inches':104.625,'precut':True},
                     {'sku':'long','length_inches':144,'precut':False}]
    def result(self,height=108):return calculate(self.field,self.assemblies,self.aliases,self.offsets,height,4.5,self.stocks)
    def test_house_garage_and_mixed_corner_are_separate(self):
        r=self.result();self.assertEqual(r['stock_quantities'],{'long':5,'precut':1})
        self.assertEqual(r['full_height_members'],6);self.assertEqual(r['mixed_height_allowance_members'],4)
        self.assertEqual(r['members'][0]['cut_inches'],103.5)
        self.assertEqual(r['members'][1]['cut_inches'],114.21875)
        self.assertEqual(r['jack_studs_not_included'],2);self.assertIsNone(r['complete_stud_order_quantity'])
    def test_precut_height_changes_cuts_but_not_fitting_stock(self):
        a=self.result();b=self.result(109.125)
        self.assertEqual(a['stock_quantities'],b['stock_quantities'])
        self.assertEqual(b['members'][0]['cut_inches'],104.625)
        self.assertEqual(b['members'][1]['cut_inches'],115.34375)
    def test_reserved_and_duplicate_stations_cannot_inflate_quantity(self):
        self.field['field_studs'][0]['assembly_owners']=['corner']
        with self.assertRaisesRegex(ValueError,'Reserved'):self.result()
        self.field['field_studs'][0]['assembly_owners']=[]
        self.field['field_studs'].append(copy.deepcopy(self.field['field_studs'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.result()
    def test_changed_unknown_wall_or_insufficient_stock_not_silently_assigned(self):
        self.offsets.pop('house')
        with self.assertRaisesRegex(ValueError,'Every current wall'):self.result()
        self.offsets['house']=200
        r=self.result();self.assertEqual(len(r['pending_members']),5)
        self.assertEqual(r['stock_quantities'],{'long':1})
    def test_missing_junction_location_stays_unresolved(self):
        self.field['zones']=[];r=self.result()
        self.assertEqual(len(r['pending_members']),4);self.assertEqual(r['full_height_members'],2)
    def test_live_count_and_zero_follow_input_without_consuming_reserved_positions(self):
        first=self.result();self.field['field_studs']=[]
        self.assertEqual(self.result()['stock_quantities'],{'long':4})
        self.assemblies['components']=[];self.assertEqual(self.result()['stock_quantities'],{})
        self.assertEqual(first['full_height_members'],6)
    def test_all_cuts_fit_and_length_is_conserved(self):
        r=self.result()
        for board in r['boards']:
            self.assertAlmostEqual(board['length_ft']*12,sum(c['consumed_inches'] for c in board['cuts'])+board['remaining_inches'])
            self.assertGreaterEqual(board['remaining_inches'],0)
        self.assertEqual({m['id'] for m in r['members']},{c['piece_id'] for b in r['boards'] for c in b['cuts']})

    def test_jack_allowance_reserves_whole_blanks_without_inventing_cuts(self):
        self.assemblies['components'].append({'id':'door','quantities':{'jack_studs':2}})
        self.field['zones'].append({'run':'house','assembly':'door'})
        r=calculate(self.field,self.assemblies,self.aliases,self.offsets,108,4.5,self.stocks,True)
        self.assertEqual(r['stock_quantities'],{'long':5,'precut':3})
        self.assertEqual((r['full_height_members'],r['jack_stock_blanks'],r['jack_studs_not_included']),(6,2,0))
        jacks=[m for m in r['members'] if m['kind']=='jack_studs']
        self.assertTrue(all(m['cut_inches'] is None for m in jacks))
        for board in r['boards'][-2:]:
            self.assertEqual(len(board['cuts']),1)
            self.assertIsNone(board['cuts'][0]['cut_inches'])
            self.assertTrue(board['cuts'][0]['allocation_only'])
            self.assertEqual(board['cuts'][0]['consumed_inches'],104.625)
            self.assertEqual(board['remaining_inches'],0)

    def test_jack_missing_location_and_inconsistent_total_cannot_be_priced(self):
        self.assemblies['components'].append({'id':'door','quantities':{'jack_studs':2}})
        r=calculate(self.field,self.assemblies,self.aliases,self.offsets,108,4.5,self.stocks,True)
        self.assertEqual(r['jack_stock_blanks'],0)
        self.assertEqual(r['jack_studs_not_included'],2)
        self.assertEqual(len(r['pending_members']),2)
        self.assemblies['component_totals']['jack_studs']=3
        with self.assertRaisesRegex(ValueError,'Jack assembly details'):
            calculate(self.field,self.assemblies,self.aliases,self.offsets,108,4.5,self.stocks,True)

    def test_jacks_on_taller_walls_use_long_stock_and_zero_needs_no_purchase(self):
        self.assemblies['components'].append({'id':'door','quantities':{'jack_studs':2}})
        self.field['zones'].append({'run':'garage','assembly':'door'})
        r=calculate(self.field,self.assemblies,self.aliases,self.offsets,108,4.5,self.stocks,True)
        self.assertEqual(r['stock_quantities'],{'long':7,'precut':1})
        self.assemblies['components'][-1]['quantities']['jack_studs']=0
        self.assemblies['component_totals']['jack_studs']=0
        r=calculate(self.field,self.assemblies,self.aliases,self.offsets,108,4.5,self.stocks,True)
        self.assertEqual(r['jack_stock_blanks'],0)
        self.assertEqual(r['stock_quantities'],{'long':5,'precut':1})


if __name__=='__main__':unittest.main()
