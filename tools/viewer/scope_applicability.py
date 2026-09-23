"""Apply explicit, source-backed project exclusions without deleting template rows."""
import copy
import hashlib
import math
from pathlib import Path


def apply_applicability(draft, decisions, evidence_root):
    result = copy.deepcopy(draft)
    rows = {r['row_id']: r for r in result['rows']}
    if len(rows) != len(result['rows']):
        raise ValueError('Duplicate template row identity')
    root = Path(evidence_root).resolve()
    if not isinstance(decisions.get('reviewer'), str) or not decisions['reviewer'].strip():
        raise ValueError('Applicability reviewer identity required')
    current = (decisions.get('plan_sha256') == draft['plan_sha256'] and
               decisions.get('measurement_version') == draft['measurement_version'])
    claimed = set()
    reviews = []
    zero_inputs = decisions.get('zero_area_inputs', [])
    zero_ids = {d['row_id'] for d in zero_inputs}
    for decision in decisions['exclusions'] + zero_inputs:
        identity = decision['row_id']
        if identity in claimed or identity not in rows:
            raise ValueError('Unknown or duplicate applicability row')
        claimed.add(identity)
        row = rows[identity]
        zero_area = identity in zero_ids
        if zero_area:
            if (row.get('pricing_role') != 'input_only' or row.get('parent', '').strip().upper() != 'INPUTS'
                    or row['unit'] not in ('ft2', 'sq ft', 'SF') or row['cost_type'] in ('GROUP', 'ASSEMBLY')):
                raise ValueError('Reviewed zero area requires a nonbillable area input')
            prior = row.get('quantity_sources', [])
            if (row.get('draft_quantity') == 0 and len(prior) == 1
                    and prior[0].get('kind') == 'reviewed_absent_floor_area'
                    and prior[0].get('row_id') == identity):
                row['draft_quantity'] = None
                row['quantity_sources'] = []
        elif row['cost_type'] in ('GROUP', 'ASSEMBLY') or row.get('pricing_role') == 'input_only':
            raise ValueError('Exclude explicit cost options, not groups, assemblies or inputs')
        if not isinstance(decision.get('reason'), str) or not decision['reason'].strip():
            raise ValueError('An explicit exclusion reason is required')
        sources = decision.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError('Exclusion source evidence required')
        valid = current
        for source in sources:
            path = (root / source['file']).resolve()
            if not path.is_relative_to(root):
                raise ValueError('Applicability source must be inside the evidence folder')
            valid = valid and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        review = {'row_id': identity, 'reason': decision['reason'], 'sources': sources,
                  'status': 'excluded_by_review' if valid else 'source_or_revision_changed_review_required'}
        if 'job_sources' in decision:
            dependencies=decision['job_sources']
            if not isinstance(dependencies,list) or not dependencies:
                raise ValueError('Job-dependent exclusion needs source files')
            job_root=root.parent
            for source in dependencies:
                path=(job_root/source['file']).resolve()
                if not path.is_relative_to(job_root):
                    raise ValueError('Applicability job source must stay inside the job')
                valid=valid and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==source['sha256']
            review['job_sources']=copy.deepcopy(dependencies)
            review['status']='excluded_by_review' if valid else 'source_or_revision_changed_review_required'
        if 'requires_mapped_cost_rows' in decision:
            selected = decision['requires_mapped_cost_rows']
            fields = ('row_id', 'name', 'parent', 'unit', 'cost_type')
            excluded_ids = {d['row_id'] for d in decisions['exclusions']}
            if (not isinstance(selected, list) or not selected
                    or any(not isinstance(s, dict) or any(not s.get(k) for k in fields) for s in selected)
                    or len({s['row_id'] for s in selected}) != len(selected)):
                raise ValueError('Alternative pricing needs unique explicit selected cost rows')
            for selection in selected:
                target = rows.get(selection['row_id'], {})
                quantity = target.get('draft_quantity')
                mapped = (type(quantity) in (int, float) and math.isfinite(quantity) and quantity > 0)
                if selection['row_id'] in excluded_ids:
                    raise ValueError('Selected pricing row is also configured as excluded')
                valid = (valid and all(target.get(k) == selection[k] for k in fields)
                         and target.get('cost_type') in ('MATERIAL', 'LABOR', 'SUBCONTRACTOR', 'EQUIPMENT', 'ALLOWANCE')
                         and not target.get('completion_status', '').startswith('not_applicable')
                         and (mapped or bool(target.get('assembly_inputs'))))
            review['requires_mapped_cost_rows'] = copy.deepcopy(selected)
            review['status'] = 'excluded_by_review' if valid else 'source_or_revision_changed_review_required'
        if valid:
            if (row.get('draft_quantity') is not None or row.get('assembly_inputs') or row.get('quantity_sources') or
                    row.get('covered_by_package') or row.get('cost_owner_row_id') or
                    any(row.get(k) is not None for k in ('unit_cost', 'line_cost', 'line_price'))):
                raise ValueError('Excluded option conflicts with mapped quantity, package or price: ' + identity)
            if zero_area:
                review['status'] = 'zero_area_reviewed'
                row['draft_quantity'] = 0
                row['quantity_sources'] = [{'kind': 'reviewed_absent_floor_area', 'row_id': identity,
                                            'quantity': 0, 'unit': 'SF', 'basis': decision['reason'],
                                            'sources': copy.deepcopy(sources), 'certified': False}]
                row['completion_status'] = 'zero_area_source_reviewed'
            else:
                row['completion_status'] = 'not_applicable_source_reviewed'
            row['next_check'] = decision['reason']
        elif zero_area or row.get('completion_status', '').startswith('not_applicable'):
            row['completion_status'] = 'applicability_review_required'
        row['applicability_review'] = review
        reviews.append(review)
    result['applicability_reviews'] = reviews
    return result
