import copy
import unittest
from below_window_stock_review import calculate


class BelowWindowTests(unittest.TestCase):
    def setUp(self):
        self.field={'points_per_foot':12,'zones':[{'run':'wall','assembly':'window'}],
            'field_studs':[],'reserved_stations':[{'id':str(n),'run':'wall','along_pt':x,
                'point_pt':[x,0],'assembly_owners':['window']} for n,x in enumerate([8,24,40])]}
        self.state={'measurements':{'window':{'kind':'length','points_per_foot':12,'points':[[0,0],[48,0]]}}}
        self.assemblies=[{'opening_id':'window','assembly_quantity':1,'component_count':3,'rough_opening_height_in':72}]
        self.offsets={'wall':0};self.stock={'sku':'PRECUT','length_inches':104.625}

    def calc(self):return calculate(self.field,self.state,self.assemblies,self.offsets,self.stock,96,1.5,1.5)

    def test_existing_field_grid_controls_piece_count_not_number_of_window_units(self):
        result=self.calc();self.assertEqual(result['member_count'],3)
        self.assertEqual([p['raw_cut_inches'] for p in result['pieces']],[21]*3)
        self.assertEqual(result['candidate_whole_sticks'],1)
        self.assertEqual(result['pending'],[])
        self.assertEqual(result['windows'][0]['station_ids'],['0','1','2'])

    def test_garage_offset_and_supplier_height_change_lengths_with_upward_cut_reservation(self):
        self.offsets['wall']=10.71875
        result=self.calc();self.assertEqual(result['pieces'][0]['raw_cut_inches'],31.71875)
        self.assertEqual(result['pieces'][0]['cut_inches'],31.75)
        self.assemblies[0]['rough_opening_height_in']=52.25
        result=self.calc();self.assertEqual(result['pieces'][0]['raw_cut_inches'],51.46875)
        self.assertEqual(result['pieces'][0]['cut_inches'],51.5)

    def test_partial_width_and_other_assembly_ownership_do_not_create_duplicate_studs(self):
        self.field['reserved_stations'][0].update(along_pt=.5,point_pt=[.5,0])
        self.field['reserved_stations'][1]['assembly_owners']=['corner','window']
        station=self.field['reserved_stations'].pop();station['assembly_owners']=[]
        self.field['field_studs'].append(station)
        result=self.calc();self.assertEqual(result['member_count'],0)
        self.assertEqual(len(result['pending']),2)
        self.assertEqual(result['boards'],[])

    def test_unlocated_gable_and_nonpositive_cut_remain_unquantified(self):
        self.assemblies.append({**self.assemblies[0],'opening_id':'gable'})
        result=self.calc();self.assertEqual(result['member_count'],3)
        self.assertEqual(result['pending'][0]['id'],'gable')
        self.assemblies[0]['rough_opening_height_in']=96
        result=self.calc();self.assertEqual(result['member_count'],0)
        self.assertEqual(len(result['pending']),2)

    def test_missing_offset_duplicate_station_and_bad_dimensions_rejected(self):
        original=copy.deepcopy(self.field)
        self.field['reserved_stations'].append(copy.deepcopy(self.field['reserved_stations'][0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.calc()
        self.field=original;self.offsets={}
        with self.assertRaisesRegex(ValueError,'offset'):self.calc()
        self.offsets={'wall':0};self.assemblies[0]['rough_opening_height_in']=float('nan')
        with self.assertRaisesRegex(ValueError,'height'):self.calc()


if __name__=='__main__':unittest.main()
