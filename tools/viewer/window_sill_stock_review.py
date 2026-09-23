"""Whole-board rough-sill allowances tied to selected window assemblies."""
import hashlib
import json
import math
from pathlib import Path
from linear_stock import pack_sawn_cuts
from measurement_store import MeasurementStore
from measurement_quantities import geometry_digest


def calculate(assemblies,stock):
    """One horizontal member between jambs per physical window, not per sash."""
    if not assemblies:raise ValueError('A selected window assembly schedule is required')
    length=stock['length_inches']
    if type(length) not in (int,float) or not math.isfinite(length) or length<=0:
        raise ValueError('Positive finite stock length required')
    pieces=[];seen=set()
    for item in assemblies:
        identity=item['opening_id'];width=item['rough_opening_width_in']
        if not isinstance(identity,str) or not identity.strip() or identity in seen:
            raise ValueError('Unique physical window opening IDs required')
        seen.add(identity)
        if type(item['assembly_quantity']) is not int or item['assembly_quantity']!=1:
            raise ValueError('Each schedule entry must identify one physical window assembly')
        if type(width) not in (int,float) or not math.isfinite(width) or width<=0:
            raise ValueError('Positive finite supplier rough-opening width required')
        pieces.append({'id':'sill:'+identity,'opening_id':identity,'supplier_width_inches':width,
            'cut_inches':math.ceil(width*8-1e-8)/8,'sku':stock['sku'],'stock_length_ft':length/12})
    boards=pack_sawn_cuts(pieces,.125)
    return {'pieces':pieces,'boards':boards,'sill_members':len(pieces),
        'net_sill_lf':math.fsum(p['supplier_width_inches'] for p in pieces)/12,
        'cut_lf':math.fsum(p['cut_inches'] for p in pieces)/12,
        'candidate_whole_sticks':len(boards),'stock_lf':len(boards)*length/12,
        'kerf_inches':.125,'cut_rounding_inches':.125,'optimality_proven':False}


def from_folder(folder):
    folder=Path(folder).resolve();mapping_path=folder/'window_sill_stock_review.json'
    raw=mapping_path.read_bytes();config=json.loads(raw);store=MeasurementStore(folder);state=store.read()
    if config['plan_sha256']!=state['plan_sha256']:
        raise ValueError('Window sill mapping belongs to another drawing')
    evidence={};files={mapping_path:raw}
    for key in ('schedule','supplier'):
        ref=config[key];path=(folder/ref['path']).resolve()
        if not path.is_relative_to(folder):raise ValueError('Sill evidence must remain inside the job')
        content=path.read_bytes();files[path]=content
        if hashlib.sha256(content).hexdigest()!=ref['sha256']:
            raise ValueError('Window sill source changed: '+key)
        if key=='schedule':evidence=json.loads(content)
    if (evidence['plan_sha256']!=state['plan_sha256']
            or evidence['supplier_specification_sha256']!=config['supplier']['sha256']):
        raise ValueError('Window schedule and supplier source do not match')
    identities={a['opening_id'] for a in evidence['assemblies']}
    bindings=dict(config['geometry_sha256']);unmeasured=config['supplier_only_openings']
    changed=[identity for identity,digest in bindings.items()
        if identity not in state['measurements'] or geometry_digest(state['measurements'][identity])!=digest]
    linked=[]
    for reference in config.get('linked_measurements',[]):
        job=(folder/reference['job']).resolve()
        if job==folder or not job.is_relative_to(folder.parent):
            raise ValueError('Linked sill measurements must remain in the neighboring jobs')
        path=job/'measurements.json';content=path.read_bytes();files[path]=content
        if hashlib.sha256(content).hexdigest()!=reference['config_sha256']:
            raise ValueError('Linked sill measurement configuration changed')
        source_store=MeasurementStore(job);source_state=source_store.read()
        if source_state['plan_sha256']!=state['plan_sha256']:
            raise ValueError('Linked sill measurements belong to another drawing')
        openings=reference['openings']
        if not isinstance(openings,dict) or not openings:
            raise ValueError('Linked sill openings need explicit geometry bindings')
        if any(not isinstance(r.get('related_geometry_sha256',{}),dict) for r in openings.values()):
            raise ValueError('Related window dimensions need explicit geometry bindings')
        measurement_ids=[i for r in openings.values() for i in
            [r['measurement_id'],*r.get('related_geometry_sha256',{})]]
        if len(set(measurement_ids))!=len(measurement_ids):
            raise ValueError('One linked sill width cannot represent multiple openings')
        for identity,binding in openings.items():
            if identity in bindings or identity in unmeasured:
                raise ValueError('Window sill opening has duplicate source ownership')
            bindings[identity]=binding['geometry_sha256']
            dimensions={binding['measurement_id']:binding['geometry_sha256'],**binding.get('related_geometry_sha256',{})}
            if any(i not in source_state['measurements'] or geometry_digest(source_state['measurements'][i])!=digest
                   for i,digest in dimensions.items()):
                changed.append(identity)
        linked.append((source_store,source_state))
    if (not bindings or len(unmeasured)!=len(set(unmeasured)) or set(bindings)&set(unmeasured)
            or set(bindings)|set(unmeasured)!=identities):
        raise ValueError('Every window needs either a geometry binding or explicit supplier-only provenance')
    result=calculate(evidence['assemblies'],config['stock']) if not changed else {
        'pieces':[],'boards':[],'sill_members':None,'net_sill_lf':None,'cut_lf':None,
        'candidate_whole_sticks':None,'stock_lf':None}
    result.update(plan_sha256=state['plan_sha256'],measurement_version=state['version'],
        mapping_sha256=hashlib.sha256(raw).hexdigest(),supplier_sha256=config['supplier']['sha256'],
        schedule_sha256=config['schedule']['sha256'],geometry_sha256=bindings,
        supplier_only_openings=unmeasured,changed_measurements=changed,
        status='withheld_geometry_changed' if changed else 'documented_estimating_allowance',
        basis=config['basis'],remaining=config['remaining'],company_default_changed=False,
        purchase_quantity=None,structural_adequacy_verified=False,purchase_order_released=False,
        cross_scope_offcut_credit=False)
    if linked:
        result['linked_measurement_versions']=[{'job':str(s.folder),'version':v['version']} for s,v in linked]
    if (any(path.read_bytes()!=content for path,content in files.items()) or store.read()!=state
            or any(s.read()!=v for s,v in linked)):
        raise ValueError('Window sill sources changed during calculation; retry')
    return result
