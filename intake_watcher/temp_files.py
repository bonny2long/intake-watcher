from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable


def is_temp_file(path: Path, temp_suffixes: Iterable[str]) -> bool:
    name = path.name.lower()
    for suffix in temp_suffixes:
        if name.endswith(suffix.lower()):
            return True
    return False


def find_temp_files(path: Path, temp_suffixes: Iterable[str]) -> list[Path]:
    if path.is_file():
        return [path] if is_temp_file(path, temp_suffixes) else []

    temp_files: list[Path] = []
    if not path.exists():
        return temp_files

    for child in path.rglob("*"):
        if child.is_file() and is_temp_file(child, temp_suffixes):
            temp_files.append(child)
    return temp_files
