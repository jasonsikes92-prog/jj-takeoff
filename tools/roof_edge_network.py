"""Recover bounded-view faces from exact shared CAD edges without closing gaps."""
from shapely.geometry import LineString,Point,Polygon
from shapely.ops import polygonize_full,unary_union


def network_faces(edges,labels):
    lines=[LineString([a,b]) for a,b,_ in edges if a!=b]
    if not lines:return [],[],{}
    polygons,cuts,dangles,invalid=polygonize_full(unary_union(lines))
    simple=[];complex_faces=[]
    for polygon in polygons.geoms:
        matched=[label for label in labels if polygon.contains(Point(label['point_pt']))]
        if not matched or len({label['rise'] for label in matched})!=1:continue
        boundary=polygon.boundary
        refs=sorted({ref for (a,b,ref),line in zip([e for e in edges if e[0]!=e[1]],lines)
            if boundary.intersection(line).length>.0005})
        face={'points':[list(p) for p in polygon.exterior.coords[:-1]],
            'pitch_candidate':matched[0],'source_cad_paths':refs,
            'source_method':'shared CAD edge network in selected roof view',
            'source_precision_pt':.001}
        if len(matched)>1:face['pitch_candidates']=matched
        if polygon.interiors:
            complex_faces.append({**face,'holes':[[list(p) for p in ring.coords[:-1]] for ring in polygon.interiors],
                'reason':'Interior rings need roof-cutout interpretation; no single-ring area released',
                'physical_quantity':None})
        else:simple.append(face)
    interior_faces=[]
    for parent in complex_faces:
        for ring in parent['holes']:
            region=Polygon(ring);faces=[]
            for polygon in polygons.geoms:
                if polygon.interiors or not region.covers(polygon):continue
                if any(polygon.contains(Point(label['point_pt'])) for label in labels):continue
                refs=sorted({ref for (a,b,ref),line in zip([e for e in edges if e[0]!=e[1]],lines)
                    if polygon.boundary.intersection(line).length>.0005})
                faces.append({'points':[list(p) for p in polygon.exterior.coords[:-1]],
                    'source_cad_paths':refs,'pitch_candidate':None,'physical_quantity':None})
            if faces:
                covered=unary_union([Polygon(face['points']) for face in faces])
                interior_faces.append({'interior_ring_points':ring,'faces':faces,
                    'parent_pitch_label_for_location_only':parent['pitch_candidate'],
                    'uncovered_area_pt2':region.difference(covered).area,
                    'reason':'Unlabeled faces inside an exclusion; establish their own pitch and roof role',
                    'scope_certified':False})
    return simple,complex_faces,{'polygon_count':len(polygons.geoms),
        'unpitched_interior_faces':interior_faces,
        'cut_edges':len(cuts.geoms),'dangling_edges':len(dangles.geoms),'invalid_rings':len(invalid.geoms)}
