"""Deleting files the integration no longer needs. Functions are blocking."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
import re
import shutil
import time

from . import cache
from .cache import unused_for

# The library and media browser show 320 px thumbs at rotation 0; those are
# kept. Editor-size thumbs and rotations are recreated when needed.
THUMB_GRACE_SECONDS = 86400
KEPT_THUMB = (320, 0)
_THUMB_RE = re.compile(r"^(?P<id>.+)_(?P<size>\d+)_(?P<rotation>\d+)\.jpg$")
# Config entry ids are ULIDs; only directories named like one are ours to delete.
_ENTRY_ID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def evict_thumbs(directory: Path, photo_ids: Collection[str]) -> int:
    """Delete thumbnails that are no longer needed.

    The library thumb (KEPT_THUMB) of each photo in ``photo_ids`` is kept;
    other sizes and rotations go once unused for THUMB_GRACE_SECONDS, and
    thumbs of photos not in the library after the (short) cache grace period.
    """
    if not directory.is_dir():
        return 0
    now = time.time()
    deleted = 0
    for path in directory.iterdir():
        match = _THUMB_RE.match(path.name)
        if match is None:
            remove = unused_for(path, cache.GRACE_SECONDS, now)
        elif match["id"] not in photo_ids:
            # Grace period: a photo added after ``photo_ids`` was taken.
            remove = unused_for(path, cache.GRACE_SECONDS, now)
        else:
            kept = (int(match["size"]), int(match["rotation"])) == KEPT_THUMB
            remove = not kept and unused_for(path, THUMB_GRACE_SECONDS, now)
        if remove and path.is_file():
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def evict_unreferenced(directory: Path, pattern: str, referenced: Collection[str]) -> int:
    """Delete files matching ``pattern`` that aren't ``referenced`` (by name).

    Used for originals left behind by a crash between writing and saving the
    library, and for old ``override.*`` files. The grace period protects a file
    that is being added right now.
    """
    if not directory.is_dir():
        return 0
    deleted = 0
    now = time.time()
    for path in directory.glob(pattern):
        if path.name in referenced or not path.is_file():
            continue
        if unused_for(path, cache.GRACE_SECONDS, now):
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def remove_orphan_entries(
    root: Path, storage: Path, domain: str, entry_ids: Collection[str]
) -> list[str]:
    """Delete per-frame directories and stores of config entries that no longer exist.

    ``root`` holds one directory per entry, ``storage`` is HA's ``.storage``.
    Only paths unchanged for the grace period go, so a frame being added while
    this runs is safe. Returns the removed entry ids.
    """
    now = time.time()
    removed: set[str] = set()

    def orphan(path: Path, entry_id: str) -> bool:
        return (
            bool(_ENTRY_ID_RE.match(entry_id))
            and entry_id not in entry_ids
            and unused_for(path, cache.GRACE_SECONDS, now)
        )

    if root.is_dir():
        for path in root.iterdir():
            if path.is_dir() and orphan(path, path.name):
                shutil.rmtree(path, ignore_errors=True)
                removed.add(path.name)
    if storage.is_dir():
        for path in storage.glob(f"{domain}.*"):
            entry_id = path.name.removeprefix(f"{domain}.")
            if path.is_file() and orphan(path, entry_id):
                path.unlink(missing_ok=True)
                removed.add(entry_id)
    return sorted(removed)


def usage(directory: Path) -> dict[str, int]:
    """File count and total bytes below a directory."""
    files = 0
    size = 0
    if directory.is_dir():
        for path in directory.rglob("*"):
            try:
                if path.is_file():
                    files += 1
                    size += path.stat().st_size
            except FileNotFoundError:
                continue
    return {"files": files, "bytes": size}
