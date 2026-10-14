"""On-disk cache of rendered images."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
import json
from pathlib import Path
from typing import Any

RENDER_VERSION = 1
MAX_ENTRIES = 24


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
        """Whether both files exist."""
        return self.bmp_path(key).is_file() and self.png_path(key).is_file()

    def put(self, key: str, bmp: bytes, png: bytes) -> None:
        """Store a render atomically."""
        self.directory.mkdir(parents=True, exist_ok=True)
        for path, data in ((self.bmp_path(key), bmp), (self.png_path(key), png)):
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)

    def read_bmp(self, key: str) -> bytes | None:
        """Read a cached BMP."""
        try:
            return self.bmp_path(key).read_bytes()
        except FileNotFoundError:
            return None

    def read_png(self, key: str) -> bytes | None:
        """Read a cached preview."""
        try:
            return self.png_path(key).read_bytes()
        except FileNotFoundError:
            return None

    def prune(self, keep: Iterable[str | None], max_entries: int = MAX_ENTRIES) -> None:
        """Delete old entries beyond ``max_entries``, never touching ``keep``."""
        if not self.directory.is_dir():
            return
        protected = {k for k in keep if k}
        bmps = sorted(self.directory.glob("*.bmp"), key=lambda p: p.stat().st_mtime, reverse=True)
        for index, bmp in enumerate(bmps):
            key = bmp.stem
            if index < max_entries or key in protected:
                continue
            bmp.unlink(missing_ok=True)
            self.png_path(key).unlink(missing_ok=True)
