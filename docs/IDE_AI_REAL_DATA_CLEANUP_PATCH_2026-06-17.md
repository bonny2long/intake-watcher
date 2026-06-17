# IDE AI Patch: Intake Watcher Real-Data Cleanup + Safety Lock

Owner: Bonny Makaniankhondo
Project: NAS Intake Watcher
Date: 2026-06-17

## Goal

Clean the Intake Watcher repo for real incoming-folder testing. Keep the lightweight dashboard, remove demo/scaffold leftovers, and prevent overlapping watcher runs.

## Runtime Boundary

```text
Download app on computer
  -> _INGEST/incoming
  -> Intake Watcher checks stability
  -> _INGEST/intake-processing
  -> _INGEST/ready
  -> Archive Assistant scans ready later
```

Intake Watcher stays shallow. It does not parse metadata, import Archive Assistant code, move files to final libraries, delete files, or expose cleanup actions.

## Cleanup Applied

- Removed duplicate nested project folder: `intake-watcher-main/`.
- Removed generated package metadata: `intake_watcher.egg-info/`.
- Removed demo dummy-data script: `scripts/create_sample_intake_tree.py`.
- Added `*.egg-info/` to `.gitignore`.
- Removed stale scaffold/demo implementation docs.
- Kept the lightweight dashboard and current architecture docs.

## Safety Fix Applied

`intake_watcher/server.py` uses a shared `RunCoordinator` with a `threading.Lock`.

Both dashboard paths now run through the same coordinator:

- Background `AUTO_RUN=true` polling loop.
- Manual dashboard `POST /api/run-once` from the `Check now` button.

This prevents the background watcher and manual run from moving the same item at the same time.

## Dashboard Scope

Allowed endpoints:

```text
GET  /
GET  /api/health
GET  /api/status
GET  /api/items
GET  /api/events
GET  /api/dashboard
POST /api/run-once
```

Do not add delete, cleanup, metadata-editing, Archive Assistant scan, or final-library movement endpoints.

## Real-Data Local Test

Use a shorter stability window for first local testing:

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

For later NAS testing:

```env
STABILITY_SECONDS=1200
POLL_SECONDS=300
AUTO_RUN=true
```

## Do Not Add

- React
- PostgreSQL or SQLite
- Archive Assistant imports
- metadata extraction
- media classification
- final library movement
- cleanup or deletion
- quarantine movement
- public internet exposure
