from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.fingerprint import fingerprint_path
from intake_watcher.watcher import IntakeWatcher


class FingerprintStabilityTests(unittest.TestCase):
    def test_fingerprint_changes_when_file_size_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = IntakeConfig(data_root=root, stability_seconds=0)
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            file_path = movie / "movie.mkv"
            file_path.write_bytes(b"abc")

            before = fingerprint_path(movie, cfg)
            file_path.write_bytes(b"abcdef")
            after = fingerprint_path(movie, cfg)

            self.assertNotEqual(before.total_size_bytes, after.total_size_bytes)

    def test_stable_folder_promotes_after_second_run_with_zero_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = IntakeConfig(data_root=root, stability_seconds=0)
            movie = cfg.incoming_dir / "Movie"
            movie.mkdir(parents=True)
            (movie / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            first = watcher.run_once()
            self.assertEqual(first["results"][0]["status"], "first_seen")

            second = watcher.run_once()
            self.assertTrue(second["results"][0]["promoted"])
            self.assertTrue((cfg.ready_dir / "Movie" / "movie.mkv").exists())


if __name__ == "__main__":
    unittest.main()
