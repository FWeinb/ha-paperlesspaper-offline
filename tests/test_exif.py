"""Photo date and location from EXIF (photo variables)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
import io

from homeassistant.core import HomeAssistant
from PIL import Image

from custom_components.paperlessoffline.diagnostics import async_get_config_entry_diagnostics
from custom_components.paperlessoffline.exif import EXIF_IFD, GPS_IFD, read_capture

from .conftest import make_jpeg


def _jpeg(date=None, offset=None, gps=None) -> bytes:
    exif = Image.Exif()
    if date or offset:
        ifd = exif.get_ifd(EXIF_IFD)
        if date:
            ifd[0x9003] = date
        if offset:
            ifd[0x9011] = offset
    if gps:
        exif.get_ifd(GPS_IFD).update(gps)
    buf = io.BytesIO()
    Image.new("RGB", (64, 40), "red").save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_date_with_offset() -> None:
    date, _ = read_capture(_jpeg("2024:07:14 15:30:05", "+02:00"))
    assert datetime.fromisoformat(date) == datetime(
        2024, 7, 14, 15, 30, 5, tzinfo=timezone(timedelta(hours=2))
    )


def test_date_without_offset_uses_default_zone() -> None:
    zone = timezone(timedelta(hours=-5))
    date, _ = read_capture(_jpeg("2024:07:14 15:30:05"), zone)
    assert datetime.fromisoformat(date).utcoffset() == timedelta(hours=-5)


def test_missing_and_malformed_tags() -> None:
    assert read_capture(make_jpeg()) == (None, None)
    assert read_capture(_jpeg("0000:00:00 00:00:00")) == (None, None)
    assert read_capture(_jpeg("garbage")) == (None, None)
    assert read_capture(b"not an image") == (None, None)


def test_bad_offset_falls_back_to_default() -> None:
    date, _ = read_capture(_jpeg("2024:07:14 15:30:05", "nonsense"), UTC)
    assert datetime.fromisoformat(date).utcoffset() == timedelta(0)


def _gps(lat_ref, lat, lon_ref, lon, *, alt=None, alt_ref=0):
    gps = {1: lat_ref, 2: lat, 3: lon_ref, 4: lon}
    if alt is not None:
        gps.update({5: alt_ref, 6: alt})
    return gps


def test_gps_all_hemispheres() -> None:
    cases = {
        ("N", "E"): (48.1372, 11.5756),
        ("N", "W"): (48.1372, -11.5756),
        ("S", "E"): (-48.1372, 11.5756),
        ("S", "W"): (-48.1372, -11.5756),
    }
    for (ns, ew), (lat, lon) in cases.items():
        gps = _gps(ns, (48, 8, 13.92), ew, (11, 34, 32.16), alt=520.5)
        _, location = read_capture(_jpeg(gps=gps))
        assert location["latitude"] == lat
        assert location["longitude"] == lon
        assert location["altitude"] == 520.5


def test_gps_below_sea_level_and_no_altitude() -> None:
    gps = _gps("N", (31, 30, 0), "E", (35, 30, 0), alt=400.0, alt_ref=1)
    _, location = read_capture(_jpeg(gps=gps))
    assert location["altitude"] == -400.0
    _, location = read_capture(_jpeg(gps=_gps("N", (1, 0, 0), "E", (2, 0, 0))))
    assert location == {"latitude": 1.0, "longitude": 2.0}


async def test_add_photo_stores_capture_and_templates(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    data = _jpeg(
        "2024:07:14 15:30:05",
        "+02:00",
        _gps("N", (48, 8, 13.92), "E", (11, 34, 32.16)),
    )
    photo = await manager.async_add_photo(data, "Munich")
    assert photo.exif_read and photo.date and photo.location["latitude"] == 48.1372
    plain = await manager.async_add_photo(make_jpeg(), "Plain")
    assert plain.date is None and plain.location is None

    variables = manager.template_variables(photo)
    from custom_components.paperlessoffline.templates import render_text

    out = render_text(
        hass,
        "{{ date_local(photo.date, 'long') }}|{{ date_local(photo.date, 'time') }}"
        "|{{ photo.location }}|{{ photo.location.altitude }}",
        variables,
    )
    assert out == "Sunday, July 14, 2024|15:30|48.1372, 11.5756|None"
    hass.config.latitude = hass.config.longitude = 0
    km = render_text(
        hass,
        "{{ distance(photo.location.latitude, photo.location.longitude) | round(0) > 0 }}",
        variables,
    )
    assert km == "True"
    assert (
        render_text(
            hass, "{{ photo.date }}|{{ photo.location }}", manager.template_variables(plain)
        )
        == "None|None"
    )

    listed = await hass.services.async_call(
        "paperlessoffline",
        "list_photos",
        {"config_entry_id": loaded_entry.entry_id},
        blocking=True,
        return_response=True,
    )
    by_name = {p["name"]: p for p in listed["photos"]}
    assert by_name["Munich"]["location"]["longitude"] == 11.5756
    assert by_name["Munich"]["date"].startswith("2024-07-14T15:30:05+02:00")
    assert by_name["Plain"]["date"] is None


async def test_migration_fills_existing_photos(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    photo = await manager.async_add_photo(_jpeg("2023:01:02 03:04:05", "-08:00"), "Old")
    # As stored by an older version: no capture data and not yet read.
    photo.date, photo.location, photo.exif_read = None, None, False
    await manager._async_read_missing_exif()
    assert photo.exif_read
    assert datetime.fromisoformat(photo.date).utcoffset() == timedelta(hours=-8)


async def test_diagnostics_redact_location(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    await manager.async_add_photo(_jpeg(gps=_gps("N", (48, 0, 0), "E", (11, 0, 0))), "Geo")
    diag = await async_get_config_entry_diagnostics(hass, loaded_entry)
    assert diag["photos"][0]["location"] == "**REDACTED**"
    assert "48" not in str(diag["photos"][0])
