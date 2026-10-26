from __future__ import annotations

import errno
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intake_watcher import safe_move
from intake_watcher.config import IntakeConfig
from intake_watcher.safe_move import CrossDeviceMoveError, move_by_rename
from intake_watcher.watcher import IntakeWatcher


def _stage(tmp: str) -> tuple[IntakeConfig, Path]:
    cfg = IntakeConfig(data_root=Path(tmp), stability_seconds=0, collision_policy="block")
    item = cfg.incoming_dir / "Album"
    item.mkdir(parents=True)
    (item / "01.flac").write_bytes(b"audio" * 100)
    return cfg, item


def _promote(cfg: IntakeConfig) -> dict:
    watcher = IntakeWatcher(cfg)
    watcher.run_once()          # first sighting
    return watcher.run_once()   # stable, so it is promoted


class RenameOnlyMoveTests(unittest.TestCase):
    def test_a_normal_promotion_still_reaches_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, item = _stage(tmp)
            result = _promote(cfg)
            self.assertEqual(result["results"][0]["status"], "promoted_to_ready")
            self.assertEqual((cfg.ready_dir / "Album" / "01.flac").read_bytes(), b"audio" * 100)
            self.assertFalse(item.exists())

    def test_a_move_across_filesystems_fails_and_leaves_the_download_where_it_was(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, item = _stage(tmp)

            def other_filesystem(_source, _destination):
                raise OSError(errno.EXDEV, "Invalid cross-device link")

            with mock.patch.object(safe_move.os, "rename", other_filesystem):
                result = _promote(cfg)

            outcome = result["results"][0]
            self.assertEqual(outcome["status"], "move_to_processing_failed")
            logged = [json.loads(line) for line in cfg.log_path.read_text(encoding="utf-8").splitlines()]
            failure = [entry for entry in logged if entry.get("event") == "move_to_processing_failed"]
            self.assertTrue(failure and "different filesystems" in failure[0]["message"], logged)
            self.assertEqual((item / "01.flac").read_bytes(), b"audio" * 100)
            self.assertFalse(any(cfg.processing_dir.iterdir()))
            self.assertFalse(any(cfg.ready_dir.iterdir()))

    def test_a_failure_on_the_last_step_keeps_the_item_in_processing_not_copied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg, item = _stage(tmp)
            real_rename = safe_move.os.rename
            calls = []

            def fail_second(source, destination):
                calls.append(destination)
                if len(calls) == 2:
                    raise OSError(errno.EXDEV, "Invalid cross-device link")
                return real_rename(source, destination)

            with mock.patch.object(safe_move.os, "rename", fail_second):
                result = _promote(cfg)

            self.assertEqual(result["results"][0]["status"], "move_to_ready_failed")
            self.assertEqual((cfg.processing_dir / "Album" / "01.flac").read_bytes(), b"audio" * 100)
            self.assertFalse((cfg.ready_dir / "Album").exists())

    def test_nothing_that_exists_is_replaced_and_other_errors_pass_through(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_bytes(b"new")
            (root / "b").write_bytes(b"old")
            with self.assertRaises(FileExistsError):
                move_by_rename(root / "a", root / "b")
            self.assertEqual((root / "b").read_bytes(), b"old")
            self.assertEqual((root / "a").read_bytes(), b"new")

            def denied(_source, _destination):
                raise PermissionError(errno.EACCES, "denied")

            with mock.patch.object(safe_move.os, "rename", denied):
                with self.assertRaises(PermissionError):
                    move_by_rename(root / "a", root / "c")

    def test_the_windows_cross_drive_error_is_recognised(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a").write_bytes(b"x")

            def other_drive(_source, _destination):
                error = OSError(errno.EINVAL, "The system cannot move the file to a different disk drive")
                error.winerror = 17
                raise error

            with mock.patch.object(safe_move.os, "rename", other_drive):
                with self.assertRaises(CrossDeviceMoveError):
                    move_by_rename(root / "a", root / "b")
            self.assertTrue((root / "a").exists())


if __name__ == "__main__":
    unittest.main()
