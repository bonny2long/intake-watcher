from __future__ import annotations

import argparse
import json
from typing import Any

from .config import IntakeConfig
from .watcher import IntakeWatcher


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe pre-ingest watcher for Archive Assistant")
    parser.add_argument(
        "command",
        choices=("inspect", "run-once", "watch", "status"),
        help="Command to run",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Override DATA_ROOT for this command",
    )
    parser.add_argument(
        "--stability-seconds",
        type=int,
        default=None,
        help="Override STABILITY_SECONDS for this command",
    )
    return parser


def make_config(args: argparse.Namespace) -> IntakeConfig:
    config = IntakeConfig.from_env()
    if args.data_root is not None or args.stability_seconds is not None:
        config = IntakeConfig(
            data_root=config.data_root if args.data_root is None else __import__("pathlib").Path(args.data_root),
            mode=config.mode,
            stability_seconds=config.stability_seconds if args.stability_seconds is None else args.stability_seconds,
            poll_seconds=config.poll_seconds,
            require_ready_marker=config.require_ready_marker,
            ready_markers=config.ready_markers,
            allow_single_file_promotion=config.allow_single_file_promotion,
            collision_policy=config.collision_policy,
            destructive_actions_enabled=config.destructive_actions_enabled,
            temp_suffixes=config.temp_suffixes,
            supported_media_extensions=config.supported_media_extensions,
            ignored_names=config.ignored_names,
            state_filename=config.state_filename,
            log_filename=config.log_filename,
        )
    return config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    watcher = IntakeWatcher(make_config(args))

    if args.command == "inspect":
        _print_json(watcher.inspect())
        return 0

    if args.command == "run-once":
        _print_json(watcher.run_once())
        return 0

    if args.command == "status":
        _print_json(watcher.status())
        return 0

    if args.command == "watch":
        watcher.watch()
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
