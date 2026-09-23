"""Repack source header cuts only while their reviewed opening geometry still agrees."""
from collections import Counter
import copy
import math
from linear_stock import pack_sawn_cuts


def estimate_replacements(result, study, current, records):
    """Budget revised cuts without erasing the conflicting source-plan detail."""
    updated=copy.deepcopy(result);applied=[];withheld=[];seen=set()
    fixed={r['header']['id']:r['header'] for r in result['withheld_source_headers']}
    openings={r['opening_id']:r for r in current['openings']}
    for record in records:
        identity=record['header_id'];opening=record['opening_id']
        if identity in seen or identity not in fixed or opening not in openings:
            raise ValueError('Estimate replacement requires one existing withheld header and opening')
        seen.add(identity);header=fixed[identity];row=openings[opening]
        if (row['header_id']!=identity or record['original_cut_inches']!=header['length_inches']
                or record['pieces']!=header['pieces'] or type(record['pieces']) is not int
                or record.get('plan_sha256')!=result['plan_sha256']
                or not record.get('basis') or not record.get('opening_geometry_sha256')
                or record.get('status')!='documented_estimating_allowance'):
            raise ValueError('Estimate replacement must preserve source identity, count and stated basis')
        width=record['rough_opening_width_inches'];bearing=record['end_support_allowance_inches']
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in (width,bearing)):
            raise ValueError('Positive finite rough width and end-support allowance required')
        stock=study['stock_scenarios'].get(header['material_label'])
        if not stock or stock['sku']!=record['sku'] or stock['length_ft']!=record['stock_length_ft']:
            raise ValueError('Replacement stock must match the reviewed source-material scenario')
        reasons=[]
        if current['opening_geometry_sha256'].get(opening)!=record['opening_geometry_sha256']:
            reasons.append('Opening geometry changed; review replacement cut allowance')
        if row.get('product_rough_opening_width_inches')!=width:
            reasons.append('Selected product rough width changed; review replacement cut allowance')
        if row.get('supplier_alternative') is not None:
            reasons.append('Supplier replacement requires separate reconciliation')
        cut=math.ceil((width+2*bearing)*8-1e-8)/8
        if cut>stock['length_ft']*12:reasons.append('Replacement cut exceeds selected stock; no splice assumed')
        if reasons:
            withheld.append({'header_id':identity,'opening_id':opening,'reasons':reasons});continue
        if any(p['header_id']==identity for p in updated['pieces']):
            raise ValueError('Original and replacement header cannot both be purchased')
        added=[{'id':f'estimate-{identity}-{n+1}','header_id':identity,'opening_id':opening,
            'cut_inches':cut,'sku':stock['sku'],'stock_length_ft':stock['length_ft'],
            'estimating_replacement':True} for n in range(header['pieces'])]
        updated['pieces'].extend(added)
        applied.append({**record,'cut_inches':cut,'piece_ids':[p['id'] for p in added],
            'original_plan_conflict_resolved':False,'structural_adequacy_verified':False})
    updated['boards']=pack_sawn_cuts(updated['pieces'],study['kerf_inches_assumed'])
    updated['candidate_cut_piece_count']=len(updated['pieces'])
    updated['candidate_board_counts']=dict(Counter(b['sku'] for b in updated['boards']))
    updated['estimating_replacements']=applied
    updated['withheld_estimating_replacements']=withheld
    if applied:
        updated['basis']+=' Explicit replacement cut allowances are included separately; original drawing conflicts remain visible.'
    return updated


def calculate(headers, study, baseline, current):
    if not study['plan_sha256']==baseline['plan_sha256']==current['plan_sha256']:
        raise ValueError('Header cuts and openings must belong to the same drawing')
    by_header={h['id']:h for h in headers}
    if len(by_header)!=len(headers) or any(type(h['pieces']) is not int or h['pieces']<=0 for h in headers):
        raise ValueError('Unique header IDs with positive whole-piece counts required')
    def mapped(review):
        rows=review['openings'];by_opening={r['opening_id']:r for r in rows}
        if len(by_opening)!=len(rows):raise ValueError('Duplicate opening in header review')
        mapped_headers=[r['header_id'] for r in rows if r['header_id'] is not None]
        if len(mapped_headers)!=len(set(mapped_headers)) or set(mapped_headers)!=set(by_header):
            raise ValueError('Each inventoried header needs exactly one opening association')
        for row in rows:
            if row['header_id'] and row['header_cut_length_inches']!=by_header[row['header_id']]['length_inches']:
                raise ValueError('Header cut length differs from the source inventory')
        return by_opening
    old=mapped(baseline);live=mapped(current)
    if set(old)!=set(live) or any(old[i]['header_id']!=live[i]['header_id'] for i in old):
        raise ValueError('Opening/header associations changed; reconcile cutting scope')
    pieces=study['pieces'];eligible=[];withheld=[];counts=Counter();seen=set()
    unresolved=study['unresolved_material_or_stock'];fixed=study['withheld_conflicting_headers']
    for item in unresolved+[b['header'] for b in fixed]:
        if item['id'] not in by_header or item!=by_header[item['id']] or item['id'] in seen:
            raise ValueError('Unresolved or withheld header does not match the source inventory')
        seen.add(item['id']);counts[item['id']]+=item['pieces']
    if len({p['id'] for p in pieces})!=len(pieces):raise ValueError('Duplicate header cut piece')
    for piece in pieces:
        identity=piece['header_id']
        if (identity not in by_header or identity in seen
                or piece['cut_inches']!=by_header[identity]['length_inches']):
            raise ValueError('Candidate cut differs from its source header')
        counts[identity]+=1
    if counts!=Counter({h['id']:h['pieces'] for h in headers}):
        raise ValueError('Every source header piece must be accounted for exactly once')
    changes={};by_id={r['header_id']:r for r in current['openings'] if r['header_id']}
    for identity,row in live.items():
        reasons=[];expected=baseline['opening_geometry_sha256'].get(identity)
        actual=current['opening_geometry_sha256'].get(identity)
        if row['header_id']:
            if not expected or not actual:reasons.append('Opening geometry is not bound to the cutting reference')
            elif actual!=expected:reasons.append('Opening geometry changed; revised header cut requires review')
            if row['status']!='end_support_length_unverified':reasons.append(row['status'])
            supplier=row.get('supplier_alternative')
            if supplier is not None:
                reasons.append('Supplier alternative requires material and revision reconciliation')
                if supplier.get('flags'):reasons.append('Supplier/header dimensions conflict')
        if reasons:changes[row['header_id']]=reasons
    for piece in pieces:
        reasons=changes.get(piece['header_id'],[])
        if reasons:
            withheld.append({'piece':piece,'opening_id':by_id[piece['header_id']]['opening_id'],'reasons':reasons})
        else:eligible.append(piece)
    boards=pack_sawn_cuts(eligible,study['kerf_inches_assumed'])
    if Counter(c['piece_id'] for b in boards for c in b['cuts'])!=Counter(p['id'] for p in eligible):
        raise ValueError('Header stock allocation lost or duplicated a cut')
    return {'plan_sha256':current['plan_sha256'],'measurement_version':current['measurement_version'],
        'pieces':eligible,'boards':boards,'candidate_cut_piece_count':len(eligible),
        'candidate_board_counts':dict(Counter(b['sku'] for b in boards)),
        'withheld_changed_or_conflicting_cuts':withheld,'header_issues':changes,
        'withheld_source_headers':fixed,'unresolved_material_or_stock':unresolved,
        'additional_missing_headers':[r['opening_id'] for r in current['openings'] if r['header_id'] is None],
        'source_piece_count':sum(counts.values()),'kerf_inches':study['kerf_inches_assumed'],
        'end_trim_allowance_inches':study['end_trim_allowance_inches'],'end_trim_basis':study['end_trim_basis'],
        'purchase_quantity':None,'order_released':False,'current_prices_applied':False,
        'optimality_proven':False,'cross_scope_offcut_credit':False,
        'basis':'Unchanged source header cuts with provisional exact-SKU stock allocation; changed openings remain unquantified.',
        'remaining':study['remaining']}
