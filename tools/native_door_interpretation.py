"""Derive estimating roles from current symbols and named regions, not old answers."""
import copy
import hashlib
import json
from room_use_review import binding


def interpret(schedule,rooms):
    if (schedule['plan_sha256'],schedule['measurement_version'])!=(rooms['plan_sha256'],rooms['measurement_version']):
        raise ValueError('Native door interpretation needs current plan and room geometry')
    result=copy.deepcopy(schedule)
    symbols={c['opening_id']:c for c in result.get('door_symbol_candidates',{}).get('candidates',[])}
    links={c['opening_id']:c for c in rooms['opening_connections']}
    regions={r['id']:r for r in rooms['regions']}
    if len(links)!=len(rooms['opening_connections']) or len(regions)!=len(rooms['regions']):
        raise ValueError('Native door interpretation requires unique room and connection identities')
    supported={'bedroom','bathroom','toilet_room','closet','office','laundry','pantry','utility','storage',
        'hall','hallway','circulation','foyer','open_living_kitchen_dining','living','kitchen','dining'}
    inferred=[o['opening_id'] for o in result['openings'] if o['review_status']=='native_symbol_inference']
    for opening in result['openings']:
        if opening['review_status']!='role_unreviewed':continue
        symbol=symbols.get(opening['opening_id'],{});link=links.get(opening['opening_id'],{})
        kind=symbol.get('configuration_candidate')
        if (symbol.get('status')!='candidate_requires_review' or kind not in ('single_hinged','pocket','double_hinged','sliding_pair')
                or (kind in ('double_hinged','sliding_pair') and symbol.get('drawn_panel_count_candidate')!=2)
                or symbol.get('opening_source_sha256')!=opening['source_sha256']
                or link.get('status') not in ('two_region_boundaries','region_and_exterior_boundary') or link.get('page')!=opening['page']
                or link.get('points_per_foot')!=opening['points_per_foot']):continue
        exterior=link['status']=='region_and_exterior_boundary'
        if exterior:
            outer=[side for side in link['sides'] if side.get('status')=='exterior_boundary'
                   and len(side.get('exterior_enclosure_ids',[]))==1
                   and side.get('region_id') is None and not side.get('candidate_region_ids')]
            if len(link['sides'])!=2 or len(outer)!=1 or kind=='pocket':continue
        adjacent=[]
        for side in link['sides']:
            region=regions.get(side.get('region_id'),{})
            use=region.get('room_use_review',{}) if region.get('room_use_confirmed') else region.get('room_use_inference',{})
            if (side.get('status')=='region_boundary' and region.get('page')==opening['page']
                    and region.get('points_per_foot')==opening['points_per_foot']
                    and use.get('status') in ('current_source_review','native_label_inference','equipment_symbol_inference','shelf_symbol_inference')
                    and use.get('room_use') in supported
                    and use.get('source_sha256')==binding(rooms['plan_sha256'],region)):
                adjacent.append({'region_id':region['id'],'room_use':use['room_use'],'source_sha256':use['source_sha256']})
        expected=1 if exterior else 2
        if len(adjacent)!=expected or len({r['region_id'] for r in adjacent})!=expected:continue
        evidence={'plan_sha256':schedule['plan_sha256'],'opening_source_sha256':opening['source_sha256'],
            'symbol_source_sha256':symbol['source_sha256'],'room_sources_sha256':rooms['source_sha256'],
            'connection':link,'adjacent_rooms':adjacent,'configuration':kind}
        evidence['source_sha256']=hashlib.sha256(json.dumps(evidence,sort_keys=True,allow_nan=False).encode()).hexdigest()
        opening.update(role='exterior_door' if exterior else 'interior_door' if kind=='single_hinged' else 'special_interior_door',
            door_configuration='sliding' if kind=='sliding_pair' else kind,
            drawn_panel_count=2 if kind in ('double_hinged','sliding_pair') else 1,room_class=None,
            location=' / '.join(r['room_use'].replace('_',' ') for r in adjacent)+(' / exterior' if exterior else ''),
            role_source=('Automatic estimating interpretation: native door geometry connects a source-bound interior room to the current exterior enclosure boundary. Exterior assembly, product fit and full coverage are not confirmed.' if exterior else
                'Automatic estimating interpretation: native door geometry connects two source-bound interior room interpretations. Room served, product fit and full coverage are not confirmed.'),
            review_status='native_symbol_inference',interpretation_requires_review=True,native_interpretation=evidence)
        inferred.append(opening['opening_id'])
    result['unresolved_opening_ids']=([o['opening_id'] for o in result['openings'] if o['role'] is None]
        +[o['opening_id'] for o in result.get('unlocated_opening_tags',[])])
    result['inferred_opening_ids']=inferred
    result['reviewed_role_counts']={role:sum(o['role']==role and o['review_status']=='current_source_review' for o in result['openings'])
        for role in result['reviewed_role_counts']}
    result['inferred_role_counts']={role:sum(o['role']==role and o['review_status']=='native_symbol_inference' for o in result['openings'])
        for role in result['reviewed_role_counts']}
    windows=[o for o in result['openings'] if o['role']=='window']
    result['enumerated_window_unit_count']=(sum(o['window_component_count'] for o in windows)
        if windows and not result['unresolved_opening_ids'] and not result['stale_or_missing_label_ids']
        and all(o.get('window_component_count') is not None for o in windows) else None)
    return result
