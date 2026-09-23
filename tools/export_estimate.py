"""Export a verified draft snapshot into its original J&J Excel template."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent/'viewer'))
from estimate_export_snapshot import verify_snapshot
from new_plan_template import read_template


def validate_sources(snapshot_path,template_path):
    raw=Path(snapshot_path).read_bytes();snapshot=json.loads(raw)
    verify_snapshot(snapshot)
    original=read_template(template_path)
    rows=snapshot['draft']['rows']
    expected={r['row_id']:r for r in original['rows']}
    if len(rows)!=len(expected) or {r['row_id'] for r in rows}!=set(expected):
        raise ValueError('Snapshot does not belong to the selected original template')
    for row in rows:
        source=expected[row['row_id']]
        if any(row[k]!=source[k] for k in ('excel_row','cost_type','markup_pct')):
            raise ValueError('Template row identity, cost type or markup changed: '+row['row_id'])
    return hashlib.sha256(raw).hexdigest(),original['template_sha256']


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','template','output','node'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--preview',action='store_true',help='Render the template before authoring')
    parser.add_argument('--check-only',action='store_true',help='Build and reconcile in memory without saving a workbook')
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('Output exists; choose a new path')
    if not args.output.parent.is_dir():parser.error('Output parent directory must exist')
    try:digests=validate_sources(args.snapshot,args.template)
    except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    return subprocess.call([str(args.node.resolve()),str(Path(__file__).with_suffix('.mjs')),
        str(args.snapshot.resolve()),str(args.template.resolve()),str(args.output.resolve()),*digests,
        *(['--preview'] if args.preview else []),*(['--check-only'] if args.check_only else [])])


if __name__=='__main__':raise SystemExit(main())
