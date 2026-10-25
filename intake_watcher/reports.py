from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": utc_now_iso(), **record}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=_json_default) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, default=_json_default)
        handle.write("\n")
    tmp_path.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_json_or_quarantine(path: Path) -> tuple[dict[str, Any], Path | None]:
    """Read a JSON object, moving a file that cannot be parsed out of the way.

    Returns ``(data, moved_to)``. A missing file is empty, not corrupt. A corrupt file
    is renamed to ``<name>.corrupt-<UTC time>`` so it is kept for inspection, and the
    caller starts from empty instead of crashing on every start and every dashboard load.
    """
    try:
        data = read_json(path)
        if isinstance(data, dict):
            return data, None
    except FileNotFoundError:
        return {}, None
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    moved_to = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        path.replace(moved_to)
    except OSError:
        return {}, None
    return {}, moved_to


def write_promotion_report(
    promotions_dir: Path,
    item_name: str,
    report: dict[str, Any],
) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in item_name)
    timestamp = utc_now_iso().replace(":", "-")
    path = promotions_dir / f"{timestamp}_{safe_name}.json"
    write_json(path, {"timestamp": utc_now_iso(), **report})
    return path
