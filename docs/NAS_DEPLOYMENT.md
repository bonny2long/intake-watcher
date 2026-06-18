# NAS Deployment

This document describes the intended TrueNAS deployment shape for Intake Watcher.

Local development mirrors this shape through one shared NAS-style data root:

```text
C:\Users\BonnyMakaniankhondo\Documents\GitHub\NAS\nas-data
```

Do not use Archive Assistant's old project `data/_INGEST` during bridged testing.

## NAS Folder Layout

```text
/mnt/rust-pool/_INGEST/incoming
/mnt/rust-pool/_INGEST/intake-processing
/mnt/rust-pool/_INGEST/ready
/mnt/rust-pool/_INGEST/failed
/mnt/rust-pool/_REPORTS/intake-watcher
```

Intake Watcher watches `incoming` and promotes stable completed items into `ready`.
Archive Assistant later scans `ready`.

## Docker Compose Shape

```yaml
services:
  intake-watcher:
    build: .
    container_name: intake-watcher
    restart: unless-stopped
    environment:
      DATA_ROOT: /app/data
      INTAKE_MODE: hybrid
      STABILITY_SECONDS: "1200"
      POLL_SECONDS: "300"
      STATUS_LOG_HEARTBEAT_SECONDS: "900"
      REQUIRE_READY_MARKER: "false"
      ALLOW_SINGLE_FILE_PROMOTION: "true"
      COLLISION_POLICY: block
      DESTRUCTIVE_ACTIONS_ENABLED: "false"
      AUTO_RUN: "true"
    volumes:
      - /mnt/rust-pool:/app/data
    ports:
      - "8091:8091"
```

## Network Safety

Expose the dashboard only on local LAN, Tailscale, or VPN.

Do not expose Intake Watcher publicly.

## Production Boundary

Intake Watcher does not write final libraries. It only promotes stable uploads to `_INGEST/ready`.

Cleaner behavior is not active here.

Archive Assistant owns final-library folders such as `Music`, `Movies`, `TV`, `Books`, and `Audiobooks`. Intake Watcher must not write final library destinations.
