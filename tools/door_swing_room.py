"""Corroborate a private-room entry with its native single-door swing."""
from shapely.geometry import LineString,Polygon
from shapely.ops import substring

SHARED={'living','kitchen','dining','open_living_kitchen_dining','hall','hallway','circulation','foyer'}
PRIVATE={'bedroom','bathroom','toilet_room'}


def candidate(opening,adjacent,regions,symbol):
    private=[r for r in adjacent if r['room_use'] in PRIVATE]
    shared=[r for r in adjacent if r['room_use'] in SHARED]
    if (len(private)!=1 or len(shared)!=1 or opening.get('role')!='interior_door'
            or opening.get('door_configuration')!='single_hinged'
            or symbol.get('status') not in ('candidate_requires_review','corroborates_review')
            or symbol.get('configuration_candidate')!='single_hinged'
            or symbol.get('opening_source_sha256')!=opening.get('source_sha256')
            or len(symbol.get('matches',[]))!=1):return None
    match=symbol['matches'][0]
    if match.get('configuration')!='single_hinged':return None
    points=match.get('points_pt',[]);center=match.get('center_pt');closed=match.get('closed_arc_endpoint')
    if len(points)<5 or center is None or closed not in (0,1):return None
    tip=points[-1 if closed==0 else 0]
    leaf=LineString([center,tip]);arc=LineString(points)
    if leaf.length<=0 or arc.length<=0:return None
    # Avoid the hinge and closed tip at the wall itself; require continuous
    # interior portions, not just one probe point in a possibly concave room.
    swing=substring(arc,.1,.9,normalized=True);outer_leaf=substring(leaf,.5,1,normalized=True)
    selected=private[0];region=regions[selected['region_id']]
    shape=Polygon(region['points'],region['holes'])
    other=regions[shared[0]['region_id']];other_shape=Polygon(other['points'],other['holes'])
    if not shape.covers(swing) or not shape.covers(outer_leaf):return None
    if other_shape.intersects(swing) or other_shape.intersects(outer_leaf):return None
    return {'room_class':selected['room_class'],'region_id':region['id'],
        'room_source_sha256':selected['review']['source_sha256'],
        'shared_region_id':other['id'],'shared_room_source_sha256':shared[0]['review']['source_sha256'],
        'opening_source_sha256':opening['source_sha256'],'symbol_source_sha256':symbol['source_sha256'],
        'arc_interior_points_pt':[list(p) for p in swing.coords],
        'leaf_outer_half_points_pt':[list(p) for p in outer_leaf.coords],
        'basis':'A unique native single-leaf swing enters the named private room from an adjoining shared living/circulation region; estimating interpretation requiring review.',
        'requires_review':True,'product_fit_verified':False}
