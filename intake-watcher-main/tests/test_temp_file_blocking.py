from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.watcher import IntakeWatcher


class TempFileBlockingTests(unittest.TestCase):
    def test_crdownload_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=0)
            folder = cfg.incoming_dir / "Active Download"
            folder.mkdir(parents=True)
            (folder / "movie.mkv.crdownload").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            result = watcher.run_once()

            self.assertEqual(result["results"][0]["status"], "blocked_temp_files")
            self.assertTrue(folder.exists())
            self.assertFalse((cfg.ready_dir / folder.name).exists())


if __name__ == "__main__":
    unittest.main()
