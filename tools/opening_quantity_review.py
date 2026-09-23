"""Map current, reviewed opening counts to draft estimate rows, without buying products."""
import copy
import hashlib
import json
from pathlib import Path
from company_profile import resolve
from opening_schedule import from_folder
from hardware_quantity_review import apply_hardware_quantities


def default_mapping(folder,template,plan_sha256):
    """Reserve exact template scopes for new jobs; do not approve any opening."""
    folder=Path(folder);specs=[('Windows','Windows','ALLOWANCE','window_assemblies',None,None),
        ('Windows - Labor to Install','Windows','LABOR','window_installation',None,None),
        ('Cleaning - Final window cleaning','Cleaning','SUBCONTRACTOR','window_cleaning',None,None)]
    for height,name_hollow,name_solid,prefix in ((80,'6\'8" Hinged','6\'8" Single',"6'8"),
            (96,'8\'0" Single','8\'0" Single',"8'")):
        for core,name in (('hollow',name_hollow),('solid',name_solid)):
            specs.append((name,prefix+' Doors - '+core.title(),'MATERIAL','ordinary_single_hinged_door',height,core))
    mappings=[];unresolved=[]
    for name,parent,cost_type,kind,height,core in specs:
        matches=[r for r in template['rows'] if r['name']==name and r.get('parent')==parent and r['cost_type']==cost_type]
        if len(matches)!=1 or matches[0]['unit'] not in ('each','EA') or matches[0]['cost_type']!=cost_type:
            unresolved.append({'name':name,'parent':parent,'reason':'Template scope is missing, ambiguous or has an incompatible unit/cost type'})
            continue
        row=matches[0];mapping={k:row[k] for k in ('row_id','name','parent')};mapping['kind']=kind
        if core is not None:mapping.update(core=core,nominal_height_inches=height)
        mappings.append(mapping)
    config={'plan_sha256':plan_sha256,'template_sha256':hashlib.sha256((folder/'template_rows.json').read_bytes()).hexdigest(),
        'reviewer':'Automatic template mapping rule v3; opening interpretation requires source review',
        'basis':'Match exact template name, parent, each-unit basis and cost type. Current reviewed opening roles, configurations and saved policies determine draft quantities.',
        'mapping_method':'exact_template_opening_scopes_v3','mappings':mappings,'unresolved_template_scopes':unresolved}
    intake=folder.parent/'estimate_intake.json'
    hardware=[r for r in template['rows'] if r['name']=='Door knobs' and r['parent']=='Attic doors and Knobs'
        and r['cost_type']=='ALLOWANCE' and r['unit'] in ('EA','each')]
    if len(hardware)==1:
        config['hardware_target']={k:hardware[0][k] for k in ('row_id','name','parent')}
    else:
        config['unresolved_template_scopes'].append({'name':'Door knobs','parent':'Attic doors and Knobs',
            'reason':'Hardware reference target is missing, ambiguous or incompatible'})
    if intake.exists():
        config['installation_policy']={'path':'../estimate_intake.json','sha256':hashlib.sha256(intake.read_bytes()).hexdigest()}
    return config


def window_basis(folder,ref,plan_sha256):
    folder=Path(folder).resolve();path=(folder/ref['path']).resolve()
    if not path.is_relative_to(folder.parent):raise ValueError('Window policy must stay inside the job')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('Window policy intake changed')
    intake=json.loads(raw)
    if intake['plan_sha256']!=plan_sha256:raise ValueError('Window policy belongs to another drawing')
    profile_path=(path.parent/intake['company_profile_snapshot']).resolve()
    if not profile_path.is_relative_to(path.parent):raise ValueError('Window profile must stay inside its job')
    profile_raw=profile_path.read_bytes();profile=json.loads(profile_raw)
    if hashlib.sha256(profile_raw).hexdigest()!=intake['company_profile_sha256']:
        raise ValueError('Window company profile changed')
    if (profile['profile_id'],profile['version'])!=(intake['company_profile_id'],intake['company_profile_version']):
        raise ValueError('Window profile identity differs from intake')
    replay=resolve(profile,intake['project_facts'],intake['project_overrides'])
    if any(replay[k]!=intake[k] for k in ('settings','provenance','resolved_conflicts')):
        raise ValueError('Window policy differs from its saved source decisions')
    key='windows.installation_quantity_basis'
    return {'value':replay['settings'].get(key),'provenance':replay['provenance'].get(key),
        'intake_sha256':ref['sha256'],'company_profile_sha256':intake['company_profile_sha256']}


def apply_quantities(draft,schedule,config,installation_policy=None):
    if config['plan_sha256']!=draft['plan_sha256'] or schedule['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Opening quantities belong to another drawing')
    if schedule['measurement_version']!=draft['measurement_version']:
        raise ValueError('Opening quantities belong to another measurement revision')
    if 'opening_quantity_review' in draft:raise ValueError('Opening quantities already imported')
    if any(not isinstance(config.get(k),str) or not config[k].strip() for k in ('reviewer','basis')):
        raise ValueError('Opening quantity mapping needs reviewer and basis')
    if not isinstance(config.get('mappings'),list) or not config['mappings']:
        raise ValueError('Opening quantity mappings required')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']}
    if len(rows)!=len(result['rows']):raise ValueError('Template row identities must be unique')
    openings=schedule['openings'];ids=[o['opening_id'] for o in openings]
    if len(set(ids))!=len(ids):raise ValueError('Opening identities must be unique')
    current=(bool(openings) and not schedule['unresolved_opening_ids'] and not schedule['stale_or_missing_label_ids']
        and all(o['review_status'] in ('current_source_review','native_symbol_inference') for o in openings))
    ordinary=[o for o in openings if o['role']=='interior_door']
    core_review=schedule.get('door_core_review');cores={o['opening_id']:o for o in core_review['openings']} if core_review else {}
    doors_ready=(current and bool(ordinary) and all(o.get('door_configuration')=='single_hinged'
        and o.get('printed_nominal_size') and cores.get(o['opening_id'],{}).get('core') in ('solid','hollow') for o in ordinary))
    claimed=set();groups=set();summaries=[]
    for mapping in config['mappings']:
        row=rows[mapping['row_id']];kind=mapping['kind']
        if kind not in ('window_assemblies','window_installation','window_cleaning','ordinary_single_hinged_door'):
            raise ValueError('Unsupported opening quantity kind')
        if (row['row_id'] in claimed or row.get('unit') not in ('each','EA')
                or row.get('completion_status','').startswith('not_applicable')
                or row.get('covered_by_package') or row.get('cost_owner_row_id')
                or row.get('draft_quantity') is not None or row.get('assembly_inputs') or row.get('quantity_sources')
                or any(row.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
            raise ValueError('Opening target is excluded, assigned, priced or not an each-unit row')
        if any(row.get(k)!=mapping[k] for k in ('name','parent')):raise ValueError('Opening template scope changed')
        if kind=='window_assemblies':
            if row['cost_type']!='ALLOWANCE':raise ValueError('Window assemblies must own a material allowance row')
            group=(kind,);selected=[o for o in openings if o['role']=='window']
            quantity=len(selected) if current and selected else None
            policy=None;reason='Window assembly enumeration needs current source review'
            quantity_basis='complete window assembly'
        elif kind=='window_installation':
            if row['cost_type']!='LABOR':raise ValueError('Window installation must own a labor row')
            group=(kind,);selected=[o for o in openings if o['role']=='window']
            ready=current and installation_policy and installation_policy['value']=='individual_window_unit'
            quantity=schedule['enumerated_window_unit_count'] if ready else None
            policy=installation_policy;reason='Window enumeration or saved individual-unit installation policy needs review'
            quantity_basis='individual window unit'
        elif kind=='window_cleaning':
            if row['cost_type']!='SUBCONTRACTOR':raise ValueError('Window cleaning must own a subcontractor row')
            group=(kind,);selected=[o for o in openings if o['role']=='window']
            quantity=schedule['enumerated_window_unit_count'] if current and selected else None
            policy=None;reason='Window cleaning enumeration needs current source review and known component counts'
            quantity_basis='individual window unit; interior/exterior faces counted together'
        else:
            height=mapping['nominal_height_inches'];core=mapping['core']
            if row['cost_type']!='MATERIAL' or type(height) is not int or height<=0 or core not in ('solid','hollow'):
                raise ValueError('Ordinary door mapping needs a material row, nominal height and core')
            group=(kind,height,core)
            selected=[o for o in ordinary if (o.get('printed_nominal_size') or {}).get('height_inches')==height
                and cores.get(o['opening_id'],{}).get('core')==core]
            quantity=len(selected) if doors_ready else None
            policy=core_review;reason='Ordinary door role, single-hinged configuration, nominal height or core policy needs review'
            quantity_basis='ordinary single-hinged door'
        if group in groups:raise ValueError('Opening scope would be counted in multiple template rows')
        groups.add(group);claimed.add(row['row_id'])
        source={'id':'opening-quantity-'+row['row_id'],'kind':kind,'label':row['name'],'unit':'EA','use':'direct',
            'quantity':quantity,'template_rows':[row['excel_row']],'opening_ids':[o['opening_id'] for o in selected],
            'opening_sources':{o['opening_id']:o['source_sha256'] for o in selected},
            'quantity_basis':quantity_basis,'opening_details':[{k:copy.deepcopy(o.get(k)) for k in
                ('opening_id','page','tag','location','printed_nominal_size','window_component_count','source_sha256','review_status','native_interpretation')}
                for o in selected],
            'basis':config['basis'],'reviewer':config['reviewer'],'opening_review_sha256':schedule['review_sha256'],
            'policy_source':copy.deepcopy(policy),'certified':False,'coverage_certified':False,'purchase_released':False,
            'remaining':['Complete opening coverage and product specifications; current pricing and purchase approval remain separate.']}
        if kind=='window_cleaning':
            source['remaining'].append('Confirm cleaning contractor billing units, screens, frames and any glazed doors or other scope. This plan count does not transfer historical invoice quantities or prices.')
        inferred=[o['opening_id'] for o in (ordinary if kind=='ordinary_single_hinged_door' else selected)
            if o['review_status']=='native_symbol_inference' or o.get('room_assignment_requires_review')]
        if inferred:
            source['inferred_opening_ids']=inferred
            source['interpretation_requires_review']=True
            source['basis']='Current native opening/room estimating interpretation plus the saved company policy; verify against the plan.'
        if quantity is None:
            result.setdefault('pending_quantities',[]).append({**source,'reason':reason})
        else:
            row['draft_quantity']=quantity;row.setdefault('quantity_sources',[]).append(source)
            result['mapped_quantity_rows']+=1
        summaries.append({'row_id':row['row_id'],'kind':kind,'quantity':quantity,'opening_ids':source['opening_ids'],
            'status':'enumerated_draft_count' if quantity is not None else 'withheld_pending_review'})
    mapped_ids={identity for s in summaries if s['quantity'] is not None for identity in s['opening_ids']}
    unmapped=[]
    for opening in openings:
        if opening['opening_id'] in mapped_ids or opening['role']=='open_passage':continue
        reviewed=opening['review_status'] in ('current_source_review','native_symbol_inference')
        unmapped.append({'opening_id':opening['opening_id'],'page':opening.get('page'),'tag':opening.get('tag'),
            'location':opening.get('location') if reviewed else None,'role':opening['role'] if reviewed else None,
            'printed_nominal_size':copy.deepcopy(opening.get('printed_nominal_size')),
            'door_configuration':opening.get('door_configuration') if reviewed else None,
            'drawn_panel_count':opening.get('drawn_panel_count') if reviewed else None,
            'source_sha256':opening['source_sha256'],
            'reference_assembly_count':1 if reviewed and opening['role'] is not None else None,
            'review_status':opening['review_status'],
            'interpretation_requires_review':opening['review_status']=='native_symbol_inference' or bool(opening.get('room_assignment_requires_review')),
            'purchase_quantity':None,'reason':('Current source enumeration needs review before template assignment'
                if not current else 'No resolved template quantity for this opening; reconcile configuration, dimensions, core and assembly billing basis')})
    result['opening_quantity_review']={'mappings':summaries,'review_sha256':schedule['review_sha256'],
        'unlocated_opening_tags':copy.deepcopy(schedule.get('unlocated_opening_tags',[])),
        'mapping_sha256':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),
        'unmapped_opening_ids':[o['opening_id'] for o in openings if o['opening_id'] not in mapped_ids and o['role']!='open_passage'],
        'unmapped_openings':unmapped,
        'stale_or_missing_label_ids':schedule['stale_or_missing_label_ids'],
        'coverage_certified':False,'purchase_released':False,'limitations':schedule['limitations']}
    if config.get('hardware_target'):
        result=apply_hardware_quantities(result,schedule,config['hardware_target'])
    return result


def import_quantities(draft,state,config,folder):
    folder=Path(folder)
    if hashlib.sha256((folder/'template_rows.json').read_bytes()).hexdigest()!=config['template_sha256']:
        raise ValueError('Opening quantity template source changed')
    policy=window_basis(folder,config['installation_policy'],state['plan_sha256']) if config.get('installation_policy') and any(
        m['kind']=='window_installation' for m in config['mappings']) else None
    return apply_quantities(draft,from_folder(folder,state),config,policy)
