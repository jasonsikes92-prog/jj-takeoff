"""Recalculate partial paint references from the current saved measurement states."""
import copy
import hashlib
import json
import math
from shapely.geometry import box,shape
from shapely.ops import unary_union
from measurement_store import MeasurementStore, encode
from measurement_quantities import rollup, geometry_digest
from wall_finish_allocation import allocate


def checked_json(path, digest):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:
        raise ValueError('Paint source changed; review its mapping before recalculating')
    return json.loads(raw)


def gross_rule(rules, identity):
    matches = [r for r in rules['rules'] if r['id'] == identity]
    if len(matches) != 1:
        raise ValueError('Paint gross source rule must be present and unique')
    return matches[0]


def read_gross_rules(folder, config):
    path = folder/'quantity_rules.json'
    if 'gross_rule_sha256' not in config:
        return checked_json(path, config['quantity_rules_sha256'])
    if 'quantity_rules_sha256' in config:
        raise ValueError('Use one paint gross-rule binding method')
    rules = json.loads(path.read_bytes())
    source = gross_rule(rules, config['gross_rule_id'])
    if hashlib.sha256(encode(source).encode()).hexdigest() != config['gross_rule_sha256']:
        raise ValueError('Paint gross source rule changed; review its mapping before recalculating')
    return rules


def combine_room_allocations(partial):
    """Union validated finish patches in each physical room-wall plane."""
    rooms={}
    for entry in partial:
        result=entry['result'];room=rooms.setdefault(entry['room_id'],{
            'gross_wall_sf':result['gross_wall_sf'],'patches':{},'separate_deductions_sf':0})
        if not math.isclose(room['gross_wall_sf'],result['gross_wall_sf'],rel_tol=0,abs_tol=1e-7):
            raise ValueError('Finish allocations disagree about the room wall reference')
        room['separate_deductions_sf']+=result['excluded_wall_sf']
        for face in result.get('mapped_faces',[]):
            room['patches'].setdefault(face['room_edge_index'],[]).append(
                box(face['start_ft'],0,face['end_ft'],face['height_ft']))
        for field in result.get('mapped_elevation_fields',[]):
            room['patches'].setdefault(field['room_edge_index'],[]).append(shape(field['wall_plane_geometry_ft']))
    combined=[]
    for identity,room in rooms.items():
        excluded=math.fsum(unary_union(patches).area for patches in room['patches'].values())
        if excluded>room['gross_wall_sf']+1e-7:raise ValueError('Combined finishes exceed the room wall reference')
        combined.append({'room_id':identity,'gross_wall_sf':room['gross_wall_sf'],
            'known_finish_exclusion_sf':excluded,'remaining_wall_reference_sf':room['gross_wall_sf']-excluded,
            'overlap_between_allocations_sf':max(0,room['separate_deductions_sf']-excluded),
            'final_paint_quantity':None})
    return combined


def calculate_review(state, rules, config, finishes):
    if state['plan_sha256']!=config['plan_sha256'] or rules['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Paint review belongs to another drawing')
    source=gross_rule(rules,config['gross_rule_id'])
    exclusions=config.get('excluded_components',[])
    excluded_ids=set()
    for exclusion in exclusions:
        identity=exclusion['component_id']
        terms=[t for t in source['surface_components'] if t['id']==identity]
        if len(terms)!=1 or identity in excluded_ids or terms[0].get('operation','add')!='add':
            raise ValueError('Paint exclusion must identify one distinct positive surface component')
        if not exclusion.get('reason') or not exclusion.get('source_files'):
            raise ValueError('Paint exclusion requires a reason and source evidence')
        if geometry_digest(state['measurements'][terms[0]['measurement_id']])!=exclusion['geometry_sha256']:
            raise ValueError('Excluded paint geometry changed; review its scope before recalculating')
        excluded_ids.add(identity)
    candidates=[]
    for zone in ('house','garage'):
        terms=[copy.deepcopy(t) for t in source['surface_components']
               if t['id'] not in excluded_ids
               and (t['measurement_id']==config['garage_measurement_id'])==(zone=='garage')]
        candidates.append({'id':f'paint-{zone}-gross-reference','label':f'{zone.title()} gross paint reference',
            'measurement_ids':list(dict.fromkeys(t['measurement_id'] for t in terms)),
            'unit':'SF','rounding':'none','template_rows':[],'use':'assembly_input',
            'surface_components':terms,'basis':'Gross geometry only; not paint billing',
            'remaining':config['remaining']})
    gross=rollup(state,{'plan_sha256':state['plan_sha256'],'rules':candidates})
    if gross['pending_quantities']:raise ValueError('Paint gross source geometry needs review')
    partial=[]
    for mapping,finish_state,finish_rules in finishes:
        if finish_state['plan_sha256']!=state['plan_sha256'] or finish_rules['plan_sha256']!=state['plan_sha256']:
            raise ValueError('Paint finish belongs to another drawing')
        walls=[t for t in source['surface_components'] if t['id']==mapping['room_wall_component_id']]
        if mapping['room_wall_component_id'] in excluded_ids:
            raise ValueError('Finish deduction cannot target an excluded paint surface')
        if len(walls)!=1 or walls[0]['kind']!='perimeter_wall' or walls[0].get('operation','add')!='add':
            raise ValueError('Paint finish requires one sourced gross room wall component')
        wall=walls[0]
        finish=next((r for r in finish_rules['rules'] if r['id']==mapping['finish_rule_id']),None)
        if finish is None:raise ValueError('Paint finish source rule is missing')
        if any(t.get('operation','add')!='add' for t in finish.get('surface_components',[])):
            raise ValueError('Paint finish mapping requires positive finish faces')
        product=mapping.get('product_footprint')
        if product is not None:
            m=finish_state['measurements'][product['measurement_id']]
            tolerance=product['tolerance_ft']
            dimensions=[product['width_ft'],product['depth_ft']]
            if (type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 0<=tolerance<=0.25
                    or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in dimensions)):
                raise ValueError('Product footprint needs positive dimensions and a bounded alignment tolerance')
            actual=[(max(p[i] for p in m['points'])-min(p[i] for p in m['points']))/m['points_per_foot'] for i in (0,1)]
            if any(abs(a-b)>tolerance+1e-7 for a,b in zip(actual,dimensions)):
                raise ValueError('Finish outline no longer matches the selected product footprint; review the product and drawing')
        if 'elevation_fields' in mapping:
            from elevation_finish_allocation import allocate_elevations
            fields=mapping['elevation_fields']
            for operation in ('include','exclude'):
                mapped_ids=[identity for field in fields for identity in field.get(operation,[])]
                if sorted(mapped_ids)!=sorted(finish['footprint'][operation]):
                    raise ValueError('Elevation mappings must partition the source finish field exactly once')
            result=allocate_elevations(state['measurements'][wall['measurement_id']],wall['height_ft'],
                finish_state['measurements'],fields,mapping['room_geometry_sha256'])
            source_quantity=rollup(finish_state,{'plan_sha256':finish_state['plan_sha256'],'rules':[finish]})
            if (source_quantity['pending_quantities'] or not math.isclose(result['excluded_wall_sf'],
                    source_quantity['quantities'][0]['measured_quantity'],abs_tol=1e-8,rel_tol=0)):
                raise ValueError('Mapped elevation finish does not reconcile to the source quantity')
        else:
            result=allocate(state['measurements'][wall['measurement_id']],wall['height_ft'],
                            finish_state['measurements'],finish['surface_components'],mapping['tolerance_ft'])
        partial.append({'room_id':wall['measurement_id'],'source_rule_id':finish['id'],
            'finish_measurement_version':finish_state['version'],
            'finish_geometry_sha256':hashlib.sha256(encode({k:geometry_digest(finish_state['measurements'][k])
                for k in finish['measurement_ids']}).encode()).hexdigest(),
            'result':result})
    combined=combine_room_allocations(partial)
    zones=[]
    for zone,quantity in zip(('house','garage'),gross['quantities']):
        excluded=math.fsum(r['known_finish_exclusion_sf'] for r in combined
                          if (r['room_id']==config['garage_measurement_id'])==(zone=='garage'))
        zones.append({'zone':zone,'gross_wall_and_ceiling_sf':quantity['measured_quantity'],
            'known_wall_finish_exclusion_sf':excluded,
            'remaining_surface_reference_sf':quantity['measured_quantity']-excluded,'final_paint_quantity':None})
    return {'plan_sha256':state['plan_sha256'],'measurement_version':state['version'],
        'geometry_sha256':hashlib.sha256(encode({k:geometry_digest(v) for k,v in state['measurements'].items()}).encode()).hexdigest(),
        'gross_references':gross['quantities'],'partial_finish_allocations':partial,
        'excluded_components':copy.deepcopy(exclusions),
        'combined_room_references':combined,'partial_zone_references':zones,
        'basis':'Gross saved geometry plus separately mapped finish deductions. Partial references only; no paint billing convention inferred.',
        'remaining':config['remaining'],'paint_quantity_certified':False,'final_paint_quantity':None,
        'purchase_quantity':None,'estimate_released':False,'whole_house_total':None}


def from_folder(folder, state):
    config=json.loads((folder/'paint_surface_review.json').read_bytes())
    rules=read_gross_rules(folder,config)
    for exclusion in config.get('excluded_components',[]):
        for source in exclusion['source_files']:
            if hashlib.sha256((folder/source['file']).read_bytes()).hexdigest()!=source['sha256']:
                raise ValueError('Paint exclusion evidence changed; review its scope')
    finishes=[]
    for mapping in config['finish_mappings']:
        child=(folder/mapping['job']).resolve()
        checked_json(child/'measurements.json',mapping['config_sha256'])
        finish_rules=checked_json(child/'quantity_rules.json',mapping['rules_sha256'])
        for source in mapping.get('source_files',[]):
            if hashlib.sha256((child/source['file']).read_bytes()).hexdigest()!=source['sha256']:
                raise ValueError('Paint finish source evidence changed; review its mapping')
        if not (child/'measurement_edits.sqlite3').is_file():
            raise ValueError('Paint finish has no saved measurement history')
        finishes.append((mapping,MeasurementStore(child).read(),finish_rules))
    result=calculate_review(state,rules,config,finishes)
    result['mapping_sha256']=hashlib.sha256(encode(config).encode()).hexdigest()
    return result


def import_references(draft, folder, state):
    config = json.loads((folder/'paint_surface_review.json').read_bytes())
    mapping = config.get('template_reference_rows')
    if mapping is None:
        return draft
    if (not isinstance(mapping, dict) or set(mapping) != {'house','garage'}
            or len(set(mapping.values())) != 2):
        raise ValueError('Paint references require distinct house and garage template rows')
    if draft['plan_sha256'] != state['plan_sha256'] or draft['measurement_version'] != state['version']:
        raise ValueError('Paint references require the current drawing and measurement revision')
    review = from_folder(folder, state)
    return attach_references(draft, review, mapping)


def attach_references(draft, review, mapping):
    result = copy.deepcopy(draft)
    rows = {r['row_id']:r for r in result['rows']}
    for zone in review['partial_zone_references']:
        row = rows.get(mapping[zone['zone']])
        if (row is None or row.get('cost_type') not in ('MATERIAL','LABOR','SUBCONTRACTOR')
                or row.get('completion_status','').startswith('not_applicable')):
            raise ValueError('Paint reference target must be an active cost row')
        identity = 'paint-' + zone['zone'] + '-remaining-surface-reference'
        if any(q['id'] == identity for q in row.get('assembly_inputs',[])):
            raise ValueError('Duplicate paint surface reference')
        row.setdefault('assembly_inputs',[]).append({
            'id':identity, 'label':zone['zone'].title()+' partial paint surface',
            'quantity':zone['remaining_surface_reference_sf'], 'unit':'SF', 'use':'assembly_input',
            'template_rows':[row['excel_row']], 'certified':False, 'order_released':False,
            'basis':f"Gross walls/ceilings {zone['gross_wall_and_ceiling_sf']:.6f} SF less known wall finishes {zone['known_wall_finish_exclusion_sf']:.6f} SF. Partial physical surface only; not floor SF, final paint coverage, gallons or a billing quantity. Existing package cost remains separate.",
            'remaining':copy.deepcopy(review['remaining']),
            'source_review':{k:review[k] for k in ('plan_sha256','measurement_version','geometry_sha256','mapping_sha256')},
        })
    return result
