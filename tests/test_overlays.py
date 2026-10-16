"""Overlays: markdown engine, fonts, compositing, templates, wakes, actions."""

from __future__ import annotations

from datetime import datetime, timedelta
import io

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import numpy as np
from PIL import Image
import pytest

from custom_components.paperlessoffline.const import DOMAIN
from custom_components.paperlessoffline.render import (
    OverlayStyle,
    RenderOptions,
    canvas_for,
    composite,
    render,
)
from custom_components.paperlessoffline.render.overlay import (
    COLORS,
    SENTINEL,
    draw_overlay,
    icon_char,
    new_layer,
    parse_inline,
    parse_markdown,
    segments,
)
from custom_components.paperlessoffline.render.pipeline import finish, positions_from_bmp
from custom_components.paperlessoffline.templates import (
    is_truthy,
    make_date_local,
    make_entity_icon,
    weather_icon,
)

from .conftest import TOKEN, make_jpeg

SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"
IMAGE_URL = f"/api/paperlessoffline/{TOKEN}/image.bmp"


# ------------------------------------------------------------------ engine


def test_parse_inline_styles() -> None:
    runs = parse_inline("a **b *c*** {red}d{/red} :mdi:thermometer: \\*e")
    assert [(r.text, r.bold, r.italic, r.color, r.icon) for r in runs] == [
        ("a ", False, False, None, None),
        ("b ", True, False, None, None),
        ("c", True, True, None, None),
        (" ", False, False, None, None),
        ("d", False, False, "red", None),
        (" ", False, False, None, None),
        ("", False, False, None, "thermometer"),
        (" *e", False, False, None, None),
    ]


def test_parse_markdown_blocks() -> None:
    lines = parse_markdown("\n# Title\n\n\n- one\n* two\nplain\n\n")
    assert [(line.kind, line.level) for line in lines] == [
        ("heading", 1),
        ("blank", 0),
        ("bullet", 0),
        ("bullet", 0),
        ("text", 0),
    ]
    assert lines[0].runs[0].bold


def test_icons_and_fallback_fonts() -> None:
    assert icon_char("thermometer") == icon_char("mdi:thermometer") is not None
    assert icon_char("no-such-icon-xyz") is None
    parts = segments("7.5↓", 24, False, False)
    assert [text for text, _ in parts] == ["7.5", "↓"]
    assert parts[0][1] is not parts[1][1]


def _drawn(layer: Image.Image) -> np.ndarray:
    return ~(np.asarray(layer) == SENTINEL).all(axis=2)


@pytest.mark.parametrize(("w", "h"), [(480, 800), (800, 480)])
@pytest.mark.parametrize(
    ("anchor", "quadrant"),
    [
        ("top_left", (0, 0)),
        ("top_right", (0, 1)),
        ("bottom_left", (1, 0)),
        ("bottom_right", (1, 1)),
    ],
)
def test_anchor_positions(w, h, anchor, quadrant) -> None:
    layer = new_layer(w, h)
    box = draw_overlay(layer, "**21.4 °C**", OverlayStyle(anchor=anchor))
    assert box is not None
    cy, cx = (box[1] + box[3]) / 2, (box[0] + box[2]) / 2
    assert (int(cy > h / 2), int(cx > w / 2)) == quadrant


def test_only_palette_colours_and_wrapping() -> None:
    layer = new_layer(480, 800)
    text = "# Heading\nA long line of text that certainly has to wrap {blue}*somewhere*{/blue} ↓\n- item"
    box = draw_overlay(layer, text, OverlayStyle(anchor="center", width=50, backing="box"))
    assert box is not None
    assert box[2] - box[0] <= 241
    colours = {tuple(c) for c in np.asarray(layer).reshape(-1, 3).tolist()}
    assert colours <= {*COLORS.values(), SENTINEL}


def test_halo_and_empty() -> None:
    layer = new_layer(400, 200)
    assert draw_overlay(layer, "   \n\n", OverlayStyle()) is None
    draw_overlay(layer, "Hi", OverlayStyle(anchor="center", backing="halo", text_color="white"))
    colours = {tuple(c) for c in np.asarray(layer)[_drawn(layer)].tolist()}
    assert colours == {COLORS["white"], COLORS["black"]}


@pytest.mark.parametrize(
    "mounting", ["portrait", "landscape", "portrait_flipped", "landscape_flipped"]
)
def test_bmp_roundtrip_and_composite(mounting) -> None:
    canvas = canvas_for(800, 480, mounting)
    base = render(make_jpeg((20, 120, 30), size=(400, 300)), RenderOptions(), canvas)
    positions = positions_from_bmp(base.bmp, canvas)
    assert finish(positions.copy(), canvas).bmp == base.bmp
    out = composite(base.bmp, [("**X**", OverlayStyle(anchor="top_left", size="xl"))], canvas)
    after = positions_from_bmp(out.bmp, canvas)
    changed = after != positions
    assert changed.any()
    ys, xs = np.nonzero(changed)
    assert ys.max() < canvas.height / 2 and xs.max() < canvas.width / 2


# --------------------------------------------------------------- templates


def test_weather_icon_and_truthy() -> None:
    assert weather_icon("partlycloudy") == ":mdi:weather-partly-cloudy:"
    assert weather_icon("nonsense") == ""
    assert is_truthy(" yes ") and is_truthy("3.2")
    assert not any(is_truthy(v) for v in ("", "False", "0", "off", "unknown", "unavailable"))


async def test_date_local(hass: HomeAssistant) -> None:
    moment = datetime(2026, 10, 14, 18, 5)
    fmt = make_date_local(hass)
    hass.config.language = "en"
    assert fmt(moment, "long") == "Wednesday, October 14, 2026"
    assert fmt(moment, "short") == "Oct 14, 2026"
    hass.config.language = "de"
    assert fmt(moment, "long") == "Mittwoch, 14. Oktober 2026"
    assert fmt(moment, "short") == "14.10.2026"
    assert fmt(moment, "month_year") == "Oktober 2026"
    assert fmt(moment, "weekday") == "Mittwoch"
    assert fmt(moment, "time") == "18:05"
    assert fmt("2026-03-01", "month_year") == "März 2026"
    assert fmt("garbage", "long") == ""


async def test_entity_icon(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.door", "on", {"icon": "mdi:door-open"})
    hass.states.async_set("sensor.plain", "1")
    icon = make_entity_icon(hass)
    assert icon("sensor.door") == ":mdi:door-open:"
    assert icon("sensor.plain") == ""


# ---------------------------------------------------------- frame behaviour


async def _call(hass, service, **data):
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=True
    )


async def _setup_overlay(hass, entry, photo_path, **extra) -> str:
    await hass.services.async_call(
        DOMAIN,
        "add_photo",
        {"config_entry_id": entry.entry_id, "file_path": str(photo_path)},
        blocking=True,
    )
    resp = await _call(
        hass,
        "add_overlay",
        config_entry_id=entry.entry_id,
        name="Temperature",
        template="**{{ states('sensor.t') }} °C**",
        **extra,
    )
    return resp["overlay_id"]


async def _wake(client, freezer, minutes: int = 61):
    freezer.tick(timedelta(minutes=minutes))
    await client.get(SETTINGS_URL)
    probe = await client.get(IMAGE_URL)
    image = await client.get(IMAGE_URL)
    assert probe.headers["Last-Modified"] == image.headers["Last-Modified"]
    return image


async def _texts(hass, entry) -> dict:
    resp = await _call(hass, "list_overlays", config_entry_id=entry.entry_id)
    return {o["name"]: (o["last_text"], o["last_error"]) for o in resp["overlays"]}


async def test_overlay_updates_when_value_changes(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, freezer
) -> None:
    hass.states.async_set("sensor.t", "21.4")
    await _setup_overlay(hass, loaded_entry, photo_path)
    assert "overlays" in loaded_entry.runtime_data.pending_changes()
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry))["Temperature"] == ("**21.4 °C**", None)
    assert "overlays" not in loaded_entry.runtime_data.pending_changes()

    same = await _wake(client, freezer)
    assert same.headers["Last-Modified"] == first.headers["Last-Modified"]

    hass.states.async_set("sensor.t", "19.0")
    changed = await _wake(client, freezer)
    assert changed.headers["Last-Modified"] != first.headers["Last-Modified"]
    assert (await _texts(hass, loaded_entry))["Temperature"][0] == "**19.0 °C**"

    # The overlay really is on the image: it differs from the bare photo.
    bare = await loaded_entry.runtime_data.async_photo_preview(
        loaded_entry.runtime_data.photos[0].id
    )
    served = await loaded_entry.runtime_data.async_preview("showing")
    assert bare != served


async def test_photo_redraw_policy_keeps_text(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, freezer
) -> None:
    hass.states.async_set("sensor.t", "21.4")
    await _setup_overlay(hass, loaded_entry, photo_path, redraw="photo")
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    hass.states.async_set("sensor.t", "5.0")
    again = await _wake(client, freezer)  # same single photo: text kept
    assert again.headers["Last-Modified"] == first.headers["Last-Modified"]
    assert (await _texts(hass, loaded_entry))["Temperature"][0] == "**21.4 °C**"


async def test_errors_show_if_and_hide(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, freezer
) -> None:
    hass.states.async_set("sensor.t", "21.4")
    overlay_id = await _setup_overlay(hass, loaded_entry, photo_path)
    await _call(
        hass,
        "add_overlay",
        config_entry_id=loaded_entry.entry_id,
        name="Broken",
        template="{{ states('sensor.t') | nonexistent_filter }}",
    )
    client = await hass_client_no_auth()
    image = await _wake(client, freezer)
    assert image.status == 200
    texts = await _texts(hass, loaded_entry)
    assert texts["Broken"][0] is None and texts["Broken"][1]
    assert texts["Temperature"][0] == "**21.4 °C**"

    await _call(
        hass,
        "update_overlay",
        config_entry_id=loaded_entry.entry_id,
        overlay_id=overlay_id,
        show_if="{{ states('sensor.t') | float > 30 }}",
    )
    await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry))["Temperature"] == (None, None)

    # Photos can opt out of frame overlays entirely.
    photo_id = loaded_entry.runtime_data.photos[0].id
    await hass.services.async_call(
        DOMAIN,
        "update_photo",
        {
            "config_entry_id": loaded_entry.entry_id,
            "photo_id": photo_id,
            "hide_frame_overlays": True,
        },
        blocking=True,
    )
    await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry)) == {
        "Temperature": (None, None),
        "Broken": (None, None),
    }


async def test_overlay_management_actions(
    hass: HomeAssistant, loaded_entry, config_entry_factory, photo_path
) -> None:
    entry_id = loaded_entry.entry_id
    first = await _setup_overlay(hass, loaded_entry, photo_path)
    second = (
        await _call(hass, "add_overlay", config_entry_id=entry_id, name="Date", template="x")
    )["overlay_id"]
    await hass.services.async_call(
        DOMAIN,
        "move_overlay",
        {"config_entry_id": entry_id, "overlay_id": second, "position": 0},
        blocking=True,
    )
    assert [o.id for o in loaded_entry.runtime_data.overlays] == [second, first]
    updated = await _call(
        hass,
        "update_overlay",
        config_entry_id=entry_id,
        overlay_id=first,
        anchor="top_left",
        width=40,
    )
    assert updated["anchor"] == "top_left" and updated["width"] == 40

    other = await config_entry_factory("epd13-aabbccddeeff", "Hall")
    assert (
        await _call(
            hass, "copy_overlays", config_entry_id=entry_id, target_config_entry_id=other.entry_id
        )
    ) == {"copied": 2}
    assert [o.name for o in other.runtime_data.overlays] == ["Date", "Temperature"]
    assert {o.id for o in other.runtime_data.overlays}.isdisjoint({first, second})

    await hass.services.async_call(
        DOMAIN, "remove_overlay", {"config_entry_id": entry_id, "overlay_id": second}, blocking=True
    )
    assert [o.id for o in loaded_entry.runtime_data.overlays] == [first]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "remove_overlay",
            {"config_entry_id": entry_id, "overlay_id": "nope"},
            blocking=True,
        )


async def test_overlay_websocket(
    hass: HomeAssistant, hass_ws_client, loaded_entry, photo_path
) -> None:
    hass.states.async_set("sensor.t", "7")
    await hass.services.async_call(
        DOMAIN,
        "add_photo",
        {"config_entry_id": loaded_entry.entry_id, "file_path": str(photo_path)},
        blocking=True,
    )
    ws = await hass_ws_client(hass)
    entry_id = loaded_entry.entry_id

    async def call(msg_id: int, **payload):
        await ws.send_json({"id": msg_id, **payload})
        msg = await ws.receive_json()
        assert msg["success"], msg
        return msg["result"]

    saved = await call(
        1,
        type=f"{DOMAIN}/overlay/save",
        entry_id=entry_id,
        overlay={"name": "T", "template": "{{ states('sensor.t') }} °C", "size": "l"},
    )
    overlay_id = saved["overlay_id"]
    listing = await call(2, type=f"{DOMAIN}/overlays", entry_id=entry_id)
    assert listing["overlays"][0]["size"] == "l"

    preview = await call(
        3,
        type=f"{DOMAIN}/overlay/preview",
        entry_id=entry_id,
        overlays=[
            {"id": overlay_id, "template": "{{ states('sensor.t') }} °C"},
            {"name": "Bad", "template": "{{ bad | nope }}"},
        ],
    )
    assert preview["image"].startswith("data:image/png;base64,")
    results = list(preview["results"].values())
    assert results[0] == {"text": "7 °C", "error": None}
    assert results[1]["text"] is None and results[1]["error"]

    second = await call(
        4, type=f"{DOMAIN}/overlay/save", entry_id=entry_id, overlay={"name": "D", "template": "d"}
    )
    await call(
        5,
        type=f"{DOMAIN}/overlay/reorder",
        entry_id=entry_id,
        order=[second["overlay_id"], overlay_id],
    )
    assert [o.name for o in loaded_entry.runtime_data.overlays] == ["D", "T"]
    await call(6, type=f"{DOMAIN}/overlay/delete", entry_id=entry_id, overlay_id=overlay_id)
    assert [o.name for o in loaded_entry.runtime_data.overlays] == ["D"]

    photo_id = loaded_entry.runtime_data.photos[0].id
    photo = await call(
        7,
        type=f"{DOMAIN}/photo/update",
        entry_id=entry_id,
        photo_id=photo_id,
        hide_frame_overlays=True,
    )
    assert photo["hide_frame_overlays"] is True

    await ws.send_json(
        {
            "id": 8,
            "type": f"{DOMAIN}/overlay/save",
            "entry_id": entry_id,
            "overlay": {"anchor": "nowhere"},
        }
    )
    assert not (await ws.receive_json())["success"]


async def test_up_next_preview_has_live_overlay(
    hass: HomeAssistant, loaded_entry, photo_path
) -> None:
    hass.states.async_set("sensor.t", "1")
    await _setup_overlay(hass, loaded_entry, photo_path)
    manager = loaded_entry.runtime_data
    with_overlay = await manager.async_preview("up_next")
    bare = await manager.async_photo_preview(manager.photos[0].id)
    assert with_overlay != bare
    img = Image.open(io.BytesIO(with_overlay))
    assert img.size == (manager.canvas.width, manager.canvas.height)
