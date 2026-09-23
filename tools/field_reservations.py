"""Resolve reviewed stud exclusions from wall ends, openings and intersections."""
import math


def junction_points(runs, definitions, *, points_per_foot):
    """Rebuild reviewed intersections while retaining source drawing offsets."""
    if type(points_per_foot) not in (int,float) or not math.isfinite(points_per_foot) or points_per_foot <= 0:
        raise ValueError('Positive finite drawing scale required')
    by_id = {r['id']:r for r in runs}; inch = points_per_foot/12; points = {}
    if len(by_id) != len(runs):raise ValueError('Unique junction wall runs required')
    for definition in definitions:
        identity = definition['id']
        if not isinstance(identity,str) or not identity or identity in points:
            raise ValueError('Unique junction identity required')
        x_run,y_run = by_id[definition['x_run']],by_id[definition['y_run']]
        if x_run['orientation'] != 'vertical' or y_run['orientation'] != 'horizontal':
            raise ValueError('Junction needs reviewed perpendicular reference walls')
        offsets = [definition['x_offset_inches'],definition['y_offset_inches']]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in offsets):
            raise ValueError('Finite reviewed junction offsets required')
        point = [x_run['coordinate_pt']+offsets[0]*inch,y_run['coordinate_pt']+offsets[1]*inch]
        if not definition['attachments']:raise ValueError('Junction needs reviewed wall attachments')
        seen = set()
        for attachment in definition['attachments']:
            run = by_id[attachment['run']]
            if run['id'] in seen:raise ValueError('Duplicate junction wall attachment')
            seen.add(run['id']);axis = 0 if run['orientation']=='horizontal' else 1
            normal = attachment['normal_offset_inches']
            if type(normal) not in (int,float) or not math.isfinite(normal):
                raise ValueError('Finite junction alignment offset required')
            if abs(point[1-axis]-run['coordinate_pt']-normal*inch)>1e-6:
                raise ValueError('Wall no longer aligns with junction: '+identity+'/'+run['id'])
            endpoint = attachment['endpoint']
            if endpoint == 'through':
                if not run['start_pt'] <= point[axis] <= run['end_pt']:
                    raise ValueError('Junction moved beyond its through wall: '+identity)
            elif endpoint in ('start_pt','end_pt'):
                gap = attachment['signed_gap_inches']
                if type(gap) not in (int,float) or not math.isfinite(gap):
                    raise ValueError('Finite reviewed junction end gap required')
                if abs(point[axis]-run[endpoint]-gap*inch)>1e-6:
                    raise ValueError('Wall end no longer meets junction: '+identity+'/'+run['id'])
            else:raise ValueError('Unknown junction wall attachment')
        points[identity] = point
    return points


def resolve(runs, bindings, openings, branches, *, points_per_foot, junctions=None):
    if type(points_per_foot) not in (int,float) or not math.isfinite(points_per_foot) or points_per_foot <= 0:
        raise ValueError('Positive finite drawing scale required')
    by_id = {r['id']:r for r in runs}
    if len(by_id) != len(runs):raise ValueError('Unique wall runs required')
    inch = points_per_foot/12; zones = []; seen = set()
    for binding in bindings:
        identity = binding['id']
        if not isinstance(identity,str) or not identity or identity in seen:
            raise ValueError('Unique reservation identity required')
        seen.add(identity)
        wall = by_id[binding['run']]
        axis = 0 if wall['orientation'] == 'horizontal' else 1
        allowance = binding['allowance_inches']
        if type(allowance) not in (int,float) or not math.isfinite(allowance) or allowance < 0:
            raise ValueError('Finite nonnegative reservation allowance required')
        kind = binding['kind']
        if kind == 'run_end':
            if binding['endpoint'] not in ('start_pt','end_pt'):
                raise ValueError('Reservation needs a reviewed wall end')
            start = end = wall[binding['endpoint']]
        elif kind == 'junction':
            point = junctions[binding['junction']]
            start = end = point[axis]
        elif kind == 'opening':
            points = openings[binding['opening']]
            if (len(points) != 2 or any(len(p) != 2 for p in points)
                    or any(type(v) not in (int,float) or not math.isfinite(v) for p in points for v in p)):
                raise ValueError('Opening needs two finite drawing points')
            offset = binding['normal_offset_inches']
            if type(offset) not in (int,float) or not math.isfinite(offset):
                raise ValueError('Reviewed opening offset required')
            normal = wall['coordinate_pt'] + offset*inch
            if any(abs(p[1-axis]-normal) > 1e-6 for p in points):
                raise ValueError('Opening no longer follows its wall: '+binding['opening'])
            start,end = sorted(p[axis] for p in points)
            if not wall['start_pt'] <= start < end <= wall['end_pt']:
                raise ValueError('Opening no longer lies within its wall: '+binding['opening'])
        elif kind == 'intersection':
            branch = branches[binding['branch']]
            if branch['orientation'] == wall['orientation']:
                raise ValueError('Reviewed intersection needs perpendicular wall runs')
            endpoint = binding['branch_endpoint']
            if endpoint not in ('start_pt','end_pt'):
                raise ValueError('Reviewed branch endpoint required')
            gap = binding['signed_gap_inches']
            if type(gap) not in (int,float) or not math.isfinite(gap):
                raise ValueError('Reviewed branch gap required')
            if abs(branch[endpoint]-wall['coordinate_pt']-gap*inch) > 1e-6:
                raise ValueError('Branch no longer meets its wall: '+binding['branch'])
            start = end = branch['coordinate_pt']
            if not wall['start_pt'] <= start <= wall['end_pt']:
                raise ValueError('Intersection moved beyond the wall')
        else:raise ValueError('Unknown reservation anchor')
        zones.append({'assembly':binding['assembly'],'run':binding['run'],
            'interval':[start-allowance*inch,end+allowance*inch],'source':binding['source']})
    return zones
