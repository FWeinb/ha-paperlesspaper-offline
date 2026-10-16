"""Overlays owned by one photo, alongside the frame's global ones."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.paperlessoffline.const import DOMAIN

from .test_overlays import _call, _wake


async def _add_photo(hass, entry, path: Path) -> str:
    resp = await _call(hass, "add_photo", config_entry_id=entry.entry_id, file_path=str(path))
    return resp["photo_id"]


async def _add(hass, entry, name: str, template: str, photo_id: str | None = None) -> str:
    data = {"config_entry_id": entry.entry_id, "name": name, "template": template}
    if photo_id:
        data["photo_id"] = photo_id
    return (await _call(hass, "add_overlay", **data))["overlay_id"]


async def test_photo_overlays_are_separate_lists(
    hass: HomeAssistant,
    loaded_entry,
    photo_path,
) -> None:
    manager = loaded_entry.runtime_data
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    mine = await _add(hass, loaded_entry, "Mine", "x", photo_id)
    other = await _add(hass, loaded_entry, "Global", "y")
    second = await _add(hass, loaded_entry, "Mine 2", "z", photo_id)
    assert [o.id for o in manager.overlays] == [other]
    assert [o.id for o in manager.photos[0].overlays] == [mine, second]

    await hass.services.async_call(
        DOMAIN,
        "move_overlay",
        {
            "config_entry_id": loaded_entry.entry_id,
            "photo_id": photo_id,
            "overlay_id": second,
            "position": 0,
        },
        blocking=True,
    )
    assert [o.id for o in manager.photos[0].overlays] == [second, mine]
    listed = await _call(hass, "list_overlays", config_entry_id=loaded_entry.entry_id)
    assert [o["overlay_id"] for o in listed["overlays"]] == [other]
    listed = await _call(
        hass, "list_overlays", config_entry_id=loaded_entry.entry_id, photo_id=photo_id
    )
    assert [o["overlay_id"] for o in listed["overlays"]] == [second, mine]

    updated = await _call(
        hass,
        "update_overlay",
        config_entry_id=loaded_entry.entry_id,
        photo_id=photo_id,
        overlay_id=mine,
        anchor="top_left",
    )
    assert updated["anchor"] == "top_left"
    # A photo's overlay is not found in the global list and vice versa.
    with pytest.raises(ServiceValidationError):
        await _call(hass, "update_overlay", config_entry_id=loaded_entry.entry_id, overlay_id=mine)
    await hass.services.async_call(
        DOMAIN,
        "remove_overlay",
        {"config_entry_id": loaded_entry.entry_id, "photo_id": photo_id, "overlay_id": mine},
        blocking=True,
    )
    assert [o.id for o in manager.photos[0].overlays] == [second]
    assert [o.id for o in manager.overlays] == [other]


async def test_wake_draws_photo_then_global(
    hass: HomeAssistant,
    hass_client_no_auth,
    loaded_entry,
    photo_path,
    freezer,
) -> None:
    manager = loaded_entry.runtime_data
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "Global", "g")
    await _add(hass, loaded_entry, "Mine", "{{ photo.name }}", photo_id)
    assert "overlays" in manager.pending_changes()
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    st = manager.state
    assert list(st.overlay_texts.values()) == ["a", "g"]
    assert "overlays" not in manager.pending_changes()
    draw = manager._overlay_draw_list(
        manager._applicable_overlays("photo", manager.photos[0]), st.overlay_texts
    )
    assert [text for text, _ in draw] == ["a", "g"]

    # Editing the shown photo's overlay is pending until the next wake.
    await _call(
        hass,
        "update_overlay",
        config_entry_id=loaded_entry.entry_id,
        photo_id=photo_id,
        overlay_id=manager.photos[0].overlays[0].id,
        template="edited",
    )
    assert "overlays" in manager.pending_changes()
    await _wake(client, freezer)
    assert "overlays" not in manager.pending_changes()
    assert list(st.overlay_texts.values()) == ["edited", "g"]


async def test_hide_switch_keeps_photo_overlays(
    hass: HomeAssistant,
    hass_client_no_auth,
    loaded_entry,
    photo_path,
    freezer,
) -> None:
    manager = loaded_entry.runtime_data
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "Global", "g")
    await _add(hass, loaded_entry, "Mine", "m", photo_id)
    manager.async_set_photo_hide_overlays(photo_id, True)
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert list(manager.state.overlay_texts.values()) == ["m"]


async def test_one_off_image_gets_only_global(
    hass: HomeAssistant,
    hass_client_no_auth,
    loaded_entry,
    photo_path,
    freezer,
) -> None:
    manager = loaded_entry.runtime_data
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "Global", "{% if photo %}p{% else %}none{% endif %}")
    await _add(hass, loaded_entry, "Mine", "m", photo_id)
    await hass.services.async_call(
        DOMAIN,
        "show_image",
        {"config_entry_id": loaded_entry.entry_id, "file_path": str(photo_path), "wakes": 1},
        blocking=True,
    )
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    assert list(manager.state.overlay_texts.values()) == ["none"]
    await _wake(client, freezer)
    assert manager.state.current_kind == "photo"
    assert list(manager.state.overlay_texts.values()) == ["m", "p"]


async def test_copy_photo_copies_overlays_with_new_ids(
    hass: HomeAssistant,
    loaded_entry,
    config_entry_factory,
    photo_path,
) -> None:
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    mine = await _add(hass, loaded_entry, "Mine", "m", photo_id)
    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    copy = await _call(
        hass,
        "copy_photo",
        config_entry_id=loaded_entry.entry_id,
        photo_id=photo_id,
        target_config_entry_id=other.entry_id,
    )
    copied = other.runtime_data.get_photo(copy["photo_id"])
    assert [o.name for o in copied.overlays] == ["Mine"]
    assert copied.overlays[0].id != mine
    assert other.runtime_data.overlays == []


async def test_photo_overlays_survive_storage_and_preview(
    hass: HomeAssistant,
    loaded_entry,
    photo_path,
) -> None:
    manager = loaded_entry.runtime_data
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "Mine", "{{ photo.name }}", photo_id)
    await manager.store.async_save()
    await manager.store.async_load()
    assert [o.template for o in manager.photos[0].overlays] == ["{{ photo.name }}"]

    bare, _ = await manager.async_overlay_preview(photo_id, [], for_photo=True)
    drawn, results = await manager.async_overlay_preview(photo_id)
    assert bare != drawn
    assert [r["text"] for r in results.values()] == ["a"]


async def test_photo_overlay_websocket(
    hass: HomeAssistant, hass_ws_client, loaded_entry, photo_path
) -> None:
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    ws = await hass_ws_client(hass)
    entry_id = loaded_entry.entry_id

    async def call(msg_id: int, **payload):
        await ws.send_json({"id": msg_id, **payload})
        msg = await ws.receive_json()
        assert msg["success"], msg
        return msg["result"]

    scope = {"entry_id": entry_id, "photo_id": photo_id}
    first = await call(
        1,
        type=f"{DOMAIN}/overlay/save",
        overlay={"name": "A", "template": "{{ photo.name }}"},
        **scope,
    )
    second = await call(
        2, type=f"{DOMAIN}/overlay/save", overlay={"name": "B", "template": "b"}, **scope
    )
    assert loaded_entry.runtime_data.overlays == []
    listing = await call(3, type=f"{DOMAIN}/overlays", **scope)
    assert [o["name"] for o in listing["overlays"]] == ["A", "B"]
    assert (await call(4, type=f"{DOMAIN}/overlays", entry_id=entry_id))["overlays"] == []

    await call(
        5,
        type=f"{DOMAIN}/overlay/reorder",
        order=[second["overlay_id"], first["overlay_id"]],
        **scope,
    )
    preview = await call(
        6,
        type=f"{DOMAIN}/overlay/preview",
        for_photo=True,
        overlays=[{"id": first["overlay_id"]}, {"id": second["overlay_id"]}],
        **scope,
    )
    assert [r["text"] for r in preview["results"].values()] == ["a", "b"]
    photos = await call(7, type=f"{DOMAIN}/photos", entry_id=entry_id)
    assert photos["photos"][0]["overlay_count"] == 2

    await call(8, type=f"{DOMAIN}/overlay/delete", overlay_id=first["overlay_id"], **scope)
    assert [o.name for o in loaded_entry.runtime_data.photos[0].overlays] == ["B"]
