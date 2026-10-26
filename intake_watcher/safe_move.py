"""Moves that rename and nothing else.

``shutil.move`` falls back to copying and then deleting whenever a rename fails, which is what
happens when the source and the destination are on different filesystems (two ZFS datasets, two
Docker mounts, two drives). A copy-then-delete of an incoming download is slow, is not atomic, and
a crash halfway leaves a partial file where the next stage will pick it up. Every move here is a
rename, and one that cannot be a rename fails before touching anything.
"""

from __future__ import annotations

import errno
import os
from pathlib import Path

# Windows reports "different disk drive" as winerror 17 (ERROR_NOT_SAME_DEVICE).
_WINERROR_NOT_SAME_DEVICE = 17

CROSS_DEVICE_MESSAGE = (
    "The source and the destination are on different filesystems. Intake Watcher only moves by "
    "rename and never copies then deletes. Keep incoming, intake-processing, ready and failed on "
    "one filesystem (one dataset, one mount)."
)


class CrossDeviceMoveError(OSError):
    """A move would have to copy because source and destination are on different filesystems."""


def move_by_rename(source: str | os.PathLike, destination: str | os.PathLike) -> Path:
    """Rename ``source`` to ``destination`` and return the destination. Never copies or replaces."""
    if os.path.lexists(destination):
        raise FileExistsError(errno.EEXIST, "Destination already exists", str(destination))
    try:
        os.rename(source, destination)
    except OSError as exc:
        if exc.errno == errno.EXDEV or getattr(exc, "winerror", None) == _WINERROR_NOT_SAME_DEVICE:
            raise CrossDeviceMoveError(exc.errno, f"{CROSS_DEVICE_MESSAGE} ({source} -> {destination})") from exc
        raise
    return Path(destination)
