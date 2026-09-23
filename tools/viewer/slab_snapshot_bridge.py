"""Carry a verified saved slab snapshot into a combined draft without repricing."""
import copy
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from estimate_readiness import valid_number
from slab_outputs import profile_hash


def import_slab_snapshot(draft, source_file, mappings, supplemental_mappings=None):
    path=Path(source_file);raw=path.read_bytes();snapshot=json.loads(raw)
    if snapshot['plan_sha256']!=draft['plan_sha256']:raise ValueError('Slab belongs to another drawing')
    attachment=snapshot['construction']
    if profile_hash(attachment['profile'])!=attachment['profile_sha256']:
        raise ValueError('Slab profile hash does not match')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']}
    if result.get('slab_snapshot'):raise ValueError('Slab snapshot already imported')
    source={'file':str(path),'sha256':hashlib.sha256(raw).hexdigest(),
            'measurement_version':snapshot['version'],'profile_sha256':attachment['profile_sha256'],
            'pricing_as_of':attachment['profile'].get('pricing_as_of')}
    supplemental=[];seen=set();mapped=[]
    for item in attachment['outputs']['estimate_rows']:
        identity=item['template_row_id']
        if identity in seen:raise ValueError('Duplicate slab cost ownership')
        seen.add(identity)
        if not valid_number(item['quantity']):raise ValueError('Slab quantity is unresolved or invalid')
        record={**copy.deepcopy(item),'source_snapshot':source,'current_price_revalidated':False}
        if identity not in rows:
            supplemental.append(record);continue
        if identity not in mappings:raise ValueError('Explicit slab unit mapping required')
        mapping=mappings[identity];row=rows[identity]
        if mapping['source_unit']!=item['unit'] or mapping['template_unit']!=row['unit'] or not mapping.get('basis'):
            raise ValueError('Slab unit mapping does not match source and template')
        if Decimal(str(item['markup_percent']))!=Decimal(str(row['markup_pct'])):
            raise ValueError('Slab markup differs from current template')
        if row.get('draft_quantity') is not None or row.get('line_cost') is not None or row.get('covered_by_package'):
            raise ValueError('Slab target already has quantity or pricing ownership')
        if row['cost_type']=='GROUP' or row.get('parent','').strip().upper()=='INPUTS' or row['completion_status'].startswith('not_applicable'):
            raise ValueError('Slab cannot populate a nonbillable target')
        row['draft_quantity']=item['quantity']
        row.setdefault('quantity_sources',[]).append({'kind':'saved_slab_snapshot','source':source,
            'source_unit':item['unit'],'template_unit':row['unit'],'mapping_basis':mapping['basis'],
            'quantity_status':item['quantity_status'],'certified':False})
        row['saved_trade_budget']=record
        row['certified']=False;row['current_price_certified']=False
        mapped.append(identity)
    if set(mappings)!=set(mapped):raise ValueError('Unused slab mapping')
    assignments=supplemental_mappings or {}
    by_id={item['template_row_id']:item for item in supplemental}
    extras=result.setdefault('additional_cost_rows',[]) if assignments else result.get('additional_cost_rows',[])
    occupied=set(rows)|{item['row_id'] for item in extras}
    for identity,mapping in assignments.items():
        if identity not in by_id or identity in occupied:raise ValueError('Unknown or duplicate supplemental cost owner')
        item=by_id[identity];parent=rows.get(mapping['parent_row_id'])
        if (not parent or parent['cost_type']!='ASSEMBLY' or parent.get('covered_by_package')
                or parent.get('line_cost') is not None):raise ValueError('Supplemental cost needs an unpriced assembly parent')
        if (mapping['unit']!=item['unit'] or mapping['markup_pct']!=item['markup_percent']
                or mapping['cost_type'] not in ('MATERIAL','SUBCONTRACTOR','EQUIPMENT') or not mapping.get('basis')):
            raise ValueError('Supplemental purchase unit, markup or cost type is invalid')
        extras.append({'row_id':identity,'parent_row_id':mapping['parent_row_id'],'name':item['name'],
            'parent':parent['name'],'unit':item['unit'],'cost_type':mapping['cost_type'],
            'markup_pct':mapping['markup_pct'],'draft_quantity':item['quantity'],'unit_cost':None,
            'line_cost':None,'line_price':None,'pricing_role':'cost_line','certified':False,
            'current_price_certified':False,'completion_status':'evidence_in_progress',
            'quantity_sources':[{'kind':'saved_slab_supplemental','source':source,
                'quantity_status':item['quantity_status'],'basis':mapping['basis']}],
            'assembly_inputs':[],'saved_trade_budget':copy.deepcopy(item)})
        occupied.add(identity)
    result['slab_snapshot']={**source,'mapped_rows':mapped,'supplemental_rows':supplemental,
        'assigned_supplemental_ids':list(assignments),
        'note':'Saved budgets remain separate from current prices; supplemental ownership, pricing and certification are reviewed separately.'}
    result.update(whole_house_total=None,estimate_released=False)
    return result
