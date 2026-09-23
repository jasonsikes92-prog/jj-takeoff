"""Record estimating acceptance after source validation, without certifying a quote."""
import hashlib
import json
from decimal import Decimal, InvalidOperation


def price_binding(row):
    keys = ('row_id', 'unit', 'draft_quantity', 'unit_cost', 'line_cost', 'line_price',
            'markup_pct', 'pricing_basis', 'price_evidence', 'quantity_sources',
            'assembly_inputs', 'covered_by_package', 'cost_owner_row_id',
            'completion_status', 'supplier_cost', 'purchase_tax', 'purchase_tax_percent')
    return hashlib.sha256(json.dumps({k: row.get(k) for k in keys},
        sort_keys=True, allow_nan=False).encode()).hexdigest()


def priced(row):
    for key in ('line_cost', 'line_price'):
        value = row.get(key)
        if value is None or isinstance(value, bool):
            return False
        try:
            amount = Decimal(str(value))
        except InvalidOperation:
            return False
        if not amount.is_finite() or amount < 0:
            return False
    return True


def accept_estimating_price(row, as_of, kind):
    """Call only after the owning importer validates sources and authorization."""
    row.pop('estimating_price_review', None)
    if kind not in ('authorized_dated_allowance', 'owner_estimating_rate'):
        raise ValueError('Unknown estimating price acceptance')
    if priced(row):
        row['estimating_price_review'] = {'kind': kind, 'as_of': as_of,
            'row_sha256': price_binding(row), 'current_supplier_quote': False}


def accepted_estimating_price(row):
    review = row.get('estimating_price_review', {})
    if review.get('kind') not in ('authorized_dated_allowance', 'owner_estimating_rate'):
        return False
    if not review.get('as_of') or not priced(row):
        return False
    try:
        return review.get('row_sha256') == price_binding(row)
    except (TypeError, ValueError):
        return False
