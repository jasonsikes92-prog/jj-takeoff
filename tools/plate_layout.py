"""Lay out two staggered top plates and one full bottom plate per measured run."""
import math
from collections import Counter
if __package__:
    from .linear_stock import pack_sawn_cuts
else:
    from linear_stock import pack_sawn_cuts


def layout(run_id, length_inches, stock_inches=192, stagger_inches=96):
    if any(type(v) not in (int, float) or not math.isfinite(v)
           for v in (length_inches, stock_inches, stagger_inches)):
        raise ValueError('Finite lengths required')
    if length_inches <= 0 or stock_inches <= 0:
        raise ValueError('Lengths must be positive')
    if any(abs(v * 8 - round(v * 8)) > 1e-8 for v in (stock_inches, stagger_inches)):
        raise ValueError('Stock and stagger must follow the eighth-inch cutting increment')
    if not 24 <= stagger_inches <= stock_inches - 24:
        raise ValueError('Stagger must leave at least 24 inches between layer joints')
    result = []
    for layer, first_length in [('top_lower', stock_inches), ('top_upper', stagger_inches), ('bottom', stock_inches)]:
        start = 0
        index = 0
        while start < length_inches - 1e-8:
            end = min(length_inches, start + (first_length if index == 0 else stock_inches))
            result.append({'id': f'{run_id}-{layer}-{index+1:02}', 'run': run_id, 'layer': layer,
                           'from_inches': start, 'to_inches': end,
                           'cut_inches': math.ceil((end-start)*8-1e-8)/8})
            start = end
            index += 1
    return result


def stock_study(runs, material_groups, stock_inches=192, stagger_inches=96, kerf_inches=.125,
                bottom_material_groups=None):
    """Straight-run estimating cuts; connection ends and treatment stay separate."""
    if set(material_groups) != {'top', 'bottom'}:
        raise ValueError('Separate top and bottom material groups required')
    if (any(not isinstance(v, str) or not v.strip() for v in material_groups.values())
            or material_groups['top'] == material_groups['bottom']):
        raise ValueError('Top and bottom groups must remain distinct until treatment review')
    if not runs:
        raise ValueError('Measured wall runs required')
    overrides={} if bottom_material_groups is None else bottom_material_groups
    if (not isinstance(overrides,dict) or set(overrides)-{r['id'] for r in runs}
            or any(not isinstance(v,str) or not v.strip() or v==material_groups['top'] for v in overrides.values())):
        raise ValueError('Bottom material assignments must name existing runs and stay separate from top plates')
    seen = set(); pieces = []
    for run in runs:
        identity = run['id']
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError('Unique wall run IDs required')
        seen.add(identity)
        for piece in layout(identity, run['length_inches'], stock_inches, stagger_inches):
            group = 'bottom' if piece['layer'] == 'bottom' else 'top'
            sku=overrides.get(identity,material_groups['bottom']) if group=='bottom' else material_groups['top']
            pieces.append({**piece, 'sku':sku,
                           'stock_length_ft':stock_inches / 12})
    boards = pack_sawn_cuts(pieces, kerf_inches)
    return {'runs':runs, 'pieces':pieces, 'boards':boards,
        'summary':{'run_lf':math.fsum(r['length_inches'] for r in runs) / 12,
                   'three_layer_net_lf':math.fsum(r['length_inches'] for r in runs) / 4,
                   'cut_pieces':len(pieces), 'candidate_whole_sticks':len(boards),
                   'stock_lf':len(boards) * stock_inches / 12,
                   'stock_by_material_group':dict(Counter(b['sku'] for b in boards))},
        'basis':{'stock_inches':stock_inches, 'stagger_inches':stagger_inches,
                 'kerf_inches':kerf_inches, 'cut_rounding_inches':.125,
                 'top_layers':2, 'bottom_layers':1},
        'remaining':['Resolve corner/intersection end cuts and overlaps.',
                     'Assign bottom-plate treatment and compatible fastening.',
                     'Add applicable gable, tall-wall and roof-support plates.',
                     'Verify structural connections and current stock availability.'],
        'purchase_quantity':None, 'complete_framing_total':None,
        'price_applied':False, 'optimality_proven':False}
