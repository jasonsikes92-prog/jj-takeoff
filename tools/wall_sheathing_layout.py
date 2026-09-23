"""Calculate nominal wall-sheet scenarios from current outlines and elevation bindings."""
import math
from collections import Counter
from shapely.geometry import Polygon
from shapely.ops import unary_union
from wall_panel_layout import wall_modules
from roof_panel_layout import pack_blanks


def bodies(outline, basis, plate_inches):
    points=outline['points'];scale=outline['points_per_foot'];polygon=Polygon(points)
    if not polygon.is_valid or polygon.area<=0:raise ValueError('Valid exterior outline required')
    ids=basis['wall_ids'];garage=set(basis['garage_wall_ids'])
    if len(ids)!=len(points) or len(set(ids))!=len(ids) or not garage<=set(ids):
        raise ValueError('Exterior wall identities must match the outline')
    offset=basis['half_wall_inches']/12*scale*(1 if polygon.exterior.is_ccw else -1)
    lines=[]
    for a,b in zip(points,points[1:]+points[:1]):
        horizontal=abs(b[1]-a[1])<1e-6
        if math.dist(a,b)<=0 or (not horizontal and abs(b[0]-a[0])>=1e-6):
            raise ValueError('Exterior sheathing requires orthogonal wall runs')
        lines.append((horizontal,a[1]-(b[0]-a[0])/math.dist(a,b)*offset if horizontal
                      else a[0]+(b[1]-a[1])/math.dist(a,b)*offset))
    vertices=[]
    for i,(horizontal,coordinate) in enumerate(lines):
        previous=lines[i-1]
        if horizontal==previous[0]:raise ValueError('Exterior corner mapping requires alternating axes')
        vertices.append([previous[1],coordinate] if horizontal else [coordinate,previous[1]])
    if not Polygon(vertices).is_valid:raise ValueError('Outside-face offset is invalid')
    faces=[]
    for i,identity in enumerate(ids):
        length=math.dist(vertices[i],vertices[(i+1)%len(vertices)])/scale
        height=(plate_inches+(basis['garage_height_adjustment_inches'] if identity in garage else 0))/12
        if min(length,height)<=0:raise ValueError('Positive wall length and height required')
        face=wall_modules(identity,[[0,0],[length,0],[length,height],[0,height]])
        face.update(length_ft=length,height_ft=height,zone='garage' if identity in garage else 'house')
        faces.append(face)
    return faces


def upper_faces(measurements, bindings):
    faces=[]
    for binding in bindings:
        identity=binding['id'];kind=binding['kind'];ids=binding['measurement_ids']
        sources=[measurements[k] for k in ids]
        if not sources or len(set(ids))!=len(ids):raise ValueError('Unique upper-face measurement references required')
        if kind in ('area_union','reconstructed_gable'):
            reference=sources[0];scale=reference['points_per_foot']
            if any(s['kind']!='area' or s['page']!=reference['page'] or s['points_per_foot']!=scale for s in sources):
                raise ValueError('Upper polygons must share a sheet and scale')
            polygons=[Polygon(s['points']) for s in sources]
            if any(not p.is_valid or p.area<=0 for p in polygons):raise ValueError('Valid upper polygons required')
            if kind=='area_union':
                polygon=unary_union(polygons)
                if polygon.geom_type!='Polygon' or polygon.interiors or abs(sum(p.area for p in polygons)-polygon.area)>1e-7:
                    raise ValueError('Upper face parts must meet without a gap, overlap or hole')
                points=[list(p) for p in polygon.exterior.coords[:-1]]
            else:
                if len(sources)!=1 or len(reference['points'])!=binding['vertex_count']:
                    raise ValueError('Gable topology changed; review its rake mapping')
                visible=polygons[0];rake,ridge,right=[reference['points'][i] for i in binding['rake_indices']]
                if not (rake[0]<ridge[0]<right[0] and min(rake[1],right[1])>ridge[1]):
                    raise ValueError('Gable rake and peak directions changed')
                base=max(p[1] for p in reference['points'])
                left=ridge[0]+(right[1]-ridge[1])*(rake[0]-ridge[0])/(rake[1]-ridge[1])
                points=[[left,right[1]],ridge,right,[right[0],base],[left,base]]
                polygon=Polygon(points)
                if not polygon.is_valid or visible.difference(polygon).area>1e-7:
                    raise ValueError('Reconstructed gable must contain its visible source')
            xmin=min(p[0] for p in points);base=max(p[1] for p in points)
            face=wall_modules(identity,[[(x-xmin)/scale,(base-y)/scale] for x,y in points])
            if kind=='reconstructed_gable':face['reconstructed_hidden_sf']=polygon.difference(visible).area/scale**2
        elif kind in ('rectangle','level_cap_trapezoid'):
            if any(s['kind']!='length' or len(s['points'])!=2 for s in sources):
                raise ValueError('Chase faces require straight length measurements')
            lengths=[math.dist(*s['points'])/s['points_per_foot'] for s in sources]
            if min(lengths)<=0:raise ValueError('Positive chase dimensions required')
            if kind=='rectangle':
                if len(lengths)!=2:raise ValueError('Rectangle needs width and height')
                width,height=lengths;points=[[0,0],[width,0],[width,height],[0,height]]
            else:
                if len(lengths)!=3:raise ValueError('Chase side needs width and two heights')
                width,start,end=lengths;top=max(start,end)
                points=[[0,top-start],[width,top-end],[width,top],[0,top]]
            face=wall_modules(identity,points)
        else:raise ValueError('Unsupported upper sheathing face kind')
        face.update(source_measurement_ids=ids,basis=binding['basis']);faces.append(face)
    if len({f['face_id'] for f in faces})!=len(faces):raise ValueError('Duplicate upper sheathing face')
    return faces


def allocate(faces):
    pieces=[p for f in faces for p in f['pieces']];sheets=pack_blanks(pieces)
    if Counter(p['id'] for p in pieces)!=Counter(c['piece_id'] for s in sheets for c in s['cuts']):
        raise ValueError('Sheathing stock allocation lost or duplicated a piece')
    return {'faces':faces,'sheets':sheets,'candidate_sheets':len(sheets),
        'cut_sections':len(pieces),'gross_surface_sf':math.fsum(f['surface_sf'] for f in faces),'purchase_quantity':None}


def calculate(outline, measurements, basis, *, selected_wall_height_inches=None):
    for key in ('half_wall_inches','plate_height_inches','precut_plate_height_inches','floor_band_height_inches'):
        value=basis[key]
        if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite sheathing dimensions required')
    adjustment=basis['garage_height_adjustment_inches']
    if type(adjustment) not in (int,float) or not math.isfinite(adjustment):raise ValueError('Finite garage height adjustment required')
    if selected_wall_height_inches is not None and (type(selected_wall_height_inches) not in (int,float)
            or selected_wall_height_inches not in (basis['plate_height_inches'],basis['precut_plate_height_inches'])):
        raise ValueError('Selected sheathing height must match a saved scenario')
    upper=upper_faces(measurements,basis['upper_faces'])
    height=basis['plate_height_inches'] if selected_wall_height_inches is None else selected_wall_height_inches
    body=bodies(outline,basis,height);combined=allocate(body+upper)
    alternate=allocate(bodies(outline,basis,basis['precut_plate_height_inches'])+upper)
    band=[]
    for face in body:
        if face['zone']=='garage':continue
        width=face['length_ft'];band_height=basis['floor_band_height_inches']/12
        band.append(wall_modules('FLOOR-BAND-'+face['face_id'],[[0,0],[width,0],[width,band_height],[0,band_height]]))
    result={'combined':combined,'precut_height_sensitivity':alternate,
        'conditional_floor_band':allocate(body+upper+band),
        'floor_band_area_sf':math.fsum(f['surface_sf'] for f in band),
        'purchase_quantity':None,'complete_wall_sheathing_quantity':None,'price_applied':False,
        'remaining':basis['remaining']}
    if selected_wall_height_inches is not None:
        result['selected_wall_height_inches']=height
        result['printed_height_comparison']=allocate(bodies(outline,basis,basis['plate_height_inches'])+upper)
    return result
