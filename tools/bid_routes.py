"""Verify that template scope routes use the active indexed bid drafts."""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path


def supplemental_scope_digest(row):
    keys=('row_id','name','parent_row_id','source_row_id','source_assembly_input_id',
          'replaces_row_id','draft_quantity','unit','covered_by_package','cost_owner_row_id',
          'package_scope_id','installed_scope')
    return hashlib.sha256(json.dumps({k:row.get(k) for k in keys},allow_nan=False,
                                    sort_keys=True,separators=(',',':')).encode()).hexdigest()


def supplemental_bid_entry(row,note):
    """Render current scope and quantity without presenting it as a released order."""
    identity=row['row_id'];quantity=row.get('draft_quantity')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',identity):raise ValueError('Invalid supplemental scope identity')
    if not isinstance(note,str) or not note.strip() or '\n' in note or '\r' in note:
        raise ValueError('Supplemental bid scope needs one explicit responsibility note')
    if quantity is not None and (type(quantity) not in (int,float) or not math.isfinite(quantity) or quantity<0):
        raise ValueError('Supplemental quantity must be finite, nonnegative or unresolved')
    amount='Unresolved' if quantity is None else format(quantity,'.12g')
    cell=lambda v:str(v).replace('|','\\|').replace('\n',' ').replace('\r',' ')
    return f"| {cell(row['name'])} <!-- estimate-scope:{identity} --> | {amount} {cell(row['unit'])} | {cell(note)} |"


def validate_supplemental_routes(coverage,draft,index_path,files):
    rows={r['row_id']:r for r in draft.get('additional_cost_rows',[])}
    routes=coverage.get('supplemental_cost_routes',[]);errors=[]
    if not isinstance(routes,list):return ['Supplemental cost routes must be a list']
    identities=[r['row_id'] for r in routes]
    if len(set(identities))!=len(identities):errors.append('Duplicate supplemental cost routes')
    if set(identities)!=set(rows):
        errors.append(f'Supplemental bid scope must cover every current cost row: {len(set(rows)-set(identities))} missing, {len(set(identities)-set(rows))} unknown')
    bodies={p:p.read_text(encoding='utf-8') for p in files if p.is_file()}
    for route in routes:
        identity=route['row_id'];row=rows.get(identity)
        if row is None:continue
        path=(index_path.parent/route.get('draft_file','')).resolve()
        if path not in bodies or not route.get('draft_owner') or route.get('status')!='draft_scope_routed':
            errors.append(f'Supplemental {identity} needs an indexed responsible trade draft');continue
        if (route.get('quantity_or_price_verified_by_routing') is not False
                or route.get('scope_binding')!=supplemental_scope_digest(row)):
            errors.append(f'Supplemental {identity} scope or quantity changed; renew its bid entry');continue
        entry=supplemental_bid_entry(row,route.get('scope_note'))
        marker=f'<!-- estimate-scope:{identity} -->'
        if entry not in bodies[path] or sum(body.count(marker) for body in bodies.values())!=1:
            errors.append(f'Supplemental {identity} must appear once with its current quantity and responsibility in its owning bid')
    return errors


def reconcile_applicability(coverage, draft):
    """Keep reviewed exclusions as references, not requested trade scope."""
    result = copy.deepcopy(coverage)
    sources = {str(row['excel_row']): row for row in draft['rows']}
    identities = [str(row['excel_row']) for row in result['rows']]
    if (len(sources) != len(draft['rows']) or len(set(identities)) != len(identities)
            or set(identities) != set(sources)):
        raise ValueError('Bid routes must cover the same unique template rows as the draft')
    if not draft.get('plan_sha256') or type(draft.get('measurement_version')) is not int:
        raise ValueError('A source-bound draft is required')
    prior = result.get('applicability_basis')
    if prior and prior['plan_sha256'] != draft['plan_sha256']:
        raise ValueError('Different plan requires a new bid scope review')
    for index, route in enumerate(result['rows']):
        source = sources[str(route['excel_row'])]
        if source.get('name') != route.get('name') or source.get('parent') != route.get('parent'):
            raise ValueError('Bid row identity or scope changed')
        baseline = copy.deepcopy(route.get('route_before_exclusion', route))
        if source.get('completion_status') == 'not_applicable_source_reviewed':
            review = source.get('applicability_review', {})
            if (review.get('status') != 'excluded_by_review' or not review.get('reason')
                    or not review.get('sources') or review.get('row_id') != source['row_id']
                    or any(source.get(k) is not None for k in ('draft_quantity', 'unit_cost', 'line_cost', 'line_price'))):
                raise ValueError('Excluded bid scope requires unpriced, reviewed source evidence')
            route = copy.deepcopy(baseline)
            route.update(status='not_applicable_source_reviewed', draft_file=None,
                         excluded_scope_reference=baseline.get('draft_file'),
                         route_before_exclusion=baseline, applicability_review=copy.deepcopy(review))
        elif 'route_before_exclusion' in route:
            # A changed or withdrawn decision must not silently remain excluded.
            route = baseline
            route['status'] = 'scope_review_required'
            route['scope_review_reason'] = 'Previous exclusion no longer applies; review before requesting a bid.'
        result['rows'][index] = route
    result['applicability_basis'] = {k: draft[k] for k in ('plan_sha256', 'measurement_version')}
    return result


def validate(index_path):
    index_path = Path(index_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    coverage = json.loads((index_path.parent / index["coverage"]).read_text(encoding="utf-8"))
    files = [(index_path.parent / name).resolve() for name in index["files"]]
    errors = []
    if len(set(files)) != len(files):
        errors.append("Duplicate indexed draft paths")
    for path in files:
        if not path.is_file():
            errors.append(f"Missing indexed draft: {path}")
    ids = [row["excel_row"] for row in coverage["rows"]]
    if len(set(ids)) != len(ids):
        errors.append("Duplicate template row IDs")
    routed = 0
    for row in coverage["rows"]:
        name = row.get("draft_file")
        if row['status'] == 'not_applicable_source_reviewed':
            if name or not row.get('applicability_review') or 'route_before_exclusion' not in row:
                errors.append(f"Row {row['excel_row']} exclusion lacks evidence or still requests scope")
            reference = row.get('excluded_scope_reference')
            if reference and (index_path.parent / reference).resolve() not in files:
                errors.append(f"Row {row['excel_row']} exclusion references an unindexed draft")
        if row["status"] == "draft_scope_routed" and not name:
            errors.append(f"Row {row['excel_row']} has no draft path")
        if name:
            routed += 1
            if (index_path.parent / name).resolve() not in files:
                errors.append(f"Row {row['excel_row']} routes to an unindexed draft: {name}")
    additional = coverage.get('additional_scopes', [])
    required = index.get('required_additional_scope_ids', [])
    if (len(required) != len(set(required))
            or set(required) != {scope.get('id') for scope in additional}):
        errors.append('Required additional scopes do not match bid coverage')
    scope_ids = set()
    for scope in additional:
        identity = scope.get('id')
        if not isinstance(identity, str) or not identity.strip() or identity in scope_ids:
            errors.append('Missing or duplicate additional scope ID')
        scope_ids.add(identity)
        name = scope.get('draft_file')
        if not name or (index_path.parent / name).resolve() not in files:
            errors.append(f'Additional scope {identity} has no indexed draft')
        if (scope.get('status') != 'draft_scope_routed' or not scope.get('name')
                or not scope.get('draft_owner') or scope.get('quantity_or_price_verified_by_routing') is not False):
            errors.append(f'Additional scope {identity} needs an explicit unverified bid assignment')
        source = scope.get('source_review', {})
        path = (index_path.parent / source.get('file', '')).resolve()
        if (not path.is_relative_to(index_path.parent.parent.resolve()) or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != source.get('sha256')):
            errors.append(f'Additional scope {identity} source is missing or changed')
            continue
        review = json.loads(path.read_text(encoding='utf-8'))
        basis = coverage.get('applicability_basis', {})
        if (review.get('scope_id') != identity or not basis.get('plan_sha256')
                or any(review.get(k) != basis.get(k) for k in ('plan_sha256', 'measurement_version'))):
            errors.append(f'Additional scope {identity} source belongs to another scope or revision')
    estimate_basis_checked=False;estimate_snapshot_sha256=None
    if coverage.get('supplemental_cost_routes') and 'published_estimate' not in index:
        errors.append('Supplemental cost routes require the current published estimate binding')
    if 'published_estimate' in index:
        try:
            reference=index['published_estimate']
            workspace=(index_path.parent/reference['workspace']).resolve()
            checkpoint_path=(index_path.parent/reference['checkpoint']).resolve()
            if not checkpoint_path.is_relative_to(workspace):
                raise ValueError('Estimate checkpoint is outside its workspace')
            checkpoint=json.loads(checkpoint_path.read_bytes())
            book=(workspace/checkpoint['current_workbook']).resolve()
            if not book.is_relative_to(workspace):raise ValueError('Estimate workbook is outside its workspace')
            snapshot=json.loads(book.with_name('source_snapshot.json').read_bytes())
            body={k:snapshot[k] for k in ('draft','readiness')}
            digest=hashlib.sha256(json.dumps(body,allow_nan=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if digest!=snapshot['snapshot_sha256'] or digest!=checkpoint['live_snapshot_sha256']:
                raise ValueError('Published estimate snapshot is missing its current content binding')
            expected=reconcile_applicability(coverage,snapshot['draft'])
            for prior,current in zip(coverage['rows'],expected['rows']):
                if prior!=current:errors.append(f"Row {prior['excel_row']} bid scope is stale against the published estimate")
            if coverage.get('applicability_basis')!=expected['applicability_basis']:
                errors.append('Bid scope revision is stale against the published estimate')
            errors.extend(validate_supplemental_routes(coverage,snapshot['draft'],index_path,files))
            estimate_basis_checked=True;estimate_snapshot_sha256=digest
        except (OSError,ValueError,KeyError,TypeError) as exc:
            errors.append('Cannot verify bid scope against published estimate: '+str(exc))
    return {"valid": not errors, "indexed_drafts": len(files),
            "template_rows": len(ids), "routed_rows": routed,
            "additional_scopes": len(additional), "estimate_basis_checked":estimate_basis_checked,
            "supplemental_cost_routes":len(coverage.get('supplemental_cost_routes',[])),
            "estimate_snapshot_sha256":estimate_snapshot_sha256,"errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    result = validate(parser.parse_args().index)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)
