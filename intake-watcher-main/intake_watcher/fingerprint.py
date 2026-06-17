from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .config import IntakeConfig
from .media_probe import find_media_files
from .temp_files import find_temp_files


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


def _iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return [child for child in path.rglob("*") if child.is_file()]


def has_ready_marker(path: Path, ready_markers: tuple[str, ...]) -> bool:
    if path.is_file():
        return False
    marker_names = {marker.lower() for marker in ready_markers}
    for child in path.iterdir() if path.exists() else []:
        if child.is_file() and child.name.lower() in marker_names:
            return True
    return False


def fingerprint_path(path: Path, config: IntakeConfig) -> Fingerprint:
    files = _iter_files(path)
    file_count = len(files)
    total_size = 0
    latest_mtime_ns = 0

    for file_path in files:
        try:
            stat = file_path.stat()
        except FileNotFoundError:
            continue
        total_size += stat.st_size
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)

    temp_files = find_temp_files(path, config.temp_suffixes)
    media_files = find_media_files(path, config.supported_media_extensions)

    return Fingerprint(
        file_count=file_count,
        total_size_bytes=total_size,
        latest_mtime_ns=latest_mtime_ns,
        temp_file_count=len(temp_files),
        media_file_count=len(media_files),
        has_ready_marker=has_ready_marker(path, config.ready_markers),
    )
