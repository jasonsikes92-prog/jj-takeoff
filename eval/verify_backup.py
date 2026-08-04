"""Prove the OneDrive mirror is a complete, faithful copy of the repo.

`jj.py backup` reports a file COUNT. A count is not integrity -- it cannot see a truncated
copy, a stale file the mtime check skipped, or a directory the walk never reached. This
compares the two trees file-by-file and hashes the ones that matter.

Run:  python eval/verify_backup.py
Exit: 0 = mirror is complete and the critical files match by sha256.
"""
import hashlib
import os
import sys

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "Claude",
                   "_backup", "jj-takeoff")
SKIP = {"__pycache__", ".pytest_cache", "node_modules", ".vercel"}

# Losing any one of these loses something that exists nowhere else.
CRITICAL = [
    "tools/jnj_takeoff.py",
    "reference/calibration.md",
    "reference/rate_book.json",
    "eval/truth/measurement_truth_v3.json",
    "jj.py",
]


def walk(root):
    out = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            p = os.path.join(base, f)
            out[os.path.relpath(p, root).replace("\\", "/")] = os.path.getsize(p)
    return out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()[:16]


def main():
    if not os.path.isdir(DST):
        print(f"FAIL  no mirror at {DST}  -- run: python jj.py backup")
        return 1

    src, dst = walk(SRC), walk(DST)
    missing = sorted(set(src) - set(dst))
    sized = sorted(k for k in set(src) & set(dst) if src[k] != dst[k])

    print(f"  source (post-skip) : {len(src)} files")
    print(f"  mirror             : {len(dst)} files")
    print(f"  missing from mirror: {len(missing)}")
    print(f"  size mismatches    : {len(sized)}")
    for k in missing[:10]:
        print(f"     MISSING  {k}")
    for k in sized[:10]:
        print(f"     SIZE     {k}  src {src[k]} != mirror {dst[k]}")

    bad = 0
    print("  critical files (sha256):")
    for rel in CRITICAL:
        s, d = os.path.join(SRC, rel), os.path.join(DST, rel)
        if not (os.path.exists(s) and os.path.exists(d)):
            print(f"     ABSENT   {rel}")
            bad += 1
            continue
        hs, hd = sha(s), sha(d)
        match = hs == hd
        bad += 0 if match else 1
        print(f"     {'OK  ' if match else 'DIFF'}     {rel:<44} {hs}")

    failed = bool(missing or sized or bad)
    print("\n  " + ("BACKUP NOT COMPLETE" if failed else "BACKUP VERIFIED - mirror is faithful"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
