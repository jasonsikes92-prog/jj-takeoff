"""Export current opening, drywall or flooring quote scope without sending it."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from measurement_store import MeasurementStore
from opening_bid_scope import from_folder,render_markdown
from drywall_bid_scope import from_folder as drywall_scope,render_markdown as render_drywall
from flooring_bid_scope import from_folder as flooring_scope,render_markdown as render_flooring


def source_files(job):
    # The schedule reads job reviews and the frozen intake/profile in its parent.
    sources={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in (job,job.parent) for pattern in ('*.json','plan.pdf') for p in folder.glob(pattern)}
    selections=job/'flooring_selection_review.json'
    if selections.exists():
        for decision in json.loads(selections.read_bytes())['decisions']:
            source=(job/decision['source_file']).resolve()
            if not source.is_relative_to(job):raise ValueError('Floor selection evidence must stay inside the job')
            sources[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
    mapping=job/'roof_edge_review.json'
    if mapping.exists():
        from roof_edge_scope import linked_folder
        linked=linked_folder(job,json.loads(mapping.read_bytes()))
        for name in ('measurements.json','measurement_edits.sqlite3','plan.pdf'):
            p=linked/name;sources[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    return sources


def export_bid(job,output,trade='openings'):
    if trade not in ('openings','drywall','flooring'):raise ValueError('Unknown bid trade')
    job=Path(job).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError('Bid output already exists; choose a new directory')
    if not output.parent.is_dir():raise ValueError('Bid output parent directory must exist')
    store=MeasurementStore(job);state=store.read();sources=source_files(job)
    builder,renderer={'openings':(from_folder,render_markdown),
                      'drywall':(drywall_scope,render_drywall),
                      'flooring':(flooring_scope,render_flooring)}[trade]
    scope=builder(job,state)
    if scope['plan_sha256']!=state['plan_sha256'] or scope['measurement_version']!=state['version']:
        raise ValueError('Bid scope differs from the selected measurement revision')
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),
        'job':str(job),'plan_sha256':scope['plan_sha256'],
        'measurement_version':scope['measurement_version'],'source_files':sources,
        'trade':trade,'status':'unsent_draft','sent':False,'ready_to_order':False}
    with tempfile.TemporaryDirectory(prefix='.opening-bid-',dir=output.parent) as temp:
        staged=Path(temp)/'package';staged.mkdir()
        (staged/'scope.json').write_text(json.dumps(scope,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (staged/'request_DRAFT.md').write_text(renderer(scope),encoding='utf-8')
        manifest['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in staged.iterdir()}
        (staged/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        if store.read()!=state or source_files(job)!=sources:
            raise ValueError('Job changed during bid generation; regenerate from the current review')
        staged.rename(output)
    if trade=='flooring':counts={'rooms':len(scope['items']),'unresolved_finishes':len(scope['unresolved_finish_region_ids'])}
    else:counts=({'surfaces':len(scope['items']),'unmeasured_surfaces':len(scope['unmeasured_surface_ids'])}
                 if trade=='drywall' else {'openings':len(scope['openings']),'unresolved_openings':len(scope['unresolved_opening_ids'])})
    return {'output':str(output),'plan_sha256':scope['plan_sha256'],
        'measurement_version':scope['measurement_version'],
        **counts,'sent':False,'ready_to_order':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True,type=Path,help='Selected draft_takeoff measurement folder')
    parser.add_argument('--output',required=True,type=Path,help='New directory for the draft request and source record')
    parser.add_argument('--trade',choices=('openings','drywall','flooring'),default='openings')
    args=parser.parse_args(argv)
    try:result=export_bid(args.job,args.output,args.trade)
    except (ValueError,OSError) as exc:parser.exit(1,str(exc)+'\n')
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
