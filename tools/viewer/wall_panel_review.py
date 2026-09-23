"""Bind wall-sheet calculations to current editable exterior and elevation jobs."""
import copy
import hashlib
import json
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
from plate_stock_review import outline_runs
from wall_sheathing_layout import calculate
from owner_height_selection import select as select_height


def from_folder(folder):
    folder=Path(folder).resolve();path=folder/'wall_panel_review.json';raw=path.read_bytes();config=json.loads(raw)
    own=MeasurementStore(folder).read();checked=[];states={};stores={};originals={}
    ref=config['basis'];source=(folder/ref['path']).resolve()
    if not source.is_relative_to(folder):raise ValueError('Wall sheathing evidence must stay inside its job')
    evidence_raw=source.read_bytes()
    if hashlib.sha256(evidence_raw).hexdigest()!=ref['sha256']:raise ValueError('Wall sheathing basis changed')
    basis=json.loads(evidence_raw);checked.append((source,evidence_raw))
    if basis['plan_sha256']!=own['plan_sha256']:raise ValueError('Wall sheathing basis belongs to another drawing')
    selection=None
    if config.get('height_selection'):
        ref=config['height_selection'];source=(folder/ref['path']).resolve()
        if not source.is_relative_to(folder):raise ValueError('Wall height evidence must stay inside its job')
        data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Wall height evidence changed')
        checked.append((source,data))
        selection=select_height(json.loads(data),own['plan_sha256'],basis['height_scenarios'])
        if {s['wall_height_inches'] for s in basis['height_scenarios']}!={basis['plate_height_inches'],basis['precut_plate_height_inches']}:
            raise ValueError('Wall height scenario mapping differs from the sheathing dimensions')
    for key in ('exterior','upper'):
        link=config[key];job=(folder/link['job']).resolve()
        if not job.is_relative_to(folder.parent) or job==folder:raise ValueError('Wall sheathing source must be a neighboring job')
        source=job/'measurements.json';data=source.read_bytes()
        if hashlib.sha256(data).hexdigest()!=link['config_sha256']:raise ValueError('Wall sheathing measurement configuration changed')
        checked.append((source,data));originals[key]={m['id']:m for m in json.loads(data)['measurements']}
        stores[key]=MeasurementStore(job);states[key]=stores[key].read()
        if states[key]['plan_sha256']!=own['plan_sha256']:raise ValueError('Wall sheathing sources belong to different drawings')
    outline=states['exterior']['measurements'][config['exterior']['measurement_id']]
    old=originals['exterior'][config['exterior']['measurement_id']]
    if outline['page']!=old['page'] or outline['points_per_foot']!=old['points_per_foot']:
        raise ValueError('Exterior wall sheet or scale changed')
    outline_runs(outline,old,basis['wall_ids'],'exterior')
    used={k for face in basis['upper_faces'] for k in face['measurement_ids']}
    measurements={k:states['upper']['measurements'][k] for k in used}
    for key,m in measurements.items():
        old=originals['upper'][key]
        if m['page']!=old['page'] or m['kind']!=old['kind'] or m['points_per_foot']!=old['points_per_foot']:
            raise ValueError('Upper sheathing sheet, kind or scale changed')
        if m['kind']=='length':
            a,b=m['points'];c,d=old['points'];axis=0 if abs(c[1]-d[1])<1e-6 else 1
            if abs(a[1-axis]-b[1-axis])>=1e-6 or (b[axis]-a[axis])*(d[axis]-c[axis])<=0:
                raise ValueError('Chase dimension axis changed')
    result=calculate(outline,measurements,basis,selected_wall_height_inches=selection['wall_height_inches'] if selection else None)
    if selection:
        result.update(selected_scenario=selection['id'],height_selection_source=config['height_selection'])
    if any(stores[k].read()['version']!=states[k]['version'] for k in stores):
        raise ValueError('Wall sheathing measurements changed during calculation; retry')
    if path.read_bytes()!=raw or any(p.read_bytes()!=data for p,data in checked):
        raise ValueError('Wall sheathing source references changed during calculation')
    return {**result,'plan_sha256':own['plan_sha256'],
        'measurement_versions':{k:states[k]['version'] for k in states},
        'source_geometry_sha256':{'exterior':geometry_digest(outline),'upper':{k:geometry_digest(m) for k,m in measurements.items()}},
        'mapping_sha256':hashlib.sha256(raw).hexdigest(),'basis_sha256':config['basis']['sha256']}


def import_wall_panels(draft, folder, template_row, mapping_sha256):
    """Attach one combined cut candidate; alternatives never become additive quantities."""
    if 'wall_panel_review' in draft:
        raise ValueError('Wall panels already imported')
    matches=[r for r in draft['rows'] if str(r['excel_row'])==str(template_row)]
    if len(matches)!=1:raise ValueError('One wall panel template owner required')
    row=matches[0]
    if (row['cost_type']!='MATERIAL' or row['completion_status'].startswith('not_applicable')
            or row.get('covered_by_package') or row.get('line_cost') is not None
            or row.get('draft_quantity') is not None):
        raise ValueError('Wall panel target is excluded, assigned or priced')
    identity='wall-sheathing-combined-candidate'
    if any(q['id']==identity for r in draft['rows'] for q in r.get('assembly_inputs',[])):
        raise ValueError('Wall panel component already assigned')
    panels=from_folder(folder)
    if panels['plan_sha256']!=draft['plan_sha256'] or panels['mapping_sha256']!=mapping_sha256:
        raise ValueError('Wall panel drawing or mapping changed')
    source=copy.deepcopy({key:panels[key] for key in ('plan_sha256','measurement_versions',
        'source_geometry_sha256','mapping_sha256','basis_sha256')})
    if panels.get('selected_scenario'):
        source.update({key:panels[key] for key in ('selected_scenario','selected_wall_height_inches','height_selection_source')})
    result=copy.deepcopy(draft)
    target=next(r for r in result['rows'] if str(r['excel_row'])==str(template_row))
    combined=panels['combined']
    target.setdefault('assembly_inputs',[]).append({
        'id':identity,'label':'Combined wall, gable and chimney sheathing cut candidate',
        'quantity':combined['candidate_sheets'],'unit':'sheet','use':'assembly_input',
        'template_rows':[str(template_row)],'certified':False,'order_released':False,
        'source_snapshot':source,'component_ids':[f['face_id'] for f in combined['faces']],
        'basis':'Nominal 4 x 8 sheets with shared rectangular offcuts; conditional floor band excluded',
        'remaining':panels['remaining']})
    target['certified']=False
    result['wall_panel_review']={**source,'status':'partial_cut_candidate',
        'candidate_sheets':combined['candidate_sheets'],'gross_surface_sf':combined['gross_surface_sf'],
        'cut_sections':combined['cut_sections'],
        'alternative_totals_not_additions':{key:panels[key]['candidate_sheets'] for key in
            (('printed_height_comparison','conditional_floor_band') if panels.get('selected_scenario') else
             ('precut_height_sensitivity','conditional_floor_band'))},
        'complete_wall_sheathing_quantity':None,'price_applied':False,'remaining':panels['remaining']}
    return result
