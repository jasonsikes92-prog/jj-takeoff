"""Recompute explicitly mapped draft quantities from a verified measurement state.

This does not select prices, infer absent geometry or release material orders.
"""
import math
import hashlib

from measurement_store import calculate, encode
from wall_boundary_surfaces import wall_surface,opening_spans,WallBoundaryReviewRequired


def geometry_digest(measurement):
    """Bind a scope review to geometry, scale, page and slope interpretation."""
    fields=('id','page','kind','points','points_per_foot','width_pt','height_pt',
            'surface_factor','plane_gradients')
    return hashlib.sha256(encode({k:measurement[k] for k in fields if k in measurement}).encode()).hexdigest()


def surface_components(values, terms, measurements=None):
    """Calculate explicitly identified surface faces, retaining gross/deductions.

    Terms classify physical faces; geometry alone cannot infer drywall scope.
    Heights are sourced feet or an explicitly measured vertical span. Opening placement and overlapping
    finishes require separate review before a draft can become an order.
    """
    if not terms:raise ValueError('Surface assembly needs components')
    seen=set();used=set();components=[];wall_openings={}
    for term in terms:
        if not term.get('id') or term['id'] in seen:raise ValueError('Duplicate or missing surface face ID')
        seen.add(term['id']);identity=term['measurement_id'];used.add(identity)
        if identity not in values:raise ValueError('Surface component has undeclared geometry')
        value=values[identity];kind=term['kind'];resolved={}
        if kind=='area' and value['unit']=='SF':quantity=value['quantity']
        elif kind=='projected_area' and value['unit']=='SF':quantity=value['projected_area_sf']
        elif kind in ('rectangular_wall_faces','exposed_boundary_wall') and value['unit']=='SF':
            if measurements is None:raise ValueError('Selected wall faces need source outlines')
            if kind=='exposed_boundary_wall':
                excluded=term.get('exclude_measurement_id')
                if excluded not in values:raise ValueError('Excluded wall outline must be declared')
                used.add(excluded)
            resolved['wall_profile']=wall_surface(measurements,term)
            quantity=resolved['wall_profile']['surface_sf']
        elif kind=='symmetric_vault_upper_wall' and value['unit']=='SF':
            if measurements is None or identity not in measurements:
                raise ValueError('Vault upper walls need the source boundary')
            from vault_wall_surface import vault_upper_wall_area
            profile=vault_upper_wall_area(measurements[identity],term.get('transverse_direction'),
                term.get('pitch_rise'),term.get('pitch_run'),term.get('pitch_source'))
            quantity=profile['gross_upper_wall_sf']
            resolved['vault_profile']={k:v for k,v in profile.items() if k!='edges'}
        elif kind=='symmetric_gable_wall' and value['unit']=='LF':
            rise,run=term.get('pitch_rise'),term.get('pitch_run')
            if (any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (rise,run))
                    or not isinstance(term.get('pitch_source'),str) or not term['pitch_source'].strip()):
                raise ValueError('Gable surface needs positive pitch and source')
            quantity=value['quantity']**2*rise/run/4
        elif kind in ('perimeter_wall','length_wall','trapezoid_wall'):
            height=term.get('height_ft')
            height_id=term.get('height_measurement_id')
            if height_id is not None:
                if 'height_ft' in term:raise ValueError('Wall height has competing fixed and measured values')
                if height_id not in values or values[height_id]['unit']!='LF':
                    raise ValueError('Wall height needs a declared length measurement')
                used.add(height_id);height=values[height_id]['quantity']
                resolved['resolved_height_ft']=height
            if (type(height) not in (int,float) or not math.isfinite(height) or height<=0
                    or not isinstance(term.get('height_source'),str) or not term['height_source'].strip()):
                raise ValueError('Wall surface needs positive height and source')
            if kind=='perimeter_wall' and value['unit']=='SF':length=value['perimeter_lf']
            elif kind in ('length_wall','trapezoid_wall') and value['unit']=='LF':length=value['quantity']
            else:raise ValueError('Surface component geometry has the wrong unit')
            if kind=='trapezoid_wall':
                end_id=term.get('end_height_measurement_id')
                if height_id is None or end_id not in values or values[end_id]['unit']!='LF':
                    raise ValueError('Trapezoid wall needs two declared measured heights')
                end_height=values[end_id]['quantity']
                if not math.isfinite(end_height) or end_height<=0:
                    raise ValueError('Trapezoid wall needs positive end height')
                used.add(end_id);resolved['resolved_end_height_ft']=end_height
                height=(height+end_height)/2
            quantity=length*height
        else:raise ValueError('Unknown surface component or wrong unit')
        operation=term['operation']
        if operation not in ('add','deduct'):raise ValueError('Unknown surface operation')
        if 'wall_face_of' in term:
            owner=term['wall_face_of'];parent=next((c for c in components if c['id']==owner),{})
            if (kind!='length_wall' or operation!='deduct' or 'wall_profile' not in parent
                    or not isinstance(term.get('alignment_source'),str) or not term['alignment_source'].strip()):
                raise ValueError('Wall opening needs a preceding selected wall face and alignment source')
            wall=measurements[parent['measurement_id']];opening=measurements[identity]
            if any(opening.get(k)!=wall.get(k) for k in ('page','width_pt','height_pt','points_per_foot')):
                raise WallBoundaryReviewRequired('Wall opening and selected faces must share the drawing frame')
            spans=opening_spans(opening,parent['wall_profile'],term.get('alignment_tolerance_ft',0))
            previous=wall_openings.setdefault(owner,[])
            for span in spans:
                if any(p['segment_index']==span['segment_index'] and min(p['end_ft'],span['end_ft'])-max(p['start_ft'],span['start_ft'])>1e-7 for p in previous):
                    raise WallBoundaryReviewRequired('Opening deductions overlap on selected wall faces')
            previous.extend(spans);resolved['wall_opening_spans']=spans
        components.append({**term,**resolved,'surface_sf':quantity})
    if used!=set(values):raise ValueError('Surface assembly has unused measurements')
    gross=math.fsum(c['surface_sf'] for c in components if c['operation']=='add')
    deductions=math.fsum(c['surface_sf'] for c in components if c['operation']=='deduct')
    if deductions>gross:raise ValueError('Surface deductions exceed gross area')
    return {'components':components,'gross_sf':gross,'deductions_sf':deductions,'net_sf':gross-deductions}


def linear_components(values, terms):
    seen=set();used=set();components=[]
    for term in terms:
        if not term.get('id') or term['id'] in seen:raise ValueError('Duplicate or missing linear component')
        seen.add(term['id']);identity=term['measurement_id'];used.add(identity)
        value=values[identity]
        if term['kind']=='perimeter' and value['unit']=='SF':quantity=value['perimeter_lf']
        elif term['kind']=='length' and value['unit']=='LF':quantity=value['quantity']
        else:raise ValueError('Linear component has incompatible geometry')
        if term['operation'] not in ('add','deduct'):raise ValueError('Unknown linear operation')
        components.append({**term,'length_lf':quantity})
    if used!=set(values):raise ValueError('Linear assembly has unused measurements')
    gross=math.fsum(c['length_lf'] for c in components if c['operation']=='add')
    deductions=math.fsum(c['length_lf'] for c in components if c['operation']=='deduct')
    if deductions>gross:raise ValueError('Linear deductions exceed gross length')
    return {'components':components,'gross_lf':gross,'deductions_lf':deductions,'net_lf':gross-deductions}


def rollup(state,rules):
    if rules['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Quantity rules belong to another drawing')
    result=[];pending=[];identities=set()
    for rule in rules['rules']:
        if rule['id'] in identities:raise ValueError('Duplicate quantity rule')
        identities.add(rule['id'])
        ids=rule['measurement_ids']
        if not ids or len(ids)!=len(set(ids)):raise ValueError('Quantity needs unique measurement IDs')
        count_openings=rule.get('count_openings',False)
        if count_openings and (rule['unit']!='EA' or 'surface_components' in rule or 'footprint' in rule):
            raise ValueError('Opening count must be a separate EA quantity')
        if 'units_per_opening' in rule and (not count_openings
                or type(rule['units_per_opening']) is not int or rule['units_per_opening']<=0
                or not isinstance(rule.get('units_per_opening_source'),str)
                or not rule['units_per_opening_source'].strip()):
            raise ValueError('Units per opening require a positive integer, opening count and source')
        if 'linear_components' in rule and (rule['unit']!='LF' or count_openings or 'surface_components' in rule or 'footprint' in rule):
            raise ValueError('Linear assembly must be a separate LF quantity')
        if 'boundary_route' in rule and (rule['unit']!='LF' or count_openings
                or any(k in rule for k in ('linear_components','surface_components','footprint','disjoint_areas','disjoint_area_components'))):
            raise ValueError('Boundary route must be a separate LF quantity')
        if 'elevation_trim_route' in rule and (rule['unit']!='LF' or count_openings
                or any(k in rule for k in ('linear_components','surface_components','footprint','boundary_route','disjoint_areas','disjoint_area_components','disjoint_projected_areas'))):
            raise ValueError('Elevation trim route must be a separate LF quantity')
        values=[];by_id={};surface=None;linear=None;boundary=None;trim=None;unreviewed=[];invalid_spans=[];invalid_heights=[]
        for identity in ids:
            if identity not in state['measurements']:raise ValueError('Quantity measurement is missing: '+identity)
            measurement=state['measurements'][identity]
            # Engine candidates are not estimate quantities merely because their
            # polygons are valid. This also catches drafts created before this gate.
            review=rule.get('geometry_reviews',{}).get(identity,{})
            if rule.get('requires_geometry_review') is True or measurement.get('engine_line_ids') or review:
                if (review.get('decision')!='approved_for_draft' or
                        review.get('geometry_sha256')!=geometry_digest(measurement) or
                        not isinstance(review.get('scope'),str) or not review['scope'].strip()):
                    if rule.get('defer_pending_scope') is True:
                        unreviewed.append(identity)
                        continue
                    raise ValueError('Engine boundary needs a current scope review: '+identity)
            if any(identity in (t.get('height_measurement_id'),t.get('end_height_measurement_id')) for t in rule.get('surface_components',[])):
                points=measurement['points']
                if (measurement['kind']!='length' or len(points)!=2 or 'plane_gradients' in measurement
                        or not math.isclose(points[0][0],points[1][0],abs_tol=1e-6,rel_tol=0)
                        or points[0][1]==points[1][1]):
                    invalid_heights.append(identity)
                    continue
            if any(t['measurement_id']==identity and t['kind']=='trapezoid_wall' for t in rule.get('surface_components',[])):
                points=measurement['points']
                if (measurement['kind']!='length' or len(points)!=2 or 'plane_gradients' in measurement
                        or points[0]==points[1]):
                    invalid_spans.append(identity)
                    continue
            value=calculate(measurement)
            if any(t['measurement_id']==identity and t['kind']=='symmetric_gable_wall'
                   for t in rule.get('surface_components',[])):
                if measurement['kind']!='length' or len(measurement['points'])!=2 or 'plane_gradients' in measurement:
                    invalid_spans.append(identity)
                    continue
            by_id[identity]=value
            if count_openings:
                if measurement['kind']!='length' or value['quantity']<=0:
                    raise ValueError('Each counted opening requires a positive measured span')
            elif not any(k in rule for k in ('surface_components','linear_components','boundary_route','elevation_trim_route')) and value['unit']!=rule['unit']:raise ValueError('Mixed measurement units')
            values.append(1 if count_openings else value['quantity'])
        if invalid_heights:
            pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                'measurement_ids':ids,'invalid_measurement_ids':invalid_heights,
                'reason':'Measured wall height must be one positive vertical elevation span with two endpoints','quantity':None})
            continue
        if invalid_spans:
            pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                'measurement_ids':ids,'invalid_measurement_ids':invalid_spans,
                'reason':'Gable or trapezoid width must be one positive straight plan span with two endpoints','quantity':None})
            continue
        if 'contained_projections' in rule:
            from area_cutouts import projection_containment_issues
            issues=projection_containment_issues({i:state['measurements'][i] for i in ids},rule['contained_projections'])
            if issues:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'containment_issues':issues,
                    'reason':'Review projected boundary containment before using this quantity','quantity':None})
                continue
        if any('cutout_of' in term for term in rule.get('surface_components',[])):
            from area_cutouts import cutout_issues
            issues=cutout_issues(state['measurements'],rule['surface_components'])
            if issues:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'cutout_issues':issues,
                    'reason':'Interior area deductions require valid placement, separate boundaries and matching scale/slope',
                    'quantity':None})
                continue
        if unreviewed:
            pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                'measurement_ids':ids,'unreviewed_measurement_ids':unreviewed,
                'reason':'Current boundary, scale and scope review required','quantity':None})
            continue
        measured=math.fsum(values)
        if rule.get('disjoint_area_components'):
            if rule['unit']!='SF' or not rule.get('surface_components'):
                raise ValueError('Disjoint area components require a surface assembly')
            area_ids=[t['measurement_id'] for t in rule['surface_components']
                      if t['kind']=='area' and t['operation']=='add']
            if not area_ids or len(area_ids)!=len(set(area_ids)):
                raise ValueError('Disjoint area components need unique added area measurements')
            from area_overlap import overlapping_measurements
            pages={}
            for identity in area_ids:
                measurement=state['measurements'][identity]
                pages.setdefault(measurement['page'],[]).append(measurement)
            overlaps=[pair for areas in pages.values() for pair in overlapping_measurements(areas)]
            if overlaps:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'overlapping_measurement_ids':overlaps,
                    'reason':'Overlapping surface boundaries require correction before adding areas','quantity':None})
                continue
        if rule.get('disjoint_areas') or rule.get('disjoint_projected_areas'):
            if rule['unit']!='SF' or any(k in rule for k in ('surface_components','linear_components','footprint')):
                raise ValueError('Disjoint area review requires a simple sum of measured surfaces')
            from area_overlap import overlapping_measurements
            overlaps=overlapping_measurements([state['measurements'][i] for i in ids],
                projected=rule.get('disjoint_projected_areas') is True)
            if overlaps:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'overlapping_measurement_ids':overlaps,
                    'reason':'Overlapping surface boundaries require correction before adding areas','quantity':None})
                continue
        if 'linear_components' in rule:
            linear=linear_components(by_id,rule['linear_components']);measured=linear['net_lf']
        if 'boundary_route' in rule:
            from boundary_routes import calculate as boundary_route
            mapping=rule['boundary_route']
            if set(mapping)!= {'outline_id','deduction_ids'}:
                raise ValueError('Boundary route needs outline_id and deduction_ids')
            try:
                boundary=boundary_route({i:state['measurements'][i] for i in ids},
                    mapping['outline_id'],mapping['deduction_ids'])
            except ValueError as exc:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'reason':str(exc),'quantity':None})
                continue
            measured=boundary['net_lf']
        if 'elevation_trim_route' in rule:
            from elevation_trim_routes import calculate as trim_route
            selection=rule['elevation_trim_route'];groups=selection.get('groups',[])
            allowed={'horizontal_wall_top','sloped_gable','recessed_porch_return','gable_base_scope_pending'}
            if set(selection)!={'mapping','groups'} or not groups or len(groups)!=len(set(groups)) or set(groups)-allowed:
                raise ValueError('Elevation trim needs explicit unique route groups')
            try:
                trim=trim_route({i:state['measurements'][i] for i in ids},selection['mapping'])
            except ValueError as exc:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'reason':str(exc),'quantity':None})
                continue
            measured=math.fsum(trim['group_lf'][g] for g in groups)
            trim['selected_groups']=groups
        if 'footprint' in rule:
            if rule['unit']!='SF' or 'surface_components' in rule:raise ValueError('Footprint must be a separate SF assembly')
            from footprint_area import footprint_area
            measured=footprint_area({i:state['measurements'][i] for i in ids},
                rule['footprint']['include'],rule['footprint'].get('exclude',[]))
        if 'surface_components' in rule:
            if rule['unit']!='SF':raise ValueError('Surface assembly output must be SF')
            try:surface=surface_components(by_id,rule['surface_components'],state['measurements'])
            except WallBoundaryReviewRequired as exc:
                pending.append({'id':rule['id'],'label':rule['label'],'template_rows':rule['template_rows'],
                    'measurement_ids':ids,'reason':str(exc),'quantity':None})
                continue
            measured=surface['net_sf']
        opening_count=measured if 'units_per_opening' in rule else None
        if opening_count is not None:measured*=rule['units_per_opening']
        rounding=rule['rounding']
        if rounding not in ('none','whole_up'):raise ValueError('Unknown quantity rounding')
        if rule['use'] not in ('template_quantity','assembly_input'):raise ValueError('Unknown quantity use')
        adjusted=measured
        if 'waste_percent' in rule:
            waste=rule['waste_percent']
            if (type(waste) not in (int,float) or not math.isfinite(waste) or waste<0
                    or not isinstance(rule.get('waste_source'),str) or not rule['waste_source'].strip()):
                raise ValueError('Waste allowance needs a nonnegative percentage and source')
            adjusted=measured*(1+waste/100)
        result.append({'id':rule['id'],'label':rule['label'],'measurement_ids':ids,
            'measured_quantity':measured,'quantity':math.ceil(adjusted) if rounding=='whole_up' else adjusted,
            'unit':rule['unit'],'rounding':rounding,'template_rows':rule['template_rows'],'use':rule['use'],
            'basis':rule['basis'],'remaining':rule['remaining'],'current_price':None,
            'certified':False,'order_released':False})
        if opening_count is not None:
            result[-1]['opening_assembly']={'opening_count':opening_count,
                'units_per_opening':rule['units_per_opening'],
                'source':rule['units_per_opening_source']}
        if 'waste_percent' in rule:
            result[-1].update(waste_percent=waste,waste_source=rule['waste_source'],
                             waste_adjusted_quantity=adjusted)
        if 'purchase_pack' in rule:
            pack=rule['purchase_pack']
            coverage=pack.get('coverage_quantity');count=pack.get('packs_per_coverage')
            if (type(coverage) not in (int,float) or not math.isfinite(coverage) or coverage<=0
                    or type(count) is not int or count<=0 or pack.get('coverage_unit')!=rule['unit']
                    or any(not isinstance(pack.get(k),str) or not pack[k].strip()
                           for k in ('unit','product','source'))):
                raise ValueError('Purchase pack needs positive coverage, matching units, product and source')
            # Use the unrounded, waste-adjusted area; template SF rounding is independent.
            result[-1]['purchase_pack']={**pack,'required_quantity':adjusted,
                'quantity':math.ceil(adjusted*count/coverage),'order_released':False}
        if surface is not None:result[-1]['surface_assembly']=surface
        if linear is not None:result[-1]['linear_assembly']=linear
        if boundary is not None:result[-1]['boundary_route']=boundary
        if trim is not None:result[-1]['elevation_trim_route']=trim
    return {'measurement_version':state['version'],'plan_sha256':state['plan_sha256'],
        'quantities':result,'pending_quantities':pending,'whole_house_total':None,'estimate_released':False}
