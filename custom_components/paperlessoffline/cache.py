"""On-disk cache of rendered images."""

from __future__ import annotations

from collections.abc import Iterable
import contextlib
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

RENDER_VERSION = 2
# Files not needed and unused for this long are deleted. It also protects
# renders in progress (e.g. an editor preview between writing and reading).
GRACE_SECONDS = 600


def touch(path: Path) -> None:
    """Mark a file as used now (its mtime is its last use), if it still exists."""
    with contextlib.suppress(FileNotFoundError):
        os.utime(path)


def unused_for(path: Path, seconds: float, now: float | None = None) -> bool:
    """Whether a file was last used (modified or touched) more than ``seconds`` ago."""
    try:
        return path.stat().st_mtime < (time.time() if now is None else now) - seconds
    except FileNotFoundError:
        return False


def cache_key(source: str, options: dict[str, Any], canvas: dict[str, Any]) -> str:
    """Return a stable key for a render of ``source`` with given options/canvas."""
    payload = json.dumps(
        {"v": RENDER_VERSION, "src": source, "opts": options, "canvas": canvas},
        sort_keys=True,
        default=list,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


class RenderCache:
    """Stores ``<key>.bmp`` and ``<key>.png`` files. Methods are blocking."""

    def __init__(self, directory: Path) -> None:
        """Initialise."""
        self.directory = directory

    def bmp_path(self, key: str) -> Path:
        """Path of the BMP for a key."""
        return self.directory / f"{key}.bmp"

    def png_path(self, key: str) -> Path:
        """Path of the preview PNG for a key."""
        return self.directory / f"{key}.png"

    def has(self, key: str) -> bool:
        """Whether both files exist (a hit counts as a use)."""
        bmp, png = self.bmp_path(key), self.png_path(key)
        if not (bmp.is_file() and png.is_file()):
            return False
        touch(bmp)
        touch(png)
        return True

    def put(self, key: str, bmp: bytes, png: bytes) -> None:
        """Store a render atomically."""
        self.directory.mkdir(parents=True, exist_ok=True)
        for path, data in ((self.bmp_path(key), bmp), (self.png_path(key), png)):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)

    def read_bmp(self, key: str) -> bytes | None:
        """Read a cached BMP."""
        path = self.bmp_path(key)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None
        touch(path)
        return data

    def read_png(self, key: str) -> bytes | None:
        """Read a cached preview."""
        path = self.png_path(key)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return None
        touch(path)
        return data

    def evict(self, needed: Iterable[str | None], grace: float | None = None) -> int:
        """Delete every entry not in ``needed`` that has been unused for ``grace`` seconds.

        Leftover ``*.tmp`` files go after the grace period too, needed or not.
        Returns the number of files deleted.
        """
        if not self.directory.is_dir():
            return 0
        grace = GRACE_SECONDS if grace is None else grace
        keep = {k for k in needed if k}
        now = time.time()
        files: dict[str, list[Path]] = {}
        for path in self.directory.iterdir():
            if path.suffix == ".tmp" or not path.is_file():
                if path.is_file() and unused_for(path, grace, now):
                    path.unlink(missing_ok=True)
                continue
            files.setdefault(path.name.split(".", 1)[0], []).append(path)
        deleted = 0
        for key, paths in files.items():
            # An entry's last use is that of its most recently used file.
            if key in keep or not all(unused_for(p, grace, now) for p in paths):
                continue
            for path in paths:
                # Check again right before deleting: the entry may just have been used.
                if unused_for(path, grace):
                    path.unlink(missing_ok=True)
                    deleted += 1
        return deleted
