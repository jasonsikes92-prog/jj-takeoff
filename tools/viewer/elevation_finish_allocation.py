"""Place reviewed elevation polygons on identified room-wall planes."""
import math
from shapely.geometry import Polygon, box, mapping as geometry_mapping
from shapely.ops import unary_union
from measurement_store import calculate
from measurement_quantities import geometry_digest


def allocate_elevations(room, height_ft, measurements, fields, room_geometry_sha256):
    if geometry_digest(room)!=room_geometry_sha256:
        raise ValueError('Room boundary changed; review elevation-to-wall anchors')
    if (type(height_ft) not in (int,float) or not math.isfinite(height_ft) or height_ft<=0
            or room['kind']!='area' or room.get('surface_factor',1)!=1 or 'plane_gradients' in room):
        raise ValueError('Elevation finish allocation needs a flat room and positive wall height')
    gross=calculate(room)['perimeter_lf']*height_ft
    edges=list(zip(room['points'],room['points'][1:]+room['points'][:1]))
    patches={};mapped=[];seen=set()
    if not fields:raise ValueError('Elevation finish fields are missing')
    for field in fields:
        identity=field.get('id');index=field['room_edge_index']
        if not identity or identity in seen:raise ValueError('Elevation field IDs must be distinct')
        seen.add(identity)
        if type(index) is not int or not 0<=index<len(edges):raise ValueError('Unknown room wall edge')
        if (field['anchor_end'] not in ('start','end') or type(field['direction']) is not int
                or field['direction'] not in (-1,1)
                or not isinstance(field.get('datum_source'),str) or not field['datum_source'].strip()):
            raise ValueError('Elevation field needs a sourced datum, anchor end and direction')
        anchor_x,floor_y=field['elevation_anchor_x_pt'],field['elevation_floor_y_pt']
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (anchor_x,floor_y)):
            raise ValueError('Elevation datums must be finite')
        includes=field['include'];excludes=field.get('exclude',[]);ids=includes+excludes
        if not includes or len(ids)!=len(set(ids)):raise ValueError('Elevation field needs distinct include/exclude measurements')
        length=math.dist(*edges[index])/room['points_per_foot']
        offset=0 if field['anchor_end']=='start' else length
        shapes={};frame=None
        for key in ids:
            measurement=measurements[key];calculate(measurement)
            if (measurement['kind']!='area' or measurement.get('surface_factor',1)!=1
                    or 'plane_gradients' in measurement):raise ValueError('Finish field needs flat elevation polygons')
            current=tuple(measurement.get(k) for k in ('page','width_pt','height_pt','points_per_foot'))
            if frame is not None and current!=frame:raise ValueError('Elevation inclusions and cutouts must share a frame')
            frame=current
            if not (0<=anchor_x<=measurement['width_pt'] and 0<=floor_y<=measurement['height_pt']):
                raise ValueError('Elevation datum must lie on its source drawing')
            scale=measurement['points_per_foot']
            shapes[key]=Polygon([(offset+field['direction']*(x-anchor_x)/scale,(floor_y-y)/scale)
                                 for x,y in measurement['points']])
        included=unary_union([shapes[k] for k in includes]);excluded=unary_union([shapes[k] for k in excludes])
        if not box(0,0,length,height_ft).buffer(1e-7).covers(included):
            raise ValueError('Elevation finish extends outside the mapped room wall')
        if excluded.difference(included).area>1e-8:
            raise ValueError('Elevation cutout is outside its included finish field')
        visible=included.difference(excluded)
        patches.setdefault(index,[]).append(visible)
        mapped.append({'id':identity,'room_edge_index':index,'include':includes,'exclude':excludes,
            'surface_sf':visible.area,'wall_plane_geometry_ft':geometry_mapping(visible),
            'datum_source':field['datum_source']})
    total=math.fsum(unary_union(parts).area for parts in patches.values())
    return {'gross_wall_sf':gross,'excluded_wall_sf':total,'remaining_wall_reference_sf':gross-total,
        'overlapping_exclusion_sf':max(0,math.fsum(p['surface_sf'] for p in mapped)-total),
        'mapped_elevation_fields':mapped,'paint_quantity_certified':False,'purchase_quantity':None}
