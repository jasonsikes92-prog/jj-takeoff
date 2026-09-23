"""Attach an evidence-checked partial material study after normal estimate pricing."""
import copy
import hashlib
import json
import math
from pathlib import Path
from historical_material_rates import checked_catalog
from component_material_allowances import calculate, public_allowance_catalog


def reference_kit_purchases(study, components, draft, references):
    """Link duplicate count references to their existing charge, without adding money."""
    owned=[]
    for mapping in references:
        identity=mapping['component_id']
        component=next((c for c in components if c['id']==identity),None)
        owners=[r for r in draft.get('additional_cost_rows',[]) if r['row_id']==mapping['owner_row_id']]
        reason='Separate kit purchase or current framing count is missing'
        owner=owners[0] if len(owners)==1 else None
        source=None
        if component is not None and owner is not None:
            sources=[q for q in owner.get('quantity_sources',[]) if q.get('kind')=='reviewed_kit_purchase']
            source=sources[0] if len(sources)==1 else None
            count=source.get('count_reference',{}) if source else {}
            quantities=[component.get('quantity'),owner.get('draft_quantity'),
                        source.get('quantity') if source else None,count.get('quantity')]
            valid_counts=all(type(v) in (int,float) and math.isfinite(v) and v>=0 and int(v)==v for v in quantities)
            reason='Separate kit purchase count, units or source no longer match the framing input'
            if (valid_counts and len(set(quantities))==1 and component.get('unit')=='EA'
                    and owner.get('unit')=='kit' and owner.get('pricing_role')=='cost_line'
                    and owner.get('cost_type')=='MATERIAL' and not owner.get('covered_by_package')
                    and not owner.get('completion_status','').startswith('not_applicable')
                    and source and source.get('unit')=='kit' and count.get('unit')=='EA'
                    and owner.get('source_assembly_input_id')==count.get('id')):
                locations=component.get('component_ids',[]);other=count.get('measurement_ids',[])
                reason='Separate kit purchase locations no longer match the framing input'
                if (len(locations)==len(set(locations))==quantities[0]
                        and len(other)==len(set(other))==quantities[0] and set(locations)==set(other)):
                    owned.append({'component_id':identity,'label':component['label'],
                        'quantity':component['quantity'],'quantity_unit':component['unit'],
                        'measurement_ids':sorted(locations),'owner_row_id':owner['row_id'],
                        'owner_unit':owner['unit'],'owner_line_cost':owner.get('line_cost'),
                        'owner_price_status':owner.get('price_status','Price unresolved'),
                        'current_price_certified':owner.get('current_price_certified',False),
                        'basis':mapping['basis'],'quantity_certified_for_order':False,
                        'included_in_framing_subtotal':False})
                    study['unpriced_components']=[c for c in study['unpriced_components'] if c['component_id']!=identity]
                    continue
        unresolved=next((c for c in study['unpriced_components'] if c['component_id']==identity),None)
        if unresolved is None:
            unresolved={'component_id':identity};study['unpriced_components'].append(unresolved)
        unresolved['reason']=reason
    study['separately_owned_components']=owned


def reference_plate_measurement(study, components, review, source_job, rule_id):
    """Retain wall geometry as a calculation input, not a second material purchase."""
    study['measurement_references']=[]
    source=next((c for c in components if c['id']==rule_id),None)
    if source is None:return
    runs=[r for r in review['runs'] if r['source_kind']=='editable_measurement']
    ids=[r['id'] for r in runs];actual_ids=source.get('measurement_ids',[])
    linked=source.get('linked_review',{})
    expected=math.fsum(r['length_inches'] for r in runs)/12
    quantities=[source.get('quantity'),source.get('measured_quantity')]
    if (source.get('unit')!='LF' or source.get('use')!='assembly_input'
            or len(ids)!=len(set(ids)) or not ids
            or len(actual_ids)!=len(set(actual_ids)) or set(ids)!=set(actual_ids)
            or Path(linked.get('job','')).resolve()!=Path(source_job).resolve()
            or linked.get('measurement_version')!=review['source_version']
            or any(type(q) not in (int,float) or not math.isfinite(q)
                   or not math.isclose(q,expected,rel_tol=0,abs_tol=1e-7) for q in quantities)):
        return
    owners=[c for c in components if c['id'].startswith('framing-stock-plates-')]
    boards={b['id']:b for b in review['boards']};board_ids=set(boards)
    actual_boards=[i for c in owners for i in c.get('component_ids',[])]
    if (not owners or len(actual_boards)!=len(set(actual_boards)) or set(actual_boards)!=board_ids
            or any(c.get('unit')!='stick' or c.get('quantity')!=len(c.get('component_ids',[]))
                   or c.get('source_snapshot',{}).get('mapping_sha256')!=review['mapping_sha256']
                   or any(boards[i]['sku']!=c.get('sku') or boards[i]['length_ft']!=c.get('stock_length_ft')
                          for i in c.get('component_ids',[])) for c in owners)):
        return
    if any(rule_id in [c['component_id'],*c.get('source_component_ids',[])]
           for c in study['priced_components']+study.get('separately_owned_components',[])):
        raise ValueError('Raw plate measurement cannot also be a material purchase')
    study['measurement_references']=[{'component_id':rule_id,'label':source['label'],
        'quantity':source['quantity'],'unit':'LF','measurement_ids':sorted(ids),
        'derived_purchase_component_ids':sorted(c['id'] for c in owners),
        'source_job':str(Path(source_job).resolve()),'source_version':review['source_version'],
        'source_geometry_sha256':{i:review['source_geometry_sha256'][i] for i in ids},
        'included_in_material_subtotal':False,'is_purchase':False,
        'basis':'Wall length drives the separate plate stock quantities; do not add another LF material charge.',
        'remaining':source.get('remaining',[])+review.get('remaining',[])}]
    study['unpriced_components']=[c for c in study['unpriced_components'] if c['component_id']!=rule_id]


def import_allowances(draft, folder, config, as_of):
    folder=Path(folder).resolve()
    if 'framing_material_allowance_review' in draft:raise ValueError('Framing material allowances already imported')
    if draft['plan_sha256']!=config['plan_sha256']:raise ValueError('Framing material mapping belongs to another drawing')
    checked=[];loaded={}
    for key in ['ledger','authorization']:
        ref=config[key];path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Framing price evidence must stay inside its job')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('Framing price evidence changed: '+key)
        checked.append((path,raw));loaded[key]=json.loads(raw)
    if loaded['authorization'].get('answer')!='Use saved rates as dated allowances':
        raise ValueError('Dated material pricing requires saved owner authorization')
    root=(folder/config['pdf_directory']).resolve()
    if not root.is_relative_to(folder):raise ValueError('Framing invoice originals must stay inside the job')
    catalog=checked_catalog(checked[0][0],root,as_of=as_of)
    public_records=[]
    for ref in config.get('public_rate_sources',[]):
        path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Public framing price source must stay inside its job')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('Public framing price evidence changed')
        checked.append((path,raw));public_records.append(json.loads(raw))
    catalog=public_allowance_catalog(catalog,public_records,as_of)
    matches=[r for r in draft['rows'] if str(r['excel_row'])==str(config['template_row'])]
    if len(matches)!=1:raise ValueError('One framing allowance owner required')
    row=matches[0]
    if row.get('line_cost') is not None or row.get('covered_by_package') or row['cost_type']!='MATERIAL':
        raise ValueError('Partial framing allowances must not duplicate a priced package')
    references=config.get('kit_purchase_references',[])
    if len({r['component_id'] for r in references})!=len(references):
        raise ValueError('A framing component may have only one purchase reference')
    if {r['component_id'] for r in references} & {r['component_id'] for r in config['mappings']}:
        raise ValueError('A component cannot have both a framing rate and a separate purchase reference')
    if any(not r.get('basis') or not r.get('owner_row_id') for r in references):
        raise ValueError('A separate purchase reference needs its cost owner and scope basis')
    study=calculate(row.get('assembly_inputs',[]),config['mappings'],catalog)
    reference_kit_purchases(study,row.get('assembly_inputs',[]),draft,references)
    plate_config=folder/'plate_stock_review.json'
    if draft.get('framing_stock_review',{}).get('sources',{}).get('plates') and plate_config.exists():
        from plate_stock_review import from_folder as plate_stock
        raw=plate_config.read_bytes();plate_settings=json.loads(raw)
        checked.append((plate_config,raw));plates=plate_stock(folder)
        saved=draft['framing_stock_review']['sources']['plates']
        if any(plates.get(k)!=v for k,v in saved.items()):
            raise ValueError('Plate stock and material review changed during calculation; retry')
        reference_plate_measurement(study,row.get('assembly_inputs',[]),plates,
            folder/plate_settings['source_job'],plate_settings['quantity_rule_id'])
    study.update(as_of=as_of,ledger_sha256=catalog['ledger_sha256'],
        source_pdf_hashes=catalog['source_pdf_hashes'],authorization_sha256=config['authorization']['sha256'],
        excluded_scope=config['excluded_scope'],
        quantity_limits={key:value.get('remaining',[]) for key,value in draft.get('framing_stock_review',{}).get('sources',{}).items()},
        wall_sheathing_limits=draft.get('wall_panel_review',{}).get('remaining',[]),
        pending_quantity_issues=[copy.deepcopy(p) for p in draft.get('pending_quantities',[])
                                if str(config['template_row']) in p.get('template_rows',[])])
    if (folder/'stud_stock_review.json').exists():
        from stud_stock_review import from_folder
        from stud_material_allowances import apply
        stock=from_folder(folder)
        if stock['plan_sha256']!=draft['plan_sha256']:
            raise ValueError('Stud stock and estimate belong to different drawings')
        current=draft.get('wall_component_review',{}).get('measurement_dependencies',[])
        if {r['job']:r['version'] for r in current}!={r['job']:r['version'] for r in stock['measurement_dependencies']}:
            raise ValueError('Stud stock and estimate measurement versions differ; retry')
        apply(study,row.get('assembly_inputs',[]),stock)
        if study['stud_stock_mapping']['applied']:
            study['excluded_scope']=[s.replace('Studs,','Jacks, cripples and other unquantified stud scope,')
                                     for s in study['excluded_scope']]
            if 'wall-component-jack_studs' in study['stud_stock_mapping']['included_component_ids']:
                study['excluded_scope']=[s.replace('Jacks,','Jack cut details,') for s in study['excluded_scope']]
    if any(path.read_bytes()!=raw for path,raw in checked):raise ValueError('Framing price evidence changed during calculation')
    result=copy.deepcopy(draft);result['framing_material_allowance_review']=study
    return result
