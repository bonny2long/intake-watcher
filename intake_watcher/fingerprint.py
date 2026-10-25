from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import IntakeConfig


@dataclass(frozen=True)
class Fingerprint:
    file_count: int
    total_size_bytes: int
    latest_mtime_ns: int
    temp_file_count: int
    media_file_count: int
    has_ready_marker: bool

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Fingerprint":
        return cls(
            file_count=int(data.get("file_count", 0)),
            total_size_bytes=int(data.get("total_size_bytes", 0)),
            latest_mtime_ns=int(data.get("latest_mtime_ns", 0)),
            temp_file_count=int(data.get("temp_file_count", 0)),
            media_file_count=int(data.get("media_file_count", 0)),
            has_ready_marker=bool(data.get("has_ready_marker", False)),
        )


def _walk_files(path: Path):
    """Yield (name, size, mtime_ns) for every file under ``path`` in one pass.

    ``size`` and ``mtime_ns`` are None when the file vanished or could not be read,
    which still counts as a file, matching how the fingerprint always behaved.
    """
    if path.is_file():
        try:
            stat = path.stat()
            yield path.name, stat.st_size, stat.st_mtime_ns
        except OSError:
            yield path.name, None, None
        return
    if not path.exists():
        return
    stack = [path]
    while stack:
        folder = stack.pop()
        try:
            entries = os.scandir(folder)
        except OSError:
            continue
        with entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                        continue
                    if not entry.is_file():
                        continue
                except OSError:
                    continue
                try:
                    stat = entry.stat()
                    yield entry.name, stat.st_size, stat.st_mtime_ns
                except OSError:
                    yield entry.name, None, None


def has_ready_marker(path: Path, ready_markers: tuple[str, ...]) -> bool:
    if path.is_file():
        return False
    marker_names = {marker.lower() for marker in ready_markers}
    for child in path.iterdir() if path.exists() else []:
        if child.is_file() and child.name.lower() in marker_names:
            return True
    return False


def fingerprint_path(path: Path, config: IntakeConfig) -> Fingerprint:
    """Describe a folder or file in one walk: counts, bytes, newest change, temp and media files."""
    temp_suffixes = tuple(suffix.lower() for suffix in config.temp_suffixes)
    media_extensions = {extension.lower() for extension in config.supported_media_extensions}
    file_count = 0
    total_size = 0
    latest_mtime_ns = 0
    temp_file_count = 0
    media_file_count = 0

    for name, size, mtime_ns in _walk_files(path):
        file_count += 1
        if size is not None:
            total_size += size
            latest_mtime_ns = max(latest_mtime_ns, mtime_ns)
        lower_name = name.lower()
        if temp_suffixes and lower_name.endswith(temp_suffixes):
            temp_file_count += 1
        if Path(lower_name).suffix in media_extensions:
            media_file_count += 1

    return Fingerprint(
        file_count=file_count,
        total_size_bytes=total_size,
        latest_mtime_ns=latest_mtime_ns,
        temp_file_count=temp_file_count,
        media_file_count=media_file_count,
        has_ready_marker=has_ready_marker(path, config.ready_markers),
    )
