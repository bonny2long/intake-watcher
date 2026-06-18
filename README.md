# Intake Watcher

Intake Watcher is a safe pre-ingest watcher for Bonny's NAS workflow.
It watches `_INGEST/incoming`, waits until uploads stop changing, then promotes completed items to `_INGEST/ready`.
Archive Assistant scans `_INGEST/ready` later.

Intake Watcher is intentionally shallow. Its job is to answer one question:

```text
Is this upload finished?
```

It does not decide what the media is, where it belongs, what metadata it should use, or what leftovers can be deleted. Those jobs belong to Archive Assistant and the future Cleaner project.

## What Intake Watcher Does

- Watches `nas-data/_INGEST/incoming`.
- Detects temporary, incomplete, changing, empty, unsupported, or colliding items.
- Waits for files and folders to remain stable for the configured stability window.
- Moves completed items through `nas-data/_INGEST/intake-processing` into `nas-data/_INGEST/ready`.
- Logs every decision to `_REPORTS/intake-watcher`.
- Provides a small local dashboard for current state and recent events.

## What Intake Watcher Does Not Do

- No media library organization.
- No deep media classification.
- No metadata editing.
- No embedded tag mutation.
- No final library writes.
- No Archive Assistant imports.
- No Cleaner behavior.
- No cleanup or deletion of media.
- No public internet exposure.

## Safety Contract

These rules are part of the project boundary:

```text
No deletion.
No overwrite by default.
No final library writes.
No metadata editing.
No embedded tag mutation.
No Archive Assistant imports.
No Cleaner behavior.
No public internet exposure.
Every decision is logged.
```

`COLLISION_POLICY=block` is the safest behavior. If a destination already exists in `ready`, Intake Watcher logs the collision and leaves the source out of `ready`.

`DESTRUCTIVE_ACTIONS_ENABLED=false` should remain false. Intake Watcher should not delete media.

## Folder Flow

```text
Download app / copied media
  -> nas-data/_INGEST/incoming
  -> Intake Watcher waits until upload is stable
  -> nas-data/_INGEST/ready
  -> Archive Assistant scans ready
  -> Bonny reviews/approves
  -> Archive Assistant moves into final libraries and writes manifests/logs
```

Preferred local shared NAS-style data root:

```text
C:\Users\BonnyMakaniankhondo\Documents\GitHub\NAS\nas-data
```

Use `nas-data/_INGEST/incoming` for new test drops. Do not use Archive Assistant's old project `data/_INGEST` during bridged testing.

Local shared layout:

```text
nas-data/
  _INGEST/
    incoming/
    intake-processing/
    ready/
    failed/
    leftover-review/
  _STAGING/
  _QUARANTINE/
  _REPORTS/
    intake-watcher/
    archive-assistant/
    cleaner/
  Music/
  Movies/
  TV/
  Books/
  Audiobooks/
```

## Local Development Quick Start

Windows PowerShell:

```powershell
cd C:\Users\BonnyMakaniankhondo\Documents\GitHub\NAS\intake-watccher

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .

$env:STABILITY_SECONDS="60"
$env:POLL_SECONDS="15"
$env:AUTO_RUN="true"

python -m intake_watcher.server --host 127.0.0.1 --port 8091
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

STABILITY_SECONDS=60 POLL_SECONDS=15 AUTO_RUN=true python -m intake_watcher.server --host 127.0.0.1 --port 8091
```

## Dashboard Quick Start

Open:

```text
http://127.0.0.1:8091
```

The dashboard is local-only by default. Do not expose it publicly.

Installed dashboard command:

```bash
intake-watcher-dashboard
```

## CLI Commands

Module commands:

```bash
python -m intake_watcher.cli inspect
python -m intake_watcher.cli run-once
python -m intake_watcher.cli watch
python -m intake_watcher.cli status
python -m intake_watcher.cli serve
```

Installed script names:

```bash
intake-watcher
intake-watcher-dashboard
```

## Environment Variables

```env
DATA_ROOT=../nas-data
INTAKE_MODE=hybrid
STABILITY_SECONDS=1200
POLL_SECONDS=300
STATUS_LOG_HEARTBEAT_SECONDS=900
AUTO_RUN=true
REQUIRE_READY_MARKER=false
READY_MARKERS=READY.txt,.done
ALLOW_SINGLE_FILE_PROMOTION=true
COLLISION_POLICY=block
DESTRUCTIVE_ACTIONS_ENABLED=false
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8091
```

Important settings:

- `DATA_ROOT`: root containing `_INGEST`, `_REPORTS`, and shared NAS-style folders. For Bonny's local setup, use `C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/nas-data`.
- `STABILITY_SECONDS`: how long files/folders must stop changing before promotion.
- `POLL_SECONDS`: how often the background watcher checks.
- `INTAKE_MODE`: `hybrid`, `stability`, or `manual_marker`.
- `COLLISION_POLICY=block`: safest behavior; do not overwrite ready items.
- `DESTRUCTIVE_ACTIONS_ENABLED=false`: should remain false; Intake Watcher should not delete media.

## Dashboard Lanes

```text
Incoming / Waiting to Finish
Blocked / Needs Check
Ready for Archive Assistant
Processing / Failed
Recent Unique Events
```

Interpretation:

- `Incoming / Waiting to Finish`: normal while copying or downloading.
- `Blocked / Needs Check`: Bonny should inspect.
- `Ready for Archive Assistant`: Intake Watcher is done.
- `Processing / Failed`: currently moving or failed during safe promotion.
- `Recent Unique Events`: history only, not current truth.

Current lane cards and counts show the live state.
Clear recent hides events from the dashboard but does not delete raw JSONL logs.

## Archive Assistant Bridge

Archive Assistant should scan `_INGEST/ready`, not `_INGEST/incoming`.

Local proven bridge:

```text
Shared ready folder:
C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/nas-data/_INGEST/ready

Archive Assistant backend .env:
INGEST_ROOT=C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/nas-data/_INGEST/ready
```

Archive Assistant remains responsible for media classification, review, metadata suggestions, approval, move manifests, and final library writes.

## NAS Deployment Summary

Target NAS layout:

```text
/mnt/rust-pool/_INGEST/incoming
/mnt/rust-pool/_INGEST/intake-processing
/mnt/rust-pool/_INGEST/ready
/mnt/rust-pool/_INGEST/failed
/mnt/rust-pool/_REPORTS/intake-watcher
```

In production, Intake Watcher and Archive Assistant should mount the same NAS root so both see:

```text
/app/data/_INGEST/ready
```

See `docs/NAS_DEPLOYMENT.md`.

## Testing

Run:

```bash
python -m unittest discover -s tests -v
```

Expected tests include:

```text
test_dashboard_clear_events.py
test_dashboard_waiting_copy.py
test_fingerprint_stability.py
test_log_deduplication.py
test_logs_written.py
test_no_overwrite_promotion.py
test_ready_marker_mode.py
test_temp_file_blocking.py
```

See `docs/TESTING.md`.

## Current Local Proof Cases

Local workflow proof completed:

- PDF/book files promoted from incoming to ready.
- Archive Assistant scanned Intake Watcher ready folder.
- Books were reviewed, approved, moved, and received move manifests.
- Large music discography folder waited during active transfer, promoted after stability, then Archive Assistant moved it to `Music/Discographies/Kanye West`.
- Lil Wayne mixtape/discography folder also completed through final Archive Assistant movement.

These are local workflow proof cases, not final NAS production certification.

## Future Cleaner Boundary

Cleaner is a future project. It is not active in Intake Watcher.

Any documentation that mentions cleanup should mean future Cleaner or Archive Assistant v3. Intake Watcher does not clean leftovers, delete files, or decide what can be safely removed.

## Troubleshooting

If files stay in `Incoming / Waiting`:

- They may still be copying.
- Temporary files may still exist.
- The stability timer may not have elapsed.

If items show as `Blocked / Needs Check`:

- Check for collisions in `ready`.
- Check unsupported or empty folders.
- Check raw logs in `_REPORTS/intake-watcher`.

If Archive Assistant does not see ready items:

- Confirm the items are in `_INGEST/ready`.
- Confirm Archive Assistant is configured to scan the same ready folder.
- Restart Archive Assistant after changing its `.env`.

## Documentation Map

- `docs/ARCHITECTURE.md`: system boundary and internals.
- `docs/LOCAL_DEVELOPMENT.md`: local setup and manual checks.
- `docs/NAS_DEPLOYMENT.md`: TrueNAS/Docker deployment notes.
- `docs/OPERATIONS.md`: day-to-day operator guide.
- `docs/ARCHIVE_ASSISTANT_BRIDGE.md`: handoff to Archive Assistant.
- `docs/TESTING.md`: test commands and manual test cases.
- `docs/CHANGELOG.md`: project history.
