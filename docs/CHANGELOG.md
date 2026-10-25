# Changelog

## Unreleased - Origin check

- `POST` requests (Run once, Clear recent) are rejected with 403 when their `Origin` header is not a loopback address or listed in the new `ALLOWED_ORIGINS` setting. This stops a web page on another site from driving the dashboard through the browser. Requests with no `Origin` header (curl, scripts) still work.
- `main()` now builds its overridden config with `dataclasses.replace`, so new settings cannot be dropped by `--data-root` or `--stability-seconds`.
- Tests: 37.

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

