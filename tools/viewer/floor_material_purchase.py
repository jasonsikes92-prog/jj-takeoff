"""Pool one reviewed flooring product into whole cartons before allocating room costs."""
import copy
import hashlib
import json
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path


def carton_allocation(areas, coverage, waste):
    raw = [*areas, coverage, waste]
    if any(type(value) not in (int, float) for value in raw):
        raise ValueError('Carton inputs must be finite numbers')
    values = [Decimal(str(value)) for value in raw]
    if any(not value.is_finite() for value in values):
        raise ValueError('Carton inputs must be finite numbers')
    net, cover, percent = values[:-2], values[-2], values[-1]
    if not net or any(value < 0 for value in net) or cover <= 0 or percent < 0:
        raise ValueError('Cartons need nonnegative areas/waste and positive coverage')
    total = sum(net)
    required = total * (1 + percent / 100)
    cartons = int((required / cover).to_integral_value(rounding=ROUND_CEILING))
    purchased = cartons * cover
    # These are financial area allocations, not separate room orders. Preserve
    # every purchased hundredth-SF using the largest remainders, ties by row order.
    if purchased != purchased.quantize(Decimal('.01')):
        raise ValueError('Carton coverage needs whole hundredths of square feet')
    shares = [purchased * area / total if total else Decimal(0) for area in net]
    units = [(share * 100).to_integral_value(rounding=ROUND_FLOOR) for share in shares]
    remaining = int(purchased * 100 - sum(units))
    order = sorted(range(len(net)), key=lambda i: (-(shares[i] * 100 - units[i]), i))
    for i in order[:remaining]: units[i] += 1
    return dict(cartons=cartons, required_sf=float(required), purchased_sf=float(purchased),
                allocated_sf=[float(value / 100) for value in units])


def apply_material_purchase(draft, config, folder):
    root = Path(folder).resolve()
    def checked(ref):
        path = (root / ref['file']).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != ref['sha256']:
            raise ValueError('Floor carton evidence changed')
        return path
    proof = json.loads(checked(config).read_bytes())
    checked(proof['source_document'])
    review = draft['floor_finish_review']; billing = review['billing_review']
    groups = review['cost_allocation']['groups']; ids = [g['cost_rows'][0] for g in groups]
    if (proof['plan_sha256'] != draft['plan_sha256'] or proof['material_cost_owner_ids'] != ids
            or proof.get('basis') != 'dated_invoice_carton_allowance' or not proof.get('product_sku')
            or proof.get('current_carton_spec_verified') is not False):
        raise ValueError('Floor cartons need one explicit dated product and all material cost owners')
    result = carton_allocation([g['net_sf'] for g in groups], proof['coverage_sf'], billing['material_waste_pct'])
    rows = {r['row_id']: r for r in draft['rows']}
    planned = []
    for group, quantity in zip(groups, result['allocated_sf']):
        row = rows[group['cost_rows'][0]]
        if (row['cost_type'] not in ('MATERIAL','ALLOWANCE') or row['unit'] not in ('SF','sq ft','ft2')
                or row.get('draft_quantity') is not None or row.get('quantity_sources')
                or row.get('covered_by_package') or row.get('line_cost') is not None
                or len(row.get('assembly_inputs', [])) != 1 or row['assembly_inputs'][0]['id'] != group['id']):
            raise ValueError('Floor cartons need distinct unpriced material owners')
        part = copy.deepcopy(row['assembly_inputs'][0])
        part.update(use='template_quantity', kind='pooled_floor_cartons', quantity=quantity,
                    measured_quantity=group['net_sf'], rounding='pooled_whole_cartons_then_area_allocation',
                    product_sku=proof['product_sku'], purchase_source=copy.deepcopy(config),
                    pooled_cartons=result['cartons'], coverage_sf=proof['coverage_sf'],
                    basis='Whole cartons for the shared product after owner waste; purchased SF allocated by installed room area. This row is a cost allocation, not a separate room order.',
                    remaining=['Dated invoice carton allowance; confirm current carton specification, stock and delivery before ordering. Original invoice quantity discrepancy remains unresolved.'],
                    certified=False, order_released=False)
        planned.append((row, part))
    for row, part in planned:
        row.update(draft_quantity=part['quantity'], quantity_sources=[part])
    review['material_purchase'] = {**result, 'coverage_sf':proof['coverage_sf'], 'product_sku':proof['product_sku'],
        'material_cost_owner_ids':ids, 'source':copy.deepcopy(config), 'basis':proof['basis'],
        'current_carton_spec_verified':False, 'order_released':False}
