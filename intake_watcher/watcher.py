from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import IntakeConfig
from .fingerprint import Fingerprint, fingerprint_path
from .promotion import promote_item
from .reports import append_jsonl, read_json, write_json


@dataclass
class ItemState:
    fingerprint: dict[str, Any]
    stable_since: float
    last_seen: float
    status: str
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ItemState":
        return cls(
            fingerprint=dict(data.get("fingerprint", {})),
            stable_since=float(data.get("stable_since", 0)),
            last_seen=float(data.get("last_seen", 0)),
            status=str(data.get("status", "unknown")),
            message=str(data.get("message", "")),
        )


class IntakeWatcher:
    def __init__(self, config: IntakeConfig | None = None) -> None:
        self.config = config or IntakeConfig.from_env()
        self.config.validate()
        self.config.ensure_directories()
        self.state: dict[str, ItemState] = self._load_state()

    def _load_state(self) -> dict[str, ItemState]:
        raw = read_json(self.config.state_path)
        items = raw.get("items", {}) if raw else {}
        return {name: ItemState.from_dict(value) for name, value in items.items()}

    def _save_state(self) -> None:
        write_json(
            self.config.state_path,
            {
                "version": 1,
                "items": {name: state.to_dict() for name, state in sorted(self.state.items())},
            },
        )

    def _log(self, event: str, item: Path | None = None, **extra: Any) -> None:
        record: dict[str, Any] = {"event": event}
        if item is not None:
            record.update({"item_name": item.name, "item_path": str(item)})
        record.update(extra)
        append_jsonl(self.config.log_path, record)

    def _incoming_items(self) -> list[Path]:
        if not self.config.incoming_dir.exists():
            return []
        items = []
        ignored = {name.lower() for name in self.config.ignored_names}
        marker_names = {name.lower() for name in self.config.ready_markers}

        for item in sorted(self.config.incoming_dir.iterdir(), key=lambda p: p.name.lower()):
            lower_name = item.name.lower()
            if lower_name in ignored:
                self._log("ignored_name", item)
                continue
            if lower_name in marker_names:
                self._log("ignored_top_level_marker", item)
                continue
            if item.is_file() and not self.config.allow_single_file_promotion:
                self._log("blocked_single_file", item, message="Single-file promotion disabled")
                continue
            items.append(item)
        return items

    def inspect(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in self._incoming_items():
            fp = fingerprint_path(item, self.config)
            state = self.state.get(item.name)
            results.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "kind": "file" if item.is_file() else "directory",
                    "fingerprint": fp.to_dict(),
                    "state": state.to_dict() if state else None,
                    "eligible_now": self._eligible_reason(item, fp, time.time())[0],
                }
            )
        return results

    def status(self) -> dict[str, Any]:
        return {
            "incoming_dir": str(self.config.incoming_dir),
            "processing_dir": str(self.config.processing_dir),
            "ready_dir": str(self.config.ready_dir),
            "reports_dir": str(self.config.reports_dir),
            "mode": self.config.mode,
            "stability_seconds": self.config.stability_seconds,
            "tracked_items": {name: state.to_dict() for name, state in sorted(self.state.items())},
        }

    def _ready_marker_required(self) -> bool:
        return self.config.require_ready_marker or self.config.mode == "manual_marker"

    def _eligible_reason(self, item: Path, fp: Fingerprint, now: float) -> tuple[bool, str]:
        if fp.temp_file_count > 0:
            return False, "blocked_temp_files"
        if fp.media_file_count <= 0:
            return False, "blocked_no_media_files"
        if self._ready_marker_required() and not fp.has_ready_marker:
            return False, "blocked_missing_ready_marker"

        state = self.state.get(item.name)
        if state is None:
            return False, "first_seen"

        previous_fp = Fingerprint.from_dict(state.fingerprint)
        if previous_fp != fp:
            return False, "changed"

        stable_for = now - state.stable_since
        if stable_for < self.config.stability_seconds:
            return False, "waiting_for_stability_window"

        return True, "eligible_for_promotion"

    def _record_state(self, item: Path, fp: Fingerprint, now: float, status: str, message: str = "") -> None:
        existing = self.state.get(item.name)
        stable_since = now
        if existing is not None:
            previous_fp = Fingerprint.from_dict(existing.fingerprint)
            stable_since = existing.stable_since if previous_fp == fp else now

        self.state[item.name] = ItemState(
            fingerprint=fp.to_dict(),
            stable_since=stable_since,
            last_seen=now,
            status=status,
            message=message,
        )

    def run_once(self) -> dict[str, Any]:
        now = time.time()
        results: list[dict[str, Any]] = []

        for item in self._incoming_items():
            fp = fingerprint_path(item, self.config)
            eligible, reason = self._eligible_reason(item, fp, now)

            if not eligible:
                self._record_state(item, fp, now, reason, reason)
                self._log(reason, item, fingerprint=fp.to_dict())
                results.append({"item": item.name, "status": reason, "promoted": False})
                continue

            result = promote_item(item, self.config, fp)
            if result.promoted:
                self.state.pop(item.name, None)
            else:
                self._record_state(item, fp, now, result.status, result.message)

            self._log(
                result.status,
                item,
                promoted=result.promoted,
                destination=str(result.destination) if result.destination else None,
                report_path=str(result.report_path) if result.report_path else None,
                message=result.message,
                fingerprint=fp.to_dict(),
            )
            results.append(
                {
                    "item": item.name,
                    "status": result.status,
                    "promoted": result.promoted,
                    "destination": str(result.destination) if result.destination else None,
                }
            )

        self._save_state()
        return {"results": results, "count": len(results)}

    def watch(self) -> None:
        self._log("watch_started", None, poll_seconds=self.config.poll_seconds)
        while True:
            self.run_once()
            time.sleep(self.config.poll_seconds)
