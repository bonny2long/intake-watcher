from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable


def is_supported_media_file(path: Path, supported_extensions: Iterable[str]) -> bool:
    suffix = path.suffix.lower()
    return suffix in {ext.lower() for ext in supported_extensions}


def find_media_files(path: Path, supported_extensions: Iterable[str]) -> list[Path]:
    if path.is_file():
        return [path] if is_supported_media_file(path, supported_extensions) else []

    media_files: list[Path] = []
    if not path.exists():
        return media_files

    for child in path.rglob("*"):
        if child.is_file() and is_supported_media_file(child, supported_extensions):
            media_files.append(child)
    return media_files
