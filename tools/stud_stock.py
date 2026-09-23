"""Whole-stock scenarios for identified full-height studs, separate from other framing."""
import math
from collections import Counter
from linear_stock import pack_sawn_cuts


def calculate(field, assemblies, aliases, run_offsets, wall_height_inches, plate_inches, stocks,
              jack_stock_allowance=False):
    if type(jack_stock_allowance) is not bool:raise ValueError('Explicit jack stock allowance required')
    runs={r['run'] for r in field['runs']}
    if set(run_offsets)!=runs:raise ValueError('Every current wall run needs an explicit height assignment')
    dimensions=[wall_height_inches,plate_inches,*run_offsets.values()]
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in dimensions):
        raise ValueError('Finite wall and plate dimensions required')
    lengths={r:wall_height_inches+offset-plate_inches for r,offset in run_offsets.items()}
    if plate_inches<=0 or any(v<=0 for v in lengths.values()):raise ValueError('Positive stud and plate lengths required')
    if len({s['sku'] for s in stocks})!=len(stocks):raise ValueError('Unique stock products required')
    for stock in stocks:
        if (not stock.get('sku') or type(stock.get('precut')) is not bool
                or type(stock.get('length_inches')) not in (int,float)
                or not math.isfinite(stock['length_inches']) or stock['length_inches']<=0):
            raise ValueError('Stock needs an exact product, length and precut designation')
    members=[];pending=[];seen=set()
    def add(identity,source,kind,member_runs):
        if identity in seen:raise ValueError('Duplicate stud member')
        seen.add(identity)
        if not member_runs or not set(member_runs)<=runs:
            pending.append({'id':identity,'reason':'Stud assembly lacks a reviewed wall location'});return
        sizes={lengths[r] for r in member_runs};cut=max(sizes)
        choices=[s for s in stocks if s['length_inches']>=cut]
        if not choices:
            pending.append({'id':identity,'required_inches':cut,'reason':'No compatible full-length stock; no splice assumed'});return
        stock=min(choices,key=lambda s:(not s['precut'],s['length_inches'],s['sku']))
        members.append({'id':identity,'source_id':source,'kind':kind,'runs':sorted(member_runs),
            'cut_inches':None if kind=='jack_studs' else cut,'mixed_height_upper_bound':len(sizes)>1,
            'sku':stock['sku'],'stock_length_ft':stock['length_inches']/12})
    for station in field['field_studs']:
        if station['assembly_owners']:raise ValueError('Reserved stations are not additional field studs')
        add('field:'+station['id'],station['id'],'field', [station['run']])
    for assembly in assemblies['components']:
        names={assembly['id'],*aliases.get(assembly['id'],[])}
        member_runs={z['run'] for z in field['zones'] if z['assembly'] in names}
        for kind in ('king_studs','junction_studs')+(('jack_studs',) if jack_stock_allowance else ()):
            count=assembly['quantities'].get(kind,0)
            if type(count) is not int or count<0:raise ValueError('Whole nonnegative assembly counts required')
            for n in range(count):add(f'{kind}:{assembly["id"]}:{n+1}',assembly['id'],kind,member_runs)
    full_height=[m for m in members if m['kind']!='jack_studs']
    blanks=[m for m in members if m['kind']=='jack_studs']
    if jack_stock_allowance and len(blanks)+sum(p['id'].startswith('jack_studs:') for p in pending)!=assemblies['component_totals'].get('jack_studs',0):
        raise ValueError('Jack assembly details do not match the total')
    boards=pack_sawn_cuts(full_height)
    for member in blanks:
        member['basis']='One whole blank sized to the adjoining wall; installed jack cut length unresolved. No offcut credit.'
        boards.append({'id':f'B{len(boards)+1:03}','sku':member['sku'],
            'length_ft':member['stock_length_ft'],'remaining_inches':0,
            'cuts':[{'piece_id':member['id'],'cut_inches':None,
                     'consumed_inches':member['stock_length_ft']*12,'allocation_only':True}]})
    counts=Counter(b['sku'] for b in boards)
    return {'status':'Partial full-height stud stock scenario; wall-height decision remains open',
        'wall_height_inches':wall_height_inches,'plate_inches':plate_inches,
        'members':members,'boards':boards,'stock_quantities':dict(sorted(counts.items())),
        'full_height_members':len(full_height),'member_counts':dict(Counter(m['kind'] for m in members)),
        'mixed_height_allowance_members':sum(m['mixed_height_upper_bound'] for m in members),
        'pending_members':pending,'jack_stock_allowance':jack_stock_allowance,
        'jack_stock_blanks':len(blanks),'jack_cut_lengths_unresolved':len(blanks),
        'jack_studs_not_included':assemblies['component_totals'].get('jack_studs',0)-len(blanks),
        'complete_stud_order_quantity':None,'purchase_order_released':False,
        'basis':['Precut stock where long enough; otherwise shortest listed full-length stock.',
                 'Mixed-height junctions use the taller adjoining wall for the whole existing allowance; this is a stock upper bound, not a construction cut detail.',
                 'No speculative shared-member or offcut credit; reserved field stations are excluded.',
                 'Jack stock, when enabled, reserves one whole wall-height blank per counted jack; no installed cut length or offcut reuse is inferred.',
                 'Cripples, unresolved exterior supports, gables, special framing and kit-supplied members remain separate.']}
