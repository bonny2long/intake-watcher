# Intake Watcher Architecture

Intake Watcher is intentionally shallow.

## Main data flow

```text
Windows / phone / laptop / work computer
  -> NAS Archive_Ingest share
  -> _INGEST/incoming
  -> Intake Watcher stable-upload check
  -> _INGEST/intake-processing
  -> _INGEST/ready
  -> Archive Assistant scan/review/approve/move
```

## Responsibilities

Intake Watcher:

- Watches or polls incoming uploads.
- Detects active temporary files.
- Detects whether file count and folder size are stable.
- Promotes stable completed uploads into ready.
- Logs every decision.

Archive Assistant:

- Scans ready.
- Classifies media.
- Handles metadata suggestions.
- Waits for Bonny approval.
- Moves approved media to final libraries.
- Writes move manifests and media metadata.

Cleaner, later:

- Handles safe empty source folder cleanup after approved moves.
- Routes uncertain leftovers for review.
- Never auto-deletes quarantine.

## Design choices

Polling is used first because it is simpler and safer on NAS/SMB paths than filesystem events. Event watching can be added after the logic is proven.

JSON state is used first because the watcher only needs to remember stable timestamps and fingerprints. A database is unnecessary for the MVP.
