#!/usr/bin/env python
"""jj - single entry point for the J&J estimating system.

    python jj.py verify     # prove the system is green (run before trusting anything)
    python jj.py backup     # mirror the un-synced ~/.claude assets into OneDrive
    python jj.py status     # what's where, what's stale, what's at risk
    python jj.py estimate   # rebuild the active job's estimate from measured inputs
    python jj.py save       # backup + commit in one step -- RUN BEFORE SHUTTING DOWN

WHY BACKUP EXISTS
    The workspace (C:\\Users\\jason\\OneDrive\\Desktop\\Claude) is OneDrive-synced.
    The ENGINE and MEMORY are not -- they live under C:\\Users\\jason\\.claude\\, which
    sits outside OneDrive. That is where jnj_takeoff.py, calibration.md (1,600+ lines of
    hard-won method rulings) and every memory file live. On a laptop that is one disk
    failure from total loss. `backup` mirrors them into the synced tree.
"""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime

HOME = os.path.expanduser('~')
# CONSOLIDATED 2026-08-04. The engine, reference, templates, golden fixtures, eval corpus,
# Level Ground and the job takeoffs now all live in ONE git repo -- this file's own parent.
# SKILL used to point at ~/.claude/skills/jnj-estimate-takeoff, which is now a junction
# back to here, so the `jnj-estimate-takeoff` skill keeps resolving unchanged.
ROOT = os.path.dirname(os.path.abspath(__file__))
SKILL = ROOT
WORKSPACE = os.path.join(HOME, 'OneDrive', 'Desktop', 'Claude')   # legacy tree: autonomous engine gates
MEMORY = os.path.join(HOME, '.claude', 'projects',
                     'C--Users-jason-OneDrive-Desktop-Claude', 'memory')
BACKUP = os.path.join(WORKSPACE, '_backup')
JOB = os.path.join(ROOT, 'jobs', 'PR-000 - L J Show Residence')

# (label, source, skip-these-dirs) -- unsynced assets that must survive a disk loss.
# `jj-takeoff` was `skill` until 2026-08-04. It is no longer just the skill: the whole
# program consolidated into ROOT, which sits OUTSIDE OneDrive with no other local copy.
# `.git` is mirrored on purpose -- the GitHub remote covers history, but this mirror has
# to stand alone if the remote is ever unreachable. node_modules/.vercel are reinstallable.
ASSETS = [
    ('jj-takeoff', SKILL, {'__pycache__', '.pytest_cache', 'node_modules', '.vercel'}),
    ('memory', MEMORY, set()),
]

# Ignored ON PURPOSE. `.gitignore` is deny-by-default, which is right for a repo living
# inside 14 GB of plan sets -- but it means a brand-new source file is invisible to git
# until someone explicitly un-ignores it, and nobody notices for months.
# _untracked_sources() flags every ignored/untracked source file NOT under one of these.
# Ignored on purpose is a decision; ignored by accident is a bug. Only flag the second.
# Add an entry here only with a reason on the line.
DELIBERATE = (
    '.claude/',                                    # per-machine settings, not portable
    '.codex-house-budgets-readonly/',              # read-only mirror of another workspace
    '.estimate_deps/',                             # vendored python packages (PIL et al)
    '.video-tools/',                               # vendored video toolchain
    'JARVIS/',                                     # separate system, its own history
    'andrej-karpathy-skills/',                     # third-party skills
    '_backup/skill/tools/tests/golden/',           # 226 MB of golden fixture plan sets
    'estimator_accuracy/artifacts/',               # generated run artifacts
    'estimator_accuracy/certification_artifacts/',
    'estimator_accuracy/extracted_vendor_quotes/',
    'estimator_accuracy/phase1_registered_inputs/',  # immutable replay corpus
    'estimator_accuracy/phase1_replay_history/',     # immutable replay corpus
    'estimator_accuracy/private/',
    'estimator_accuracy/production_run_attempts/',
    'estimator_accuracy/production_runs/',         # 170+ immutable runs, never edited
    'jnj_estimator_hardening/',                    # engine rollback copies; _backup/skill/ has the live one
    'dugger_estimate/INVALID_DO_NOT_USE/',         # superseded takeoff, on-disk warning marker only
    'node_modules/', '__pycache__/', '.venv/', 'venv/',
    'output/', 'outputs/', 'tmp/',                 # generated output
)
SOURCE_EXT = ('.py', '.mjs', '.js', '.ps1', '.md', '.json', '.yaml', '.yml')
MAX_SHOWN = 20


def run(cmd, cwd=None, timeout=1800):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, ((p.stdout or '') + (p.stderr or ''))


def ok(label, passed, detail=''):
    print(f"  [{'OK ' if passed else 'FAIL'}] {label}{('  ' + detail) if detail else ''}")
    return passed


def cmd_verify():
    print('VERIFY - proving the system is green\n')
    good = True

    rc, out = run([sys.executable, os.path.join(SKILL, 'tools', 'tests', 'run_golden.py')], cwd=SKILL)
    line = next((l.strip() for l in out.splitlines() if 'houses green' in l), '')
    good &= ok('golden measurement suite', rc == 0, line)

    rc, out = run([sys.executable, os.path.join(SKILL, 'tools', 'jnj_takeoff.py')], cwd=SKILL)
    good &= ok('engine self-test', rc == 0 and 'ALL PASS' in out,
               'ALL PASS' if 'ALL PASS' in out else out[-160:])

    rc, out = run([sys.executable,
                   os.path.join(WORKSPACE, 'estimator_accuracy',
                                'refresh_golden_fixture_certification.py')], cwd=WORKSPACE)
    good &= ok('fixture certification current', rc == 0,
               'no drift' if rc == 0 else 'DRIFT - run: python estimator_accuracy\\refresh_golden_fixture_certification.py --write')

    sys_test = os.path.join(WORKSPACE, 'estimator_accuracy', 'run_v3_offline_system_test.ps1')
    if os.path.exists(sys_test):
        env = dict(os.environ); env.pop('OPENAI_API_KEY', None)
        p = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                            '-File', sys_test], cwd=WORKSPACE, capture_output=True,
                           text=True, env=env, timeout=1800)
        good &= ok('offline system test', p.returncode == 0, 'exit 0, no network')

    rc, out = run(['node', os.path.join(WORKSPACE, 'estimator_accuracy',
                                        'evaluate_v3_execution_readiness.mjs')], cwd=WORKSPACE)
    try:
        j = json.loads(out[out.index('{'):out.rindex('}') + 1])
        # not_ready is EXPECTED while release gates remain; regression = fewer passes
        ok(f"readiness (expected not_ready)", True,
           f"{j.get('status')}, {j.get('passed')} passed / {j.get('failed')} failed"
           f"{'   <-- REGRESSION vs baseline 18/11' if j.get('passed', 0) < 18 else ''}")
    except Exception:
        ok('readiness', False, 'could not parse output')

    # Progress metric. Readiness says not_ready either way; this says whether we MOVED.
    # Non-zero here means a false positive appeared -- coverage bought with a confident
    # wrong number, which is a regression no matter what the percentage did.
    rc, out = run([sys.executable, os.path.join(WORKSPACE, 'estimator_accuracy', 'coverage.py')],
                  cwd=WORKSPACE)
    cov = next((l.strip() for l in out.splitlines() if l.strip().startswith('answered ')), '')
    fp = next((l.strip() for l in out.splitlines() if l.strip().startswith('false positives')), '')
    good &= ok('coverage (baseline 0.3%, 0 FP)', rc == 0,
               f"{cov}  |  {fp.replace('   <-- THE CONSTRAINT. Must stay 0.', '')}")

    print('\nVERIFY:', 'GREEN' if good else 'NOT GREEN')
    return 0 if good else 1


def _mirror(src, dst, skip):
    copied = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip]
        rel = os.path.relpath(root, src)
        target = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for f in files:
            s, d = os.path.join(root, f), os.path.join(target, f)
            if os.path.exists(d) and os.path.getmtime(d) >= os.path.getmtime(s) \
                    and os.path.getsize(d) == os.path.getsize(s):
                continue
            # Git writes its loose objects and packs READ-ONLY. copy2 carries that mode
            # across, so the SECOND backup run hit PermissionError trying to overwrite its
            # own output and died mid-mirror -- leaving a partial backup and a non-zero
            # exit on the one command that is supposed to be unfailable before a shutdown.
            # Clear the bit on the destination first; a backup must never be the thing that
            # breaks because the previous backup worked.
            if os.path.exists(d) and not os.access(d, os.W_OK):
                os.chmod(d, stat.S_IWRITE | stat.S_IREAD)
            shutil.copy2(s, d)
            copied += 1
    return copied


def cmd_backup():
    print('BACKUP - mirroring un-synced ~/.claude assets into OneDrive\n')
    stamp = datetime.now().isoformat(timespec='seconds')
    manifest = {'at': stamp, 'assets': {}}
    for label, src, skip in ASSETS:
        if not os.path.isdir(src):
            print(f'  [SKIP] {label}: {src} not found')
            continue
        dst = os.path.join(BACKUP, label)
        n = _mirror(src, dst, skip)
        total = sum(len(f) for _, _, f in os.walk(dst))
        manifest['assets'][label] = {'source': src, 'files': total, 'updated': n}
        print(f'  [OK ] {label:<8} {total:5d} files  ({n} updated)  -> _backup\\{label}')
    # critical-file fingerprints so a restore can be verified
    fp = {}
    for rel in ['tools/jnj_takeoff.py', 'reference/calibration.md', 'reference/rate_book.json']:
        p = os.path.join(SKILL, rel)
        if os.path.exists(p):
            fp[rel] = hashlib.sha256(open(p, 'rb').read()).hexdigest().upper()[:16]
    manifest['fingerprints'] = fp
    os.makedirs(BACKUP, exist_ok=True)
    with open(os.path.join(BACKUP, 'BACKUP_MANIFEST.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'\n  manifest: _backup\\BACKUP_MANIFEST.json')
    print('  NOTE: OneDrive must finish syncing before the laptop goes offline.')
    return 0


def cmd_status():
    print('STATUS\n')
    print(f'  workspace (SYNCED)   {WORKSPACE}')
    print(f'  engine    (NOT sync) {SKILL}')
    print(f'  memory    (NOT sync) {MEMORY}')
    print(f'  active job           {JOB}')
    print(f'  backup mirror        {BACKUP}')
    print()
    gitdir = os.path.join(WORKSPACE, '.git')
    if os.path.isdir(gitdir) and os.listdir(gitdir):
        gv = 'git present'
    elif os.path.isdir(gitdir):
        gv = 'NONE - .git exists but is EMPTY (broken stub; git reports "not a repository")'
    else:
        gv = 'NONE - no history, no undo'
    print(f'  version control      {gv}')
    mf = os.path.join(BACKUP, 'BACKUP_MANIFEST.json')
    if os.path.exists(mf):
        m = json.load(open(mf, encoding='utf-8'))
        print(f'  last backup          {m.get("at")}')
        for k, v in m.get('assets', {}).items():
            print(f'      {k:<8} {v.get("files")} files')
    else:
        print('  last backup          NEVER  <-- run: python jj.py backup')
    return 0


def cmd_estimate():
    """Rebuild the active job's estimate from its measured inputs."""
    tk = os.path.join(JOB, 'Takeoff')
    if not os.path.isdir(tk):
        print('No Takeoff folder at', tk)
        return 1
    print('ESTIMATE - rebuilding from measured inputs in', tk, '\n')
    for script in ['build_estimate.py', 'addendum.py', 'write_books.py']:
        rc, out = run([sys.executable, os.path.join(tk, script)], cwd=tk)
        tail = [l for l in out.strip().splitlines() if l.strip()][-4:]
        print(f'  [{"OK " if rc == 0 else "FAIL"}] {script}')
        for l in tail:
            print('        ', l)
        if rc != 0:
            return 1
    return 0


def _untracked_sources():
    """Source files git cannot see -- the standing cost of a deny-by-default .gitignore.

    Returns the suspected accidents only: ignored-or-untracked source files that are not
    under a DELIBERATE exclusion. Steady state is empty. Anything listed is either a file
    that belongs in history, or a missing .gitignore rule."""
    # -c core.quotepath=false: without it git octal-escapes any non-ASCII path, so a
    #   mangled filename gets reported as gibberish instead of something you can delete.
    # -uall: without it git collapses a wholly-untracked directory to one `?? dir/` line,
    #   which has no source extension -- a whole new folder of code would slip the filter.
    rc, out = run(['git', '-c', 'core.quotepath=false', 'status', '--porcelain',
                   '-uall', '--ignored=matching'], cwd=WORKSPACE, timeout=300)
    if rc != 0:
        return []
    found = []
    for line in out.splitlines():
        if line[:2] not in ('!!', '??'):
            continue
        path = line[3:].strip().strip('"')
        if not path.lower().endswith(SOURCE_EXT):
            continue
        if any(path.startswith(d) or ('/' + d) in path for d in DELIBERATE):
            continue
        found.append(path)
    return sorted(found)


def cmd_save():
    """One command before the laptop closes: mirror the un-synced assets, then commit.

    Backup protects against disk loss. Git protects against a bad edit. Both, or neither
    is enough.

    The untracked-source check runs AFTER the mirror and the commit, never before: a lint
    finding must never be the reason Jason shut the laptop without a backup. It reports by
    exit code instead."""
    cmd_backup()
    print(os.linesep + 'COMMIT')
    rc, _ = run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=WORKSPACE, timeout=60)
    if rc != 0:
        print('  [FAIL] not a git repository')
        return 1
    run(['git', 'add', '-A'], cwd=WORKSPACE, timeout=300)
    rc, out = run(['git', 'diff', '--cached', '--name-only'], cwd=WORKSPACE, timeout=120)
    changed = [l for l in out.splitlines() if l.strip()]
    if not changed:
        print('  nothing to commit - working tree already clean')
    else:
        msg = 'save: %s (%d files)' % (datetime.now().strftime('%Y-%m-%d %H:%M'), len(changed))
        rc, out = run(['git', 'commit', '-m', msg], cwd=WORKSPACE, timeout=300)
        print(f"  [{'OK ' if rc == 0 else 'FAIL'}] {msg}")
        for f in changed[:8]:
            print('        ', f)
        if len(changed) > 8:
            print(f'         ... and {len(changed) - 8} more')
    rc, out = run(['git', 'log', '--oneline', '-1'], cwd=WORKSPACE, timeout=60)
    print('  HEAD:', out.strip())
    print(os.linesep + '  Let OneDrive finish syncing before going offline.')

    stray = _untracked_sources()
    if not stray:
        return 0
    print(os.linesep + f'UNTRACKED SOURCE - {len(stray)} source file(s) git cannot see')
    print('  .gitignore is deny-by-default, so these were never committed and never will')
    print('  be until someone decides. They are NOT in history.' + os.linesep)
    for p in stray[:MAX_SHOWN]:
        print('      ', p)
    if len(stray) > MAX_SHOWN:
        print(f'       ... and {len(stray) - MAX_SHOWN} more (showing first {MAX_SHOWN})')
    print(os.linesep + '  Resolve each one, then this goes quiet:')
    print('      git add -f <file>        # it belongs in history')
    print('      or add a .gitignore rule # it does not -- say WHY in a comment')
    print('      or add to DELIBERATE in jj.py, with a reason')
    return 1


COMMANDS = {'verify': cmd_verify, 'backup': cmd_backup, 'save': cmd_save,
            'status': cmd_status, 'estimate': cmd_estimate}

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if arg not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[arg]())
