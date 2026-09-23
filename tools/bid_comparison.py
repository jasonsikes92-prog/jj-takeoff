"""Compare explicitly reviewed trade quotes against one source-bound scope revision."""
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from quote_pricing_review import review_pricing


def scope_digest(scope):
    return hashlib.sha256(json.dumps({k:v for k,v in scope.items() if k!='scope_sha256'},sort_keys=True,allow_nan=False).encode()).hexdigest()


def required_scope_items(scope):
    items=[*scope['items'],*[{'id':'requirement:'+r['id'],'label':r['request']}
        for r in scope.get('scope_requirements',[])]]
    ids=[i['id'] for i in items]
    if not ids or any(not isinstance(i,str) or not i.strip() for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Scope IDs must be unique and nonempty')
    return items


def compare_quotes(scope, quotes, as_of, evidence_root):
    """No keyword inference, omitted-item pricing, winning bid or order release."""
    today=date.fromisoformat(as_of);root=Path(evidence_root).resolve()
    required={s['id']:s for s in required_scope_items(scope)}
    if not scope.get('plan_sha256') or type(scope.get('measurement_version')) is not int or scope['measurement_version']<1:
        raise ValueError('Source drawing and positive measurement version required')
    digest=scope_digest(scope);results=[];seen=set()
    for quote in quotes:
        if not quote.get('id') or quote['id'] in seen:raise ValueError('Unique quote IDs required')
        seen.add(quote['id'])
        source=(root/quote['source_file']).resolve()
        if not source.is_relative_to(root) or not source.is_file():raise ValueError('Quote evidence must be within evidence root')
        if hashlib.sha256(source.read_bytes()).hexdigest()!=quote['source_sha256']:raise ValueError('Quote evidence changed')
        confirmation=quote.get('scope_confirmation')
        if confirmation is not None:
            confirmation_path=(root/confirmation['source_file']).resolve()
            if (not confirmation_path.is_relative_to(root) or not confirmation_path.is_file()
                    or hashlib.sha256(confirmation_path.read_bytes()).hexdigest()!=confirmation['source_sha256']):
                raise ValueError('Quote scope confirmation evidence changed')
        issues=[];current_issues=[]
        if scope.get('unresolved_opening_ids'):
            issues.append('Opening locations or interpretations remain unresolved in the source scope; quote inclusion alone cannot resolve the drawing review')
        if quote.get('reviewed_scope_sha256')!=digest:issues.append('Scope or measurement revision needs a new review')
        if quote.get('reviewed') is not True:issues.append('Quote extraction has not been reviewed')
        if quote.get('evidence_kind') not in ('current_supplier_quote','current_subcontractor_quote'):
            current_issues.append('Historical or unclassified evidence is not current pricing')
        issued=date.fromisoformat(quote['date']) if quote.get('date') else None
        expires=date.fromisoformat(quote['valid_through']) if quote.get('valid_through') else None
        if expires is not None and issued is not None and expires<issued:raise ValueError('Quote expires before issue date')
        if issued is None:issues.append('Quote issue date is unconfirmed')
        elif issued>today:issues.append('Quote issue date is in the future')
        if not isinstance(quote.get('supplier'),str) or not quote['supplier'].strip():
            issues.append('Supplier identity is unconfirmed')
        if expires is None:current_issues.append('Quote validity is unconfirmed')
        elif expires<today:current_issues.append('Printed validity date has passed; follow up on whether the supplier still honors the quoted price')
        if quote.get('currency')!='USD':issues.append('Currency is not confirmed USD')
        amount=quote.get('total')
        if amount is not None:
            if isinstance(amount,bool):raise ValueError('Invalid quote total')
            try:amount=Decimal(str(amount))
            except InvalidOperation as exc:raise ValueError('Invalid quote total') from exc
            if not amount.is_finite() or amount<0:raise ValueError('Invalid quote total')
        else:issues.append('Package total is unknown')
        assignments={};orphaned=[];assigned_ids=set()
        for item in quote.get('scope_items',[]):
            identity=item['scope_id']
            if identity in assigned_ids:raise ValueError('Unknown or duplicate quoted scope')
            assigned_ids.add(identity)
            if item['status'] not in ('included','excluded','allowance','unknown'):raise ValueError('Invalid scope status')
            if item['status']!='unknown' and (not isinstance(item.get('source_ref'),str) or not item['source_ref'].strip()):
                raise ValueError('Scope assertion needs a source location')
            if identity not in required:
                if quote.get('reviewed_scope_sha256')==digest:raise ValueError('Unknown or duplicate quoted scope')
                orphaned.append(item);issues.append('Previously quoted scope is absent from the current revision: '+identity)
            else:assignments[identity]=item
        matrix=[]
        for identity,item in required.items():
            match=assignments.get(identity,{'status':'unknown','source_ref':None})
            matrix.append({'scope_id':identity,'label':item['label'],'status':match['status'],
                'source_ref':match.get('source_ref'),'note':match.get('note','')})
            if match['status']!='included':issues.append(item['label']+': '+match['status'])
        pricing=({'issues':['Pricing lines need review against the current scope revision'],'charged_line_total':None}
            if quote.get('reviewed_scope_sha256')!=digest and (scope.get('requires_pricing_basis_review') or quote.get('pricing_lines'))
            else review_pricing(scope,quote))
        if pricing is not None:issues.extend(pricing['issues'])
        results.append({'id':quote['id'],'supplier':quote['supplier'],
            'quoted_total':str(amount) if amount is not None else None,'currency':quote.get('currency'),
            'scope_matrix':matrix,'comparison_issues':issues+current_issues,
            'same_scope_current_quote':not (issues+current_issues),
            'same_scope_dated_allowance':quote.get('evidence_kind')=='dated_supplier_allowance' and not issues,
            'date':quote.get('date'),
            **({'pricing_review':pricing} if pricing is not None else {}),
            **({'previous_scope_items_not_in_current_revision':orphaned} if orphaned else {}),
            **({'scope_confirmation':confirmation} if confirmation is not None else {}),
            'source_file':quote['source_file'],'source_sha256':quote['source_sha256'],
            'adjusted_total':None,'purchase_authorized':False})
    return {'scope_sha256':digest,'plan_sha256':scope['plan_sha256'],
        'measurement_version':scope['measurement_version'],'as_of':as_of,'quotes':results,
        'winner':None,'estimate_released':False,
        'note':'Missing scope and allowances remain explicit; package totals are not normalized by invented costs.'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope',required=True);parser.add_argument('--quotes',required=True)
    parser.add_argument('--evidence-root',required=True);parser.add_argument('--as-of',required=True)
    args=parser.parse_args()
    result=compare_quotes(json.loads(Path(args.scope).read_text(encoding='utf-8')),
        json.loads(Path(args.quotes).read_text(encoding='utf-8')),args.as_of,args.evidence_root)
    print(json.dumps(result,indent=2,allow_nan=False))
