"""Build an unsent, source-bound opening quote scope from the current schedule."""
import copy
import hashlib
import json
from pathlib import Path
from opening_schedule import from_folder as opening_schedule
from opening_quantity_review import window_basis


def build_scope(schedule,installation_policy=None):
    openings=schedule['openings'];ids=[o['opening_id'] for o in openings]
    if not schedule.get('plan_sha256') or type(schedule.get('measurement_version')) is not int or schedule['measurement_version']<1:
        raise ValueError('Opening quote scope needs a drawing and positive measurement revision')
    if len(ids)!=len(set(ids)):raise ValueError('Unique opening identities required')
    cores={o['opening_id']:o for o in (schedule.get('door_core_review') or {}).get('openings',[])}
    hardware_specs={o['opening_id']:o for o in (schedule.get('door_hardware_review') or {}).get('openings',[])}
    records=[];items=[];unresolved=[];passages=[];hardware=[]
    for opening in openings:
        identity=opening['opening_id'];current=opening['review_status'] in ('current_source_review','native_symbol_inference')
        role=opening['role'] if current else None
        if role=='open_passage':passages.append(identity);continue
        core=cores.get(identity,{}).get('core') if current else None
        requirements=['Manufacturer/model and product schedule', 'Manufacturer rough opening and field verification']
        if role=='window':
            requirements+=['Frame material, finish, glazing and performance ratings',
                'Screens, mulling/accessories and installation/flashing inclusions']
        else:
            requirements+=['Material/core, finish, jamb and handing',
                'Slab/panel versus complete assembly purchase basis; hinges/track/frame and hardware inclusions']
        problems=[]
        if opening['review_status']=='native_symbol_inference':problems.append('Automatic opening interpretation requires verification against the plan')
        if opening.get('room_assignment_requires_review'):problems.append('Automatic served-room assignment requires verification against the plan')
        if role is None:problems.append('Opening role or source association needs review')
        nominal=opening.get('printed_nominal_size')
        if not nominal:problems.append('Nominal dimensions need source review')
        configuration=opening.get('door_configuration') if current else None
        panel_conflict=configuration=='single_hinged' and opening.get('drawn_panel_count') not in (None,1)
        if panel_conflict:problems.append('Single-hinged operation conflicts with the drawn panel count')
        components=opening.get('window_component_count') if role=='window' else None
        if role=='window' and components is None:problems.append('Individual window count needs source review')
        if role=='window' and (installation_policy or {}).get('value')!='individual_window_unit':
            problems.append('Window installation billing basis is unconfirmed')
        if role and role!='window' and not configuration:problems.append('Door operation/configuration needs source review')
        quantity=1 if current and role else None
        location=opening.get('location') if current else None
        record={'opening_id':identity,'location':location,'role':role,'printed_tag':opening['tag'],
            'plan_pdf_page':opening['page'],'source_sha256':opening['source_sha256'],
            'printed_nominal_size':copy.deepcopy(nominal),'product_rough_opening':None,
            'door_configuration':configuration,'drawn_panel_count':opening.get('drawn_panel_count') if current else None,
            'core':core,'core_basis':copy.deepcopy(cores.get(identity)) if current else None,
            'assembly_count':quantity,'individual_window_units':components,
            'purchase_quantity':None,'supplier_requirements':requirements,'unresolved':problems}
        if opening['review_status']=='native_symbol_inference':
            record['automatic_interpretation']=copy.deepcopy(opening['native_interpretation'])
        if opening.get('room_assignment_requires_review'):
            record['automatic_room_assignment']=copy.deepcopy(opening['room_association'])
        records.append(record)
        if problems:unresolved.append(identity)
        name=location or identity
        if role in ('window','exterior_door'):
            items.append({'id':identity+':exterior-trim',
                'label':name+' — identify exterior trim material and installation inclusion, or name the separate trade and quote exclusions',
                'opening_id':identity,'work':'exterior_trim_scope_confirmation',
                'reference_quantity':quantity,'reference_unit':'complete opening surround; not individual panels or window units',
                'purchase_quantity':None})
        if role!='window':
            ordinary=role=='interior_door' and configuration=='single_hinged'
            known=role is not None and configuration is not None and not panel_conflict
            hardware_spec=hardware_specs.get(identity,{}) if known else {}
            function=hardware_spec.get('hardware_function')
            hardware.append({'opening_id':identity,'location':location,'configuration':configuration,
                'ordinary_hinged_set_reference':(1 if ordinary else 0) if known else None,
                'hardware_function':function,'hardware_policy_source':copy.deepcopy(hardware_spec) or None,'purchase_quantity':None,
                'basis':('Opening type or panel count requires source review before assigning hardware.' if not known else
                    'Saved hardware function: '+function+'. Confirm compatible product, required sets and package inclusions.' if function else
                    'One ordinary hinged set reference; privacy, passage and product remain unconfirmed.' if ordinary else
                    'Specify compatible recessed pulls, latches, tracks and included hardware for this complete opening; panel count is not a hardware count.'
                    if role=='special_interior_door' else
                    'Reconcile handleset, active/inactive leaves, locks and supplied hardware within the exterior-door package.'
                    if role=='exterior_door' else 'Opening type requires source review before assigning hardware.')})
            items.append({'id':identity+':hardware','label':name+' — identify included hardware and separately quote exclusions only',
                'opening_id':identity,'work':'hardware_scope_confirmation',
                'reference_quantity':None,'reference_unit':'hardware package; configuration and inclusions pending',
                'purchase_quantity':None})
        for work in ('supply','installation'):
            window_install=role=='window' and work=='installation'
            reference=(components if (installation_policy or {}).get('value')=='individual_window_unit' else None) if window_install else quantity
            items.append({'id':identity+':'+work,'label':name+' — '+work,
                'opening_id':identity,'work':work,'reference_assembly_count':quantity,
                'reference_quantity':reference,'reference_unit':'individual window unit' if window_install else 'complete opening assembly',
                'unit_basis':'Identify included panels, accessories and labor; reference counts are not purchase authorization',
                'individual_window_units':components,'purchase_quantity':None})
    for label in schedule['stale_or_missing_label_ids']:
        identity='opening-'+label.removeprefix('printed-tag-')
        if identity in ids:raise ValueError('Missing opening label is also in the current schedule')
        unresolved.append(identity)
        items.append({'id':identity+':source-review','label':'Previously reviewed opening missing from current geometry: '+label,
            'opening_id':identity,'work':'source_review','reference_assembly_count':None,'purchase_quantity':None})
    for opening in schedule.get('unlocated_opening_tags',[]):
        identity=opening['opening_id']
        if identity in ids or identity in unresolved:raise ValueError('Unlocated opening is also in the current or missing schedule')
        unresolved.append(identity)
        items.append({'id':identity+':source-review',
            'label':f"Locate and reconcile {opening['tag']} on PDF page {opening['page']} before confirming supply and installation scope",
            'opening_id':identity,'work':'source_review','reference_assembly_count':None,'purchase_quantity':None})
    for identity,label in (
            ('hardware-accessories','Identify hardware, tracks, frames, screens, flashing and accessories included in each assembly; price exclusions separately'),
            ('delivery','Identify delivery, unloading and any separate delivery charge'),
            ('tax','Identify sales tax and whether quoted prices include it'),
            ('field-verification','Verify dimensions, handing, product schedule and all opening scope against the plans before ordering')):
        items.append({'id':identity,'label':label,'work':'scope_confirmation','purchase_quantity':None})
    return {'plan_sha256':schedule['plan_sha256'],'measurement_version':schedule['measurement_version'],
        'opening_review_sha256':schedule['review_sha256'],
        'window_installation_policy':copy.deepcopy(installation_policy),
        'opening_schedule_sha256':hashlib.sha256(json.dumps(schedule,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        'title':'Windows and doors — draft supply and installation quote scope','status':'unsent_draft',
        'openings':records,'items':items,'excluded_open_passage_ids':passages,
        'unlocated_opening_tags':copy.deepcopy(schedule.get('unlocated_opening_tags',[])),
        'unresolved_opening_ids':sorted(set(unresolved)|{o['opening_id'] for o in schedule.get('unlocated_opening_tags',[])}),
        'hardware_references':hardware,
        'enumerated_ordinary_hinged_set_reference':(sum(r['ordinary_hinged_set_reference'] for r in hardware)
            if openings and not schedule['stale_or_missing_label_ids']
            and all(r['ordinary_hinged_set_reference'] is not None for r in hardware) else None),
        'source_enumeration_current':bool(records) and not unresolved,
        'scope_coverage_certified':False,'ready_to_order':False,'sent':False,
        'instructions':['Quote each listed assembly and identify supply and installation separately, or list exact scope IDs covered by a package total.',
            'Show brand/model, nominal size, rough opening, finish, glazing, handing, hardware and accessory inclusions. Resolve unspecified selections as explicit options.',
            'Drawn panels are reference counts, not separately ordered slabs. Do not multiply an assembly price by its panel count.',
            'Identify hardware inclusion per opening. Hardware scope responses do not add another charge when supply or installation already includes it. Door core does not determine privacy or passage function.',
            'For each window and exterior door, identify exterior trim material, finish, installation and package owner. Distinguish factory brickmold from additional site-applied trim. Confirm included, excluded or not applicable with source evidence; do not add a second charge for included work.',
            'For windows, identify both opening assemblies and individual units; J&J installation billing basis must be confirmed from the saved job policy.',
            'Identify omissions and plan discrepancies. This enumerated schedule does not certify full-plan coverage.',
            'State quote date, lead time, availability and validity or confirmation that a dated rate is still honored.'],
        'limitations':copy.deepcopy(schedule['limitations'])}


def attach_cross_view(scope,review):
    """Carry unresolved elevation evidence into bids without adding window counts."""
    if review is None:
        scope['window_cross_view_review']=None
        return scope
    if review['plan_sha256']!=scope['plan_sha256']:
        raise ValueError('Cross-view window review belongs to another drawing')
    scope['window_cross_view_review']=copy.deepcopy(review)
    for candidate in review['unrepresented_elevation_tags']:
        fingerprint=hashlib.sha256(json.dumps(candidate,sort_keys=True,allow_nan=False).encode()).hexdigest()[:16]
        identity='elevation-window-'+fingerprint
        scope['unresolved_opening_ids'].append(identity)
        scope['items'].append({'id':identity+':source-review','work':'cross_view_window_confirmation',
            'label':f"Window tag {candidate['tag']} on PDF page {candidate['page']} is not represented by a floor-plan tag. Confirm whether it is a separate window, an alternate/detail view, or an already listed assembly; identify the matching opening ID and supply/installation scope before adding any quantity.",
            'source_candidate':copy.deepcopy(candidate),'reference_quantity':None,'purchase_quantity':None})
        scope['source_enumeration_current']=False
    return scope


def from_folder(folder,state):
    folder=Path(folder);path=folder/'opening_quantity_review.json';policy=None
    if path.exists():
        config=json.loads(path.read_bytes())
        if config.get('installation_policy'):
            policy=window_basis(folder,config['installation_policy'],state['plan_sha256'])
    from window_cross_view_review import from_folder as cross_view_review
    return attach_cross_view(build_scope(opening_schedule(folder,state),policy),cross_view_review(folder))


def render_markdown(scope):
    def cell(value):return str(value if value is not None else 'Unconfirmed').replace('|','\\|').replace('\n',' ')
    installation=('Individual window unit' if (scope.get('window_installation_policy') or {}).get('value')=='individual_window_unit'
        else 'Unconfirmed; identify the proposed billing basis')
    lines=['# '+scope['title'],'','**Unsent draft — product selections and complete scope remain subject to review.**','',
        f"Drawing SHA-256: `{scope['plan_sha256']}`  ",f"Measurement revision: {scope['measurement_version']}",'',
        'Window installation billing basis: **'+installation+'**.','',
        '| Opening / location | PDF page | Nominal tag / width × height | Configuration | Reference assemblies | Drawn panels | Window units | Core |',
        '| --- | ---: | --- | --- | ---: | ---: | ---: | --- |']
    for row in scope['openings']:
        size=row['printed_nominal_size'];tag=row['printed_tag']
        if size:tag+=f" / {size['width_inches']} × {size['height_inches']} in"
        lines.append('| '+' | '.join(map(cell,[row['opening_id']+' / '+(row['location'] or 'Needs source review'),
            row['plan_pdf_page'],tag,(row['door_configuration'] or row['role'] or 'Unconfirmed').replace('_',' ')+(' (inferred)' if row.get('automatic_interpretation') else ' (room inferred)' if row.get('automatic_room_assignment') else ''),row['assembly_count'],
            row['drawn_panel_count'] if row['role']!='window' else 'Not applicable',
            row['individual_window_units'] if row['role']=='window' else 'Not applicable',
            row['core'] if row['role']!='window' else 'Not applicable']))+' |')
    lines+=['','## Door hardware references','',
        'Ordinary hinged set references among the enumerated openings: '+cell(scope['enumerated_ordinary_hinged_set_reference'])+'. This is not a whole-house purchase quantity.',
        'Saved hardware functions appear where source-reviewed room/type associations support them. Products and package inclusions remain unconfirmed.','',
        '| Opening / location | Configuration | Ordinary hinged set reference | Hardware function | Remaining scope |',
        '| --- | --- | ---: | --- | --- |']
    for row in scope['hardware_references']:
        lines.append('| '+' | '.join(map(cell,[row['opening_id']+' / '+(row['location'] or 'Needs source review'),
            row['configuration'],row['ordinary_hinged_set_reference'],row['hardware_function'],row['basis']]))+' |')
    lines+=['','## Quote instructions','']+['- '+s for s in scope['instructions']]
    lines+=['','## Required scope responses','','Mark each ID included, excluded, allowance or unknown and identify the quote page/line.','']
    lines+=['- `'+s['id']+'`: '+s['label'] for s in scope['items']]
    lines+=['','## Unresolved source associations','',', '.join(scope['unresolved_opening_ids']) or 'None among the enumerated openings.',
        '',f"Open passages excluded from door and hardware quantities: {len(scope['excluded_open_passage_ids'])}.",'',
        'Product specifications, rough openings and current pricing remain unconfirmed. No purchase quantities or order approval are issued.','']
    if scope.get('unlocated_opening_tags'):
        lines+=['## Opening tags needing a wall location','']
        lines+=['- '+cell(o['opening_id'])+' — '+cell(o['tag'])+' on PDF page '+str(o['page'])+'. '+o['reason']
            for o in scope['unlocated_opening_tags']]
    return '\n'.join(lines)
