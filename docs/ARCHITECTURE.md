# Intake Watcher Architecture

## System Purpose

Intake Watcher is the shallow pre-ingest service for Bonny's NAS workflow.

It answers:

```text
Is this upload finished?
```

It watches `_INGEST/incoming`, waits until uploads stop changing, then promotes completed files/folders into `_INGEST/ready`.

## System Boundary

```text
Intake Watcher
  Determines whether copied/downloaded items are finished.

Archive Assistant
  Scans ready items, identifies media, supports review/approval, moves into final libraries, and writes manifests/logs.

Cleaner
  Reports leftovers after approved moves; can remove reviewed empty folders
  when its production gates are on. Separate app; never part of Intake Watcher.

BM Radio
  Plays the final Music and Audiobooks libraries.
```

Intake Watcher does not import any other app and does not implement Cleaner behavior.

## Folder Lanes

```text
nas-data/_INGEST/incoming
  Active downloads/copies land here.

nas-data/_INGEST/intake-processing
  Temporary safe promotion lane.

nas-data/_INGEST/ready
  Completed handoff lane for Archive Assistant.

nas-data/_INGEST/failed
  Failed or blocked promotion lane when needed.

nas-data/_REPORTS/intake-watcher
  JSON/JSONL logs, status, stuck reports, promotion reports.
```

The preferred local root is `C:\NAS-Local\nas-data`, which mirrors the future NAS layout.

## Internal Module Map

```text
config.py        Environment/config paths and safety settings
fingerprint.py   File/folder count, size, modified-time, temp/media counts
temp_files.py    Temporary/incomplete file detection
media_probe.py   Shallow media-looking extension checks
promotion.py     Safe movement through intake-processing into ready
reports.py       JSON/JSONL state and log helpers
watcher.py       Main inspect/run-once/watch/status logic
server.py        Lightweight HTTP dashboard and API
web/             Plain HTML/CSS/JS dashboard
cli.py           Developer/debug CLI
```

## API Map

```text
GET  /
GET  /api/health
GET  /api/status
GET  /api/items
GET  /api/events?limit=100
GET  /api/dashboard
POST /api/run-once
POST /api/events/clear
```

The dashboard API is local and lightweight. It does not expose delete behavior.

## State And Logging Model

Intake Watcher records decisions in `_REPORTS/intake-watcher`.

Important idea:

```text
Current lane state is truth.
Recent events are history.
```

Clearing recent events hides them from the dashboard view but does not delete raw JSONL logs.

## Promotion Algorithm

High-level flow:

```text
inspect incoming item
  -> reject active temp/incomplete files
  -> fingerprint file/folder count, size, and modified times
  -> wait until fingerprint is stable for STABILITY_SECONDS
  -> check collision policy
  -> move through intake-processing
  -> promote to ready
  -> log decision
```

No overwrite is the default. `COLLISION_POLICY=block` keeps the source out of ready if the destination already exists.

## Failure And Blocking Behavior

Items can be blocked when:

- They are still changing.
- Temporary download/copy files are present.
- The source is empty.
- The item is unsupported.
- A destination collision exists.
- Promotion fails.

Blocked means Bonny should inspect. It does not mean Intake Watcher should delete anything.

## Why Polling Is Used First

Polling is simple and reliable for the local/NAS workflow. It avoids platform-specific watcher edge cases while the system is still being proven.

The polling interval is controlled by `POLL_SECONDS`.

## Cleaner Boundary

Cleaner is a separate app (`C:\Dev\NAS\cleaner`). Cleanup, leftover removal, and duplicate decisions never belong to Intake Watcher.

## Items With No Media Files

A folder with no supported media file is not promoted. It stays in `incoming` and shows under **Blocked / Needs Check** as `blocked_no_media_files`. Supported types are video (`.mkv .mp4 .m4v .avi .mov .wmv .webm .flv .mpg .mpeg .ts`), audio and audiobooks (`.mp3 .flac .wav .m4a .m4b .aac .ogg .opus .aiff .alac`), and books and comics (`.epub .pdf .mobi .azw3 .cbz .cbr`). Override with `SUPPORTED_MEDIA_EXTENSIONS`. Move non-media items out by hand.
