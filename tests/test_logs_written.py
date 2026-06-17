from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake_watcher.config import IntakeConfig
from intake_watcher.watcher import IntakeWatcher


class LogsWrittenTests(unittest.TestCase):
    def test_jsonl_log_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=0)
            folder = cfg.incoming_dir / "Movie"
            folder.mkdir(parents=True)
            (folder / "movie.mkv").write_bytes(b"abc")

            watcher = IntakeWatcher(cfg)
            watcher.run_once()

            self.assertTrue(cfg.log_path.exists())
            content = cfg.log_path.read_text(encoding="utf-8")
            self.assertIn("first_seen", content)


if __name__ == "__main__":
    unittest.main()
