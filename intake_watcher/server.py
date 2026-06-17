from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import IntakeConfig
from .fingerprint import fingerprint_path
from .watcher import IntakeWatcher

WEB_DIR = Path(__file__).parent / "web"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _read_recent_jsonl(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    records: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            data = {"event": "unreadable_log_line", "raw": line}
        records.append(data)
    return records


def _dir_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
        if item.name.startswith(".") and item.name not in {".done"}:
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        items.append(
            {
                "name": item.name,
                "path": str(item),
                "kind": "file" if item.is_file() else "directory",
                "size_bytes": stat.st_size if item.is_file() else None,
                "modified_time": stat.st_mtime,
            }
        )
    return items


def build_dashboard_payload(config: IntakeConfig) -> dict[str, Any]:
    watcher = IntakeWatcher(config)
    now_status = watcher.status()
    inspected = watcher.inspect()
    state = now_status.get("tracked_items", {})

    waiting: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    incoming: list[dict[str, Any]] = []

    now = time.time()
    for item in inspected:
        item_state = item.get("state") or {}
        fp = item.get("fingerprint") or {}
        item_path = Path(item.get("path", ""))
        derived_status = "untracked"
        if item_path.exists():
            eligible_fp = fingerprint_path(item_path, config)
            _eligible, derived_status = watcher._eligible_reason(item_path, eligible_fp, now)  # noqa: SLF001

        status = item_state.get("status") or derived_status
        enriched = {
            **item,
            "status": status,
            "message": item_state.get("message", status),
            "stable_since": item_state.get("stable_since"),
            "last_seen": item_state.get("last_seen"),
            "file_count": fp.get("file_count", 0),
            "media_file_count": fp.get("media_file_count", 0),
            "temp_file_count": fp.get("temp_file_count", 0),
            "total_size_bytes": fp.get("total_size_bytes", 0),
        }
        incoming.append(enriched)
        if status.startswith("blocked"):
            blocked.append(enriched)
        else:
            waiting.append(enriched)

    ready = _dir_items(config.ready_dir)
    processing = _dir_items(config.processing_dir)
    failed = _dir_items(config.failed_dir)
    events = _read_recent_jsonl(config.log_path, 100)
    recent_promotions = [
        event
        for event in events
        if event.get("promoted") is True or event.get("event") in {"promoted", "promoted_suffix"}
    ][-25:]

    return {
        "service": "intake-watcher",
        "status": "ok",
        "config": {
            "data_root": str(config.data_root),
            "incoming_dir": str(config.incoming_dir),
            "processing_dir": str(config.processing_dir),
            "ready_dir": str(config.ready_dir),
            "failed_dir": str(config.failed_dir),
            "reports_dir": str(config.reports_dir),
            "log_path": str(config.log_path),
            "mode": config.mode,
            "stability_seconds": config.stability_seconds,
            "poll_seconds": config.poll_seconds,
            "require_ready_marker": config.require_ready_marker,
            "collision_policy": config.collision_policy,
            "destructive_actions_enabled": config.destructive_actions_enabled,
        },
        "counts": {
            "incoming": len(incoming),
            "waiting": len(waiting),
            "blocked": len(blocked),
            "ready": len(ready),
            "processing": len(processing),
            "failed": len(failed),
            "events": len(events),
            "promotions": len(recent_promotions),
            "tracked": len(state),
        },
        "items": {
            "incoming": incoming,
            "waiting": waiting,
            "blocked": blocked,
            "ready": ready,
            "processing": processing,
            "failed": failed,
            "recent_promotions": recent_promotions,
        },
        "events": events,
        "state": state,
    }


class RunCoordinator:
    def __init__(self, config: IntakeConfig) -> None:
        self.config = config
        self.lock = threading.Lock()

    def run_once(self) -> dict[str, Any]:
        with self.lock:
            return IntakeWatcher(self.config).run_once()



class BackgroundRunner:
    def __init__(self, coordinator: RunCoordinator) -> None:
        self.coordinator = coordinator
        self.config = coordinator.config
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, name="intake-watcher-background", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.coordinator.run_once()
            except Exception as exc:  # Keep daemon alive and make error visible in logs if possible.
                try:
                    from .reports import append_jsonl

                    append_jsonl(self.config.log_path, {"event": "background_run_failed", "message": str(exc)})
                except Exception:
                    pass
            self.stop_event.wait(self.config.poll_seconds)

class IntakeWatcherRequestHandler(BaseHTTPRequestHandler):
    server_version = "IntakeWatcherHTTP/0.1"

    @property
    def config(self) -> IntakeConfig:
        return self.server.config  # type: ignore[attr-defined]

    @property
    def coordinator(self) -> RunCoordinator:
        return self.server.coordinator  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep default server quiet enough for NAS use. Errors still return to client.
        return

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, indent=2, sort_keys=True, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in {"/", "/index.html"}:
            self._send_file(WEB_DIR / "index.html")
            return
        if path == "/app.js":
            self._send_file(WEB_DIR / "app.js")
            return
        if path == "/styles.css":
            self._send_file(WEB_DIR / "styles.css")
            return
        if path == "/api/health":
            self._send_json({"status": "ok", "service": "intake-watcher"})
            return
        if path == "/api/status":
            payload = build_dashboard_payload(self.config)
            self._send_json({"status": payload["status"], "config": payload["config"], "counts": payload["counts"]})
            return
        if path == "/api/items":
            payload = build_dashboard_payload(self.config)
            self._send_json({"counts": payload["counts"], "items": payload["items"], "state": payload["state"]})
            return
        if path == "/api/events":
            limit = 100
            if query.get("limit"):
                try:
                    limit = max(1, min(1000, int(query["limit"][0])))
                except ValueError:
                    limit = 100
            self._send_json({"events": _read_recent_jsonl(self.config.log_path, limit)})
            return
        if path == "/api/dashboard":
            self._send_json(build_dashboard_payload(self.config))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/run-once":
            try:
                result = self.coordinator.run_once()
            except Exception as exc:  # Defensive: dashboard must show failures cleanly.
                self._send_json({"status": "error", "message": str(exc)}, status=500)
                return
            self._send_json({"status": "ok", "result": result, "dashboard": build_dashboard_payload(self.config)})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def serve(host: str, port: int, config: IntakeConfig, auto_run: bool = True) -> None:
    config.validate()
    config.ensure_directories()
    server = ThreadingHTTPServer((host, port), IntakeWatcherRequestHandler)
    coordinator = RunCoordinator(config)
    server.config = config  # type: ignore[attr-defined]
    server.coordinator = coordinator  # type: ignore[attr-defined]
    runner = BackgroundRunner(coordinator) if auto_run else None
    if runner is not None:
        runner.start()
    print(f"Intake Watcher dashboard running at http://{host}:{port}")
    print(f"DATA_ROOT={config.data_root}")
    print(f"AUTO_RUN={auto_run}; POLL_SECONDS={config.poll_seconds}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Intake Watcher dashboard")
    finally:
        if runner is not None:
            runner.stop()
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Intake Watcher lightweight dashboard")
    parser.add_argument("--host", default=os.getenv("DASHBOARD_HOST", "127.0.0.1"), help="Host interface to bind")
    parser.add_argument("--port", type=int, default=_env_int("DASHBOARD_PORT", 8091), help="Port to bind")
    parser.add_argument("--data-root", default=None, help="Override DATA_ROOT")
    parser.add_argument("--auto-run", choices=("true", "false"), default=None, help="Run intake checks automatically in the background")
    parser.add_argument("--stability-seconds", type=int, default=None, help="Override STABILITY_SECONDS")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base = IntakeConfig.from_env()
    if args.data_root is not None or args.stability_seconds is not None:
        base = IntakeConfig(
            data_root=Path(args.data_root) if args.data_root is not None else base.data_root,
            mode=base.mode,
            stability_seconds=args.stability_seconds if args.stability_seconds is not None else base.stability_seconds,
            poll_seconds=base.poll_seconds,
            require_ready_marker=base.require_ready_marker,
            ready_markers=base.ready_markers,
            allow_single_file_promotion=base.allow_single_file_promotion,
            collision_policy=base.collision_policy,
            destructive_actions_enabled=base.destructive_actions_enabled,
            temp_suffixes=base.temp_suffixes,
            supported_media_extensions=base.supported_media_extensions,
            ignored_names=base.ignored_names,
            state_filename=base.state_filename,
            log_filename=base.log_filename,
        )
    auto_run = _env_bool("AUTO_RUN", True) if args.auto_run is None else args.auto_run == "true"
    serve(args.host, args.port, base, auto_run=auto_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
