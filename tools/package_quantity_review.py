"""Keep a verified billing-package count separate from physical takeoff approval."""
import copy
from estimating_price_review import price_binding


def record_package_quantity_review(row, plan_sha256, measurement_version):
    """Called by package pricing only after quote, count source and scope checks pass."""
    row['package_quantity_review'] = {
        'status': 'verified_billing_count', 'quantity': 1, 'unit': 'EA',
        'plan_sha256': plan_sha256, 'measurement_version': measurement_version,
        'row_sha256': price_binding(row),
        'source': copy.deepcopy(row['price_evidence']['package_count_review']),
        'scope': 'One documented billing package only; physical quantities and complete trade scope remain separate.'}


def current_package_quantity_review(row, plan_sha256, measurement_version):
    review = row.get('package_quantity_review', {})
    evidence = row.get('price_evidence', {})
    sources = row.get('quantity_sources', [])
    count_sources = [s for s in sources if s.get('kind') == 'documented_package_count']
    if (review.get('status') != 'verified_billing_count'
            or review.get('plan_sha256') != plan_sha256
            or review.get('measurement_version') != measurement_version
            or type(row.get('draft_quantity')) is not int or row['draft_quantity'] != 1
            or row.get('unit') not in ('each', 'EA') or row.get('unit_cost') is not None
            or row.get('pricing_basis') not in ('reviewed_package', 'dated_package_allowance')
            or row.get('covered_by_package') != row.get('row_id')
            or row.get('cost_owner_row_id') or row.get('completion_status','').startswith('not_applicable')
            or evidence.get('billing_basis') != 'fixed_package'
            or not evidence.get('package_count_review')
            or review.get('source') != evidence['package_count_review']
            or len(count_sources) != 1
            or count_sources[0].get('source') != review['source']
            or type(count_sources[0].get('quantity')) is not int or count_sources[0]['quantity'] != 1
            or count_sources[0].get('unit') != 'EA' or not count_sources[0].get('basis')):
        return False
    try:
        return review.get('row_sha256') == price_binding(row)
    except (TypeError, ValueError):
        return False
