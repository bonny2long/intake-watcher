from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from intake_watcher import fingerprint as fingerprint_module
from intake_watcher import watcher as watcher_module
from intake_watcher.config import IntakeConfig
from intake_watcher.fingerprint import Fingerprint, fingerprint_path, has_ready_marker
from intake_watcher.media_probe import find_media_files
from intake_watcher.server import build_dashboard_payload, read_dashboard_state
from intake_watcher.temp_files import find_temp_files
from intake_watcher.watcher import IntakeWatcher


def make_config(tmp_path: Path) -> IntakeConfig:
    return IntakeConfig(data_root=tmp_path / "nas-data", stability_seconds=0)


def logged_events(config: IntakeConfig) -> list[str]:
    if not config.log_path.exists():
        return []
    return [json.loads(line)["event"] for line in config.log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def old_fingerprint(path: Path, config: IntakeConfig) -> Fingerprint:
    """The previous implementation: three separate walks."""
    if path.is_file():
        files = [path]
    elif not path.exists():
        files = []
    else:
        files = [child for child in path.rglob("*") if child.is_file()]
    total_size = 0
    latest = 0
    for file_path in files:
        try:
            stat = file_path.stat()
        except FileNotFoundError:
            continue
        total_size += stat.st_size
        latest = max(latest, stat.st_mtime_ns)
    return Fingerprint(
        file_count=len(files),
        total_size_bytes=total_size,
        latest_mtime_ns=latest,
        temp_file_count=len(find_temp_files(path, config.temp_suffixes)),
        media_file_count=len(find_media_files(path, config.supported_media_extensions)),
        has_ready_marker=has_ready_marker(path, config.ready_markers),
    )


# ---- corrupt state ---------------------------------------------------------------------------

@pytest.mark.parametrize("content", ["", "{not json", "[1, 2, 3]", '"just a string"', "\x00\x00\x00"])
def test_corrupt_state_file_is_moved_aside_and_tracking_starts_empty(tmp_path: Path, content: str) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    config.state_path.write_text(content, encoding="utf-8")

    watcher = IntakeWatcher(config)

    assert watcher.state == {}
    assert not config.state_path.exists()
    kept = list(config.reports_dir.glob("state.json.corrupt-*"))
    assert len(kept) == 1
    assert kept[0].read_text(encoding="utf-8") == content
    assert "state_file_corrupt" in logged_events(config)


def test_watcher_keeps_working_after_a_corrupt_state_file(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    config.state_path.write_text("{broken", encoding="utf-8")
    movie = config.incoming_dir / "Movie"
    movie.mkdir(parents=True)
    (movie / "movie.mkv").write_bytes(b"abc")

    watcher = IntakeWatcher(config)
    first = watcher.run_once()
    second = watcher.run_once()

    # Tracking restarted, so the item waits one more round before it is promoted.
    assert first["results"][0]["status"] == "first_seen"
    assert second["results"][0]["promoted"] is True
    assert json.loads(config.state_path.read_text(encoding="utf-8"))["version"] == 1


def test_unreadable_entries_in_a_valid_state_file_are_skipped(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    good = {"fingerprint": {}, "stable_since": 1.0, "last_seen": 2.0, "status": "first_seen"}
    config.state_path.write_text(
        json.dumps({"version": 1, "items": {"Broken": "not a dict", "Fine": good, "AlsoBroken": ["x"]}}),
        encoding="utf-8",
    )

    watcher = IntakeWatcher(config)

    assert set(watcher.state) == {"Fine"}
    assert config.state_path.exists()
    assert "state_items_skipped" in logged_events(config)


def test_dashboard_survives_corrupt_state_and_dashboard_state_files(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    config.state_path.write_text("{broken", encoding="utf-8")
    (config.reports_dir / "dashboard_state.json").write_text("nope", encoding="utf-8")
    (config.incoming_dir / "Album").mkdir(parents=True)
    ((config.incoming_dir / "Album") / "01.flac").write_bytes(b"abc")

    payload = build_dashboard_payload(config)

    assert payload["status"] == "ok"
    assert payload["counts"]["incoming"] == 1
    assert read_dashboard_state(config) == {"events_cleared_at": 0.0}
    assert list(config.reports_dir.glob("dashboard_state.json.corrupt-*"))


def test_a_missing_state_file_is_not_treated_as_corrupt(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    IntakeWatcher(config)

    assert not list(config.reports_dir.glob("*.corrupt-*"))
    assert "state_file_corrupt" not in logged_events(config)


# ---- fingerprint: same answers, one walk ---------------------------------------------------------

def build_tricky_tree(root: Path) -> Path:
    release = root / "Release"
    (release / "CD 1").mkdir(parents=True)
    (release / "CD 2" / "extras").mkdir(parents=True)
    (release / "empty folder").mkdir()
    files = {
        "CD 1/01 Track.FLAC": b"a" * 10,
        "CD 1/02 Track.mp3": b"b" * 20,
        "CD 2/01 Track.flac": b"c" * 30,
        "CD 2/extras/booklet.PDF": b"d" * 5,
        "CD 2/extras/cover.jpg": b"e" * 7,
        "CD 2/extras/notes.txt": b"f",
        "movie.mkv.PART": b"g" * 3,
        "other.crdownload": b"h",
        "weird.!qB": b"i",
        "READY.txt": b"",
        ".done": b"",
        "noextension": b"j",
        ".hidden.mp3": b"k",
    }
    for relative, content in files.items():
        target = release / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return release


def test_single_pass_fingerprint_matches_the_old_three_walk_result(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    release = build_tricky_tree(tmp_path)

    assert fingerprint_path(release, config) == old_fingerprint(release, config)
    assert fingerprint_path(release / "CD 1" / "02 Track.mp3", config) == old_fingerprint(release / "CD 1" / "02 Track.mp3", config)
    assert fingerprint_path(release / "movie.mkv.PART", config) == old_fingerprint(release / "movie.mkv.PART", config)
    assert fingerprint_path(release / "empty folder", config) == old_fingerprint(release / "empty folder", config)
    assert fingerprint_path(tmp_path / "does-not-exist", config) == old_fingerprint(tmp_path / "does-not-exist", config)

    result = fingerprint_path(release, config)
    assert result.temp_file_count == 3
    assert result.has_ready_marker is True


def test_fingerprint_lists_each_folder_once_and_never_opens_files(tmp_path: Path, monkeypatch) -> None:
    release = build_tricky_tree(tmp_path)
    folders = 1 + sum(len(dirs) for _folder, dirs, _files in os.walk(release))
    listed: list[str] = []
    original = os.scandir

    def counting_scandir(path):
        listed.append(str(path))
        return original(path)

    monkeypatch.setattr(fingerprint_module.os, "scandir", counting_scandir)

    files = list(fingerprint_module._walk_files(release))  # noqa: SLF001

    assert len(files) == 13
    assert len(listed) == folders


# ---- dashboard does not fingerprint twice -------------------------------------------------------

def test_dashboard_fingerprints_each_incoming_item_once(tmp_path: Path, monkeypatch) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    for name in ("One", "Two", "Three"):
        folder = config.incoming_dir / name
        folder.mkdir(parents=True)
        (folder / "01.flac").write_bytes(b"abc")

    calls: list[Path] = []
    original = watcher_module.fingerprint_path
    monkeypatch.setattr(watcher_module, "fingerprint_path", lambda path, cfg: calls.append(path) or original(path, cfg))

    payload = build_dashboard_payload(config)

    assert payload["counts"]["incoming"] == 3
    assert len(calls) == 3
    assert {item["status"] for item in payload["items"]["incoming"]} == {"first_seen"}


def test_dashboard_statuses_still_distinguish_blocked_items(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.ensure_directories()
    downloading = config.incoming_dir / "Downloading"
    downloading.mkdir(parents=True)
    (downloading / "movie.mkv.crdownload").write_bytes(b"abc")
    no_media = config.incoming_dir / "Notes"
    no_media.mkdir()
    (no_media / "readme.txt").write_bytes(b"abc")

    payload = build_dashboard_payload(config)
    by_name = {item["name"]: item["status"] for item in payload["items"]["incoming"]}

    assert by_name == {"Downloading": "blocked_temp_files", "Notes": "blocked_no_media_files"}
    assert payload["counts"]["blocked"] == 2
