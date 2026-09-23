"""Read a source-bound, per-page review before new-plan measurement.

The record attests to visual review; file hashes cannot prove a person looked.
Coverage approval does not certify scale, scope, quantities or prices.
"""
import hashlib
import json
from pathlib import Path
import fitz


def read_sheet_review(job):
    from jnj_takeoff import SheetLedger
    job = Path(job).resolve()
    path = job / 'sheet_review.json'
    if not path.is_file():
        raise ValueError('Complete the full-sheet review before measurement')
    review = json.loads(path.read_text(encoding='utf-8'))
    digest = hashlib.sha256((job / 'plan.pdf').read_bytes()).hexdigest()
    if review.get('plan_sha256') != digest:
        raise ValueError('Sheet review belongs to another drawing')
    if not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip():
        raise ValueError('Sheet reviewer identity required')
    with fitz.open(job / 'plan.pdf') as doc:
        count = len(doc)
    ledger = SheetLedger(str(job / 'plan.pdf'), count)
    index = review.get('cover_index')
    if not isinstance(index, list):
        raise ValueError('Record the cover index, or an empty list with a no-index explanation')
    if not index and not review.get('no_index_reason'):
        raise ValueError('Explain why no cover index is available')
    if any(not isinstance(row, list) or len(row) != 2 or
           not isinstance(row[1], str) or not row[1].strip() for row in index):
        raise ValueError('Invalid cover index entry')
    ledger.set_index(index)
    pages = review.get('pages')
    if not isinstance(pages, list):
        raise ValueError('Per-page visual review required')
    seen = set()
    roles = {}
    mapping = {'foundation': 'foundation', 'floor_plan': 'floor',
               'roof_plan': 'roof', 'electrical': 'electrical',
               'site': 'site', 'elevation': 'elevations', 'framing': 'framing'}
    for page in pages:
        number = page.get('page')
        if type(number) is not int or not 1 <= number <= count or number in seen:
            raise ValueError('Invalid or repeated reviewed PDF page')
        seen.add(number)
        relative = page.get('view')
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError('Review image must be inside the job')
        view = (job / relative).resolve()
        if not view.is_relative_to(job) or not view.is_file():
            raise ValueError('Review image missing or outside the job')
        if hashlib.sha256(view.read_bytes()).hexdigest() != page.get('view_sha256'):
            raise ValueError('Reviewed image has changed')
        role = page.get('role')
        ledger.examine(number - 1, role, str(view), page.get('title'), page.get('note'))
        mapped = mapping.get(role)
        # A generic schedule must not be mistaken for a floor-area schedule.
        if role == 'schedule' and page.get('area_schedule') is True:
            mapped = 'area_schedule'
        if mapped:
            roles.setdefault(mapped, []).append(number)
    passed, report = ledger.certify()
    issues = review.get('unresolved_issues')
    if not isinstance(issues, list) or any(not isinstance(i, str) or not i.strip() for i in issues):
        raise ValueError('Explicit unresolved sheet issues list required')
    missing = [role for role in ledger.ROLES if not ledger.pages_with_role(role)
               and (role in ledger.CORE or
                    (role in ledger.INDEXED and ledger._index_expects(role)))]
    unique = {k: v[0] for k, v in roles.items() if len(v) == 1}
    coverage_passed = passed and not issues
    scope = review.get('partial_measurement_review')
    selected = unique if coverage_passed else {}
    if scope is not None:
        # This attests only to candidate extraction from specific supplied pages.
        # Re-acknowledge changed coverage issues; never turn partial into complete.
        if not isinstance(scope, dict) or not isinstance(scope.get('basis'), str) or not scope['basis'].strip():
            raise ValueError('Partial measurement review requires a scope basis')
        if ledger.unexamined():
            raise ValueError('Examine every supplied page before selecting partial measurement scope')
        selected = scope.get('role_pages')
        allowed=dict(unique)
        if 'floor_level' in scope:
            level=scope['floor_level'];page=level.get('page')
            others=[p for p in roles.get('floor',[]) if p!=page]
            if (not isinstance(level.get('id'),str) or not level['id'].strip()
                    or type(page) is not int or page not in roles.get('floor',[])
                    or level.get('other_floor_pages')!=others
                    or selected!={'floor':page}):
                raise ValueError('Level scope must select one reviewed floor page and acknowledge every other level page')
            allowed['floor']=page
        if not isinstance(selected, dict) or not selected or any(
                role not in allowed or type(page) is not int or allowed[role] != page
                for role, page in selected.items()):
            raise ValueError('Partial measurement must select unambiguous reviewed role pages')
        if scope.get('unresolved_issues') != issues or scope.get('missing_roles') != missing:
            raise ValueError('Partial measurement review must acknowledge current coverage issues')
    return {'plan_sha256': digest, 'review_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'coverage_passed': passed and not issues, 'reviewed_pages': len(seen),
            'unexamined_pages': [i + 1 for i in ledger.unexamined()],
            'missing_roles': missing,
            'measurement_allowed': coverage_passed or scope is not None,
            'measurement_scope': 'reviewed_subset' if scope is not None else
                                 'reviewed_set' if coverage_passed else 'blocked',
            'measurement_role_pages': selected,
            'floor_level':scope.get('floor_level') if scope is not None else None,
            'page_count': count, 'coverage_report': report, 'unresolved_issues': issues,
            'role_candidates': roles,
            'unique_role_pages': unique,
            'roles_requiring_disambiguation': {k: v for k, v in roles.items() if len(v) > 1}}
