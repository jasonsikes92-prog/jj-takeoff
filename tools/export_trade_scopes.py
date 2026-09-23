"""Create current, unpriced trade scope schedules from a validated bid index."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from bid_routes import validate


def packages(index_path,index,coverage,snapshot):
    result={name:{'source_draft':str((index_path.parent/name).resolve()),'items':[],'excluded_items':[],
        'additional_scope':[],'plan_sha256':snapshot['draft']['plan_sha256'],
        'measurement_version':snapshot['draft']['measurement_version'],
        'snapshot_sha256':snapshot['snapshot_sha256'],'sent':False,'ready_to_order':False} for name in index['files']}
    rows={str(r['excel_row']):r for r in snapshot['draft']['rows']}
    durations=[r for r in rows.values() if r.get('name')=='PROJECT DURATION - # OF MONTHS'
        and r.get('parent','').strip().upper()=='INPUTS']
    if len(durations)>1:raise ValueError('Ambiguous project duration input')
    duration=None
    if durations:
        source=durations[0];value=source.get('draft_quantity')
        if value is not None:
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0 or source.get('unit')!='month':
                raise ValueError('Project duration needs positive months')
            duration={'months':value,'source_row_id':source['row_id']}
    for package in result.values():package['project_duration_reference']=duration
    supplemental={r['row_id']:r for r in snapshot['draft'].get('additional_cost_rows',[])}
    owners={r['row_id']:r for r in [*rows.values(),*supplemental.values()]}
    reviews={r['row_id']:r for r in snapshot['readiness']['rows']+snapshot['readiness'].get('additional_cost_rows',[])}
    def add(route,row):
        package=result[route['draft_file']];package['trade']=route['draft_owner']
        if row.get('completion_status','').startswith('not_applicable'):
            if any(row.get(k) is not None for k in ('draft_quantity','unit_cost','line_cost','line_price')):
                raise ValueError('Excluded scope still contains quantity or price: '+row['row_id'])
            package['excluded_items'].append({'row_id':row['row_id'],'name':row['name'],
                'basis':row.get('next_check') or 'Excluded in current published estimate'})
            return
        item={k:row.get(k) for k in ('row_id','name','parent','draft_quantity','unit','cost_type',
            'pricing_role','covered_by_package','cost_owner_row_id','completion_status')}
        item['issues']=reviews[row['row_id']]['issues']
        item['responsibility']=route.get('scope_note')
        item['assembly_references']=[{k:q.get(k) for k in ('id','quantity','unit','basis','remaining')}
            for q in row.get('assembly_inputs',[])]
        item['quantity_basis']=[]
        for source in row.get('quantity_sources',[]):
            if not source.get('basis'):
                continue
            detail={k:source.get(k) for k in ('id','label','basis','rounding','waste_percent')}
            if source.get('purchase_pack'):
                detail['purchase_pack']={k:source['purchase_pack'].get(k)
                    for k in ('product','quantity','unit','required_quantity','coverage_unit','source')}
            item['quantity_basis'].append(detail)
        matrix=(row.get('price_evidence') or {}).get('quote',{}).get('scope_matrix',[])
        item['package_scope']=[{k:part.get(k) for k in ('scope_id','label','status','note','source_ref')}
            for part in matrix]
        owner=row.get('cost_owner_row_id') or row.get('covered_by_package')
        if owner and owner!=row['row_id']:
            if owner not in owners:raise ValueError('Unknown package owner: '+str(owner))
            seen={row['row_id']};current=owner
            while current:
                if current in seen:raise ValueError('Circular package ownership: '+row['row_id'])
                seen.add(current)
                if current not in owners:raise ValueError('Unknown package owner: '+str(current))
                parent=owners[current]
                if parent.get('completion_status','').startswith('not_applicable'):
                    raise ValueError('Active scope refers to excluded package owner: '+row['row_id'])
                if parent.get('pricing_role') in ('input_only','cost_reference'):
                    raise ValueError('Active scope refers to nonbillable package owner: '+row['row_id'])
                next_owner=parent.get('cost_owner_row_id') or parent.get('covered_by_package')
                current=None if next_owner==current else next_owner
            item['quote_action']='Confirm inclusion under '+owners[owner]['name']+' ('+owner+'); no separate charge'
        elif row.get('pricing_role') in ('input_only','cost_reference'):
            item['quote_action']='Reference only; reconcile with the priced assembly, no separate charge'
        elif (row.get('cost_type')=='ASSEMBLY'
                and not row.get('assembly_inputs') and not row.get('quantity_sources')
                and all(row.get(k) is None for k in ('draft_quantity','unit_cost','line_cost','line_price'))
                and (children:=[r for r in rows.values() if r.get('parent')==row['name']])
                and all(r.get('completion_status','').startswith('not_applicable')
                    or ((r.get('cost_owner_row_id') or r.get('covered_by_package'))
                        and (r.get('cost_owner_row_id') or r.get('covered_by_package'))!=row['row_id'])
                    for r in children)):
            item['quote_action']='Reference heading only; its component options are excluded or assigned to other packages. No separate charge; retain each active component under its listed cost owner.'
        else:item['quote_action']='Quote this scope or identify its owning package'
        package['items'].append(item)
    for route in coverage['rows']:
        if route['status']=='draft_scope_routed':add(route,rows[str(route['excel_row'])])
    for route in coverage.get('supplemental_cost_routes',[]):add(route,supplemental[route['row_id']])
    for route in coverage.get('additional_scopes',[]):
        result[route['draft_file']]['additional_scope'].append({'id':route['id'],'name':route['name']})
    identities=[i['row_id'] for p in result.values() for i in p['items']]
    if len(identities)!=len(set(identities)):raise ValueError('A cost row is requested in more than one trade')
    if any(not re.fullmatch(r'[A-Za-z0-9 _-]+',p.get('trade','')) for p in result.values()):
        raise ValueError('Indexed trade needs a plain-text scope owner without path separators')
    return list(result.values())


def render(package):
    def cell(v):return str(v if v is not None else 'Unresolved').replace('|','\\|').replace('\n',' ')
    lines=['# '+package['trade'].replace('_',' ').title()+' — current scope schedule','',
        '**Draft for review; not sent. Quantities are estimating references, not purchase authorization.**','',
        'Identify included work, exclusions and allowances for every scope ID. Quote a package by its exact included IDs or price separate scopes. Confirm unknown quantities; do not treat them as zero. Do not charge a second time for work covered by another listed package or cost owner.','',
        'This schedule uses the current estimate snapshot. Earlier quantities in background working notes are historical comparisons; reconcile any conflict before quoting.','',
        f"Plan: `{package['plan_sha256']}`  ",f"Measurement revision: {package['measurement_version']}  ",
        f"Estimate snapshot: `{package['snapshot_sha256']}`",'',
        '| Scope ID | Work | Reference quantity | Requested response |','| --- | --- | --- | --- |']
    if package.get('project_duration_reference'):
        duration=package['project_duration_reference']
        lines[8:8]=[f"Project duration reference: {duration['months']:g} months ({duration['source_row_id']}). Confirm this trade's actual start, finish, mobilizations and rental/service periods. This is not a rental quantity or authorization to multiply a saved package price.",'']
    for item in package['items']:
        quantity='Unresolved' if item['draft_quantity'] is None else f"{item['draft_quantity']:g} {item['unit']}"
        lines.append('| '+' | '.join(map(cell,[item['row_id'],item['name'],quantity,item['quote_action']]))+' |')
    if package['excluded_items']:
        lines+=['','## Excluded options — do not quote','']
        lines+=['- '+i['row_id']+' — '+cell(i['name'])+': '+cell(i['basis']) for i in package['excluded_items']]
    lines+=['','## Scope details requiring resolution','']
    for item in package['items']:
        notes=[item['responsibility']] if item['responsibility'] else []
        notes+=item['issues']
        if notes:lines+=['- '+item['row_id']+' — '+cell(item['name'])+': '+'; '.join(map(cell,notes))]
        for detail in item.get('quantity_basis',[]):
            description=cell(detail['basis'])
            if detail.get('waste_percent') is not None:
                description+=f" Waste already included: {detail['waste_percent']:g}%; do not add it again."
            if detail.get('rounding'):
                description+=' Rounding: '+cell(detail['rounding'])+'.'
            pack=detail.get('purchase_pack')
            if pack:
                description+=' Separate packaging reference: '+cell(pack['quantity'])+' '+cell(pack['unit'])+' of '+cell(pack['product'])+'. Not additional work or purchase authorization.'
            lines+=['- '+item['row_id']+' — quantity basis: '+description]
        for reference in item.get('assembly_references',[]):
            amount='Unresolved' if reference['quantity'] is None else cell(reference['quantity'])+' '+cell(reference['unit'])
            lines+=['- '+item['row_id']+' / '+cell(reference['id'])+': assembly reference '+amount+
                '; not a purchase quantity or additional charge. '+cell(reference['basis'])+
                (' Remaining: '+'; '.join(map(cell,reference['remaining'])) if reference['remaining'] else '')]
        for part in item.get('package_scope',[]):
            lines+=['- '+item['row_id']+' / '+cell(part['scope_id'])+' — '+cell(part['label'])+
                ': recorded package status **'+cell(part['status'])+'**. '+
                ('Confirm within this package; no separate charge. ' if part['status']=='included' else '')+
                (cell(part['note'])+' ' if part['note'] else '')+
                ('Source: '+cell(part['source_ref']) if part['source_ref'] else '')]
    for scope in package['additional_scope']:lines+=['- '+scope['id']+' — '+scope['name']+'; reconcile with included cost rows, not an automatic additional charge.']
    lines+=['','Source working draft: '+package['source_draft'],
        'Price, delivery, tax, lead time, exclusions and validity require the supplier/subcontractor response.','']
    return '\n'.join(lines)


def export(index_path,output):
    index_path=Path(index_path).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Output exists; select a new directory')
    if not output.parent.is_dir():raise ValueError('Output parent must exist')
    check=validate(index_path)
    if not check['valid'] or not check['estimate_basis_checked']:raise ValueError('Current published estimate and bid routes must validate: '+str(check['errors']))
    index=json.loads(index_path.read_bytes());coverage_path=index_path.parent/index['coverage']
    coverage=json.loads(coverage_path.read_bytes());ref=index['published_estimate']
    checkpoint_path=(index_path.parent/ref['checkpoint']).resolve()
    checkpoint=json.loads(checkpoint_path.read_bytes())
    snapshot_path=(index_path.parent/ref['workspace']/checkpoint['current_workbook']).resolve().with_name('source_snapshot.json')
    snapshot=json.loads(snapshot_path.read_bytes())
    if snapshot['snapshot_sha256']!=check['estimate_snapshot_sha256']:raise ValueError('Published estimate changed during export')
    sources=[index_path,coverage_path,checkpoint_path,snapshot_path,*[(index_path.parent/f).resolve() for f in index['files']]]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    scopes=packages(index_path,index,coverage,snapshot)
    with tempfile.TemporaryDirectory(prefix='.trade-scopes-',dir=output.parent) as temp:
        staged=Path(temp)/'package';staged.mkdir();files=[]
        for n,scope in enumerate(scopes,1):
            stem=f'{n:02d}-{scope["trade"]}'
            (staged/(stem+'.json')).write_text(json.dumps(scope,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            (staged/(stem+'.md')).write_text(render(scope),encoding='utf-8');files.append(stem+'.md')
        manifest={'created_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':snapshot['snapshot_sha256'],
            'source_hashes':hashes,'files':files,'trade_count':len(scopes),
            'scope_rows':sum(len(s['items']) for s in scopes),'sent':False,'complete_measured_bid_book':False}
        (staged/'index.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        (staged/'README.md').write_text('# Current trade scope schedules\n\nUnsent drafts from one published estimate snapshot. Resolve listed issues before issuing bids.\n\n'+'\n'.join(f'- [{f}]({f})' for f in files)+'\n',encoding='utf-8')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):raise ValueError('Source changed during export')
        staged.rename(output)
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    try:result=export(args.index,args.output)
    except (OSError,ValueError,KeyError) as exc:parser.exit(1,str(exc)+'\n')
    print(json.dumps({k:result[k] for k in ('trade_count','scope_rows','snapshot_sha256','sent')}));return 0


if __name__=='__main__':raise SystemExit(main())
