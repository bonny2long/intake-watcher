from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.watcher import IntakeWatcher


def _workspace_tempdir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="iw-test-", dir=Path.cwd())


def _events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


class LogDeduplicationTests(unittest.TestCase):
    def test_waiting_status_is_not_logged_every_run(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(
                data_root=Path(tmp),
                stability_seconds=60,
                status_log_heartbeat_seconds=900,
            )
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            (movie / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            watcher.run_once()
            watcher.run_once()

            waiting_events = [
                event for event in _events(cfg.log_path) if event.get("event") == "waiting_for_stability_window"
            ]
            self.assertEqual(len(waiting_events), 1)

    def test_changed_fingerprint_logs_changed_event(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(
                data_root=Path(tmp),
                stability_seconds=60,
                status_log_heartbeat_seconds=900,
            )
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            file_path = movie / "movie.mkv"
            file_path.write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            watcher.run_once()
            file_path.write_bytes(b"abcdef")
            result = watcher.run_once()

            self.assertEqual(result["results"][0]["status"], "changed")
            self.assertTrue(any(event.get("event") == "changed" for event in _events(cfg.log_path)))

    def test_promotion_still_logs(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=0)
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            (movie / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            result = watcher.run_once()

            self.assertTrue(result["results"][0]["promoted"])
            self.assertTrue(any(event.get("event") == "promoted_to_ready" for event in _events(cfg.log_path)))


if __name__ == "__main__":
    unittest.main()
