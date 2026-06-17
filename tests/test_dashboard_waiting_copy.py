from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.server import build_dashboard_payload
from intake_watcher.watcher import IntakeWatcher


def _workspace_tempdir() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="iw-test-", dir=Path.cwd())


class DashboardWaitingCopyTests(unittest.TestCase):
    def test_waiting_item_has_human_status_and_remaining_time(self) -> None:
        with _workspace_tempdir() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=60)
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            (movie / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            watcher.run_once()

            payload = build_dashboard_payload(cfg)
            item = payload["items"]["waiting"][0]

            self.assertEqual(item["human_status"], "Waiting until file stops changing")
            self.assertIn("remaining_stability_seconds", item)
            self.assertGreaterEqual(item["remaining_stability_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
