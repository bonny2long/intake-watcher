# Intake Watcher Scaffold

Intake Watcher is a shallow pre-ingest service for Bonny's NAS workflow.

Its only job is to answer: **is this upload finished?**

It watches `_INGEST/incoming`, waits until uploads are stable, then promotes completed items to `_INGEST/ready` so Archive Assistant can scan them later.

It does **not** classify media deeply, edit metadata, organize libraries, clean leftovers, delete files, overwrite files, or move anything into final media folders.

## Safety contract

Intake Watcher must preserve these rules:

- No deletion.
- No overwrite.
- No final library writes.
- No metadata parsing beyond shallow media-looking extension checks.
- No Archive Assistant imports.
- Every decision must be logged.
- Anything active, temporary, unstable, empty, unsupported, or colliding must stay out of `ready`.

## Folder layout

Local development layout:

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

TrueNAS target layout:

```text
/mnt/rust-pool/_INGEST/incoming
/mnt/rust-pool/_INGEST/intake-processing
/mnt/rust-pool/_INGEST/ready
/mnt/rust-pool/_INGEST/failed
/mnt/rust-pool/_REPORTS/intake-watcher
```

## Install for development

This scaffold uses only the Python standard library.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e .
```

## Create a sample tree

```bash
python scripts/create_sample_intake_tree.py
```

## Run once

```bash
python -m intake_watcher.cli run-once
```

For quick testing, set the stability window to zero:

```bash
STABILITY_SECONDS=0 python -m intake_watcher.cli run-once
```

On Windows PowerShell:

```powershell
$env:STABILITY_SECONDS="0"
python -m intake_watcher.cli run-once
```

## Commands

```bash
python -m intake_watcher.cli inspect
python -m intake_watcher.cli run-once
python -m intake_watcher.cli watch
python -m intake_watcher.cli status
```

## Environment variables

Copy `.env.example` to your own shell/profile or compose environment later.

Important settings:

```env
DATA_ROOT=data
INTAKE_MODE=hybrid
STABILITY_SECONDS=1200
POLL_SECONDS=300
REQUIRE_READY_MARKER=false
ALLOW_SINGLE_FILE_PROMOTION=true
COLLISION_POLICY=block
```

`COLLISION_POLICY=block` is the default and safest behavior. If a destination already exists, the watcher logs `blocked_collision` and does not promote the item.

## Tests

Important Windows note: do not run ad hoc `tempfile` / `unittest` commands that create test data under the user temp directory. That has previously left Python processes running hot on this machine.

Only run tests when needed, and prefer an explicit workspace-local test root or a reviewed test helper instead of Python's default temp directory.

```bash
python -m unittest discover -s tests -v
```

## Archive Assistant integration

Archive Assistant should scan `_INGEST/ready`, not `_INGEST/incoming`.

Intake Watcher produces completed ready folders/files. Archive Assistant remains responsible for media classification, review, metadata suggestions, approval, move manifests, and final library writes.
