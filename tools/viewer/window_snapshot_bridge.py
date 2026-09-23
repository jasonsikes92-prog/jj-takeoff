"""Map enumerated window components to the owner-confirmed installation basis."""
import copy
import hashlib
import json
import math
from pathlib import Path
from window_flashing import apply_window_flashing
from window_bedding import apply_window_bedding
from window_head_caps import apply_window_head_caps


def import_window_snapshot(draft, source_file, mapping):
    if any(k in mapping for k in ('flashing', 'bedding', 'head_caps')) and 'material_row_id' not in mapping:
        raise ValueError('Window flashing requires the verified material schedule')
    trim_basis=mapping.get('trim_pricing_basis')
    if trim_basis is not None and (trim_basis!='per_assembled_opening' or 'perimeter_row_id' not in mapping):
        raise ValueError('Window trim pricing needs an explicit assembled-opening target')
    if 'perimeter_row_id' in mapping and 'material_row_id' not in mapping:
        raise ValueError('Window perimeter requires the verified material schedule')
    raw=source_file.read_bytes();saved=json.loads(raw)
    if saved['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Window record belongs to another drawing')
    if saved['owner_answer']!='Per individual window unit':
        raise ValueError('Individual-unit installation basis is not confirmed')
    seen=set();quantity=0
    for opening in saved['assemblies']:
        identity=opening['opening_id']
        if identity in seen:raise ValueError('Duplicate window opening')
        seen.add(identity)
        for key in ('assembly_quantity','component_count','source_plan_sheet'):
            if type(opening[key]) is not int or opening[key]<=0:
                raise ValueError('Window counts and sheet must be positive integers')
        quantity+=opening['assembly_quantity']*opening['component_count']
    if not seen or quantity!=saved['installation_quantity']:
        raise ValueError('Window enumeration does not reconcile')
    result=copy.deepcopy(draft)
    targets=[r for r in result['rows'] if r['row_id']==mapping['row_id']]
    if len(targets)!=1:raise ValueError('Window target must be unique')
    row=targets[0]
    if (str(row['excel_row'])!=str(saved['template_row']) or row['unit']!=saved['unit']
            or row['cost_type'] not in ('LABOR','SUBCONTRACTOR')
            or row['completion_status'].startswith('not_applicable')
            or row.get('draft_quantity') is not None or row.get('line_cost') is not None
            or row.get('covered_by_package')):
        raise ValueError('Window installation target is incompatible or already assigned')
    row['draft_quantity']=quantity
    row.setdefault('quantity_sources',[]).append({'kind':'enumerated_window_components',
        'file':str(source_file),'sha256':hashlib.sha256(raw).hexdigest(),
        'assemblies':saved['assemblies'],'basis':saved['basis'],'certified':False})
    row['certified']=False
    if 'cleaning_row_id' in mapping:
        targets=[r for r in result['rows'] if r['row_id']==mapping['cleaning_row_id']]
        if len(targets)!=1:raise ValueError('Window cleaning target must be unique')
        cleaning=targets[0]
        if (cleaning['unit']!='each' or cleaning['cost_type'] not in ('LABOR','SUBCONTRACTOR')
                or cleaning['completion_status'].startswith('not_applicable')
                or any(cleaning.get(k) is not None for k in ('draft_quantity','unit_cost','line_cost','line_price'))
                or cleaning.get('covered_by_package') or cleaning.get('cost_owner_row_id')):
            raise ValueError('Window cleaning target is incompatible or already assigned')
        cleaning['draft_quantity']=quantity
        cleaning.setdefault('quantity_sources',[]).append({
            'kind':'enumerated_window_cleaning_units','file':str(source_file),
            'sha256':hashlib.sha256(raw).hexdigest(),'assemblies':saved['assemblies'],
            'quantity':quantity,'unit':'each','certified':False,
            'basis':'Individual window units in the reviewed plan schedule; each unit includes its interior and exterior cleaning faces, not two separate window counts.',
            'remaining':['Reconcile supplier billing units and any additional glazed doors or other cleaning scope. Historical billed counts do not override the plan enumeration.']})
        cleaning['certified']=False
    if 'material_row_id' in mapping:
        material_rows=[r for r in result['rows'] if r['row_id']==mapping['material_row_id']]
        if len(material_rows)!=1:raise ValueError('Window material target must be unique')
        material=material_rows[0]
        if (material['unit']!='each' or material['cost_type'] not in ('MATERIAL','ALLOWANCE')
                or material['completion_status'].startswith('not_applicable')
                or material.get('draft_quantity') is not None or material.get('line_cost') is not None
                or material.get('covered_by_package') or material.get('cost_owner_row_id')):
            raise ValueError('Window material target is incompatible or already assigned')
        basis=saved['material_schedule']
        specification=(Path(source_file).parent/basis['specification_file']).resolve()
        if (not specification.is_relative_to(Path(source_file).parent.resolve())
                or hashlib.sha256(specification.read_bytes()).hexdigest()!=basis['specification_sha256']):
            raise ValueError('Window supplier specification changed or is outside the job')
        members=basis['assemblies']
        if (len(members)!=len(seen) or {a['opening_id'] for a in members}!=seen
                or any({k:a[k] for k in ('opening_id','assembly_quantity','component_count','source_plan_sheet')}
                       not in saved['assemblies'] for a in members)):
            raise ValueError('Material assemblies differ from the installation schedule')
        count=sum(a['assembly_quantity'] for a in members)
        material['draft_quantity']=count
        material.setdefault('quantity_sources',[]).append({'kind':'enumerated_window_assemblies',
            'file':str(source_file),'sha256':hashlib.sha256(raw).hexdigest(),
            'assemblies':members,'supplier_quote_id':basis['quote_id'],
            'specification_file':str(specification),'specification_sha256':basis['specification_sha256'],
            'quantity':count,'unit':'each','basis':basis['basis'],'certified':False})
        material['certified']=False
        if 'perimeter_row_id' in mapping:
            targets=[r for r in result['rows'] if r['row_id']==mapping['perimeter_row_id']]
            if len(targets)!=1:raise ValueError('Window perimeter target must be unique')
            target=targets[0]
            trim_units=('each',) if trim_basis else ('feet','LF')
            if (target['unit'] not in trim_units or target['cost_type'] not in ('MATERIAL','SUBCONTRACTOR')
                    or target['completion_status'].startswith('not_applicable')
                    or target.get('draft_quantity') is not None or target.get('line_cost') is not None
                    or target.get('covered_by_package') or target.get('cost_owner_row_id')
                    or target.get('assembly_inputs')):
                raise ValueError('Window perimeter target is incompatible or already assigned')
            perimeters=[]
            for member in members:
                width=member.get('rough_opening_width_in');height=member.get('rough_opening_height_in')
                if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (width,height)):
                    raise ValueError('Window perimeter needs positive supplier opening dimensions')
                perimeters.append({'opening_id':member['opening_id'],'assembly_quantity':member['assembly_quantity'],
                    'width_in':width,'height_in':height,'perimeter_lf':2*(width+height)/12*member['assembly_quantity']})
            perimeter=math.fsum(p['perimeter_lf'] for p in perimeters)
            target.setdefault('assembly_inputs',[]).append({'id':'window-rough-opening-perimeter',
                'label':'Window opening perimeter reference; trim cuts separate',
                'quantity':perimeter,'measured_quantity':perimeter,'unit':'LF','use':'assembly_input',
                'template_rows':[str(target['excel_row'])],'rounding':'none','opening_perimeters':perimeters,
                'basis':'Four sides of each supplier rough opening, counted once per assembled group, not once per individual pane. Supplier '+basis['quote_id']+'.',
                'remaining':['Reference for trim layout only; finished frame/reveal dimensions, butt/miter joints, trim widths and stock cuts remain separate.',
                    'No flashing overlaps, sealant yield, cutting waste, whole-stock order or current price inferred.'],
                'source':{'file':str(source_file),'sha256':hashlib.sha256(raw).hexdigest(),
                    'specification_file':str(specification),'specification_sha256':basis['specification_sha256']},
                'certified':False,'order_released':False,'current_price':None})
            target['certified']=False
            if trim_basis:
                target['draft_quantity']=count
                target.setdefault('quantity_sources',[]).append({'kind':'enumerated_window_trim_assemblies',
                    'file':str(source_file),'sha256':hashlib.sha256(raw).hexdigest(),
                    'specification_sha256':basis['specification_sha256'],
                    'quantity':count,'unit':'each',
                    'assemblies':[{'opening_id':a['opening_id'],'assembly_quantity':a['assembly_quantity']} for a in members],
                    'basis':'One exterior trim allowance per assembled window opening. Individual window units, doors and the garage surround are separate.',
                    'certified':False})
    if 'flashing' in mapping:
        apply_window_flashing(result, source_file, saved, mapping['flashing'])
    if 'bedding' in mapping:
        apply_window_bedding(result, source_file, saved, mapping['bedding'])
    if 'head_caps' in mapping:
        apply_window_head_caps(result, source_file, saved, mapping['head_caps'])
    result.update(whole_house_total=None,estimate_released=False)
    return result
