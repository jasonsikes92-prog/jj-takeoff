"""Draft gable faces inferred from a level ridge and a parent roof intersection.

Source interpretation supplies the parent pitch and downslope arrow. Geometry
alone does not establish that a diagonal is a valley or that the ridge is level.
"""
import hashlib
import json
import math
import sys
from pathlib import Path
from shapely.geometry import Point,Polygon
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from measurement_store import calculate


def component_candidates(group,parent,frame):
    rise=parent.get('rise');down=parent.get('downslope')
    if type(rise) not in (int,float) or not math.isfinite(rise) or not 0<rise<=24:
        raise ValueError('Explicit positive parent pitch required')
    if (not isinstance(down,(list,tuple)) or len(down)!=2 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in down) or math.hypot(*down)==0):
        raise ValueError('Explicit finite parent downslope vector required')
    if not isinstance(parent.get('source'),str) or not parent['source'].strip():
        raise ValueError('Parent pitch and arrow need a source explanation')
    digest=frame.get('plan_sha256')
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Source drawing hash required')
    faces=group.get('faces',[])
    if len(faces)!=2:raise ValueError('This inference requires exactly two gable faces')
    polygons=[]
    for face in faces:
        points=face['points']
        if (len(points)!=4 or any(len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v)
                for v in p) for p in points)):
            raise ValueError('Inference requires four finite corners per face')
        polygon=Polygon(points)
        if not polygon.is_valid or polygon.area<=0:raise ValueError('Valid gable face required')
        polygons.append(polygon)
    region=Polygon(group['interior_ring_points'])
    if (not region.is_valid or not unary_union(polygons).equals(region)
            or polygons[0].intersection(polygons[1]).area>0):
        raise ValueError('Gable faces must exactly partition their exclusion')
    ridge=polygons[0].boundary.intersection(polygons[1].boundary)
    if ridge.geom_type!='LineString' or ridge.length<=.001:
        raise ValueError('One shared straight ridge required')
    endpoints=[list(ridge.coords[0]),list(ridge.coords[-1])]
    length=math.dist(*endpoints)
    if not math.isclose(length,ridge.length,abs_tol=.001):raise ValueError('Ridge must be straight')
    direction=[(b-a)/length for a,b in zip(*endpoints)]
    normal=[-direction[1],direction[0]]
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    gradient=[-rise/12*v/math.hypot(*down) for v in down]
    if abs(dot(gradient,normal))>math.hypot(*gradient)*.001:
        raise ValueError('This gable inference requires parent downslope parallel to the ridge')
    source={'group':group,'parent':parent,'frame':frame}
    identity=hashlib.sha256(json.dumps(source,sort_keys=True,allow_nan=False).encode()).hexdigest()
    measurements=[];evidence=[]
    for index,(face,polygon) in enumerate(zip(faces,polygons)):
        valleys=[]
        for a,b in zip(face['points'],face['points'][1:]+face['points'][:1]):
            delta=[b[i]-a[i] for i in range(2)]
            if abs(dot(delta,direction))<=.001 or abs(dot(delta,normal))<=.001:continue
            if sum(ridge.distance(Point(p))<=.001 for p in (a,b))!=1:continue
            valleys.append((a,b,delta))
        if len(valleys)!=1:raise ValueError('One unambiguous oblique intersection per face required')
        a,b,delta=valleys[0]
        slope=dot(gradient,delta)/dot(normal,delta)
        derived=[slope*v for v in normal]
        inward=[polygon.centroid.x-endpoints[0][0],polygon.centroid.y-endpoints[0][1]]
        if dot(derived,inward)>=0:raise ValueError('Inferred plane rises away from the shared ridge')
        inferred_rise=12*abs(slope)
        if not 0<inferred_rise<=24:raise ValueError('Inferred pitch is outside supported range')
        record={'ridge_points_pt':endpoints,'valley_points_pt':[a,b],
            'parent_gradient':gradient,'inferred_gradient':derived,'inferred_rise_per_12':inferred_rise,
            'formula':'parent_gradient dot valley_delta / (ridge_normal dot valley_delta)',
            'source':parent['source'],'parent_pitch_evidence':parent,
            'pitch_is_inferred':True,'pitch_certified':False,
            'assumptions':['These two polygons are planar gable roof faces with a level shared ridge.',
                'Each oblique boundary is the intersection with the identified parent roof plane.',
                'The plan has equal horizontal and vertical axis scales.']}
        mid='roof-inferred-gable-'+identity[:16]+'-'+str(index+1)
        measurement={key:frame[key] for key in ('page','points_per_foot','width_pt','height_pt')}
        measurement.update(id=mid,label=f'Gable face {index+1}: inferred {inferred_rise:.4f}:12',
            kind='area',points=face['points'],surface_factor=math.sqrt(1+slope*slope),
            color=['#a16207','#a21caf'][index],dependent_rows=[],engine_line_ids=[mid],
            source_cad_paths=face['source_cad_paths'],source_pitch_evidence=record,
            source_geometry_sha256=identity,source_method='inferred intersection of reviewed roof planes',
            scope_status='Inferred pitch; verify roof identity, level ridge, valley and complete coverage before estimate use')
        calculate(measurement);measurements.append(measurement);evidence.append(record)
    return {'measurements':measurements,'pitch_evidence':evidence,'source_geometry_sha256':identity,
        'pitch_certified':False,'scope_certified':False,
        'remaining':['Review the inferred pitch and its geometric assumptions; it is not a printed specification.',
            'Verify dormer identity and roof coverage before combining with other surfaces or pricing.']}
