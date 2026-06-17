from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TEMP_SUFFIXES = (
    ".part",
    ".tmp",
    ".crdownload",
    ".download",
    ".aria2",
    ".!qb",
    ".!qB",
)

DEFAULT_SUPPORTED_MEDIA_EXTENSIONS = (
    # Video
    ".mkv",
    ".mp4",
    ".m4v",
    ".avi",
    ".mov",
    ".wmv",
    ".webm",
    ".flv",
    ".mpg",
    ".mpeg",
    ".ts",
    # Music / audio / audiobooks
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".m4b",
    ".aac",
    ".ogg",
    ".opus",
    ".aiff",
    ".alac",
    # Books / comics
    ".epub",
    ".pdf",
    ".mobi",
    ".azw3",
    ".cbz",
    ".cbr",
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class IntakeConfig:
    data_root: Path = Path("data")
    mode: str = "hybrid"
    stability_seconds: int = 20 * 60
    poll_seconds: int = 5 * 60
    require_ready_marker: bool = False
    ready_markers: tuple[str, ...] = ("READY.txt", ".done")
    allow_single_file_promotion: bool = True
    collision_policy: str = "block"  # block or suffix
    destructive_actions_enabled: bool = False
    temp_suffixes: tuple[str, ...] = DEFAULT_TEMP_SUFFIXES
    supported_media_extensions: tuple[str, ...] = DEFAULT_SUPPORTED_MEDIA_EXTENSIONS
    ignored_names: tuple[str, ...] = (".DS_Store", "Thumbs.db")
    state_filename: str = "state.json"
    log_filename: str = "intake-log.jsonl"
    status_log_heartbeat_seconds: int = 15 * 60

    @classmethod
    def from_env(cls) -> "IntakeConfig":
        data_root = Path(os.getenv("DATA_ROOT", "data"))
        return cls(
            data_root=data_root,
            mode=os.getenv("INTAKE_MODE", "hybrid").strip().lower(),
            stability_seconds=_env_int("STABILITY_SECONDS", 20 * 60),
            poll_seconds=_env_int("POLL_SECONDS", 5 * 60),
            require_ready_marker=_env_bool("REQUIRE_READY_MARKER", False),
            ready_markers=_env_csv("READY_MARKERS", ("READY.txt", ".done")),
            allow_single_file_promotion=_env_bool("ALLOW_SINGLE_FILE_PROMOTION", True),
            collision_policy=os.getenv("COLLISION_POLICY", "block").strip().lower(),
            destructive_actions_enabled=_env_bool("DESTRUCTIVE_ACTIONS_ENABLED", False),
            temp_suffixes=_env_csv("TEMP_SUFFIXES", DEFAULT_TEMP_SUFFIXES),
            supported_media_extensions=_env_csv(
                "SUPPORTED_MEDIA_EXTENSIONS", DEFAULT_SUPPORTED_MEDIA_EXTENSIONS
            ),
            status_log_heartbeat_seconds=_env_int("STATUS_LOG_HEARTBEAT_SECONDS", 15 * 60),
        )

    @property
    def ingest_root(self) -> Path:
        return self.data_root / "_INGEST"

    @property
    def incoming_dir(self) -> Path:
        return self.ingest_root / "incoming"

    @property
    def processing_dir(self) -> Path:
        return self.ingest_root / "intake-processing"

    @property
    def ready_dir(self) -> Path:
        return self.ingest_root / "ready"

    @property
    def failed_dir(self) -> Path:
        return self.ingest_root / "failed"

    @property
    def reports_dir(self) -> Path:
        return self.data_root / "_REPORTS" / "intake-watcher"

    @property
    def promotions_dir(self) -> Path:
        return self.reports_dir / "promotions"

    @property
    def stuck_dir(self) -> Path:
        return self.reports_dir / "stuck"

    @property
    def state_path(self) -> Path:
        return self.reports_dir / self.state_filename

    @property
    def log_path(self) -> Path:
        return self.reports_dir / self.log_filename

    def ensure_directories(self) -> None:
        for directory in (
            self.incoming_dir,
            self.processing_dir,
            self.ready_dir,
            self.failed_dir,
            self.reports_dir,
            self.promotions_dir,
            self.stuck_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        allowed_modes = {"manual_marker", "stability", "hybrid"}
        if self.mode not in allowed_modes:
            raise ValueError(f"INTAKE_MODE must be one of {sorted(allowed_modes)}")

        allowed_collision = {"block", "suffix"}
        if self.collision_policy not in allowed_collision:
            raise ValueError(f"COLLISION_POLICY must be one of {sorted(allowed_collision)}")

        if self.stability_seconds < 0:
            raise ValueError("STABILITY_SECONDS cannot be negative")

        if self.poll_seconds <= 0:
            raise ValueError("POLL_SECONDS must be positive")

        if self.status_log_heartbeat_seconds <= 0:
            raise ValueError("STATUS_LOG_HEARTBEAT_SECONDS must be positive")
