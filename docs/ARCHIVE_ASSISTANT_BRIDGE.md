# Archive Assistant Bridge

Intake Watcher and Archive Assistant connect through the ready folder.

## Local Development

Intake Watcher ready folder:

```text
C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/intake-watccher/data/_INGEST/ready
```

Archive Assistant backend `.env`:

```env
INGEST_ROOT=C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/intake-watccher/data/_INGEST/ready
```

If Bonny's local folder is still temporarily spelled `intake-watccher`, use the actual folder path on disk. The repo should eventually be renamed to `intake-watcher` to avoid path mistakes.

## Production NAS

Both apps should mount the same NAS root:

```text
/mnt/rust-pool -> /app/data
```

Then both apps see:

```text
/app/data/_INGEST/ready
```

## Boundary

Intake Watcher only promotes stable uploads into ready.

Archive Assistant scans ready, handles review/approval, and moves files into final libraries.

Do not make Intake Watcher import Archive Assistant code.

