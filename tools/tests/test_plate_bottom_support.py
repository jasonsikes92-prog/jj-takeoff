import copy
import unittest
from tools.plate_layout import stock_study
from plate_stock_review import bottom_floor_groups


class BottomSupportTests(unittest.TestCase):
    def setUp(self):
        self.floor={'id':'floor','kind':'area','points_per_foot':12,'points':[[0,0],[200,0],[200,100],[0,100]]}
        self.points={'inside':[[10,20],[90,20]],'edge':[[10,1],[90,1]],'outside':[[10,120],[90,120]]}
        self.runs=[{'id':key,'length_inches':80} for key in self.points]

    def classify(self):
        return bottom_floor_groups(self.runs,self.points,self.floor,3.5,'WOOD','PENDING')

    def test_full_width_not_just_centerline_controls_material(self):
        groups,review=self.classify()
        self.assertEqual(groups,{'inside':'WOOD','edge':'PENDING','outside':'PENDING'})
        self.assertEqual(review['wood_floor_run_count'],1)
        self.assertEqual(review['pending_run_count'],2)
        self.assertAlmostEqual(review['wood_floor_run_lf'],80/12)
        self.assertFalse(review['code_approval'])

    def test_changed_floor_or_wall_reclassifies_without_stale_assignment(self):
        self.assertEqual(self.classify()[0]['inside'],'WOOD')
        original=copy.deepcopy(self.floor)
        self.floor['points']=[[0,0],[200,0],[200,10],[0,10]]
        self.assertEqual(self.classify()[0]['inside'],'PENDING')
        self.floor=original
        self.assertEqual(self.classify()[0]['inside'],'WOOD')
        self.points['inside']=[[150,20],[230,20]]
        self.assertEqual(self.classify()[0]['inside'],'PENDING')

    def test_nonconvex_floor_does_not_use_only_endpoints(self):
        self.floor['points']=[[0,0],[200,0],[200,100],[60,100],[60,10],[40,10],[40,100],[0,100]]
        self.assertEqual(self.classify()[0]['inside'],'PENDING')

    def test_no_construction_tolerance_hides_small_overhang(self):
        self.points['inside']=[[10,1.749],[90,1.749]]
        self.assertEqual(self.classify()[0]['inside'],'PENDING')
        self.points['inside']=[[10,1.75],[90,1.75]]
        self.assertEqual(self.classify()[0]['inside'],'WOOD')

    def test_rejects_changed_length_or_missing_geometry(self):
        self.runs[0]['length_inches']=79
        with self.assertRaisesRegex(ValueError,'length differ'):self.classify()
        self.runs[0]['length_inches']=80;self.points.pop('inside')
        with self.assertRaisesRegex(ValueError,'all runs'):self.classify()

    def test_rejects_invalid_scale_width_polygon_or_materials(self):
        for value in (0,-1,True,float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):
                bottom_floor_groups(self.runs,self.points,self.floor,value,'WOOD','PENDING')
        for change in ({'points_per_foot':0},{'kind':'length'},{'points':[[0,0],[200,100],[0,100],[200,0]]}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                bottom_floor_groups(self.runs,self.points,{**self.floor,**change},3.5,'WOOD','PENDING')
        with self.assertRaises(ValueError):bottom_floor_groups(self.runs,self.points,self.floor,3.5,'SAME','SAME')

    def test_stock_groups_prevent_cross_material_offcut_credit(self):
        before=copy.deepcopy(self.runs);groups,_=self.classify()
        study=stock_study(self.runs,{'top':'TOP','bottom':'PENDING'},bottom_material_groups=groups)
        pieces={p['id']:p for p in study['pieces']}
        for board in study['boards']:
            self.assertEqual({pieces[c['piece_id']]['sku'] for c in board['cuts']},{board['sku']})
            self.assertAlmostEqual(sum(c['consumed_inches'] for c in board['cuts'])+board['remaining_inches'],192)
        self.assertEqual(self.runs,before)
        self.assertIsNone(study['purchase_quantity'])
        self.assertEqual(len(study['pieces']),9)
        self.assertTrue(all(p['sku']=='TOP' for p in study['pieces'] if p['layer']!='bottom'))

    def test_stock_overrides_cannot_merge_top_or_name_unknown_run(self):
        for overrides in ({'inside':'TOP'},{'missing':'WOOD'},{'inside':''}):
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):
                stock_study(self.runs,{'top':'TOP','bottom':'PENDING'},bottom_material_groups=overrides)


if __name__=='__main__':unittest.main()
