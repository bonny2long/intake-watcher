from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.watcher import IntakeWatcher


class NoOverwritePromotionTests(unittest.TestCase):
    def test_existing_ready_destination_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=0, collision_policy="block")
            incoming = cfg.incoming_dir / "Movie"
            incoming.mkdir(parents=True)
            (incoming / "movie.mkv").write_bytes(b"new")

            existing = cfg.ready_dir / "Movie"
            existing.mkdir(parents=True)
            (existing / "movie.mkv").write_bytes(b"old")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()
            result = watcher.run_once()

            self.assertEqual(result["results"][0]["status"], "blocked_collision")
            self.assertEqual((existing / "movie.mkv").read_bytes(), b"old")
            self.assertTrue(incoming.exists())


if __name__ == "__main__":
    unittest.main()
