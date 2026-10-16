"""Text cards: library items without a file, drawn from their overlays on a background."""

from __future__ import annotations

import base64
from datetime import timedelta
import io
from pathlib import Path

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from PIL import Image
import pytest

from custom_components.paperlessoffline.const import DOMAIN
from custom_components.paperlessoffline.render.overlay import SIZES
from custom_components.paperlessoffline.store import LibraryItem

from .conftest import TOKEN, make_jpeg

SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"
IMAGE_URL = f"/api/paperlessoffline/{TOKEN}/image.bmp"


async def _call(hass: HomeAssistant, service: str, **data):
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=True
    )


async def _run(hass: HomeAssistant, service: str, **data) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)


async def _add_photo(hass: HomeAssistant, entry, path: Path, **extra) -> str:
    resp = await _call(
        hass, "add_photo", config_entry_id=entry.entry_id, file_path=str(path), **extra
    )
    return resp["photo_id"]


async def _add_card(hass: HomeAssistant, entry, **data) -> dict:
    return await _call(hass, "add_card", config_entry_id=entry.entry_id, **data)


async def _wake(client, freezer: FrozenDateTimeFactory) -> Image.Image:
    freezer.tick(timedelta(minutes=61))
    await client.get(SETTINGS_URL)
    image = await client.get(IMAGE_URL)
    return Image.open(io.BytesIO(await image.read())).convert("RGB")


def _colors(img: Image.Image) -> set[tuple[int, int, int]]:
    return {c for _, c in img.getcolors(maxcolors=1 << 16)}


@pytest.fixture
def photo_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    (tmp_path / "red.jpg").write_bytes(make_jpeg((255, 0, 0), size=(800, 480)))
    (tmp_path / "blue.jpg").write_bytes(make_jpeg((0, 0, 255), size=(800, 480)))
    return tmp_path


# ------------------------------------------------------------------ model


def test_older_stores_load_as_photos() -> None:
    photo = LibraryItem.from_dict(
        {"id": "a", "filename": "a.jpg", "name": "A", "sha256": "x", "added": "2026"}
    )
    assert photo.kind == "photo"
    assert photo.background == "white"
    assert photo.background_photo_id is None


def test_xxl_size_preset() -> None:
    assert SIZES["xxl"] == 72


async def test_presets(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    blank = await _add_card(hass, loaded_entry, name="Empty")
    assert blank["kind"] == "card"
    assert blank["background"] == "white"
    assert blank["overlay_count"] == 0
    assert blank["hide_frame_overlays"] is True
    assert blank["enabled"] is True

    info = await _add_card(hass, loaded_entry, name="Info", preset="info", background="black")
    card = manager.get_photo(info["photo_id"])
    title, values = card.overlays
    assert (title.anchor, title.size, title.template) == ("top_center", "l", "# {{ frame.name }}")
    assert values.anchor == "center"
    assert values.size == "m"
    assert "date_local(now(), 'long')" in values.template
    assert "Add your values here" in values.template

    notice = await _add_card(hass, loaded_entry, name="N", preset="notice", background="red")
    (only,) = manager.get_photo(notice["photo_id"]).overlays
    assert (only.template, only.size, only.anchor, only.align, only.backing) == (
        "Notice",
        "xxl",
        "center",
        "center",
        "none",
    )
    # Readable on the chosen background.
    assert only.text_color == "white"

    # New cards go to the end of the order, like photos.
    assert [p.id for p in manager.photos] == [
        blank["photo_id"],
        info["photo_id"],
        notice["photo_id"],
    ]


async def test_presets_in_german(hass: HomeAssistant, loaded_entry) -> None:
    hass.config.language = "de"
    manager = loaded_entry.runtime_data
    notice = await _add_card(hass, loaded_entry, name="N", preset="notice")
    assert manager.get_photo(notice["photo_id"]).overlays[0].template == "Hinweis"
    info = await _add_card(hass, loaded_entry, name="I", preset="info")
    assert "Hier eigene Werte eintragen" in manager.get_photo(info["photo_id"]).overlays[1].template


async def test_add_card_validation(hass: HomeAssistant, loaded_entry, photo_dir) -> None:
    with pytest.raises(ServiceValidationError):
        await _add_card(hass, loaded_entry, name="X", background="photo")
    with pytest.raises(ServiceValidationError):
        await _add_card(
            hass, loaded_entry, name="X", background="photo", background_photo_id="missing"
        )
    card = await _add_card(hass, loaded_entry, name="Card")
    with pytest.raises(ServiceValidationError):
        # A card can't be the background of another card.
        await _add_card(
            hass,
            loaded_entry,
            name="X",
            background="photo",
            background_photo_id=card["photo_id"],
        )


# --------------------------------------------------------------- rendering


async def test_plain_background_is_not_dithered(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    await _add_card(hass, loaded_entry, name="Blue", background="blue")
    client = await hass_client_no_auth()
    img = await _wake(client, freezer)
    assert _colors(img) == {(0, 0, 255)}


async def test_card_text_is_crisp(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    await _add_card(hass, loaded_entry, name="N", preset="notice", background="yellow")
    client = await hass_client_no_auth()
    img = await _wake(client, freezer)
    assert _colors(img) == {(255, 255, 0), (0, 0, 0)}


async def test_photo_background_reuses_photo_render(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", dither="none", enabled=False)
    # The photo's own overlays are not drawn on the card.
    await _call(
        hass,
        "add_overlay",
        config_entry_id=loaded_entry.entry_id,
        photo_id=red,
        name="Caption",
        template="Photo caption",
    )
    card = await _add_card(
        hass, loaded_entry, name="On red", background="photo", background_photo_id=red
    )
    assert card["background_photo_id"] == red
    assert manager.photo_key(manager.get_photo(card["photo_id"])) == manager.photo_key(
        manager.get_photo(red)
    )
    client = await hass_client_no_auth()
    img = await _wake(client, freezer)
    assert _colors(img) == {(255, 0, 0)}


async def test_deleting_background_photo_turns_cards_white(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", enabled=False)
    card = await _add_card(
        hass, loaded_entry, name="On red", background="photo", background_photo_id=red
    )
    await _run(hass, "remove_photo", config_entry_id=loaded_entry.entry_id, photo_id=red)
    stored = manager.get_photo(card["photo_id"])
    assert (stored.background, stored.background_photo_id) == ("white", None)
    client = await hass_client_no_auth()
    assert _colors(await _wake(client, freezer)) == {(255, 255, 255)}


async def test_card_variables(hass: HomeAssistant, loaded_entry, photo_dir) -> None:
    manager = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg")
    card = await _add_card(
        hass, loaded_entry, name="Hello", background="photo", background_photo_id=red
    )
    overlay = await _call(
        hass,
        "add_overlay",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card["photo_id"],
        name="Vars",
        template="{{ photo.name }}|{{ photo.date }}|{{ photo.location }}",
    )
    stored = manager.get_photo(card["photo_id"])
    text, error = manager.evaluate_overlay(
        manager.require_overlay(overlay["overlay_id"], stored.id),
        manager.template_variables(stored),
    )
    assert error is None
    assert text == "Hello|None|None"


async def test_card_thumbnail_is_its_preview(
    hass: HomeAssistant, hass_client, loaded_entry
) -> None:
    card = await _add_card(hass, loaded_entry, name="N", preset="notice", background="green")
    client = await hass_client()
    resp = await client.get(
        f"/api/paperlessoffline/thumb/{loaded_entry.entry_id}/{card['photo_id']}.jpg"
    )
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "image/png"
    img = Image.open(io.BytesIO(await resp.read())).convert("RGB")
    assert len(_colors(img)) == 2  # background plus the text
    resp = await client.get(
        f"/api/paperlessoffline/preview/{loaded_entry.entry_id}/{card['photo_id']}.png"
    )
    assert resp.status == 200


# ---------------------------------------------------------------- rotation


async def test_card_in_rotation(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", dither="none")
    card = (await _add_card(hass, loaded_entry, name="Black", background="black"))["photo_id"]
    client = await hass_client_no_auth()
    assert _colors(await _wake(client, freezer)) == {(255, 0, 0)}
    listed = await _call(hass, "list_photos", config_entry_id=loaded_entry.entry_id)
    assert listed["up_next"] == {"kind": "photo", "photo_id": card}
    assert [p["kind"] for p in listed["photos"]] == ["photo", "card"]
    assert _colors(await _wake(client, freezer)) == {(0, 0, 0)}
    assert manager.state.current_id == card

    # Skip passes over the card; show_photo brings it back.
    assert manager.up_next() == ("photo", red)
    await _run(hass, "show_photo", config_entry_id=loaded_entry.entry_id, photo_id=card)
    assert manager.up_next() == ("photo", card)
    await _run(hass, "next_photo", config_entry_id=loaded_entry.entry_id)
    assert manager.up_next() == ("photo", red)

    # The eye toggle takes it out of the rotation.
    await _call(
        hass, "update_photo", config_entry_id=loaded_entry.entry_id, photo_id=card, enabled=False
    )
    assert manager.enabled_ids() == [red]


async def test_card_in_shuffle(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    hass.config_entries.async_update_entry(
        loaded_entry, options={**loaded_entry.options, "order": "shuffle"}
    )
    await hass.async_block_till_done()
    manager = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg")
    card = (await _add_card(hass, loaded_entry, name="Card"))["photo_id"]
    client = await hass_client_no_auth()
    seen = set()
    for _ in range(2):
        await _wake(client, freezer)
        seen.add(manager.state.current_id)
    assert seen == {red, card}


# ------------------------------------------------------------------ update


async def test_update_card_background(hass: HomeAssistant, loaded_entry, photo_dir) -> None:
    manager = loaded_entry.runtime_data
    entry_id = loaded_entry.entry_id
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg")
    card = (await _add_card(hass, loaded_entry, name="Card"))["photo_id"]

    resp = await _call(
        hass, "update_photo", config_entry_id=entry_id, photo_id=card, background="red"
    )
    assert resp["background"] == "red"
    resp = await _call(
        hass, "update_photo", config_entry_id=entry_id, photo_id=card, background_photo_id=red
    )
    assert (resp["background"], resp["background_photo_id"]) == ("photo", red)
    resp = await _call(
        hass, "update_photo", config_entry_id=entry_id, photo_id=card, background="black"
    )
    assert (resp["background"], resp["background_photo_id"]) == ("black", None)
    assert manager.get_photo(card).overrides == {}

    # Cards have no render settings; photos have no card background.
    with pytest.raises(ServiceValidationError):
        await _call(hass, "update_photo", config_entry_id=entry_id, photo_id=card, dither="none")
    with pytest.raises(ServiceValidationError):
        await _call(
            hass, "update_photo", config_entry_id=entry_id, photo_id=red, background_photo_id=red
        )
    with pytest.raises(ServiceValidationError):
        await _call(hass, "update_photo", config_entry_id=entry_id, photo_id=red, background="red")
    # On a photo, background is still its render setting.
    resp = await _call(
        hass, "update_photo", config_entry_id=entry_id, photo_id=red, background="black"
    )
    assert resp["overrides"] == {"background": "black"}


# -------------------------------------------------------------------- copy


async def test_copy_card_with_background_photo(
    hass: HomeAssistant, loaded_entry, photo_dir, config_entry_factory
) -> None:
    source = loaded_entry.runtime_data
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", dither="atkinson")
    card = await _add_card(
        hass,
        loaded_entry,
        name="On red",
        preset="notice",
        background="photo",
        background_photo_id=red,
    )
    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    target = other.runtime_data

    copied = await _call(
        hass,
        "copy_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card["photo_id"],
        target_config_entry_id=other.entry_id,
    )
    assert copied["kind"] == "card"
    assert copied["name"] == "On red"
    background, copy = target.photos
    assert background.kind == "photo"
    assert background.sha256 == source.get_photo(red).sha256
    assert background.enabled is False
    assert background.overrides == {"dither": "atkinson"}
    assert copy.background_photo_id == background.id
    assert [o.template for o in copy.overlays] == ["Notice"]
    assert copy.overlays[0].id != source.get_photo(card["photo_id"]).overlays[0].id

    # A second copy reuses the background photo already there.
    again = await _call(
        hass,
        "copy_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card["photo_id"],
        target_config_entry_id=other.entry_id,
    )
    assert len(target.photos) == 3
    assert again["background_photo_id"] == background.id


async def test_copy_plain_card(hass: HomeAssistant, loaded_entry, config_entry_factory) -> None:
    card = await _add_card(hass, loaded_entry, name="Plain", background="blue", preset="info")
    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    copied = await _call(
        hass,
        "copy_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card["photo_id"],
        target_config_entry_id=other.entry_id,
    )
    assert (copied["kind"], copied["background"], copied["overlay_count"]) == ("card", "blue", 2)
    assert len(other.runtime_data.photos) == 1


# -------------------------------------------------------------- housekeeping


async def test_removing_card_and_housekeeping(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    card = (await _add_card(hass, loaded_entry, name="Card", preset="notice"))["photo_id"]
    await manager.async_housekeeping()
    await _run(hass, "remove_photo", config_entry_id=loaded_entry.entry_id, photo_id=card)
    assert manager.photos == []
    await manager.async_housekeeping()


# --------------------------------------------------------------- websocket


async def test_websocket_cards(
    hass: HomeAssistant, hass_ws_client, loaded_entry, photo_dir
) -> None:
    red = await _add_photo(hass, loaded_entry, photo_dir / "red.jpg")
    ws = await hass_ws_client(hass)
    entry_id = loaded_entry.entry_id
    await ws.send_json(
        {"id": 1, "type": f"{DOMAIN}/card/add", "entry_id": entry_id, "preset": "notice"}
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    card = msg["result"]
    assert (card["kind"], card["name"], card["background"]) == ("card", "Notice", "white")
    assert card["thumb_url"]

    await ws.send_json(
        {
            "id": 2,
            "type": f"{DOMAIN}/photo/update",
            "entry_id": entry_id,
            "photo_id": card["photo_id"],
            "background": "photo",
            "background_photo_id": red,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    assert msg["result"]["background_photo_id"] == red

    await ws.send_json({"id": 3, "type": f"{DOMAIN}/photos", "entry_id": entry_id})
    msg = await ws.receive_json()
    assert [p["kind"] for p in msg["result"]["photos"]] == ["photo", "card"]
    assert "background" not in msg["result"]["photos"][0]

    # The overlay editor previews a card on its background.
    await ws.send_json(
        {
            "id": 4,
            "type": f"{DOMAIN}/overlay/preview",
            "entry_id": entry_id,
            "photo_id": card["photo_id"],
            "for_photo": True,
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    (result,) = msg["result"]["results"].values()
    assert result["text"] == "Notice"


async def test_websocket_preview_with_unsaved_background(
    hass: HomeAssistant, hass_ws_client, loaded_entry
) -> None:
    manager = loaded_entry.runtime_data
    card = (await _add_card(hass, loaded_entry, name="Card"))["photo_id"]
    ws = await hass_ws_client(hass)
    await ws.send_json(
        {
            "id": 1,
            "type": f"{DOMAIN}/preview",
            "entry_id": loaded_entry.entry_id,
            "photo_id": card,
            "background": "green",
        }
    )
    msg = await ws.receive_json()
    assert msg["success"], msg
    png = base64.b64decode(msg["result"]["image"].split(",", 1)[1])
    img = Image.open(io.BytesIO(png)).convert("RGB")
    assert len(_colors(img)) == 1
    assert img.getpixel((0, 0)) != (255, 255, 255)
    assert manager.get_photo(card).background == "white"  # not saved
