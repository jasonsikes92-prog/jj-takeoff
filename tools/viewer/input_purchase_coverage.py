"""Recognize an input already included in a priced, source-bound combined count."""
import copy
import math
from estimating_price_review import accepted_estimating_price
from component_allowances import quantity_binding


def owner_source(quantity):
    source = quantity.get('source', {})
    return (quantity.get('source_kind') == 'owner_confirmation'
            and all(isinstance(source.get(k), str) and source[k] for k in ('file', 'sha256', 'field'))
            and len(source['sha256']) == 64)


def same_input(left, right):
    # Linked reviews carry different destination rows but must retain the same
    # actual source, quantity, units, geometry and review revision.
    def source(value):
        value = copy.deepcopy(value)
        for key in ('template_rows', 'source_template_rows'):
            value.pop(key, None)
        value.get('linked_review', {}).pop('template_row_mapping', None)
        return value
    return source(left) == source(right)


def purchase_coverage(quantity, rows):
    """Return diagnostics only; never assign a price or certify a measurement.

    Inputs have already passed their source importers. Zero counts must be
    explicit owner decisions; ordinary measured zeros still require review.
    """
    if type(quantity.get('quantity')) is int and quantity['quantity'] == 0 and owner_source(quantity):
        return {'status': 'owner_excluded', 'source': copy.deepcopy(quantity['source'])}
    owners = []
    for row in rows:
        if (row.get('pricing_basis') != 'dated_component_allowance'
                or row.get('pricing_role') == 'input_only' or row.get('covered_by_package')
                or row.get('cost_owner_row_id') or not accepted_estimating_price(row)
                or row.get('price_evidence', {}).get('reviewed_quantity_binding') != quantity_binding(row)):
            continue
        sources = row.get('quantity_sources', [])
        if len(sources) != 1:
            continue
        source = sources[0]
        parts = source.get('included_assembly_inputs', [])
        count = source.get('owner_confirmed_count')
        if (source.get('source_kind') != 'owner_and_measured_count' or source.get('unit') != 'EA'
                or type(count) is not int or count < 0 or not parts
                or any(type(p.get('quantity')) not in (int, float) or not math.isfinite(p['quantity']) or p['quantity'] < 0
                       or p['quantity'] != int(p['quantity']) or p.get('unit') != 'EA' for p in parts)
                or count + sum(p['quantity'] for p in parts) != source.get('quantity')
                or source['quantity'] != row.get('draft_quantity')):
            continue
        measured = any(same_input(quantity, part) for part in parts)
        confirmed = (owner_source(quantity) and quantity.get('unit') == 'EA'
                     and type(quantity.get('quantity')) is int and quantity['quantity'] == count
                     and quantity['source'] == source.get('source'))
        if measured or confirmed:
            owners.append(row['row_id'])
    if owners:
        return {'status': 'covered' if len(owners) == 1 else 'duplicate', 'owner_row_ids': owners}
    return None
