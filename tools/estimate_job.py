"""Export an explicit job through the same calculation pipeline as its local review."""
import argparse
import json
import subprocess
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


def calculate(job):
    sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
    from measurement_store import MeasurementStore
    from measurement_review import make_server
    from estimate_export_snapshot import verify_snapshot
    server=make_server(MeasurementStore(job),0)
    worker=threading.Thread(target=server.serve_forever,daemon=True)
    worker.start()
    try:
        try:
            with urlopen(f'http://127.0.0.1:{server.server_port}/api/export-snapshot',timeout=120) as response:
                snapshot=json.load(response)
        except HTTPError as exc:
            raise ValueError(json.loads(exc.read()).get('error','Estimate calculation failed')) from exc
        verify_snapshot(snapshot)
        return snapshot
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True,type=Path,help='Explicit measurement-review folder, or legacy job with --legacy')
    parser.add_argument('--output',type=Path,help='New JSON snapshot path; existing files are never replaced')
    parser.add_argument('--workbook',type=Path,help='Also export this calculated snapshot to a new Excel workbook')
    parser.add_argument('--template',type=Path,help='Original Excel template, required with --workbook')
    parser.add_argument('--node',type=Path,help='Node executable with artifact-tool, required with --workbook')
    parser.add_argument('--legacy',action='store_true',help='Run the selected job\'s existing Takeoff scripts instead')
    args=parser.parse_args(argv)
    job=args.job.resolve()
    if args.workbook or args.template or args.node:
        if args.legacy:parser.error('Workbook export cannot be combined with --legacy')
        if not all((args.workbook,args.template,args.node)):parser.error('--workbook, --template and --node must be supplied together')
        if args.workbook.exists():parser.error('Workbook already exists; choose a new path')
        if not args.workbook.parent.is_dir():parser.error('Workbook parent directory must exist')
        if args.workbook.suffix.lower()!='.xlsx':parser.error('Workbook output must end in .xlsx')
        for path in (args.template,args.node):
            if not path.is_file():parser.error(f'Required export file does not exist: {path}')
    if args.legacy:
        if args.output:parser.error('--legacy does not use --output')
        folder=job/'Takeoff'
        scripts=[folder/name for name in ('build_estimate.py','addendum.py','write_books.py')]
        if not all(p.is_file() for p in scripts):parser.error('Selected legacy job is missing its Takeoff scripts')
        for script in scripts:
            result=subprocess.run([sys.executable,str(script)],cwd=folder)
            if result.returncode:return result.returncode
        return 0
    if not args.output:parser.error('--output is required for a calculated draft snapshot')
    output=args.output.resolve()
    if output.exists():parser.error('Output already exists; choose a new snapshot path')
    if not output.parent.is_dir():parser.error('Output parent directory must exist')
    if args.workbook and output==args.workbook.resolve():parser.error('Snapshot and workbook need separate output paths')
    for name in ('measurements.json','quantity_rules.json','template_rows.json'):
        if not (job/name).is_file():parser.error(f'Selected job is missing {name}; use its draft_takeoff review folder')
    try:
        snapshot=calculate(job)
        with output.open('x',encoding='utf-8') as stream:
            json.dump(snapshot,stream,indent=2,allow_nan=False);stream.write('\n')
    except (ValueError,OSError) as exc:
        parser.exit(1,str(exc)+'\n')
    if args.workbook:
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('export_estimate.py')),
            '--snapshot',str(output),'--template',str(args.template.resolve()),
            '--output',str(args.workbook.resolve()),'--node',str(args.node.resolve())])
        if result.returncode:
            print(f'Workbook export failed. Calculated snapshot retained at {output}; retry with export-workbook.',file=sys.stderr)
            return result.returncode
    ready=snapshot['readiness']
    print(json.dumps({'job':str(job),'output':str(output),'plan_sha256':ready['plan_sha256'],
        **({'workbook':str(args.workbook.resolve())} if args.workbook else {}),
        'template_open_rows':ready['rows_with_open_issues'],
        'supplemental_open_rows':ready['additional_rows_with_open_issues'],
        'estimate_released':snapshot['draft'].get('estimate_released',False)}))
    return 0


if __name__=='__main__':raise SystemExit(main())
