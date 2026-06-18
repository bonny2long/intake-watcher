# Archive Assistant Bridge

Intake Watcher and Archive Assistant connect through the ready folder.

## Local Development

Preferred shared local ready folder:

```text
C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/nas-data/_INGEST/ready
```

Archive Assistant backend `.env`:

```env
INGEST_ROOT=C:/Users/BonnyMakaniankhondo/Documents/GitHub/NAS/nas-data/_INGEST/ready
```

Use `nas-data/_INGEST/incoming` for new Intake Watcher test drops. Do not use Archive Assistant's old project `data/_INGEST` during bridged testing.

If Bonny's local Intake Watcher repo folder is still temporarily spelled `intake-watccher`, use the actual folder path on disk. Do not rename the project folder unless Bonny asks.

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

Intake Watcher must not write to shared final-library folders such as `Music`, `Movies`, `TV`, `Books`, or `Audiobooks`.
