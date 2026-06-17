# Intake Watcher Simple UI Patch

Goal: keep Intake Watcher light. The UI only shows what is happening in `_INGEST/incoming`, `_INGEST/intake-processing`, `_INGEST/ready`, and `_INGEST/failed`.

Do not add React, a database, metadata parsing, delete buttons, final-library moves, or Archive Assistant imports.

Required behavior:

- Run a local dashboard on port `8091`.
- Show Incoming / Waiting, Blocked / Needs Check, Ready for Archive Assistant, Processing / Failed, and Recent Events.
- Add a `Check now` button that runs one intake pass.
- Refresh automatically every 15 seconds.
- Use the existing JSON state and JSONL logs.
- Keep all actions safe: no delete, no overwrite, no final library movement, no metadata edits.

Local test:

```powershell
$env:STABILITY_SECONDS="0"
python -m intake_watcher.server --host 127.0.0.1 --port 8091
```

Do not seed dummy media for a clean dashboard. `scripts/create_sample_intake_tree.py` is optional demo-only.

Open:

```text
http://127.0.0.1:8091
```

NAS target:

```text
http://NAS-IP:8091
```

Mount `/mnt/rust-pool` as `/app/data` so the service sees:

```text
/app/data/_INGEST/incoming
/app/data/_INGEST/intake-processing
/app/data/_INGEST/ready
/app/data/_INGEST/failed
/app/data/_REPORTS/intake-watcher
```
