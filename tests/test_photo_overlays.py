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


async def test_show_image_overlays_false_draws_no_frame_overlays(
    hass: HomeAssistant,
    loaded_entry,
    hass_client_no_auth,
    photo_path,
    freezer,
) -> None:
    manager = loaded_entry.runtime_data
    await _add(hass, loaded_entry, "Global", "g")
    client = await hass_client_no_auth()
    for overlays, expected in ((True, ["g"]), (False, [])):
        await hass.services.async_call(
            DOMAIN,
            "show_image",
            {
                "config_entry_id": loaded_entry.entry_id,
                "file_path": str(photo_path),
                "wakes": 1,
                "overlays": overlays,
            },
            blocking=True,
        )
        await _wake(client, freezer)
        assert manager.state.current_kind == "override"
        assert list(manager.state.overlay_texts.values()) == expected


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
    assert photos["photos"][0]["overlays_enabled"] == 2

    await call(8, type=f"{DOMAIN}/overlay/delete", overlay_id=first["overlay_id"], **scope)
    assert [o.name for o in loaded_entry.runtime_data.photos[0].overlays] == ["B"]


async def test_copy_overlays_between_photos(hass: HomeAssistant, loaded_entry, photo_path) -> None:
    manager = loaded_entry.runtime_data
    src = await _add_photo(hass, loaded_entry, photo_path)
    a = await _add_photo(hass, loaded_entry, photo_path)
    b = await _add_photo(hass, loaded_entry, photo_path)
    first = await _add(hass, loaded_entry, "One", "1", src)
    second = await _add(hass, loaded_entry, "Two", "2", src)
    await _add(hass, loaded_entry, "Existing", "e", a)
    await _add(hass, loaded_entry, "Global", "g")

    result = await _call(
        hass,
        "copy_overlays",
        config_entry_id=loaded_entry.entry_id,
        photo_id=src,
        to_photo_ids=[a, b, src],
    )
    assert result == {"copied": 4}
    photos = {p.id: p for p in manager.photos}
    assert [o.name for o in photos[a].overlays] == ["Existing", "One", "Two"]
    assert [o.name for o in photos[b].overlays] == ["One", "Two"]
    assert [o.name for o in photos[src].overlays] == ["One", "Two"]
    copied_ids = {o.id for p in (photos[a], photos[b]) for o in p.overlays if o.name != "Existing"}
    assert len(copied_ids) == 4 and copied_ids.isdisjoint({first, second})
    assert [o.name for o in manager.overlays] == ["Global"]

    await _call(
        hass,
        "copy_overlays",
        config_entry_id=loaded_entry.entry_id,
        photo_id=src,
        to_photo_ids=[a],
        replace=True,
    )
    assert [o.name for o in photos[a].overlays] == ["One", "Two"]


async def test_copy_overlays_validation(hass: HomeAssistant, loaded_entry, photo_path) -> None:
    manager = loaded_entry.runtime_data
    src = await _add_photo(hass, loaded_entry, photo_path)
    a = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "One", "1", src)
    entry_id = loaded_entry.entry_id
    with pytest.raises(ServiceValidationError):
        await _call(
            hass, "copy_overlays", config_entry_id=entry_id, photo_id=src, to_photo_ids=[a, "nope"]
        )
    with pytest.raises(ServiceValidationError):
        await _call(
            hass, "copy_overlays", config_entry_id=entry_id, photo_id="nope", to_photo_ids=[a]
        )
    with pytest.raises(ServiceValidationError):
        await _call(hass, "copy_overlays", config_entry_id=entry_id, photo_id=src)
    with pytest.raises(ServiceValidationError):
        await _call(hass, "copy_overlays", config_entry_id=entry_id)
    assert manager.photos[1].overlays == []


async def test_copy_overlays_websocket(
    hass: HomeAssistant, loaded_entry, photo_path, hass_ws_client
) -> None:
    manager = loaded_entry.runtime_data
    src = await _add_photo(hass, loaded_entry, photo_path)
    a = await _add_photo(hass, loaded_entry, photo_path)
    await _add(hass, loaded_entry, "One", "1", src)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/overlays/copy",
            "entry_id": loaded_entry.entry_id,
            "photo_id": src,
            "to_photo_ids": [a],
        }
    )
    assert (await client.receive_json())["result"] == {"copied": 1}
    assert [o.name for o in manager.photos[1].overlays] == ["One"]
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/overlays/copy", "entry_id": loaded_entry.entry_id, "photo_id": src}
    )
    assert not (await client.receive_json())["success"]


async def test_editor_preview_draws_overlays(
    hass: HomeAssistant, hass_ws_client, loaded_entry, photo_path
) -> None:
    photo_id = await _add_photo(hass, loaded_entry, photo_path)
    ws = await hass_ws_client(hass)
    ids = iter(range(1, 100))

    async def preview(**extra) -> str:
        await ws.send_json(
            {
                "id": next(ids),
                "type": f"{DOMAIN}/preview",
                "entry_id": loaded_entry.entry_id,
                "photo_id": photo_id,
                **extra,
            }
        )
        msg = await ws.receive_json()
        assert msg["success"], msg
        return msg["result"]["image"]

    plain = await preview()
    await _add(hass, loaded_entry, "Global", "Hello")
    with_global = await preview()
    assert with_global != plain
    assert await preview(hide_frame_overlays=True) == plain  # unsaved hide switch
    await _add(hass, loaded_entry, "Mine", "Mine", photo_id)
    assert await preview(hide_frame_overlays=True) not in (plain, with_global)
