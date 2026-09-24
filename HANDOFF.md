# J&J Takeoff — Engineering Handoff (ASTRA import + Claude estimator training)

**Written:** 2026-09-23 20:41 EDT · **Repo:** `C:\Users\jason\JJ-Takeoff-astra` (worktree of `C:\Users\jason\JJ-Takeoff`) · **Branch:** `astra-import` @ `9687b8d` + this commit
**Prior handoff:** `HANDOFF-archive-2026-09-23-2041.md`. It remains the best source for the 8/21 virtual-takeoff / zero-ink autonomy era on branch `virtual-takeoff`.

---

## 1. Mission
The goal is plans in, accurate estimate out. ASTRA (a Codex agent) built the estimating engine plus LEVEL GROUND from 9/8 to 9/22. Its work is imported **verbatim** here and reproduces exactly. Claude is now being trained as J&J's estimator. The method is blind hand takeoffs, frozen before the key is seen and scored against Jason's own measurements. Jason's rules are captured as they are taught.

## 2. Current State
- **ASTRA import:** commit `9687b8d` on `astra-import`. Not pushed; Jason pushes.
- **Test suite:** run with `PY C:\Users\jason\Astra-Takeover\run_suite.py`.
  - Rerun 9/23 20:39: **240/244**, `engine_unchanged: true`.
  - 3 failures pre-date the import:
    - `run_golden.py`: Roberts windows 21 vs 22.
    - `test_levelground_workspace_measurement`.
    - `test_measurement_preparation_recovery`.
  - 1 failure is **flaky**: `test_levelground_reviewer_queue` failed once under full-suite load, then passed 6/6 when run on its own. The prior run was 241/244.
- **Roberts reproduction:** exact ($363,597.15 cost / $397,569.32 sell, 752 rows) through the relocation harness. See `C:\Users\jason\Astra-Takeover\README.md`.
- **Davis #2 cold engine run** (ASTRA code): 2 of 88 items produced (roof only).
- **Davis #2 Claude hand takeoff:**
  - v1 blind: 31/84 within 10%.
  - v2 with Jason's rules only: 37.
  - v2 plus key-informed re-reads: 45.
  - Scorecard: `Astra-Takeover\handread\SCORECARD.md`.
- **Anderson (Hwy 36, Covington):**
  - Blind takeoff frozen 9/23 17:05, 89 rows.
  - Rev 2 applies Jason's answers: 88 rows, `anderson\out\Anderson - Claude Takeoff rev2 2026-09-23.xlsx`.
  - **Waiting on Jason's measurements (key) to score it.**
- **Next action:** when Jason sends the Anderson key, score v1 (blind) against key-net and key-raw with `handread\score_*` as the pattern, and split any rule vs re-read changes.

## 3. Decisions Made (and Why)
- **Never modify ASTRA's work.**
  - Alternative rejected: refactoring into `virtual-takeoff`.
  - Reason: Jason paid for it, and "don't make any changes to what astra has done."
  - Load-bearing.
- **Relocation harness instead of patching digests.**
  - What it does: `serve_relocated.py` monkeypatches `scope_digest` / `quantity_binding` / `count_digest` to hash with `mirror\` mapped back to the original path.
  - Alternative rejected: editing ASTRA code.
  - Load-bearing.
- **Hand takeoff (Claude + PyMuPDF vectors) as the training track, alongside ASTRA's engine.**
  - Reason: the engine produced 2 of 88 items cold on Davis #2.
  - Direction is **not settled**: whether to extend ASTRA's extraction or finish Roberts lines is Jason's call.
- **Three quantity columns: RAW / WASTE % / ORDER.**
  - Reason: keys mix raw and with-waste numbers. Jason: "handle waste in the best way for you."
  - Easy to change.
- **Freeze with sha256 before seeing any key.** Changes after the key are tagged RE-READ and scored separately.

## 4. Architecture & Key Files
- `docs/TAKEOFF_CONVENTIONS.md` (NEW): Jason's hand-takeoff rules. Canonical copy is `C:\Users\jason\Astra-Takeover\TAKEOFF_CONVENTIONS.md`; a third copy lives in `~\.claude\skills\jnj-estimate-takeoff\reference\`. **Read it before any takeoff.**
- `C:\Users\jason\Astra-Takeover\` (its own git repo, branch `main`): the evidence and reproduction harness. `README.md` maps every result to a command.
  - `run_suite.py`, `serve_relocated.py`, `compare_snapshot.py`, `trade_status.py`, `coldrun/`.
  - `handread/`: Davis #2 v1/v2 scripts, frozen outputs, can-light diagram.
  - `anderson/`: blind + rev2 scripts, xlsx, `FROZEN.txt`.
  - `mirror/` (12 GB) is gitignored; rebuild it from `C:\Users\jason\Astra-Backup-2026-09-22`.
- Runtime: `C:\Users\jason\.astra-runtime\venv\Scripts\python.exe` (Py 3.12.14 plus ASTRA's pins).
- ASTRA original (read-only): `C:\Users\jason\Documents\Codex\2026-09-08\i-h`. Backup: `C:\Users\jason\Astra-Backup-2026-09-22`.
- Everything else in this tree is ASTRA's code, unchanged since `9687b8d`.

## 5. Gotchas & Hard-Won Knowledge
- ASTRA's review fingerprints embed absolute paths. Copy the workspace and prices get withheld; use the harness.
- The edit round-trip bumps `measurement_version`. Re-copy the mirror from the backup afterward.
- Room polygonize fails on floor plans because door gaps don't close. Use the dimension strings for room areas.
- Can-light symbol = a filled ~7.3 pt 100-segment polygon. Triples of the same symbol in a row are vanity bars, not cans.
- Anderson sheet 7 is titled "Basement Plan" but the house is slab. Standard details are not scope. **Ask.**
- Keys can carry the estimator's shortcuts. Skip's Davis key left out tile under the cabinets.
- Slow OneDrive `grep -r` / `du` over the Desktop time out; avoid them.

## 6. Conventions In Play
- All takeoff rules are in `docs/TAKEOFF_CONVENTIONS.md`. Memory has the same rules in `feedback_takeoff_conventions_davis2.md`.
- Tag every line MEASURED / PLAN-STATED / ASSUMED / JASON.
- Send ONE batch of intake questions before measuring.
- Credit ASTRA by name, never "Sol."
- Commits end with the Claude co-author line. Jason pushes.

## 7. Open Questions
- Is shingle waste 25% (template + Davis key) or 15% (`jnj-estimate-takeoff/SKILL.md`)?
- Roberts windows: 22 (ASTRA, matches the Andersen quote) or 23 (Jason 7/27)?
- Anderson assumptions still open:
  - power run 230 ft
  - backsplash 20 SF
  - pantry shelves × 3
  - shower glass 62 SF
  - dog wash valve/tile 52 SF
  - downspouts 80 LF
  - clearing 0.45 ac
- Direction: extend ASTRA's plan extraction, or keep Claude hand takeoffs as the production path?
- Is `test_levelground_reviewer_queue` flaky under load? It's ASTRA's test, so investigate but don't edit it without asking.

## 8. Do Not Touch
- ASTRA's workspace `Documents\Codex\2026-09-08\i-h` and any ASTRA-authored file in this tree.
- The frozen blind outputs (`handread/out/davis2_takeoff.json`, `anderson/out/anderson_takeoff.json`). Their sha256 values are in `FROZEN*.txt`.
- `Desktop\Claude\_backup\jj-takeoff` (627 MB snapshot). Never commit it.

## 9. Resume Command
> "Read `C:\Users\jason\JJ-Takeoff-astra\HANDOFF.md` and `docs/TAKEOFF_CONVENTIONS.md`. If Jason has sent Anderson measurements, score the frozen blind takeoff against them (raw and net-of-waste). Do not modify ASTRA's code or the frozen outputs. Confirm before changing anything outside `Astra-Takeover\`."
