"""Locate interacting framing reservation zones without inventing stud deductions.

Intervals describe excluded field-stud center zones along one wall run, not
physical member footprints. Intersections require a combined assembly layout.
"""
import math
from collections import defaultdict


def jamb_clearance(opening_interval, junction_position, points_per_foot,
                   stud_face_inches, return_wall_depth_inches, kings, jacks):
    """Screen a drawn jamb against the face of a perpendicular framing wall.

    This envelope excludes drywall and does not locate corner/backing members.
    Passing it does not prove a shared member, bearing detail or rough opening.
    """
    if (not isinstance(opening_interval,(list,tuple)) or len(opening_interval)!=2 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in opening_interval) or
            opening_interval[0]>=opening_interval[1]):raise ValueError('Ordered finite opening interval required')
    if type(junction_position) not in (int,float) or not math.isfinite(junction_position):
        raise ValueError('Finite junction position required')
    if opening_interval[0]<junction_position<opening_interval[1]:
        raise ValueError('Junction is inside the drawn opening; reconcile topology first')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0
           for v in (points_per_foot,stud_face_inches,return_wall_depth_inches)):
        raise ValueError('Positive finite scale and member dimensions required')
    if any(type(v) is not int or v<0 for v in (kings,jacks)) or kings+jacks==0:
        raise ValueError('Explicit nonnegative king/jack counts required')
    side='start' if junction_position<=opening_interval[0] else 'end'
    boundary=opening_interval[0 if side=='start' else 1]
    to_center=abs(boundary-junction_position)/points_per_foot*12
    available=to_center-return_wall_depth_inches/2
    jamb=(kings+jacks)*stud_face_inches
    return {'opening_side':side,'opening_boundary_pt':boundary,
            'junction_center_distance_inches':to_center,'framing_face_clearance_inches':available,
            'jamb_pair_width_inches':jamb,'remaining_after_jamb_inches':available-jamb,
            'remaining_after_jamb_and_separate_end_inches':available-jamb-stud_face_inches,
            'screen':('jamb_exceeds_reference_space' if available<jamb else
                      'jamb_fits_but_separate_end_does_not' if available<jamb+stud_face_inches else
                      'jamb_and_separate_end_fit_reference_space'),
            'quantity_deductions':[],'purchase_order_released':False}


def find_interactions(zones):
    by_run = defaultdict(list)
    owners = set()
    for zone in zones:
        if not all(isinstance(zone.get(k), str) and zone[k].strip()
                   for k in ('assembly', 'run', 'source')):
            raise ValueError('Each zone needs an assembly, run and source')
        interval = zone.get('interval')
        if (not isinstance(interval, (list, tuple)) or len(interval) != 2 or
                any(type(x) not in (int, float) or not math.isfinite(x) for x in interval) or
                interval[0] > interval[1]):
            raise ValueError('Reservation interval must be finite and ordered')
        by_run[zone['run']].append(zone)
        owners.add(zone['assembly'])
    edges = []
    neighbors = {owner: set() for owner in owners}
    for run, items in sorted(by_run.items()):
        items = sorted(items, key=lambda z: (z['interval'][0], z['assembly']))
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                if right['interval'][0] > left['interval'][1]:
                    break
                if left['assembly'] == right['assembly']:
                    continue  # Multiple zones can belong to one physical assembly.
                a, b = sorted((left['assembly'], right['assembly']))
                neighbors[a].add(b)
                neighbors[b].add(a)
                edges.append({'assemblies': [a, b], 'run': run,
                              'interval': [max(left['interval'][0], right['interval'][0]),
                                           min(left['interval'][1], right['interval'][1])],
                              'sources': sorted({left['source'], right['source']})})
    groups = []
    remaining = set(owners)
    while remaining:
        start = min(remaining)
        group, pending = set(), [start]
        while pending:
            owner = pending.pop()
            if owner in group:
                continue
            group.add(owner)
            pending.extend(neighbors[owner] - group)
        remaining -= group
        groups.append({'assemblies': sorted(group), 'requires_combined_layout': len(group) > 1})
    # Repeated source zones must not multiply identical interaction evidence.
    unique = {(tuple(e['assemblies']), e['run'], tuple(e['interval']), tuple(e['sources'])): e
              for e in edges}
    return {'interactions': sorted(unique.values(), key=lambda e: (e['run'], e['assemblies'], e['interval'])),
            'groups': groups, 'assembly_count': len(owners),
            'quantity_deductions': [], 'purchase_order_released': False,
            'basis': 'Reservation-zone interaction only; do not deduct or merge physical studs without their layout.'}
