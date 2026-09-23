"""Attach source-checked supplier framing components without inventing an order or price."""
import copy
import hashlib
import json
import math
from pathlib import Path


def import_framing_snapshot(draft,source_file,mapping):
    source_file=Path(source_file);raw=source_file.read_bytes();saved=json.loads(raw)
    if saved['floor_footprint']['plan_sha256']!=draft['plan_sha256']:
        raise ValueError('Framing record belongs to another drawing')
    if draft.get('framing_snapshot'):raise ValueError('Framing snapshot already imported')
    layout=(source_file.parent/mapping['supplier_layout_file']).resolve()
    if not layout.is_relative_to(source_file.parent.resolve()):raise ValueError('Supplier layout must be inside the saved trade folder')
    expected=saved['profile']['subfloor_specification']['source']['sha256']
    if hashlib.sha256(layout.read_bytes()).hexdigest()!=expected:raise ValueError('Supplier layout source changed')
    owners=mapping['scope_rows']
    if set(owners)!={'first_floor','ceiling'} or len(set(owners.values()))!=2:
        raise ValueError('Floor and ceiling components need distinct template owners')
    result=copy.deepcopy(draft);rows={r['row_id']:r for r in result['rows']}
    for identity in owners.values():
        row=rows.get(identity,{})
        if (row.get('cost_type')!='MATERIAL' or row.get('covered_by_package')
                or row.get('line_cost') is not None or row.get('completion_status','').startswith('not_applicable')):
            raise ValueError('Framing component target is incompatible or already priced')
    source={'file':str(source_file),'sha256':hashlib.sha256(raw).hexdigest(),
        'measurement_version':saved['version'],'supplier_layout_file':str(layout),'supplier_layout_sha256':expected}
    seen=set();totals={scope:{'scheduled_pieces':0,'scheduled_lf':0} for scope in owners}
    for line in saved['supplier_schedule']:
        scope=line['scope'];key=(scope,line['plot_id'])
        if scope not in owners or key in seen:raise ValueError('Unknown or duplicate supplier framing component')
        seen.add(key);quantity=line['net_qty_as_printed'];length=line['length_ft']
        if (type(quantity) is not int or quantity<=0 or type(line['plies']) is not int or line['plies']<=0
                or type(length) not in (int,float) or not math.isfinite(length) or length<=0
                or type(line['page']) is not int or line['page']<=0
                or not line['product_as_extracted'].strip()):
            raise ValueError('Invalid supplier framing schedule quantity or specification')
        row=rows[owners[scope]]
        row.setdefault('assembly_inputs',[]).append({'id':'framing-'+scope+'-'+line['plot_id'],
            'label':line['plot_id']+' — '+line['product_as_extracted'],
            'quantity':quantity,'unit':'EA','stock_length_ft':length,'scheduled_lf':quantity*length,
            'plies':line['plies'],'source_page':line['page'],'source_snapshot':source,
            'basis':f"Supplier page {line['page']}: {quantity} scheduled pieces at {length:g} FT each. Printed Net Qty already includes the pieces in multi-ply members; do not multiply by plies again.",
            'remaining':list(saved['pending_external_inputs']),
            'certified':False,'order_released':False})
        row['certified']=False;row['current_price_certified']=False
        totals[scope]['scheduled_pieces']+=quantity;totals[scope]['scheduled_lf']+=quantity*length
    if any(t['scheduled_pieces']==0 for t in totals.values()):raise ValueError('Supplier framing schedule is incomplete')
    result['framing_snapshot']={**source,'scope_totals':totals,
        'remaining':list(saved['pending_external_inputs']),
        'basis':'Supplier schedule reference only. Ceiling members are structural; decorative beams are separate. No supplier price, waste multiplier or purchase approval is imported.'}
    result.update(whole_house_total=None,estimate_released=False)
    return result
