# Testing

## Unit Tests

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

## Dashboard Manual Test

1. Start the dashboard.
2. Place a test file in `data/_INGEST/incoming`.
3. Confirm it appears in `Incoming / Waiting`.
4. Wait for stability.
5. Confirm it appears in `Ready for Archive Assistant`.

## Temp File Blocking Test

Place a file with an incomplete/temp-looking extension in `incoming`.

PASS means Intake Watcher does not promote it to ready.

## Collision Test

Create a destination with the same name in `ready`, then place the same source name in `incoming`.

PASS means the item is blocked and not overwritten.

## Stability Timer Test

Modify a file repeatedly while Intake Watcher is running.

PASS means the item waits until changes stop for `STABILITY_SECONDS`.

## Archive Assistant Bridge Test

1. Promote a test item to `ready`.
2. Confirm Archive Assistant is configured to scan the same ready folder.
3. Click Scan in Archive Assistant.

PASS means Archive Assistant sees the ready item.

## Big Folder/Discography Test

Copy a large folder into `incoming`.

PASS means Intake Watcher waits during active transfer and promotes only after the folder is stable.

## What PASS Means

PASS means Intake Watcher safely decided whether an upload is finished.

It does not mean metadata, final organization, or cleanup has been completed.

