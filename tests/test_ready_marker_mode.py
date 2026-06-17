from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.watcher import IntakeWatcher


class ReadyMarkerModeTests(unittest.TestCase):
    def test_manual_marker_mode_blocks_without_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), mode="manual_marker", stability_seconds=0)
            folder = cfg.incoming_dir / "Movie"
            folder.mkdir(parents=True)
            (folder / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            result = watcher.run_once()

            self.assertEqual(result["results"][0]["status"], "blocked_missing_ready_marker")
            self.assertTrue(folder.exists())

    def test_manual_marker_mode_promotes_with_marker_after_seen_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), mode="manual_marker", stability_seconds=0)
            folder = cfg.incoming_dir / "Movie"
            folder.mkdir(parents=True)
            (folder / "movie.mkv").write_bytes(b"abc")
            (folder / "READY.txt").write_text("done", encoding="utf-8")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            result = watcher.run_once()

            self.assertTrue(result["results"][0]["promoted"])
            self.assertTrue((cfg.ready_dir / "Movie" / "movie.mkv").exists())


if __name__ == "__main__":
    unittest.main()
