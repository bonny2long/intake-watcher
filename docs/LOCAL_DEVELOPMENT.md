# Local Development

## Setup

Windows PowerShell:

```powershell
cd C:\Users\BonnyMakaniankhondo\Documents\GitHub\NAS\intake-watccher

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Run Dashboard

The preferred local data root is the shared NAS-style folder:

```text
C:\Users\BonnyMakaniankhondo\Documents\GitHub\NAS\nas-data
```

The project `.env` points `DATA_ROOT` there by default. PowerShell overrides still work for temporary test settings.

```powershell
$env:STABILITY_SECONDS="60"
$env:POLL_SECONDS="15"
$env:AUTO_RUN="true"

python -m intake_watcher.server --host 127.0.0.1 --port 8091
```

Open:

```text
http://127.0.0.1:8091
```

## Run CLI

```bash
python -m intake_watcher.cli inspect
python -m intake_watcher.cli run-once
python -m intake_watcher.cli watch
python -m intake_watcher.cli status
python -m intake_watcher.cli serve
```

## Test Folder Structure

```text
../nas-data/_INGEST/incoming
../nas-data/_INGEST/intake-processing
../nas-data/_INGEST/ready
../nas-data/_INGEST/failed
../nas-data/_REPORTS/intake-watcher
```

Use `nas-data/_INGEST/incoming` for new test drops. Do not use Archive Assistant's old project `data/_INGEST` during bridged testing.

Do not use your only copy of media for tests. Use copies.

## Test A Small PDF/Book

1. Copy a small PDF or EPUB into `../nas-data/_INGEST/incoming`.
2. Wait for the stability window.
3. Run `run-once` or let the dashboard background watcher run.
4. Confirm the file moves to `../nas-data/_INGEST/ready`.
5. Confirm Archive Assistant can scan the ready folder.

## Test A Folder/Discography

1. Copy a test folder into `../nas-data/_INGEST/incoming`.
2. Keep copying active and confirm Intake Watcher waits.
3. Stop copying and wait for the stability window.
4. Confirm the folder promotes to `../nas-data/_INGEST/ready`.

## Clear Dashboard Events Safely

Use the dashboard Clear recent action.

This hides recent events from the dashboard but does not delete raw JSONL logs.
