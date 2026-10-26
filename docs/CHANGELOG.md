# Changelog

## Unreleased

- `POST` requests (Run once, Clear recent) are rejected with 403 when their `Origin` header is not a loopback address or listed in the new `ALLOWED_ORIGINS` setting. This stops a web page on another site from driving the dashboard through the browser. Requests with no `Origin` header (curl, scripts) still work. A refused request's body is read and dropped first, so the caller always gets the 403 and not a reset connection.
- `main()` now builds its overridden config with `dataclasses.replace`, so new settings cannot be dropped by `--data-root` or `--stability-seconds`.
- A damaged `state.json` (empty, truncated, not JSON, or the wrong shape) no longer stops Intake Watcher or the dashboard. The file is renamed `state.json.corrupt-<UTC time>` in `_REPORTS/intake-watcher`, a `state_file_corrupt` event is logged, and tracking starts empty, so waiting items simply restart their stability window. Unreadable entries inside an otherwise valid file are skipped and logged as `state_items_skipped`. `dashboard_state.json` is handled the same way.
- A fingerprint is now one walk of the folder instead of three, with identical results (checked against the old method on all 13 Restock folders: 13 of 13 equal, 6.4x faster).
- The dashboard no longer fingerprints every incoming item a second time on each refresh; it reuses the reason computed by `inspect()`.
- **Moves are renames only.** New `safe_move.py`. Promotion used `shutil.move`, which silently copies and then deletes when a rename is impossible because the source and destination are on different filesystems (two ZFS datasets, two Docker mounts, two drives). A copy of a large download is slow and not atomic, and a crash halfway would leave a partial item where the next stage looks. Promotion now renames, never replaces anything that exists, and a cross-filesystem move fails with a logged message (`move_to_processing_failed` or `move_to_ready_failed`) and leaves the item where it was. Check a NAS layout with Archive Assistant's `scripts/nas_storage_preflight.py`.
- Tests: 56.

## 2026-09-27 - Current layout and docs

- Suite navigation links point at the right apps on 127.0.0.1 (the Archive Assistant tab pointed at BM Radio).
- Docs updated for the runbook v12 layout: code in `C:\Dev\NAS\intake-watcher`, data in `C:\NAS-Local\nas-data`.
- Documented that folders with no supported media stay blocked in `incoming`.
- Added a `dev` extra with pytest. 14 tests.

## 2026-06-17 - Local MVP locked

- Added lightweight dashboard.
- Added automatic background watcher mode.
- Added dashboard Clear recent behavior that preserves raw JSONL logs.
- Matched dashboard visual styling to Archive Assistant.
- Proved local bridge to Archive Assistant ready folder.
- Proved PDF/book flow.
- Proved large music discography flow.
- Confirmed Intake Watcher remains shallow and does not organize media or clean leftovers.

