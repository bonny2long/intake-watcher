# NAS Deployment

This document describes the intended TrueNAS deployment shape for Intake Watcher.

Local development mirrors this shape through one shared NAS-style data root:

```text
C:\NAS-Local\nas-data
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

## One filesystem

`incoming`, `intake-processing`, `ready` and `failed` must be on one filesystem (one dataset or one mount), because promotion is a rename. On ZFS, do not make them separate datasets. The same applies to the rest of the NAS data root; see Archive Assistant's `docs/NAS_DEPLOYMENT.md` for the full layout and its `scripts/nas_storage_preflight.py` check.

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

Buttons that change anything (Run once, Clear recent) only work from the dashboard's own address. The server rejects a POST whose `Origin` header is not a loopback address, so a web page on another site cannot trigger them. To use the dashboard from a LAN or Tailscale address, set `ALLOWED_ORIGINS` to that exact address, for example `ALLOWED_ORIGINS=http://192.168.1.50:8091`. Plain scripts such as `curl` send no `Origin` header and are not affected.

## Production Boundary

Intake Watcher does not write final libraries. It only promotes stable uploads to `_INGEST/ready`.

Cleaner behavior is not active here.

Archive Assistant owns final-library folders such as `Music`, `Movies`, `TV`, `Books`, and `Audiobooks`. Intake Watcher must not write final library destinations.
