"""Attach reviewed partial wall components, withholding them after geometry edits."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from company_profile import resolve
from field_stud_layout import layout
from framing_assemblies import calculate
from wall_field_stud_review import from_folder as live_field_layout


def import_components(draft, state, config, folder):
    folder = Path(folder).resolve()
    if config['plan_sha256'] != draft['plan_sha256'] or state['plan_sha256'] != draft['plan_sha256']:
        raise ValueError('Framing components belong to another drawing')
    if draft.get('wall_component_review'):
        raise ValueError('Wall components already imported')
    evidence = {}; hashes = {}
    for key in ('field_inputs', 'assembly_inputs', 'profile'):
        ref = config[key]; path = (folder/ref['path']).resolve()
        if not path.is_relative_to(folder):
            raise ValueError('Framing evidence must stay inside the job')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise ValueError('Framing component evidence changed: ' + key)
        evidence[key] = json.loads(raw); hashes[key] = ref['sha256']
    inputs = evidence['field_inputs']
    if inputs['plan_sha256'] != state['plan_sha256']:
        raise ValueError('Field layout belongs to another drawing')
    if not config['dependencies']:
        raise ValueError('Framing components require measured-geometry dependencies')
    changes = []; versions = []; seen = set()
    for dependency in config['dependencies']:
        path = (folder/dependency['job']).resolve()
        if path in seen or not dependency['measurements']:
            raise ValueError('Unique, nonempty geometry dependencies required')
        seen.add(path)
        current = state if path == folder else MeasurementStore(path).read()
        if current['plan_sha256'] != draft['plan_sha256']:
            raise ValueError('Framing dependency belongs to another drawing')
        versions.append({'job':str(path),'version':current['version']})
        for identity, expected in dependency['measurements'].items():
            measurement = current['measurements'].get(identity)
            if measurement is None or geometry_digest(measurement) != expected:
                changes.append({'job':str(path),'measurement_id':identity})
    result = copy.deepcopy(draft)
    matches = [r for r in result['rows'] if str(r['excel_row']) == str(config['template_row'])]
    if len(matches) != 1:
        raise ValueError('One framing component template owner required')
    row = matches[0]
    if (row['cost_type'] != 'MATERIAL' or row['completion_status'].startswith('not_applicable')
            or row.get('covered_by_package') or row.get('line_cost') is not None
            or row.get('draft_quantity') is not None):
        raise ValueError('Framing component target is excluded, assigned or priced')
    source = {'evidence_sha256':hashes,'measurement_dependencies':versions,
              'basis':'Reviewed partial framing quantities; no complete order or current price'}
    result['wall_component_review'] = {**source,'changed_measurements':changes,
                                       'status':'withheld_geometry_changed' if changes else 'partial_components'}
    live_mode = config.get('live_field_layout', False)
    if type(live_mode) is not bool:
        raise ValueError('Live field layout must be explicitly enabled or disabled')
    if changes:
        result.setdefault('pending_quantities',[]).append({
            'id':'wall-components','label':'Wall framing component review',
            'template_rows':[str(config['template_row'])], 'unit':'EA', 'use':'assembly_input',
            'reason':('Field candidates recalculated; opening and backing assemblies require review' if live_mode
                      else 'Framing geometry changed; reconcile field positions and assembly ownership'),
            'changed_measurements':changes,'quantity':None,'certified':False})
        if not live_mode:return result
    settings = resolve(evidence['profile'], project_overrides=inputs.get('project_overrides'))['settings']
    if live_mode:
        field = live_field_layout(folder)
        if (field['plan_sha256'] != state['plan_sha256'] or field['profile_sha256'] != hashes['profile']
                or field['spacing_inches'] != settings['framing.stud_spacing_inches']
                or field['first_center_inches'] != inputs['first_center_inches']):
            raise ValueError('Live field layout and component review must use the same drawing and practices')
        if {v['job']:v['version'] for v in field['measurement_dependencies']} != {v['job']:v['version'] for v in versions}:
            raise ValueError('Framing features changed during component calculation; retry')
        source['live_field_layout'] = {key:field[key] for key in (
            'evidence_sha256','exterior_evidence_sha256','geometry_sha256','exterior_geometry_sha256')}
        result['wall_component_review'].update(live_field_layout=source['live_field_layout'],
            status='field_recalculated_assemblies_withheld' if changes else 'partial_components')
    else:
        field = layout(inputs['runs'],inputs['zones'],points_per_foot=inputs['points_per_foot'],
                       spacing_inches=settings['framing.stud_spacing_inches'],
                       first_center_inches=inputs['first_center_inches'])
    items = [('field-studs','Field-stud layout candidates',field['field_count'],
              [s['id'] for s in field['field_studs']])]
    labels = {'king_studs':'Opening king-stud allowances','jack_studs':'Opening jack-stud allowances',
              'junction_studs':'Corner and intersection stud allowances',
              'pocket_frame_kits':'Pocket-door frame-kit count'}
    components = None
    if not changes:
        assemblies = evidence['assembly_inputs']
        components = calculate(evidence['profile'],assemblies['openings'],assemblies['junctions'])
        for key, label in labels.items():
            items.append((key,label,components['component_totals'][key],
                          [c['id'] for c in components['components'] if c['quantities'].get(key)]))
    for key,label,count,identities in items:
        identity = 'wall-component-'+key
        if any(q['id']==identity for q in row.get('assembly_inputs',[])):
            raise ValueError('Wall component input already assigned')
        row.setdefault('assembly_inputs',[]).append({
            'id':identity,'label':label,'quantity':count,'unit':'EA','use':'assembly_input',
            'template_rows':[str(config['template_row'])], 'certified':False,'order_released':False,
            'source_snapshot':source,'component_ids':identities,
            'basis':field['basis'] if key=='field-studs' else 'Source-classified company practices and documented estimating allowances',
            'remaining':field['remaining']+['Complete all unquantified opening and special framing assemblies; current supplier pricing remains open.']})
    row['certified']=False
    result['wall_component_review'].update(field_candidates=field['field_count'],
        reserved_stations_not_purchase_pieces=field['reserved_count'])
    if components is not None:
        result['wall_component_review'].update(assembly_component_totals=components['component_totals'],
            component_issues=components['pending'],
            unquantified_assemblies=sorted({z['assembly'] for z in inputs['zones']}
                                          -{c['id'] for c in components['components']}))
    return result
