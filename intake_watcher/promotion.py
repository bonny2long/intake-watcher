from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import IntakeConfig
from .fingerprint import Fingerprint, fingerprint_path
from .reports import write_promotion_report


@dataclass(frozen=True)
class PromotionResult:
    promoted: bool
    status: str
    source: Path
    destination: Path | None = None
    report_path: Path | None = None
    message: str = ""


def _suffix_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem if path.is_file() else path.name
    suffix = path.suffix if path.is_file() else ""
    parent = path.parent

    for index in range(2, 1000):
        candidate_name = f"{stem} ({index}){suffix}" if suffix else f"{stem} ({index})"
        candidate = parent / candidate_name
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not create non-colliding destination for {path}")


def destination_for(source: Path, ready_dir: Path, policy: str) -> Path:
    proposed = ready_dir / source.name
    if proposed.exists() and policy == "suffix":
        return _suffix_destination(proposed)
    return proposed


def promote_item(source: Path, config: IntakeConfig, before: Fingerprint) -> PromotionResult:
    config.ensure_directories()

    if not source.exists():
        return PromotionResult(False, "missing_source", source, message="Source no longer exists")

    ready_destination = destination_for(source, config.ready_dir, config.collision_policy)
    if ready_destination.exists():
        return PromotionResult(
            False,
            "blocked_collision",
            source,
            ready_destination,
            message="Ready destination already exists; no overwrite allowed",
        )

    processing_destination = config.processing_dir / source.name
    if processing_destination.exists():
        return PromotionResult(
            False,
            "blocked_processing_collision",
            source,
            processing_destination,
            message="Processing destination already exists; no overwrite allowed",
        )

    try:
        moved_to_processing = Path(shutil.move(str(source), str(processing_destination)))
    except Exception as exc:  # noqa: BLE001 - preserve failure in report/log
        return PromotionResult(False, "move_to_processing_failed", source, message=str(exc))

    after_processing = fingerprint_path(moved_to_processing, config)
    if after_processing != before:
        failed_destination = config.failed_dir / moved_to_processing.name
        if failed_destination.exists():
            failed_destination = _suffix_destination(failed_destination)
        try:
            shutil.move(str(moved_to_processing), str(failed_destination))
        except Exception:
            # Keep item in processing if failed move cannot be performed.
            failed_destination = moved_to_processing
        return PromotionResult(
            False,
            "fingerprint_changed_during_promotion",
            source,
            failed_destination,
            message="Fingerprint changed after entering processing; item moved to failed or left in processing",
        )

    try:
        final_destination = Path(shutil.move(str(moved_to_processing), str(ready_destination)))
    except Exception as exc:  # noqa: BLE001
        return PromotionResult(False, "move_to_ready_failed", source, ready_destination, message=str(exc))

    report = {
        "event": "promoted_to_ready",
        "source_name": source.name,
        "source_path": str(source),
        "destination_path": str(final_destination),
        "fingerprint": before.to_dict(),
        "safety": {
            "deleted": False,
            "overwritten": False,
            "final_library_write": False,
        },
    }
    report_path = write_promotion_report(config.promotions_dir, source.name, report)

    return PromotionResult(
        True,
        "promoted_to_ready",
        source,
        final_destination,
        report_path,
        message="Promoted stable item to ready",
    )
