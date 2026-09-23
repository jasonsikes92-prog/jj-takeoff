import unittest
from shapely.geometry import Polygon
from shapely.ops import unary_union
from roof_edge_network import network_faces


class InteriorRoofFaceTests(unittest.TestCase):
    def edges(self):
        edges=[]
        for points in ([(0,0),(100,0),(100,100),(0,100)],
                       [(30,30),(70,30),(70,70),(30,70)]):
            for a,b in zip(points,points[1:]+points[:1]):edges.append((a,b,len(edges)))
        edges.append(((50,30),(50,70),8))
        return edges

    def test_inner_ridge_faces_preserved_without_inheriting_parent_pitch(self):
        label={'point_pt':[10,10],'rise':7,'text':'7 : 12'}
        simple,complex_faces,diagnostic=network_faces(self.edges(),[label])
        self.assertEqual(simple,[]);self.assertEqual(len(complex_faces),1)
        groups=diagnostic['unpitched_interior_faces'];self.assertEqual(len(groups),1)
        group=groups[0];self.assertEqual(len(group['faces']),2)
        self.assertEqual(group['uncovered_area_pt2'],0)
        self.assertFalse(group['scope_certified'])
        polygons=[Polygon(face['points']) for face in group['faces']]
        self.assertTrue(unary_union(polygons).equals(Polygon(group['interior_ring_points'])))
        self.assertEqual(polygons[0].intersection(polygons[1]).area,0)
        self.assertEqual(Polygon(complex_faces[0]['points'],complex_faces[0]['holes']).area,8400)
        for face in group['faces']:
            self.assertIsNone(face['pitch_candidate']);self.assertIsNone(face['physical_quantity'])
            self.assertIn(8,face['source_cad_paths'])
            self.assertFalse(set(face['source_cad_paths']) & {0,1,2,3})

    def test_labeled_inner_face_keeps_own_pitch_and_is_not_duplicated(self):
        labels=[{'point_pt':[10,10],'rise':7},{'point_pt':[40,50],'rise':10}]
        simple,complex_faces,diagnostic=network_faces(self.edges(),labels)
        self.assertEqual(len(simple),1);self.assertEqual(simple[0]['pitch_candidate']['rise'],10)
        group=diagnostic['unpitched_interior_faces'][0]
        self.assertEqual(len(group['faces']),1)
        self.assertEqual(group['uncovered_area_pt2'],800)
        self.assertEqual(group['parent_pitch_label_for_location_only']['rise'],7)

    def test_unrelated_unlabeled_region_is_not_a_dormer(self):
        edges=self.edges();points=[(150,0),(160,0),(160,10),(150,10)]
        for a,b in zip(points,points[1:]+points[:1]):edges.append((a,b,len(edges)))
        _,_,diagnostic=network_faces(edges,[{'point_pt':[10,10],'rise':7}])
        groups=diagnostic['unpitched_interior_faces']
        self.assertEqual(len(groups),1);self.assertEqual(len(groups[0]['faces']),2)

    def test_open_inner_ring_does_not_create_a_cutout(self):
        edges=[edge for edge in self.edges() if edge[2]!=4]
        _,complex_faces,diagnostic=network_faces(edges,[{'point_pt':[10,10],'rise':7}])
        self.assertEqual(complex_faces,[])
        self.assertEqual(diagnostic['unpitched_interior_faces'],[])


if __name__=='__main__':unittest.main()
