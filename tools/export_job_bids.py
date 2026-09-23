"""Export supported current job scopes together, preserving incomplete coverage."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import tempfile
from export_opening_bid import MeasurementStore,source_files
from opening_bid_scope import from_folder as openings,render_markdown as render_openings
from opening_framing_scope import from_folder as framing,render_markdown as render_framing
from drywall_bid_scope import from_folder as drywall,render_markdown as render_drywall
from roof_bid_scope import from_folder as roof,render_markdown as render_roof
from company_scope_bids import from_folder as company,render_markdown as render_company
from bid_comparison import scope_digest


def collect(job,state):
    drafts=[];missing=[]
    def add(trade,kind,scope,render):
        if scope['plan_sha256']!=state['plan_sha256'] or scope['measurement_version']!=state['version']:
            raise ValueError('Trade scope belongs to a different drawing or measurement revision')
        if scope.get('sent') is not False:raise ValueError('Unsent scope required')
        digest=scope_digest(scope)
        if scope.get('scope_sha256',digest)!=digest:raise ValueError('Trade scope fingerprint differs')
        scope={**scope,'scope_sha256':digest}
        drafts.append({'trade':trade,'kind':kind,'scope':scope,'markdown':render(scope)})
    if (job/'opening_schedule_review.json').exists():
        add('Windows and doors','opening assemblies',openings(job,state),render_openings)
        add('Framing','opening framing',framing(job,state),render_framing)
    else:missing.append('Opening assemblies and opening framing: opening review is missing.')
    if (job/'drywall_practice_review.json').exists():
        add('Drywall','wall and ceiling surfaces',drywall(job,state),render_drywall)
    else:missing.append('Drywall: job estimating-practice mapping is missing.')
    if (job/'roof_partition_inputs.json').exists():
        add('Roofing','roof faces',roof(job),render_roof)
    else:missing.append('Roofing: reviewed roof partition inputs are missing.')
    if (job/'company_scope_review.json').exists():
        for scope in company(job)['scopes']:
            add(scope['trade'],'company scope additions',scope,render_company)
    else:missing.append('Company scope additions: job practice mapping is missing.')
    return drafts,missing


def export(job,output):
    job=Path(job).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Existing bid directory preserved')
    if not output.parent.is_dir():raise ValueError('Output parent directory must exist')
    if output.is_relative_to(job):raise ValueError('Export outside the measurement folder')
    store=MeasurementStore(job);state=store.read();sources=source_files(job)
    drafts,missing=collect(job,state)
    if not drafts:raise ValueError('No supported scope reviews exist; prepare the job reviews first')
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':state['plan_sha256'],
        'measurement_version':state['version'],'job':str(job),'source_files':sources,'drafts':[],
        'missing_supported_scopes':missing,'sent':False,'complete_trade_coverage':False,'files':{}}
    lines=['# Current job bid drafts','','Unsent drafts with incomplete scope. Review before issuing.',
        'Company scope additions supplement the related trade request; do not price the same work twice.',
        'This index lists supported outputs only. It is not a complete-house trade checklist.','',
        '| Trade | Scope | Request |','| --- | --- | --- |']
    with tempfile.TemporaryDirectory(prefix='.job-bids-',dir=output.parent) as temp:
        staged=Path(temp)/'package';staged.mkdir()
        for n,item in enumerate(drafts,1):
            stem=f'scope-{n:02d}';scope=item['scope']
            (staged/(stem+'.json')).write_text(json.dumps(scope,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            (staged/(stem+'_DRAFT.md')).write_text(item['markdown'],encoding='utf-8')
            manifest['drafts'].append({'trade':item['trade'],'kind':item['kind'],'scope_file':stem+'.json',
                'request_file':stem+'_DRAFT.md','scope_sha256':scope['scope_sha256']})
            label=item['trade'].replace('|','\\|')
            lines.append(f"| {label} | {item['kind']} | [Draft]({stem}_DRAFT.md) |")
        lines+=['','## Missing supported scope inputs','']+(['- '+m for m in missing] or ['None; this does not establish complete-house coverage.'])
        (staged/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        manifest['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in staged.iterdir()}
        (staged/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        if store.read()!=state or source_files(job)!=sources:raise ValueError('Job changed during export; retry')
        staged.rename(output)
    return {'output':str(output),'drafts':len(drafts),'missing_supported_scopes':missing,'sent':False,'complete_trade_coverage':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:result=export(args.job,args.output)
    except (ValueError,OSError) as error:parser.exit(1,str(error)+'\n')
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
