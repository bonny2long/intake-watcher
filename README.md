# Intake Watcher

Intake Watcher is the first app in Bonny's NAS workflow. It watches `_INGEST/incoming`, waits until an upload stops changing, then promotes it to `_INGEST/ready` for Archive Assistant.

```text
Intake Watcher     Is the upload finished?
Archive Assistant  What is it, and where should it go after approval?
Cleaner            After approved moves, what leftovers are safe to clean?
BM Radio           Plays the final Music and Audiobooks libraries.
```

It is intentionally shallow. It never decides what media is, where it belongs, or what can be deleted.

## Where it lives

| What | Local path | NAS path |
|---|---|---|
| Code | `C:\Dev\NAS\intake-watcher` | container image |
| Data root | `C:\NAS-Local\nas-data` | `/mnt/rust-pool` mounted at `/app/data` |
| Logs and state | `C:\NAS-Local\nas-data\_REPORTS\intake-watcher` | `/app/data/_REPORTS/intake-watcher` |
| Dashboard | http://127.0.0.1:8091 | private LAN or Tailscale only |

## What it does

- Watches `_INGEST/incoming` on a timer (`POLL_SECONDS`, default 300).
- Waits until an item's file count, sizes and modification times have not changed for `STABILITY_SECONDS` (default 1200, 20 minutes).
- Blocks items with temporary or partial download files, empty items, and items with no supported media.
- Moves finished items through `_INGEST/intake-processing` into `_INGEST/ready`. It never overwrites: with `COLLISION_POLICY=block`, an item whose name already exists in `ready` stays put and is flagged.
- Logs every decision to `_REPORTS/intake-watcher`.

A folder with **no supported media file** is not promoted. It stays in `incoming` under **Blocked / Needs Check** as `blocked_no_media_files`. Supported types are video (`.mkv .mp4 .m4v .avi .mov .wmv .webm .flv .mpg .mpeg .ts`), audio and audiobooks (`.mp3 .flac .wav .m4a .m4b .aac .ogg .opus .aiff .alac`), and books and comics (`.epub .pdf .mobi .azw3 .cbz .cbr`).

## What it never does

```text
No deletion.
No overwrite.
No media classification or metadata editing.
No embedded tag changes.
No writes to final libraries.
No imports of other apps.
No cleanup (that is Cleaner's job).
No public internet exposure.
```

## Setup

```powershell
Set-Location C:\Dev\NAS\intake-watcher
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
Copy-Item .env.example .env   # DATA_ROOT=C:/NAS-Local/nas-data
```

## Run

```powershell
.\.venv\Scripts\python.exe -m intake_watcher.server --host 127.0.0.1 --port 8091
```

Open http://127.0.0.1:8091. For faster local testing, set shorter timings in `.env` and restart:

```env
STABILITY_SECONDS=60
POLL_SECONDS=30
```

CLI commands:

```powershell
.\.venv\Scripts\python.exe -m intake_watcher.cli inspect
.\.venv\Scripts\python.exe -m intake_watcher.cli run-once
.\.venv\Scripts\python.exe -m intake_watcher.cli run-once --data-root C:/some/test/root --stability-seconds 0
.\.venv\Scripts\python.exe -m intake_watcher.cli status
.\.venv\Scripts\python.exe -m intake_watcher.cli watch
```

## Settings

```env
DATA_ROOT=C:/NAS-Local/nas-data
INTAKE_MODE=hybrid                 # hybrid, stability, or manual_marker
STABILITY_SECONDS=1200
POLL_SECONDS=300
STATUS_LOG_HEARTBEAT_SECONDS=900
AUTO_RUN=true
REQUIRE_READY_MARKER=false
READY_MARKERS=READY.txt,.done
ALLOW_SINGLE_FILE_PROMOTION=true
COLLISION_POLICY=block
DESTRUCTIVE_ACTIONS_ENABLED=false  # keep false
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=8091
```

## Dashboard lanes

| Lane | Meaning |
|---|---|
| Incoming / Waiting to Finish | Still copying, or waiting out the stability window |
| Blocked / Needs Check | Temp files, collisions, empty items, or no supported media. Inspect by hand |
| Ready for Archive Assistant | Promoted. Archive Assistant takes over when you click Scan ingest |
| Processing / Failed | Mid-promotion, or a promotion that failed |
| Recent Unique Events | History only. Clear recent hides events but keeps the raw logs |

The header links to Archive Assistant (http://127.0.0.1:5173) and Cleaner (http://127.0.0.1:8092).

## Archive Assistant bridge

Archive Assistant's backend `.env` points `INGEST_ROOT` at the same ready folder:

```env
INGEST_ROOT=C:/NAS-Local/nas-data/_INGEST/ready
```

On the NAS, both apps mount the same root so both see `/app/data/_INGEST/ready`. See [docs/ARCHIVE_ASSISTANT_BRIDGE.md](docs/ARCHIVE_ASSISTANT_BRIDGE.md) and [docs/NAS_DEPLOYMENT.md](docs/NAS_DEPLOYMENT.md).

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

14 tests, all using temporary folders. See [docs/TESTING.md](docs/TESTING.md).

## Troubleshooting

- **Stuck in Waiting:** still copying, temp files present, or the stability window has not passed.
- **Blocked:** check for a name collision in `ready`, an empty folder, or no supported media. Raw logs are in `_REPORTS/intake-watcher`.
