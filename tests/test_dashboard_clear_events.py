from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.server import build_dashboard_payload, clear_recent_events


def _workspace_tempdir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="iw-test-", dir=Path.cwd())


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


class DashboardClearEventsTests(unittest.TestCase):
    def test_clear_does_not_delete_log_file(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp))
            cfg.ensure_directories()
            _write_jsonl(
                cfg.log_path,
                [
                    {"timestamp": "2026-06-17T00:00:00+00:00", "event": "first_seen"},
                    {"timestamp": "2026-06-17T00:01:00+00:00", "event": "waiting_for_stability_window"},
                ],
            )

            result = clear_recent_events(cfg)

            self.assertTrue(result["ok"])
            self.assertTrue(cfg.log_path.exists())
            state_path = cfg.reports_dir / "dashboard_state.json"
            self.assertTrue(state_path.exists())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("events_cleared_at", state)

    def test_dashboard_filters_old_events(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp))
            cfg.ensure_directories()
            state_path = cfg.reports_dir / "dashboard_state.json"
            state_path.write_text(json.dumps({"events_cleared_at": 1781672400.0}), encoding="utf-8")
            _write_jsonl(
                cfg.log_path,
                [
                    {"timestamp": "2026-06-17T00:00:00+00:00", "event": "old_event"},
                    {"timestamp": "2026-06-17T10:00:01+00:00", "event": "new_event"},
                ],
            )

            payload = build_dashboard_payload(cfg)

            self.assertEqual([event["event"] for event in payload["events"]], ["new_event"])

    def test_clear_endpoint_logic_writes_audit_event(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp))
            result = clear_recent_events(cfg)

            self.assertTrue(result["ok"])
            events = [
                json.loads(line)
                for line in cfg.log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(any(event.get("event") == "dashboard_recent_events_cleared" for event in events))


if __name__ == "__main__":
    unittest.main()
