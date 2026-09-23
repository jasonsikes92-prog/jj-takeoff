"""Reviewed wall faces derived from current plan outlines, without duplicate traces."""
import math
from shapely.geometry import Polygon,LineString,box
from measurement_store import calculate


class WallBoundaryReviewRequired(ValueError):
    pass


def opening_spans(measurement,profile,tolerance_ft):
    if type(tolerance_ft) not in (int,float) or not math.isfinite(tolerance_ft) or not 0<=tolerance_ft<=0.25:
        raise ValueError('Opening alignment tolerance must be between zero and one quarter foot')
    if measurement['kind']!='length' or len(measurement['points'])!=2:
        raise WallBoundaryReviewRequired('Wall opening must be one straight measured span')
    p,q=measurement['points'];scale=measurement['points_per_foot'];span=math.dist(p,q);parts=[]
    for i,segment in enumerate(profile['wall_segments']):
        a,b=segment['points'];dx,dy=b[0]-a[0],b[1]-a[1];length=math.dist(a,b)
        if abs(dx*(q[1]-p[1])-dy*(q[0]-p[0]))>1e-7*length*span:continue
        if max(abs(dx*(v[1]-a[1])-dy*(v[0]-a[0]))/length for v in (p,q))>tolerance_ft*scale+1e-7:continue
        positions=sorted(((v[0]-a[0])*dx+(v[1]-a[1])*dy)/length for v in (p,q))
        start=max(0,positions[0]);end=min(length,positions[1])
        if end>start:parts.append({'segment_index':i,'start_ft':start/scale,'end_ft':end/scale})
    if not math.isclose(sum(p['end_ft']-p['start_ft'] for p in parts),span/scale,rel_tol=0,abs_tol=1e-7):
        raise WallBoundaryReviewRequired('Opening no longer lies on its selected wall faces')
    return parts


def wall_surface(measurements,term):
    identity=term['measurement_id'];m=measurements[identity]
    height=term.get('height_ft')
    if (type(height) not in (int,float) or not math.isfinite(height) or height<=0
            or not isinstance(term.get('height_source'),str) or not term['height_source'].strip()
            or not isinstance(term.get('scope_source'),str) or not term['scope_source'].strip()):
        raise ValueError('Selected wall faces need positive height and height/scope sources')
    def shape(source):
        calculate(source)
        if source['kind']!='area' or source.get('surface_factor',1)!=1 or 'plane_gradients' in source:
            raise WallBoundaryReviewRequired('Wall faces require flat plan outlines')
        return Polygon(source['points'])
    if term['kind']=='length_wall':
        value=calculate(m)
        if m['kind']!='length' or len(m['points'])!=2 or 'plane_gradients' in m:
            raise WallBoundaryReviewRequired('Wall finish span must be one straight plan line')
        length=value['quantity']
        return {'wall_segments':[{'face':'measured_span','points':m['points'],'length_lf':length}],
            'selected_length_lf':length,'height_ft':height,'surface_sf':length*height,
            'basis':'Source-defined wall finish span and height'}
    outer=shape(m);scale=m['points_per_foot']
    if term['kind']=='rectangular_wall_faces':
        faces=term.get('faces');x0,y0,x1,y1=outer.bounds
        if not outer.equals(box(x0,y0,x1,y1)):
            raise WallBoundaryReviewRequired('Room is no longer an axis-aligned rectangle; review selected wall faces')
        sides={'min_x':[(x0,y0),(x0,y1)],'max_x':[(x1,y0),(x1,y1)],
               'min_y':[(x0,y0),(x1,y0)],'max_y':[(x0,y1),(x1,y1)]}
        if not isinstance(faces,list) or not faces or any(f not in sides for f in faces) or len(faces)!=len(set(faces)):
            raise ValueError('Selected wall faces must be distinct rectangle sides')
        pieces=[(f,LineString(sides[f])) for f in faces]
    elif term['kind']=='exposed_boundary_wall':
        other_id=term['exclude_measurement_id'];other=measurements[other_id];inner=shape(other)
        if other_id==identity or any(m.get(k)!=other.get(k) for k in ('page','width_pt','height_pt','points_per_foot')):
            raise WallBoundaryReviewRequired('Wall outlines must be distinct and share one drawing frame and scale')
        if not outer.covers(inner) or outer.boundary.intersection(inner.boundary).length<=0:
            raise WallBoundaryReviewRequired('House must stay inside combined outline with shared exterior edges')
        remaining=outer.boundary.difference(inner.boundary)
        lines=list(remaining.geoms) if remaining.geom_type=='MultiLineString' else [remaining]
        pieces=[]
        for line in lines:
            for a,b in zip(list(line.coords),list(line.coords)[1:]):
                if a!=b:pieces.append(('exposed',LineString([a,b])))
        if not pieces:raise WallBoundaryReviewRequired('No exposed addition walls remain')
    else:raise ValueError('Unknown selected wall surface')
    segments=[{'face':f,'points':[list(p) for p in line.coords],'length_lf':line.length/scale} for f,line in pieces]
    length=math.fsum(p['length_lf'] for p in segments)
    return {'wall_segments':segments,'selected_length_lf':length,'excluded_perimeter_lf':outer.length/scale-length,
            'height_ft':height,'surface_sf':length*height,
            'basis':'Gross selected wall field before framing cavities, openings and waste'}
