from __future__ import annotations

from pathlib import Path


def write_file(path: Path, size: int = 32) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((b"0" * size) or b"0")


def main() -> int:
    root = Path("data")
    incoming = root / "_INGEST" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    write_file(incoming / "Movie Example (2024)" / "Movie Example (2024).mkv", 128)
    write_file(incoming / "Growing Download" / "episode.mkv.crdownload", 128)
    write_file(incoming / "Notes Only" / "readme.txt", 64)
    write_file(incoming / "Loose Song.flac", 64)

    print(f"Created sample intake tree under {incoming}")
    print("Try: STABILITY_SECONDS=0 python -m intake_watcher.cli run-once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
