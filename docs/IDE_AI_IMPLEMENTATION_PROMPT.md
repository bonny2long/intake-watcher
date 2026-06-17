# IDE AI Build Prompt: Intake Watcher

Use this prompt in Cursor, Windsurf, Copilot Workspace, Claude Code, or another IDE agent when building the first Intake Watcher codebase.

This file is not executable. Do not run it with Python or PowerShell; read it as implementation guidance.

---

We are creating a separate project called `intake-watcher` for Bonny's NAS system.

Archive Assistant v2 Metadata Assist is complete and locked. Do not modify Archive Assistant. Do not import Archive Assistant code. Intake Watcher is a shallow pre-ingest service whose only job is to decide whether uploads are finished and promote completed items from `_INGEST/incoming` to `_INGEST/ready`.

System boundary:

- Intake Watcher answers: "Is the upload finished?"
- Archive Assistant answers: "What is this media, what metadata is needed, and where should it go after Bonny approves?"
- Cleaner answers later: "After approved moves, what safe leftovers can be cleaned or reviewed?"

Required safety rules:

- No deletion.
- No overwrite.
- No final library writes.
- No metadata edits.
- No embedded tag mutation.
- No media organization.
- No cleanup logic.
- No quarantine decisions.
- No React UI in MVP.
- No database in MVP.
- Every decision gets a JSONL log record.

Build a Python 3.11+ standard-library-only scaffold with this structure:

```text
intake-watcher/
  README.md
  pyproject.toml
  .env.example
  intake_watcher/
    __init__.py
    config.py
    fingerprint.py
    temp_files.py
    media_probe.py
    promotion.py
    reports.py
    watcher.py
    cli.py
  scripts/
    create_sample_intake_tree.py
    run_once.py
  tests/
    test_fingerprint_stability.py
    test_temp_file_blocking.py
    test_ready_marker_mode.py
    test_no_overwrite_promotion.py
    test_logs_written.py
```

Folder contract:

```text
data/
  _INGEST/
    incoming/
    intake-processing/
    ready/
    failed/
  _REPORTS/
    intake-watcher/
      intake-log.jsonl
      promotions/
      stuck/
```

TrueNAS target paths later:

```text
/mnt/rust-pool/_INGEST/incoming
/mnt/rust-pool/_INGEST/intake-processing
/mnt/rust-pool/_INGEST/ready
/mnt/rust-pool/_INGEST/failed
/mnt/rust-pool/_REPORTS/intake-watcher
```

MVP behavior:

1. Scan direct children of `_INGEST/incoming`.
2. For each top-level folder/file, calculate a fingerprint:
   - file count
   - total size bytes
   - latest file mtime
   - temp file count
   - media-looking file count
   - whether a ready marker exists
3. Block temp/incomplete files:
   - `.part`
   - `.tmp`
   - `.crdownload`
   - `.download`
   - `.aria2`
   - `.!qB`
4. Block items with no media-looking file.
5. Optional manual-marker mode requires `READY.txt` or `.done` inside the folder.
6. Hybrid/default mode promotes when no temp files exist and the fingerprint remains unchanged for the configured stability window.
7. Promote through `_INGEST/intake-processing` first, then into `_INGEST/ready`.
8. Verify the fingerprint after moving to processing. If it changed, do not promote to ready; move to `_INGEST/failed` if possible, otherwise leave in processing and log the failure.
9. Never overwrite a ready destination. Default collision behavior should be `block` and log `blocked_collision`.
10. Write promotion reports to `_REPORTS/intake-watcher/promotions`.

CLI commands:

```bash
python -m intake_watcher.cli inspect
python -m intake_watcher.cli run-once
python -m intake_watcher.cli watch
python -m intake_watcher.cli status
```

PowerShell local setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python scripts\create_sample_intake_tree.py
$env:STABILITY_SECONDS="0"
python -m intake_watcher.cli run-once
python -m intake_watcher.cli run-once
```

The first `run-once` records a stable fingerprint. The second `run-once` can promote unchanged eligible sample media into `_INGEST/ready`.

Environment defaults:

```env
DATA_ROOT=data
INTAKE_MODE=hybrid
STABILITY_SECONDS=1200
POLL_SECONDS=300
REQUIRE_READY_MARKER=false
READY_MARKERS=READY.txt,.done
ALLOW_SINGLE_FILE_PROMOTION=true
COLLISION_POLICY=block
DESTRUCTIVE_ACTIONS_ENABLED=false
```

Acceptance tests:

- A stable folder with a `.mkv` promotes to ready after the stability window.
- A folder containing `.crdownload` does not promote.
- A folder with changing total size or file count does not promote until stable.
- Manual marker mode blocks a folder without `READY.txt` or `.done`.
- Existing destination in ready is not overwritten.
- Every run writes JSONL logs.
- A loose media file can promote only when `ALLOW_SINGLE_FILE_PROMOTION=true`.

Local safety note:

- On this Windows workstation, do not run ad hoc Python `tempfile` / `unittest` commands that create test data under the default user temp directory. That has previously left Python processes running hot. If tests are needed, use a reviewed workspace-local test root and verify no Python process is left running afterward.

Do not add features outside this scope. Keep this first version boring, auditable, and safe.
