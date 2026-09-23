"""Relate reviewed opening faces to current room and exterior boundaries."""
from shapely.geometry import LineString,Polygon


def connections(enclosures,regions):
    shapes={r['id']:Polygon(r['points'],r['holes']) for r in regions}
    outer=[(e,Polygon(e['points'])) for e in enclosures.get('candidate_enclosures',[])]
    result=[]
    def covers(shape,line):
        return line.difference(shape.boundary.buffer(1e-6)).length<=1e-6
    for closure in enclosures.get('gap_closures',[]):
        if closure.get('opening_id') is None:continue
        x1,y1,x2,y2=closure['bounds_pt']
        if closure['axis']=='horizontal':faces=[[[x1,y1],[x2,y1]],[[x1,y2],[x2,y2]]]
        elif closure['axis']=='vertical':faces=[[[x1,y1],[x1,y2]],[[x2,y1],[x2,y2]]]
        else:raise ValueError('Opening closure needs its measured axis')
        sides=[]
        for face in faces:
            line=LineString(face)
            matched=[r for r in regions if (r['page'],r['points_per_foot'])==
                (closure['page'],closure['points_per_foot']) and covers(shapes[r['id']],line)]
            exterior=[e['id'] for e,p in outer if (e['page'],e['points_per_foot'])==
                (closure['page'],closure['points_per_foot']) and covers(p,line)]
            unique=len(matched)==1 and not exterior
            sides.append({'face_points_pt':face,'candidate_region_ids':[r['id'] for r in matched],
                'region_id':matched[0]['id'] if unique else None,
                'printed_labels':matched[0]['printed_labels'] if unique else [],
                'exterior_enclosure_ids':exterior,
                'status':'region_boundary' if unique else 'exterior_boundary' if len(exterior)==1 and not matched else 'unresolved'})
        ids=[s['region_id'] for s in sides if s['region_id'] is not None]
        status=('two_region_boundaries' if len(set(ids))==2 else
            'same_region_both_sides' if len(ids)==2 else
            'region_and_exterior_boundary' if len(ids)==1 and any(s['status']=='exterior_boundary' for s in sides)
            else 'unresolved')
        result.append({'opening_id':closure['opening_id'],'gap_id':closure['gap_id'],'page':closure['page'],
            'points_per_foot':closure['points_per_foot'],'sides':sides,'status':status,
            'room_use_confirmed':False,'finish_selection':None,
            'basis':'Entire measured opening face lies on a current region or exterior boundary; no room use or access function inferred'})
    return result
