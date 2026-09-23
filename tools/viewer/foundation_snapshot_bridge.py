"""Connect explicitly mapped foundation snapshot fields to estimate rows."""
import copy
import hashlib
import json
from pathlib import Path
from estimate_readiness import valid_number


def field(record,path):
    for part in path.split('.'):record=record[part]
    return record


def import_foundation_snapshot(draft, source_file, mappings, supplemental_mappings=None):
    path=Path(source_file);raw=path.read_bytes();saved=json.loads(raw)
    if saved['plan_sha256']!=draft['plan_sha256']:raise ValueError('Foundation belongs to another drawing')
    if draft.get('foundation_snapshot'):raise ValueError('Foundation snapshot already imported')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']};seen=set()
    source={'file':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'measurement_version':saved['version']}
    for mapping in mappings:
        identity=mapping['row_id']
        if identity not in rows or identity in seen:raise ValueError('Unknown or duplicate foundation mapping')
        seen.add(identity);row=rows[identity]
        if row.get('covered_by_package') or row['cost_type']=='GROUP' or row['completion_status'].startswith('not_applicable'):
            raise ValueError('Foundation target is excluded or already owned')
        value=field(saved,mapping['quantity_path'])
        if value is not None and not valid_number(value):raise ValueError('Invalid foundation quantity')
        if not mapping.get('basis'):raise ValueError('Foundation mapping needs its source-unit basis')
        evidence={'id':'foundation-'+identity,'quantity':value,'unit':mapping['source_unit'],
                  'source_snapshot':source,'quantity_path':mapping['quantity_path'],
                  'basis':mapping['basis'],'remaining':mapping['remaining'],'certified':False}
        conversion=mapping.get('stock_length_path')
        if conversion is not None:
            # Whole purchased sticks can feed an LF template row, but net bar LF
            # must never silently become a purchased-stick count.
            stock=field(saved,conversion)
            if (mapping['use']!='template_quantity' or mapping['source_unit']!='stick'
                    or mapping.get('template_unit')!='LF' or value is None
                    or int(value)!=value or not valid_number(stock) or stock<=0):
                raise ValueError('Stick conversion requires whole sticks and positive stock feet')
            value*=stock
            if not valid_number(value):raise ValueError('Invalid converted stock length')
            evidence.update(source_quantity=evidence['quantity'],source_unit='stick',
                stock_length_ft=stock,stock_length_path=conversion,quantity=value,unit='LF')
        if mapping['use']=='template_quantity':
            if row['unit']!=mapping['template_unit'] or value is None:raise ValueError('Unresolved or mismatched template quantity')
            if row.get('draft_quantity') is not None:raise ValueError('Template quantity already assigned')
            row['draft_quantity']=value;row.setdefault('quantity_sources',[]).append(evidence)
        elif mapping['use']=='assembly_input':
            row.setdefault('assembly_inputs',[]).append(evidence)
        else:raise ValueError('Unknown foundation mapping use')
        row['certified']=False;row['current_price_certified']=False
    assignments=supplemental_mappings or {}
    extras=result.setdefault('additional_cost_rows',[]) if assignments else result.get('additional_cost_rows',[])
    occupied=set(rows)|{r['row_id'] for r in extras}
    for identity,mapping in assignments.items():
        if identity in occupied:raise ValueError('Duplicate foundation supplemental cost owner')
        parent=rows.get(mapping['parent_row_id'],{})
        if (parent.get('cost_type')!='ASSEMBLY' or parent.get('line_cost') is not None
                or parent.get('covered_by_package')):
            raise ValueError('Foundation supplemental needs an unpriced assembly parent')
        reference=rows.get(mapping['markup_source_row_id'],{})
        markup=float(reference.get('markup_pct',-1))
        if (reference.get('cost_type') not in ('MATERIAL','SUBCONTRACTOR','EQUIPMENT')
                or not valid_number(markup) or not mapping.get('unit') or not mapping.get('basis')):
            raise ValueError('Foundation supplemental needs template cost type, markup and unit basis')
        value=field(saved,mapping['quantity_path'])
        if value is not None and not valid_number(value):raise ValueError('Invalid foundation supplemental quantity')
        replacement=mapping.get('replaces_row_id')
        if replacement:
            original=rows.get(replacement,{})
            matching=[m for m in mappings if m['row_id']==replacement
                      and m['use']=='assembly_input' and m['quantity_path']==mapping['quantity_path']]
            if (len(matching)!=1 or original.get('cost_owner_row_id') or original.get('covered_by_package')
                    or any(original.get(k) is not None for k in ('draft_quantity','unit_cost','line_cost','line_price'))
                    or replacement!=mapping['markup_source_row_id']):
                raise ValueError('Replacement needs an unpriced matching template quantity reference')
            original.update(cost_owner_row_id=identity,pricing_role='cost_reference')
            original['assembly_inputs'][-1]['basis']+='; purchase cost is assigned to '+identity
        extras.append({'row_id':identity,'parent_row_id':mapping['parent_row_id'],
            'name':mapping['name'],'parent':parent['name'],'cost_type':reference['cost_type'],
            'unit':mapping['unit'],'markup_pct':markup,'markup_source_row_id':mapping['markup_source_row_id'],
            'draft_quantity':value,'unit_cost':None,'line_cost':None,'line_price':None,
            'pricing_role':'cost_line','completion_status':'evidence_in_progress',
            'certified':False,'current_price_certified':False,'assembly_inputs':[],
            'quantity_sources':[{'kind':'saved_foundation_supplemental','source':source,
                'quantity_path':mapping['quantity_path'],'basis':mapping['basis'],
                'quantity_status':mapping['basis'],'remaining':mapping.get('remaining',[])}]})
        if replacement:extras[-1]['replaces_row_id']=replacement
        occupied.add(identity)
    result['foundation_snapshot']={**source,'mappings':copy.deepcopy(mappings),
        'assigned_supplemental_ids':list(assignments),
        'unresolved_and_separate_scope':{
            'footing_steel':saved['outputs']['footing_reinforcement'],
            'access_door':saved['outputs']['crawlspace_access_door'],
            'separate_footing_pump':saved['outputs']['footing_pump'],
            'pier_masonry':saved['outputs']['pier_masonry'],
            'pier_caps':saved['outputs']['pier_caps'],
            'pad_reinforcement':saved['outputs']['pad_reinforcement']},
        'scope_note':'Shared footing concrete includes pads; mortar and grout are pooled purchases. Wall blocks, wall caps and wall labor exclude separately retained pier components. Separate source prices are not promoted here.'}
    result.update(whole_house_total=None,estimate_released=False)
    return result
