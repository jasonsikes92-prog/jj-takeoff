"""Count window bedding sealant separately from interior air sealing."""
import copy
import hashlib
import json
import math
from pathlib import Path


def bedding_takeoff(assemblies, rule):
    for key in ('cap_return_in', 'yield_lf_per_cartridge', 'handling_percent'):
        value=rule.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('Bedding allowance dimensions must be finite and nonnegative')
    if rule['yield_lf_per_cartridge']<=0:
        raise ValueError('Bedding cartridge yield must be positive')
    runs=[];seen=set()
    for a in assemblies:
        identity=a['opening_id'];count=a['assembly_quantity']
        w=a.get('rough_opening_width_in');h=a.get('rough_opening_height_in')
        if not identity or identity in seen or type(count) is not int or count<=0:
            raise ValueError('Unique openings and positive assembly counts required')
        seen.add(identity)
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (w,h)):
            raise ValueError('Bedding needs positive opening dimensions')
        runs.append({'opening_id':identity,'assembly_quantity':count,
            'head_and_jamb_lf':(w+2*h)/12*count,
            'drip_cap_bedding_lf':(w+2*rule['cap_return_in'])/12*count,
            'interior_perimeter_reference_lf':2*(w+h)/12*count})
    if not runs:raise ValueError('Bedding needs window openings')
    length=math.fsum(r['head_and_jamb_lf']+r['drip_cap_bedding_lf'] for r in runs)
    allowance=length*(1+rule['handling_percent']/100)
    return {'runs':runs,'net_bedding_lf':length,'allowance_lf':allowance,
            'quantity':math.ceil(allowance/rule['yield_lf_per_cartridge']),
            'interior_perimeter_reference_lf':math.fsum(r['interior_perimeter_reference_lf'] for r in runs)}


def apply_window_bedding(draft, source_file, saved, mapping):
    root=Path(source_file).parent.resolve()
    def checked(reference):
        p=(root/reference['file']).resolve()
        if (not p.is_relative_to(root) or not p.is_file()
                or hashlib.sha256(p.read_bytes()).hexdigest()!=reference['sha256']):
            raise ValueError('Bedding source evidence missing or changed')
        return p
    path=checked(mapping);basis=json.loads(path.read_bytes())
    if (basis.get('plan_sha256')!=draft['plan_sha256'] or basis.get('status')!='estimating_allowance'
            or not basis.get('assumptions') or not basis.get('remaining') or not basis.get('documents')):
        raise ValueError('Bedding needs a matching plan and explicit estimating assumptions')
    for document in basis['documents']:checked(document)
    rows={r['row_id']:r for r in draft['rows']};extras=draft.setdefault('additional_cost_rows',[])
    identity=mapping['row_id'];parent=rows[mapping['parent_row_id']];markup=rows[mapping['markup_source_row_id']]
    if identity in rows or any(r['row_id']==identity for r in extras):
        raise ValueError('Duplicate bedding purchase owner')
    if (parent['cost_type']!='ASSEMBLY' or markup['cost_type']!='MATERIAL'
            or markup['parent']!=parent['name'] or parent.get('covered_by_package')
            or parent.get('completion_status','').startswith('not_applicable')
            or any(parent.get(k) is not None for k in ('unit_cost','line_cost','line_price'))):
        raise ValueError('Bedding needs an unpriced window assembly and material markup source')
    takeoff=bedding_takeoff(saved['material_schedule']['assemblies'],basis['rule'])
    product=basis['product']
    if not product.get('product_id') or not product.get('model'):
        raise ValueError('Bedding purchase requires an identified estimating product')
    extras.append({'row_id':identity,'parent_row_id':parent['row_id'],
        'name':'Window exterior bedding sealant allowance','parent':parent['name'],
        'cost_type':'MATERIAL','unit':'each','markup_pct':markup['markup_pct'],
        'markup_source_row_id':markup['row_id'],'draft_quantity':takeoff['quantity'],
        'unit_cost':None,'line_cost':None,'line_price':None,'pricing_role':'cost_line',
        'completion_status':'evidence_in_progress','certified':False,'current_price_certified':False,
        'assembly_inputs':[],'quantity_sources':[{
            'kind':'reviewed_item_purchase','quantity':takeoff['quantity'],'unit':'each',
            'product_id':product['product_id'],'model':product['model'],
            'selection_status':'estimating_candidate','basis':basis['basis'],
            'assumptions':copy.deepcopy(basis['assumptions']),'remaining':copy.deepcopy(basis['remaining']),
            'rule':copy.deepcopy(basis['rule']),'takeoff':takeoff,
            'source':{'file':str(path),'sha256':mapping['sha256'],
                      'schedule_sha256':hashlib.sha256(Path(source_file).read_bytes()).hexdigest()},
            'certified':False,'order_released':False}]})
