"""Card backgrounds from a camera or image entity, or a URL."""

from __future__ import annotations

import os
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import probatio as vol
import pytest

from custom_components.paperlessoffline import cache, overlay_images
from custom_components.paperlessoffline.const import DOMAIN
from custom_components.paperlessoffline.render import RenderOptions, canvas_for, render
from custom_components.paperlessoffline.render.pipeline import positions_from_bmp

from .conftest import make_jpeg
from .test_overlays import _call, _wake

SOURCE = "http://cam.local/garden.jpg"


@pytest.fixture
def pictures(monkeypatch):
    """What each source returns: bytes, or an exception to raise."""
    served: dict[str, bytes | Exception] = {SOURCE: make_jpeg((0, 0, 250), size=(320, 200))}

    async def fetch(hass, source):
        result = served[source]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(overlay_images, "async_download", fetch)
    monkeypatch.setattr(overlay_images, "async_entity_image", fetch)
    return served


async def _add_card(hass, entry, **extra) -> str:
    resp = await _call(
        hass,
        "add_card",
        config_entry_id=entry.entry_id,
        **{"name": "Garden", "background": "image", "background_image": SOURCE, **extra},
    )
    return resp["photo_id"]


async def _card(hass, entry, card_id) -> dict:
    photos = (await _call(hass, "list_photos", config_entry_id=entry.entry_id))["photos"]
    return next(p for p in photos if p["photo_id"] == card_id)


async def test_card_picture_at_wake(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, *, freezer, pictures
) -> None:
    card_id = await _add_card(hass, loaded_entry)
    manager = loaded_entry.runtime_data
    listed = await _card(hass, loaded_entry, card_id)
    assert listed["background"] == "image"
    assert listed["background_image"] == SOURCE
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    assert card_id in manager.state.card_pictures
    assert (await _card(hass, loaded_entry, card_id))["background_error"] is None
    white = await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id, name="White")
    assert await manager.async_photo_preview(white["photo_id"]) != await manager.async_preview(
        "showing"
    )

    # Only the card is enabled: the same picture again isn't redrawn, a new one is.
    await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=white["photo_id"],
        enabled=False,
    )
    same = await _wake(client, freezer)
    assert same.headers["Last-Modified"] == first.headers["Last-Modified"]
    pictures[SOURCE] = make_jpeg((250, 250, 0), size=(320, 200))
    changed = await _wake(client, freezer)
    assert changed.headers["Last-Modified"] != first.headers["Last-Modified"]


async def test_card_picture_failure_keeps_last_picture(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, *, freezer, pictures, caplog
) -> None:
    card_id = await _add_card(hass, loaded_entry)
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    kept = manager.state.card_pictures[card_id]

    pictures[SOURCE] = HomeAssistantError("camera offline")
    again = await _wake(client, freezer)
    assert again.status == 200
    assert again.headers["Last-Modified"] == first.headers["Last-Modified"]
    assert manager.state.card_pictures[card_id] == kept
    assert (await _card(hass, loaded_entry, card_id))["background_error"] == "camera offline"
    assert "camera offline" in caplog.text

    # Without a picture to keep, the card is white.
    manager.state.card_pictures.clear()
    await _wake(client, freezer)
    assert card_id not in manager.state.card_pictures


async def test_card_picture_empty_source_is_white(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, *, freezer, pictures
) -> None:
    hass.states.async_set("input_boolean.camera", "on")
    card_id = await _add_card(
        hass,
        loaded_entry,
        background_image=f"{{{{ '{SOURCE}' if is_state('input_boolean.camera', 'on') }}}}",
    )
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert card_id in manager.state.card_pictures
    hass.states.async_set("input_boolean.camera", "off")
    await _wake(client, freezer)
    assert card_id not in manager.state.card_pictures
    assert (await _card(hass, loaded_entry, card_id))["background_error"] is None


async def test_card_picture_validation(hass: HomeAssistant, loaded_entry, pictures) -> None:
    with pytest.raises(ServiceValidationError, match="picture source"):
        await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id, background="image")
    white = await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id)
    # A source alone switches a card to a picture background.
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=white["photo_id"],
        background_image="camera.garden",
    )
    assert (updated["background"], updated["background_image"]) == ("image", "camera.garden")
    # Another background drops the source.
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=white["photo_id"],
        background="blue",
    )
    assert (updated["background"], updated["background_image"]) == ("blue", "")


async def test_card_picture_previews(hass: HomeAssistant, loaded_entry, pictures) -> None:
    card_id = await _add_card(hass, loaded_entry)
    white = await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id, name="White")
    manager = loaded_entry.runtime_data
    plain = await manager.async_photo_preview(white["photo_id"])
    # Previews fetch live, without a wake.
    assert await manager.async_photo_preview(card_id) != plain
    assert await manager.async_preview("up_next") != plain
    assert manager._up_next_keys() == await manager._async_render_up_next()

    png, error = await manager.async_render_preview(
        white["photo_id"], None, background=("image", None, SOURCE)
    )
    assert png != plain and error is None
    pictures[SOURCE] = HomeAssistantError("offline")
    png, error = await manager.async_render_preview(
        white["photo_id"], None, background=("image", None, SOURCE)
    )
    assert png == plain and error == "offline"


async def test_card_picture_kept_by_housekeeping(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, *, freezer, pictures
) -> None:
    card_id = await _add_card(hass, loaded_entry)
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    key = manager.state.card_pictures[card_id]
    old = time.time() - cache.GRACE_SECONDS - 10
    for path in (manager.cache.bmp_path(key), manager.cache.png_path(key)):
        os.utime(path, (old, old))
    await manager.async_housekeeping()
    assert manager.cache.has(key)

    # Deleting the card forgets its picture.
    await hass.services.async_call(
        DOMAIN,
        "remove_photo",
        {"config_entry_id": loaded_entry.entry_id, "photo_id": card_id},
        blocking=True,
    )
    assert card_id not in manager.state.card_pictures


async def test_copy_card_keeps_picture_source(
    hass: HomeAssistant, loaded_entry, config_entry_factory, pictures
) -> None:
    card_id = await _add_card(hass, loaded_entry)
    other = await config_entry_factory("epd7-0123456789ab", "Hall")
    copy = await _call(
        hass,
        "copy_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        target_config_entry_id=other.entry_id,
    )
    assert (copy["background"], copy["background_image"]) == ("image", SOURCE)


async def test_card_picture_fit(hass: HomeAssistant, loaded_entry, pictures) -> None:
    """A picture background can be scaled to fit instead of following the frame's fit."""
    manager = loaded_entry.runtime_data
    card_id = await _add_card(hass, loaded_entry)
    assert (await _card(hass, loaded_entry, card_id))["background_fit"] is None
    cover = await manager.async_photo_preview(card_id)

    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background_fit="contain",
    )
    assert (updated["background"], updated["background_fit"]) == ("image", "contain")
    contain = await manager.async_photo_preview(card_id)
    assert contain != cover

    # Unsaved in the editor's preview, and back to the frame's fit.
    png, _ = await manager.async_render_preview(
        card_id, None, background=("image", None, SOURCE), background_fit="default"
    )
    assert png == cover
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background_fit="default",
    )
    assert updated["background_fit"] is None

    # Other backgrounds have no fit.
    await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background_fit="contain",
    )
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background="blue",
    )
    assert updated["background_fit"] is None
    added = await _call(
        hass,
        "add_card",
        config_entry_id=loaded_entry.entry_id,
        background="image",
        background_image=SOURCE,
        background_fit="contain",
    )
    assert added["background_fit"] == "contain"


def test_render_padding_leaves_a_border() -> None:
    canvas = canvas_for(800, 480, "landscape")
    opts = RenderOptions(fit="contain", background="black")
    plain = render(make_jpeg((250, 250, 250), size=(400, 240)), opts, canvas)
    padded = render(make_jpeg((250, 250, 250), size=(400, 240)), opts, canvas, padding=48)
    plain_px = positions_from_bmp(plain.bmp, canvas)
    padded_px = positions_from_bmp(padded.bmp, canvas)
    black = padded_px[0, 0]
    # The same aspect as the canvas: no border without padding, 48 px with it.
    assert (plain_px[:48] != black).all()
    assert (padded_px[:48] == black).all() and (padded_px[:, :80] == black).all()
    assert padded_px[240, 400] != black


async def test_card_picture_padding(hass: HomeAssistant, loaded_entry, pictures) -> None:
    manager = loaded_entry.runtime_data
    card_id = await _add_card(hass, loaded_entry, background_fit="contain")
    unpadded = await manager.async_photo_preview(card_id)
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background_padding=10,
    )
    assert updated["background_padding"] == 10
    assert await manager.async_photo_preview(card_id) != unpadded

    # Unsaved in the editor's preview.
    png, _ = await manager.async_render_preview(
        card_id,
        None,
        background=("image", None, SOURCE),
        background_fit="contain",
        background_padding=0,
    )
    assert png == unpadded

    # Only "Fit with borders" has padding.
    updated = await _call(
        hass,
        "update_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card_id,
        background_fit="cover",
    )
    assert updated["background_padding"] == 0
    with pytest.raises(vol.Invalid):
        await _call(
            hass,
            "update_photo",
            config_entry_id=loaded_entry.entry_id,
            photo_id=card_id,
            background_padding=40,
        )


async def test_panel_saves_picture_and_colour_backgrounds(
    hass: HomeAssistant, hass_ws_client, loaded_entry, pictures
) -> None:
    """The panel sends every background field, with null for the ones not in use."""
    card_id = (await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id))["photo_id"]
    ws = await hass_ws_client(hass)
    base = {
        "type": f"{DOMAIN}/photo/update",
        "entry_id": loaded_entry.entry_id,
        "photo_id": card_id,
        "name": "Garden",
        "enabled": True,
        "hide_frame_overlays": True,
    }
    await ws.send_json(
        {
            "id": 1,
            **base,
            "background": "image",
            "background_photo_id": None,
            "background_image": SOURCE,
            "background_fit": "contain",
            "background_padding": 5,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["background"] == "image"
    assert msg["result"]["background_padding"] == 5

    await ws.send_json(
        {
            "id": 2,
            **base,
            "background": "blue",
            "background_photo_id": None,
            "background_image": "",
            "background_fit": "default",
            "background_padding": 0,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert (msg["result"]["background"], msg["result"]["background_image"]) == ("blue", "")

    await ws.send_json(
        {
            "id": 3,
            "type": f"{DOMAIN}/card/add",
            "entry_id": loaded_entry.entry_id,
            "background": "image",
            "background_photo_id": None,
            "background_image": SOURCE,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
