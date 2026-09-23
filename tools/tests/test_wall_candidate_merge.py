import unittest
from wall_candidate_merge import merge


def measurement(identity,bounds,page=1):
    return {'id':identity,'source_bounds_pt':bounds,'kind':'length','page':page}


class MergeTests(unittest.TestCase):
    def test_exact_duplicate_retains_both_sources_once(self):
        f=measurement('fill',[0,0,100,5]);s=measurement('stroke',[0,0,100,5])
        r=merge({'measurements':[f]},{'measurements':[s]},[0,0,200,200])
        self.assertEqual(len(r['measurements']),1)
        self.assertEqual(r['measurements'][0]['alternative_source_measurements'],[s])
        self.assertNotIn('alternative_source_measurements',f)

    def test_partial_overlap_withheld_but_disjoint_wall_retained(self):
        f=measurement('fill',[0,0,100,5]);s=measurement('partial',[50,0,150,5])
        other=measurement('other',[0,20,100,25])
        r=merge({'measurements':[f]},{'measurements':[s,other]},[0,0,200,200])
        self.assertEqual([m['id'] for m in r['measurements']],['fill','other'])
        self.assertEqual(r['withheld_overlap_candidates'][0]['candidate'],s)
        self.assertFalse(r['coverage_certified'])

    def test_outside_view_fill_excluded_and_touching_edges_not_duplicate(self):
        f=measurement('fill',[0,0,100,5]);outside=measurement('outside',[0,300,100,305])
        s=measurement('touch',[100,0,150,5])
        r=merge({'measurements':[f,outside]},{'measurements':[s]},[0,0,200,200])
        self.assertEqual([m['id'] for m in r['measurements']],['fill','touch'])

    def test_depth_conflict_preserves_geometry_for_classification(self):
        f={**measurement('fill',[0,0,100,5]),'drawn_thickness_inches':5.5}
        r=merge({'measurements':[f]},{'measurements':[],'expected_depth_inches':3.5},[0,0,200,200])
        self.assertEqual(r['measurements'][0]['id'],'fill')
        self.assertTrue(r['measurements'][0]['requires_wall_classification'])
        self.assertEqual(r['filled_depth_mismatches'][0]['id'],'fill')


if __name__=='__main__':unittest.main()
