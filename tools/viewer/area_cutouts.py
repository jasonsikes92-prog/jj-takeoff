"""Validate explicitly related interior area deductions before subtracting them."""
import itertools
from shapely.geometry import Polygon
from measurement_store import calculate


def projection_containment_issues(measurements, relationships):
    """Check plan containment, permitting shared edges and different surface slopes."""
    if not isinstance(relationships,list) or not relationships:
        raise ValueError('Projection containment needs explicit parent/child pairs')
    seen=set();issues=[]
    for relationship in relationships:
        if not isinstance(relationship,dict) or set(relationship)!={'parent','child'}:
            raise ValueError('Projection containment requires parent and child identities')
        parent,child=relationship['parent'],relationship['child']
        if (not isinstance(parent,str) or not isinstance(child,str) or parent==child
                or (parent,child) in seen or parent not in measurements or child not in measurements):
            raise ValueError('Projection containment identities must be distinct, declared and unique')
        seen.add((parent,child));outer,inner=measurements[parent],measurements[child]
        if outer['kind']!='area' or inner['kind']!='area':
            raise ValueError('Projection containment requires area boundaries')
        calculate(outer);calculate(inner)
        if any(outer.get(k)!=inner.get(k) for k in ('page','points_per_foot','width_pt','height_pt')):
            reason='Contained projections must share a drawing frame and scale'
        elif not Polygon(outer['points']).covers(Polygon(inner['points'])):
            reason='Child projection extends outside its parent outline'
        else:continue
        issues.append({'measurement_ids':[parent,child],'reason':reason})
    return issues


def cutout_issues(measurements,terms):
    groups={};issues=[]
    for term in terms:
        if 'cutout_of' not in term:continue
        identity=term['measurement_id'];parent=term['cutout_of']
        if (term['kind']!='area' or term['operation']!='deduct' or identity==parent
                or sum(t['measurement_id']==identity for t in terms)!=1
                or sum(t['measurement_id']==parent and t['kind']=='area' and t['operation']=='add' for t in terms)!=1):
            raise ValueError('A cutout needs one deducted area and one distinct added parent area')
        if identity not in measurements or parent not in measurements:
            raise ValueError('Cutout or parent measurement is missing')
        child,outer=measurements[identity],measurements[parent]
        if child['kind']!='area' or outer['kind']!='area':raise ValueError('Cutouts require area geometry')
        calculate(child);calculate(outer)
        fields=('page','points_per_foot','width_pt','height_pt')
        if (any(child.get(k)!=outer.get(k) for k in fields)
                or child.get('surface_factor',1)!=outer.get('surface_factor',1)):
            issues.append({'measurement_ids':[parent,identity],
                'reason':'Cutout and parent must share a drawing frame, scale and roof slope'})
            continue
        shape=Polygon(child['points']);boundary=Polygon(outer['points'])
        if not boundary.contains(shape) or not boundary.boundary.disjoint(shape):
            issues.append({'measurement_ids':[parent,identity],
                'reason':'Interior cutout must lie strictly inside its parent outline'})
        groups.setdefault(parent,[]).append((identity,shape))
    for children in groups.values():
        for (first,a),(second,b) in itertools.combinations(children,2):
            if not a.disjoint(b):issues.append({'measurement_ids':[first,second],
                'reason':'Interior cutouts overlap or touch; reconcile them before subtracting'})
    return issues
