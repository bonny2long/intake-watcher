# Intake Watcher Architecture

## System Purpose

Intake Watcher is the shallow pre-ingest service for Bonny's NAS workflow.

It answers:

```text
Is this upload finished?
```

It watches `_INGEST/incoming`, waits until uploads stop changing, then promotes completed files/folders into `_INGEST/ready`.

## Three-System Boundary

```text
Intake Watcher
  Determines whether copied/downloaded items are finished.

Archive Assistant
  Scans ready items, identifies media, supports review/approval, moves into final libraries, and writes manifests/logs.

Future Cleaner
  Future cleanup/removal workflow. Not active in Intake Watcher.
```

Intake Watcher does not import Archive Assistant and does not implement Cleaner behavior.

## Folder Lanes

```text
data/_INGEST/incoming
  Active downloads/copies land here.

data/_INGEST/intake-processing
  Temporary safe promotion lane.

data/_INGEST/ready
  Completed handoff lane for Archive Assistant.

data/_INGEST/failed
  Failed or blocked promotion lane when needed.

data/_REPORTS/intake-watcher
  JSON/JSONL logs, status, stuck reports, promotion reports.
```

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

## Future Cleaner Handoff

Cleaner is future work.

Cleanup, leftover deletion, duplicate removal, and post-move trash decisions do not belong to Intake Watcher.

If cleanup is mentioned in docs, it means future Cleaner or Archive Assistant v3, not active Intake Watcher behavior.

