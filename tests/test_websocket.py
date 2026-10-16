"""Websocket API, upload endpoint and panel registration."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from homeassistant.core import HomeAssistant
from PIL import Image

from custom_components.paperlessoffline.const import DOMAIN
from custom_components.paperlessoffline.frontend import async_register_frontend

from .conftest import make_jpeg


async def _upload(hass_client, entry_id: str, *files: tuple[str, bytes]):
    client = await hass_client()
    form = aiohttp.FormData()
    for name, data in files:
        form.add_field("file", data, filename=name, content_type="image/jpeg")
    return await client.post(f"/api/{DOMAIN}/upload/{entry_id}", data=form)


async def test_upload_and_list(
    hass: HomeAssistant, hass_client, hass_ws_client, loaded_entry
) -> None:
    resp = await _upload(
        hass_client,
        loaded_entry.entry_id,
        ("beach.jpg", make_jpeg()),
        ("notes.jpg", b"not an image"),
    )
    assert resp.status == 200
    body = await resp.json()
    assert [p["name"] for p in body["added"]] == ["beach"]
    assert body["errors"][0]["file"] == "notes.jpg"

    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/photos", "entry_id": loaded_entry.entry_id})
    msg = await ws.receive_json()
    assert msg["success"]
    photo = msg["result"]["photos"][0]
    assert photo["name"] == "beach"
    assert "authSig=" in photo["thumb_url"]

    client = await hass_client()
    resp = await client.get(photo["display_urls"]["90"])
    assert resp.status == 200
    img = Image.open(io.BytesIO(await resp.read()))
    assert img.height > img.width  # landscape original rotated 90°


async def test_upload_unknown_frame(hass: HomeAssistant, hass_client, loaded_entry) -> None:
    resp = await _upload(hass_client, "nope", ("a.jpg", make_jpeg()))
    assert resp.status == 404


async def test_frames_and_editing(
    hass: HomeAssistant, hass_ws_client, loaded_entry, tmp_path: Path
) -> None:
    manager = loaded_entry.runtime_data
    a = await manager.async_add_photo(make_jpeg((200, 0, 0)), "a")
    b = await manager.async_add_photo(make_jpeg((0, 0, 200)), "b")
    ws = await hass_ws_client(hass)
    entry_id = loaded_entry.entry_id

    async def call(msg_id: int, **payload):
        await ws.send_json({"id": msg_id, **payload})
        result = await ws.receive_json()
        assert result["success"], result
        return result["result"]

    frames = await call(1, type=f"{DOMAIN}/frames")
    frame = frames["frames"][0]
    assert frame["title"] == "Kitchen"
    assert frame["up_next"]["photo_id"] == a.id
    assert frame["photo_count"] == 2

    updated = await call(
        2,
        type=f"{DOMAIN}/photo/update",
        entry_id=entry_id,
        photo_id=a.id,
        name="Apple",
        overrides={"dither": "atkinson", "crop": [0, 0, 0.5, 1]},
    )
    assert updated["name"] == "Apple"
    assert updated["overrides"] == {"dither": "atkinson", "crop": [0, 0, 0.5, 1]}

    await call(3, type=f"{DOMAIN}/photo/reorder", entry_id=entry_id, order=[b.id, a.id])
    assert [p.id for p in manager.photos] == [b.id, a.id]

    await call(4, type=f"{DOMAIN}/photo/show", entry_id=entry_id, photo_id=a.id)
    assert manager.state.queued_id == a.id
    await call(5, type=f"{DOMAIN}/frame/skip", entry_id=entry_id)

    frame = await call(
        6,
        type=f"{DOMAIN}/frame/update",
        entry_id=entry_id,
        order="shuffle",
        mounting="landscape",
        interval=600,
        render_defaults={"palette": "pure", "saturation": 1.2},
    )
    assert frame["order"] == "shuffle"
    assert frame["canvas"] == {"width": 800, "height": 480}
    assert loaded_entry.options["render_defaults"] == {"palette": "pure", "saturation": 1.2}

    preview = await call(
        7,
        type=f"{DOMAIN}/preview",
        entry_id=entry_id,
        photo_id=a.id,
        overrides={"dither": "bayer"},
        frame_defaults={},
    )
    assert preview["image"].startswith("data:image/png;base64,")
    assert (preview["width"], preview["height"]) == (800, 480)

    defaults = await call(8, type=f"{DOMAIN}/defaults/set", defaults={"dither": "sierra2"})
    assert defaults["defaults"] == {"dither": "sierra2"}
    got = await call(9, type=f"{DOMAIN}/defaults")
    assert got["defaults"] == {"dither": "sierra2"}
    assert got["builtin"]["palette"] == "perceived"

    await call(10, type=f"{DOMAIN}/photo/delete", entry_id=entry_id, photo_id=b.id)
    assert [p.id for p in manager.photos] == [a.id]

    await ws.send_json(
        {"id": 11, "type": f"{DOMAIN}/photo/delete", "entry_id": entry_id, "photo_id": "zzz"}
    )
    msg = await ws.receive_json()
    assert not msg["success"]


async def test_copy_and_import(
    hass: HomeAssistant, hass_ws_client, loaded_entry, config_entry_factory, tmp_path: Path
) -> None:
    manager = loaded_entry.runtime_data
    photo = await manager.async_add_photo(make_jpeg(), "x", {"saturation": 1.5})
    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    ws = await hass_ws_client(hass)
    await ws.send_json(
        {
            "id": 1,
            "type": f"{DOMAIN}/photo/copy",
            "entry_id": loaded_entry.entry_id,
            "photo_id": photo.id,
            "target_entry_id": other.entry_id,
        }
    )
    msg = await ws.receive_json()
    assert msg["result"]["overrides"] == {"saturation": 1.5}

    with patch(
        "custom_components.paperlessoffline.websocket.async_fetch_source",
        AsyncMock(return_value=(make_jpeg(), "sunset")),
    ):
        await ws.send_json(
            {
                "id": 2,
                "type": f"{DOMAIN}/import",
                "entry_id": loaded_entry.entry_id,
                "media_content_id": "media-source://media_source/local/sunset.jpg",
            }
        )
        msg = await ws.receive_json()
    assert msg["result"]["name"] == "sunset"


async def test_subscribe(hass: HomeAssistant, hass_ws_client, loaded_entry) -> None:
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["success"]
    manager = loaded_entry.runtime_data
    await manager.async_add_photo(make_jpeg(), "x")
    event = await ws.receive_json()
    assert event["type"] == "event"
    assert event["event"]["entry_id"] == loaded_entry.entry_id


async def test_non_admin_rejected(
    hass: HomeAssistant, hass_ws_client, hass_admin_user, loaded_entry
) -> None:
    hass_admin_user.groups = []
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/frames"})
    msg = await ws.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"


async def test_register_frontend(hass: HomeAssistant, tmp_path: Path) -> None:
    # Skipped silently without the frontend.
    await async_register_frontend(hass)

    # The bundles are build output (not committed), so stand in dummies.
    for name in ("paperlessoffline-panel.js", "paperlessoffline-card.js"):
        (tmp_path / name).write_text("export {};")

    hass.config.components.add("frontend")
    frontend = MagicMock(DATA_PANELS="frontend_panels")
    panel_custom = MagicMock(async_register_panel=AsyncMock())
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    with (
        patch.dict(
            "sys.modules",
            {
                "homeassistant.components.frontend": frontend,
                "homeassistant.components.panel_custom": panel_custom,
            },
        ),
        patch("homeassistant.components.frontend", frontend, create=True),
        patch("homeassistant.components.panel_custom", panel_custom, create=True),
        patch("custom_components.paperlessoffline.frontend.FRONTEND_DIR", tmp_path),
    ):
        await async_register_frontend(hass)
    kwargs = panel_custom.async_register_panel.call_args.kwargs
    assert kwargs["frontend_url_path"] == DOMAIN
    assert kwargs["require_admin"] is True
    assert kwargs["module_url"].startswith(f"/{DOMAIN}_static/paperlessoffline-panel.js?v=")
    card_url = frontend.add_extra_js_url.call_args.args[1]
    assert card_url.startswith(f"/{DOMAIN}_static/paperlessoffline-card.js?v=")
