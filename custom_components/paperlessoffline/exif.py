"""Capture date and location from a photo's EXIF header (no pixel decode)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
import io
import logging
from pathlib import Path
from typing import Any

from PIL import Image

_LOGGER = logging.getLogger(__name__)

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
DATE_TIME_ORIGINAL = 0x9003
OFFSET_TIME_ORIGINAL = 0x9011


def _parse_offset(text: Any) -> tzinfo | None:
    """``+02:00`` to a fixed offset (None when missing or malformed)."""
    text = str(text or "").strip().strip("\x00")
    if len(text) != 6 or text[0] not in "+-" or text[3] != ":":
        return None
    try:
        delta = timedelta(hours=int(text[1:3]), minutes=int(text[4:6]))
    except ValueError:
        return None
    return timezone(-delta if text[0] == "-" else delta)


def _parse_date(exif: Image.Exif, default_tz: tzinfo) -> str | None:
    ifd = exif.get_ifd(EXIF_IFD)
    raw = ifd.get(DATE_TIME_ORIGINAL)
    if not raw:
        return None
    try:
        naive = datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    if naive.year < 1900:
        return None
    zone = _parse_offset(ifd.get(OFFSET_TIME_ORIGINAL)) or default_tz
    return naive.replace(tzinfo=zone).isoformat()


def _degrees(value: Any) -> float | None:
    try:
        deg, minutes, seconds = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    return deg + minutes / 60 + seconds / 3600


def _parse_location(exif: Image.Exif) -> dict[str, float] | None:
    gps = exif.get_ifd(GPS_IFD)
    lat = _degrees(gps.get(2))
    lon = _degrees(gps.get(4))
    if lat is None or lon is None:
        return None
    if str(gps.get(1, "N")).upper().startswith("S"):
        lat = -lat
    if str(gps.get(3, "E")).upper().startswith("W"):
        lon = -lon
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    location: dict[str, float] = {"latitude": round(lat, 6), "longitude": round(lon, 6)}
    try:
        altitude = float(gps[6])
    except (KeyError, TypeError, ValueError):
        altitude = None
    if altitude is not None:
        if gps.get(5) in (1, b"\x01"):
            altitude = -altitude
        location["altitude"] = round(altitude, 1)
    return location


def read_capture(
    source: bytes | Path, default_tz: tzinfo = UTC
) -> tuple[str | None, dict[str, float] | None]:
    """Return ``(date as ISO text with offset, location)``; each None when absent.

    Only the header is parsed. Blocking: run it off the event loop.
    """
    try:
        with Image.open(io.BytesIO(source) if isinstance(source, bytes) else source) as image:
            exif = image.getexif()
            return _parse_date(exif, default_tz), _parse_location(exif)
    except Exception:
        _LOGGER.debug("Could not read EXIF", exc_info=True)
        return None, None
