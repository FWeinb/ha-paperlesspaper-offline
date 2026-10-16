"""End-to-end behaviour through the HTTP endpoints and actions."""

from __future__ import annotations

import base64
from datetime import timedelta
import io
from pathlib import Path
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from PIL import Image
import pytest

from custom_components.paperlessoffline.const import (
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    CONF_MOTION_WAKEUP,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    DOMAIN,
    EVENT_FRAME_WAKE,
)

from .conftest import TOKEN, make_jpeg

IMAGE_URL = f"/api/paperlessoffline/{TOKEN}/image.bmp"
SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"
COLORS = {"red": (230, 20, 20), "blue": (20, 20, 230), "yellow": (240, 230, 20)}


@pytest.fixture
def photo_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    for name, color in COLORS.items():
        (tmp_path / f"{name}.jpg").write_bytes(make_jpeg(color))
    return tmp_path


async def _add(hass: HomeAssistant, entry, path: Path, **extra) -> str:
    resp = await hass.services.async_call(
        DOMAIN,
        "add_photo",
        {"config_entry_id": entry.entry_id, "file_path": str(path), **extra},
        blocking=True,
        return_response=True,
    )
    return resp["photo_id"]


def _center_color(bmp: bytes) -> tuple[int, int, int]:
    return Image.open(io.BytesIO(bmp)).convert("RGB").getpixel((400, 240))


async def _wake(client, freezer: FrozenDateTimeFactory, minutes: int = 61):
    freezer.tick(timedelta(minutes=minutes))
    settings = await client.get(SETTINGS_URL)
    image = await client.get(IMAGE_URL)
    return settings, image


async def test_unknown_token(hass_client_no_auth, loaded_entry) -> None:
    client = await hass_client_no_auth()
    assert (await client.get("/api/paperlessoffline/nope/image.bmp")).status == 404
    assert (await client.get("/api/paperlessoffline/nope/settings.json")).status == 404


async def test_placeholder_when_empty(hass_client_no_auth, loaded_entry) -> None:
    client = await hass_client_no_auth()
    resp = await client.get(IMAGE_URL)
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "image/bmp"
    body = await resp.read()
    assert Image.open(io.BytesIO(body)).size == (800, 480)
    assert "Last-Modified" in resp.headers


async def test_slideshow_advances_once_per_wake(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    for name in COLORS:
        await _add(hass, loaded_entry, photo_dir / f"{name}.jpg", dither="none")
    events = []
    hass.bus.async_listen(EVENT_FRAME_WAKE, events.append)
    client = await hass_client_no_auth()

    _, first = await _wake(client, freezer)
    lm1 = first.headers["Last-Modified"]
    assert _center_color(await first.read()) == (255, 0, 0)

    # Retry within the debounce window: same image, same Last-Modified.
    freezer.tick(timedelta(seconds=20))
    again = await client.get(IMAGE_URL)
    assert again.headers["Last-Modified"] == lm1

    _, second = await _wake(client, freezer)
    assert _center_color(await second.read()) == (0, 0, 255)
    assert second.headers["Last-Modified"] != lm1
    await hass.async_block_till_done()
    assert len(events) == 2
    assert events[0].data["kind"] == "photo"


async def test_show_photo_and_skip(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    ids = [await _add(hass, loaded_entry, photo_dir / f"{n}.jpg", dither="none") for n in COLORS]
    client = await hass_client_no_auth()
    await hass.services.async_call(
        DOMAIN,
        "show_photo",
        {"config_entry_id": loaded_entry.entry_id, "photo_id": ids[2]},
        blocking=True,
    )
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "off"
    _, image = await _wake(client, freezer)
    assert _center_color(await image.read()) == (255, 255, 0)

    # Now up next is the first photo (wraps); skipping moves to the second.
    await hass.services.async_call(
        DOMAIN, "next_photo", {"config_entry_id": loaded_entry.entry_id}, blocking=True
    )
    _, image = await _wake(client, freezer)
    assert _center_color(await image.read()) == (0, 0, 255)


async def test_show_image_override(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    await _add(hass, loaded_entry, photo_dir / "red.jpg", dither="none")
    client = await hass_client_no_auth()
    await hass.services.async_call(
        DOMAIN,
        "show_image",
        {
            "config_entry_id": loaded_entry.entry_id,
            "file_path": str(photo_dir / "yellow.jpg"),
            "wakes": 1,
            "dither": "none",
        },
        blocking=True,
    )
    assert "image" in hass.states.get("sensor.kitchen_pending_changes").attributes["pending"]
    _, image = await _wake(client, freezer)
    color = _center_color(await image.read())
    assert color == (255, 255, 0)
    _, image = await _wake(client, freezer)
    assert _center_color(await image.read()) == (255, 0, 0)


async def test_deleting_shown_photo_keeps_image(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    photo_id = await _add(hass, loaded_entry, photo_dir / "red.jpg", dither="none")
    client = await hass_client_no_auth()
    _, image = await _wake(client, freezer)
    lm = image.headers["Last-Modified"]
    await hass.services.async_call(
        DOMAIN,
        "remove_photo",
        {"config_entry_id": loaded_entry.entry_id, "photo_id": photo_id},
        blocking=True,
    )
    _, image = await _wake(client, freezer)
    assert image.headers["Last-Modified"] == lm  # no redraw of an empty rotation


async def test_settings_json_and_304(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry
) -> None:
    client = await hass_client_no_auth()
    resp = await client.get(SETTINGS_URL)
    assert resp.status == 200
    data = await resp.json()
    assert data["timeout"] == 3600
    assert data["motionWakeup"] is False
    assert data["downloadUrl"].endswith(IMAGE_URL)
    lm = resp.headers["Last-Modified"]
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "on"

    resp = await client.get(SETTINGS_URL, headers={"If-Modified-Since": lm})
    assert resp.status == 304

    hass.config_entries.async_update_entry(
        loaded_entry, options={**loaded_entry.options, CONF_MOTION_WAKEUP: True}
    )
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "off"
    resp = await client.get(SETTINGS_URL, headers={"If-Modified-Since": lm})
    assert resp.status == 200
    assert (await resp.json())["motionWakeup"] is True
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "on"


async def test_quiet_hours(hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer) -> None:
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-06-01 23:00:00+00:00")
    hass.config_entries.async_update_entry(
        loaded_entry,
        options={
            **loaded_entry.options,
            CONF_QUIET_ENABLED: True,
            CONF_QUIET_START: "22:00:00",
            CONF_QUIET_END: "07:00:00",
            CONF_MOTION_WAKEUP: True,
        },
    )
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    data = await (await client.get(SETTINGS_URL)).json()
    assert data["timeout"] == 8 * 3600 + 60
    assert data["motionWakeup"] is False
    # The quiet-hour adjustment is not a pending user change.
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "on"


async def test_basic_auth(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    hass.config_entries.async_update_entry(
        loaded_entry,
        options={
            **loaded_entry.options,
            CONF_AUTH_ENABLED: True,
            CONF_AUTH_USER: "frame",
            CONF_AUTH_PASSWORD: "secret",
        },
    )
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    settings = await (await client.get(SETTINGS_URL)).json()
    assert settings["httpAuthUser"] == "frame"
    assert (await client.get(IMAGE_URL)).status == 401
    bad = base64.b64encode(b"frame:wrong").decode()
    assert (await client.get(IMAGE_URL, headers={"Authorization": f"Basic {bad}"})).status == 401
    good = base64.b64encode(b"frame:secret").decode()
    assert (await client.get(IMAGE_URL, headers={"Authorization": f"Basic {good}"})).status == 200


async def test_telemetry_query(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    client = await hass_client_no_auth()
    await client.get(IMAGE_URL + "?battery=3900")
    state = hass.states.get("sensor.kitchen_last_seen")
    assert state.attributes["telemetry"] == {"battery": "3900"}


async def test_library_actions(
    hass: HomeAssistant, loaded_entry, photo_dir, config_entry_factory
) -> None:
    entry_id = loaded_entry.entry_id
    red = await _add(hass, loaded_entry, photo_dir / "red.jpg", saturation=1.4)
    blue = await _add(hass, loaded_entry, photo_dir / "blue.jpg", name="Sea")
    listing = await hass.services.async_call(
        DOMAIN, "list_photos", {"config_entry_id": entry_id}, blocking=True, return_response=True
    )
    assert [p["name"] for p in listing["photos"]] == ["red", "Sea"]
    assert listing["photos"][0]["overrides"] == {"saturation": 1.4}

    await hass.services.async_call(
        DOMAIN,
        "move_photo",
        {"config_entry_id": entry_id, "photo_id": blue, "position": 0},
        blocking=True,
    )
    updated = await hass.services.async_call(
        DOMAIN,
        "update_photo",
        {
            "config_entry_id": entry_id,
            "photo_id": red,
            "reset": ["saturation"],
            "dither": "atkinson",
            "enabled": False,
        },
        blocking=True,
        return_response=True,
    )
    assert updated["overrides"] == {"dither": "atkinson"}
    assert updated["enabled"] is False
    listing = await hass.services.async_call(
        DOMAIN, "list_photos", {"config_entry_id": entry_id}, blocking=True, return_response=True
    )
    assert [p["photo_id"] for p in listing["photos"]] == [blue, red]
    assert hass.states.get("sensor.kitchen_photos_in_rotation").state == "1"
    assert hass.states.get("select.kitchen_up_next").attributes["options"] == ["Sea"]

    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    copied = await hass.services.async_call(
        DOMAIN,
        "copy_photo",
        {"config_entry_id": entry_id, "photo_id": red, "target_config_entry_id": other.entry_id},
        blocking=True,
        return_response=True,
    )
    assert copied["overrides"] == {"dither": "atkinson"}

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "remove_photo",
            {"config_entry_id": entry_id, "photo_id": "missing"},
            blocking=True,
        )


async def test_add_photo_validation(hass: HomeAssistant, loaded_entry, tmp_path: Path) -> None:
    entry_id = loaded_entry.entry_id
    with pytest.raises(ServiceValidationError, match="not in an allowed"):
        await hass.services.async_call(
            DOMAIN,
            "add_photo",
            {"config_entry_id": entry_id, "file_path": "/etc/passwd"},
            blocking=True,
        )
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    (tmp_path / "x.txt").write_text("not an image")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_photo",
            {"config_entry_id": entry_id, "file_path": str(tmp_path / "x.txt")},
            blocking=True,
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "add_photo", {"config_entry_id": entry_id}, blocking=True
        )


async def test_set_defaults(hass: HomeAssistant, loaded_entry) -> None:
    resp = await hass.services.async_call(
        DOMAIN,
        "set_defaults",
        {"dither": "bayer", "saturation": 1.2},
        blocking=True,
        return_response=True,
    )
    assert resp == {"defaults": {"dither": "bayer", "saturation": 1.2}}
    manager = loaded_entry.runtime_data
    assert manager.render_options(None).dither == "bayer"
    resp = await hass.services.async_call(
        DOMAIN, "set_defaults", {"reset": ["all"]}, blocking=True, return_response=True
    )
    assert resp == {"defaults": {}}


async def test_entities_change_options(hass: HomeAssistant, loaded_entry, photo_dir) -> None:
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.kitchen_refresh_interval", "value": 30},
        blocking=True,
    )
    assert loaded_entry.options["interval"] == 1800
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.kitchen_auto_rotation"}, blocking=True
    )
    assert loaded_entry.options["auto_rotation"] is True
    assert hass.states.get("switch.kitchen_auto_rotation").state == "on"
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.kitchen_slideshow_order", "option": "shuffle"},
        blocking=True,
    )
    assert loaded_entry.options["order"] == "shuffle"

    await _add(hass, loaded_entry, photo_dir / "red.jpg")
    blue = await _add(hass, loaded_entry, photo_dir / "blue.jpg")
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.kitchen_up_next", "option": "blue"},
        blocking=True,
    )
    assert hass.states.get("select.kitchen_up_next").attributes["photo_id"] == blue
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.kitchen_skip_photo"}, blocking=True
    )
    assert hass.states.get("select.kitchen_up_next").attributes["photo_id"] != blue


async def test_preview_images(hass: HomeAssistant, hass_client, loaded_entry, photo_dir) -> None:
    photo_id = await _add(hass, loaded_entry, photo_dir / "red.jpg")
    await hass.async_block_till_done()
    client = await hass_client()
    state = hass.states.get("image.kitchen_up_next")
    resp = await client.get(state.attributes["entity_picture"])
    assert resp.status == 200
    assert Image.open(io.BytesIO(await resp.read())).size == (800, 480)
    resp = await client.get(f"/api/paperlessoffline/preview/{loaded_entry.entry_id}/{photo_id}.png")
    assert resp.status == 200
    resp = await client.get(f"/api/paperlessoffline/thumb/{loaded_entry.entry_id}/{photo_id}.jpg")
    assert resp.status == 200
    assert max(Image.open(io.BytesIO(await resp.read())).size) <= 320


async def test_short_interval_wakes_via_settings(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    """Wakes 25 s apart still advance: the settings fetch marks each wake."""
    for name in COLORS:
        await _add(hass, loaded_entry, photo_dir / f"{name}.jpg", dither="none")
    client = await hass_client_no_auth()
    seen = []
    for _ in range(3):
        freezer.tick(timedelta(seconds=25))
        await client.get(SETTINGS_URL)
        probe = await client.get(IMAGE_URL)  # redirect probe
        image = await client.get(IMAGE_URL)  # real download
        assert probe.headers["Last-Modified"] == image.headers["Last-Modified"]
        seen.append(_center_color(await image.read()))
    assert seen == [(255, 0, 0), (0, 0, 255), (255, 255, 0)]


async def test_image_only_frame_debounces(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    """Without settings fetches, image requests start wakes after 60 s."""
    for name in COLORS:
        await _add(hass, loaded_entry, photo_dir / f"{name}.jpg", dither="none")
    client = await hass_client_no_auth()
    first = await client.get(IMAGE_URL)
    freezer.tick(timedelta(seconds=30))
    retry = await client.get(IMAGE_URL)
    assert retry.headers["Last-Modified"] == first.headers["Last-Modified"]
    freezer.tick(timedelta(seconds=61))
    nxt = await client.get(IMAGE_URL)
    assert _center_color(await nxt.read()) == (0, 0, 255)


async def test_image_retry_after_settings_is_not_a_wake(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    """A slow image retry long after the settings fetch doesn't skip a photo."""
    for name in COLORS:
        await _add(hass, loaded_entry, photo_dir / f"{name}.jpg", dither="none")
    client = await hass_client_no_auth()
    await client.get(SETTINGS_URL)
    first = await client.get(IMAGE_URL)
    freezer.tick(timedelta(seconds=90))
    retry = await client.get(IMAGE_URL)
    assert retry.headers["Last-Modified"] == first.headers["Last-Modified"]


async def test_placeholder_follows_rename_and_language(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    """A frame showing the placeholder gets the updated one (new name / language)."""
    client = await hass_client_no_auth()
    _, first = await _wake(client, freezer)
    hass.config_entries.async_update_entry(loaded_entry, title="Küche")
    await hass.async_block_till_done()
    _, second = await _wake(client, freezer)
    assert second.headers["Last-Modified"] != first.headers["Last-Modified"]
    _, third = await _wake(client, freezer)
    assert third.headers["Last-Modified"] == second.headers["Last-Modified"]  # no needless redraw
    hass.config.language = "de"
    assert loaded_entry.runtime_data.placeholder_text().subtitle == "Noch keine Fotos"


async def test_placeholder_follows_device_rename(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    """Renaming the device (not the entry) updates the "No photos yet" screen."""
    from homeassistant.helpers import device_registry as dr

    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    _, first = await _wake(client, freezer)
    assert manager.placeholder_text().title == "Kitchen"
    preview = hass.states.get("image.kitchen_up_next").state  # last-updated time

    dr.async_get(hass).async_update_device(manager.device_id, name_by_user="Wohnküche")
    await hass.async_block_till_done()
    assert manager.display_name == "Wohnküche"
    assert manager.placeholder_text().title == "Wohnküche"
    assert manager.template_variables()["frame"].name == "Wohnküche"
    assert "placeholder" in manager.pending_changes()
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "off"
    # The "Up next" preview refreshes right away.
    assert hass.states.get("image.kitchen_up_next").state != preview

    _, second = await _wake(client, freezer)
    assert second.headers["Last-Modified"] != first.headers["Last-Modified"]
    assert "placeholder" not in manager.pending_changes()
    assert hass.states.get("binary_sensor.kitchen_in_sync").state == "on"


async def test_settings_download_url_keeps_port(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry
) -> None:
    """The image URL in the settings JSON uses the host and port the frame used."""
    client = await hass_client_no_auth()
    resp = await client.get(SETTINGS_URL, headers={"Host": "192.168.1.10:8123"})
    assert (await resp.json())["downloadUrl"] == f"http://192.168.1.10:8123{IMAGE_URL}"
    resp = await client.get(SETTINGS_URL, headers={"Host": "192.168.1.10"})
    assert (await resp.json())["downloadUrl"] == f"http://192.168.1.10{IMAGE_URL}"


async def test_upload_pixel_limit(hass: HomeAssistant, loaded_entry, monkeypatch) -> None:
    """Images above the pixel limit are refused, for the library and for show_image."""
    manager = loaded_entry.runtime_data
    monkeypatch.setattr("custom_components.paperlessoffline.frame.MAX_IMAGE_PIXELS", 320 * 199)
    with pytest.raises(ServiceValidationError) as err:
        await manager.async_add_photo(make_jpeg(), "big")
    assert err.value.translation_key == "image_too_many_pixels"
    assert err.value.translation_placeholders == {"megapixels": "1", "limit": "0"}  # rounded up
    with pytest.raises(ServiceValidationError, match="megapixels"):
        await manager.async_set_override(make_jpeg(), "big", None, 1)
    assert manager.photos == []
    assert manager.state.override is None
    await manager.async_add_photo(make_jpeg(size=(320, 199)), "fits")


async def test_decompression_bomb_reports_pixels(hass: HomeAssistant, loaded_entry) -> None:
    """Images Pillow itself refuses as too large get the same message."""
    from PIL import Image as PILImage

    manager = loaded_entry.runtime_data
    with (
        patch.object(PILImage, "MAX_IMAGE_PIXELS", 1000),
        pytest.raises(ServiceValidationError) as err,
    ):
        await manager.async_add_photo(make_jpeg(), "bomb")
    assert err.value.translation_key == "image_too_many_pixels"
    assert err.value.translation_placeholders == {"megapixels": "1", "limit": "100"}
