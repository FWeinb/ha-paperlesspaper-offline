"""Image overlays: sizing, dithering, compositing, fetching, wakes, actions."""

from __future__ import annotations

import asyncio
import io
import os
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import numpy as np
from PIL import Image
import pytest

from custom_components.paperlessoffline import (
    cache,
    overlay_images,
)
from custom_components.paperlessoffline.const import DOMAIN
from custom_components.paperlessoffline.render import (
    OverlayStyle,
    RenderOptions,
    canvas_for,
    composite,
    render_fill,
    render_snapshot,
)
from custom_components.paperlessoffline.render.overlay import COLORS, image_size
from custom_components.paperlessoffline.render.pipeline import positions_from_bmp

from .conftest import make_jpeg
from .test_overlays import _call, _texts, _wake

PURE_RGB = set(COLORS.values())
MAX_PIXELS = 100_000_000


def _png_colours(png: bytes) -> set[tuple[int, int, int]]:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    return {tuple(c) for c in np.asarray(img).reshape(-1, 3).tolist()}


# ------------------------------------------------------------------ sizing


def test_image_size_keeps_aspect_within_box_width() -> None:
    style = OverlayStyle(kind="image", width=50)
    # 800 px canvas, 50 % = 400 px box, minus 12 px padding on each side.
    assert image_size((320, 200), style, 800, 480) == (376, 235)
    # Without a backing box there is no padding.
    assert (
        image_size((320, 200), OverlayStyle(kind="image", width=50, backing="none"), 800, 480)[0]
        == 400
    )


def test_image_size_defaults_and_height_cap() -> None:
    # No width: 40 % of the canvas.
    assert image_size((100, 100), OverlayStyle(kind="image", backing="none"), 800, 480)[0] == 320
    # A tall picture is capped to the canvas height minus margins.
    w, h = image_size((100, 1000), OverlayStyle(kind="image", width=100, backing="none"), 800, 480)
    margin = 0.03 * 480
    assert h == round(480 - 2 * margin)
    assert w == round(h / 10)


# --------------------------------------------------------------- rendering


def test_snapshot_is_dithered_to_pure_colours() -> None:
    canvas = canvas_for(800, 480, "landscape")
    style = OverlayStyle(kind="image", width=50)
    png = render_snapshot(make_jpeg((200, 30, 30)), style, RenderOptions(), canvas, MAX_PIXELS)
    img = Image.open(io.BytesIO(png))
    assert img.size == (376, 235)
    assert _png_colours(png) <= PURE_RGB


def test_snapshot_refuses_too_many_pixels() -> None:
    canvas = canvas_for(800, 480, "landscape")
    with pytest.raises(ValueError):
        render_snapshot(make_jpeg(), OverlayStyle(kind="image"), RenderOptions(), canvas, 1000)


@pytest.mark.parametrize(
    "mounting", ["portrait", "landscape", "portrait_flipped", "landscape_flipped"]
)
def test_composite_places_image_in_its_anchor_with_box(mounting) -> None:
    canvas = canvas_for(800, 480, mounting)
    style = OverlayStyle(kind="image", anchor="top_left", width=30, backing_color="yellow")
    png = render_snapshot(make_jpeg((0, 0, 255)), style, RenderOptions(), canvas, MAX_PIXELS)
    base = render_fill("white", canvas)
    out = composite(base.bmp, [("snap", style)], canvas, {"snap": png})
    preview = np.asarray(Image.open(io.BytesIO(out.preview_png)).convert("RGB"))
    changed = positions_from_bmp(out.bmp, canvas) != positions_from_bmp(base.bmp, canvas)
    ys, xs = np.nonzero(changed)
    assert ys.max() < canvas.height / 2 and xs.max() < canvas.width / 2
    # The backing box frames the picture: its left edge is yellow, the middle blue.
    top, left = ys.min(), xs.min()
    snap = Image.open(io.BytesIO(png))
    assert tuple(preview[top + snap.height // 2, left + 2]) != tuple(
        preview[top + snap.height // 2, left + snap.width // 2]
    )


def test_composite_skips_missing_snapshot_and_draws_text_on_top() -> None:
    canvas = canvas_for(800, 480, "landscape")
    base = render_fill("white", canvas)
    image = OverlayStyle(kind="image", anchor="center", width=100, backing="none")
    alone = composite(base.bmp, [("gone", image)], canvas, {})
    assert alone.bmp == base.bmp

    png = render_snapshot(make_jpeg((0, 0, 0)), image, RenderOptions(), canvas, MAX_PIXELS)
    text = OverlayStyle(anchor="center", size="xxl", backing="none", text_color="white")
    both = composite(base.bmp, [("snap", image), ("**X**", text)], canvas, {"snap": png})
    only_image = composite(base.bmp, [("snap", image)], canvas, {"snap": png})
    assert both.bmp != only_image.bmp  # white text drawn over the black picture


# ---------------------------------------------------------- frame behaviour

SOURCE = "http://cam.local/snapshot.jpg"


@pytest.fixture
def pictures(monkeypatch):
    """What each source returns: bytes, or an exception to raise."""
    served: dict[str, bytes | Exception] = {SOURCE: make_jpeg((0, 0, 250), size=(160, 120))}

    async def fetch(hass, source):
        result = served[source]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(overlay_images, "async_download", fetch)
    monkeypatch.setattr(overlay_images, "async_entity_image", fetch)
    return served


async def _add_image_overlay(hass, entry, photo_path, image=SOURCE, **extra) -> str:
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
        name="Camera",
        kind="image",
        image=image,
        width=50,
        **extra,
    )
    return resp["overlay_id"]


async def test_image_overlay_drawn_at_wake(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, *, freezer, pictures
) -> None:
    await _add_image_overlay(hass, loaded_entry, photo_path)
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry))["Camera"] == (SOURCE, None)
    snapshot = next(iter(manager.state.overlay_images.values()))
    assert manager.snapshots.path(snapshot).is_file()
    bare = await manager.async_photo_preview(manager.photos[0].id)
    assert await manager.async_preview("showing") != bare

    # The same picture again: the frame isn't redrawn.
    same = await _wake(client, freezer)
    assert same.headers["Last-Modified"] == first.headers["Last-Modified"]

    pictures[SOURCE] = make_jpeg((250, 250, 0), size=(160, 120))
    changed = await _wake(client, freezer)
    assert changed.headers["Last-Modified"] != first.headers["Last-Modified"]


async def test_image_overlay_from_entity_template(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, *, freezer, pictures
) -> None:
    pictures["camera.door"] = make_jpeg((0, 200, 0))
    hass.states.async_set("binary_sensor.ring", "on")
    await _add_image_overlay(
        hass,
        loaded_entry,
        photo_path,
        image="{{ 'camera.door' if is_state('binary_sensor.ring', 'on') else '' }}",
    )
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry))["Camera"] == ("camera.door", None)
    assert loaded_entry.runtime_data.state.overlay_images

    # An empty source hides the overlay without an error.
    hass.states.async_set("binary_sensor.ring", "off")
    await _wake(client, freezer)
    assert (await _texts(hass, loaded_entry))["Camera"] == (None, None)
    assert not loaded_entry.runtime_data.state.overlay_images


@pytest.mark.parametrize(
    ("image", "result", "error"),
    [
        (SOURCE, HomeAssistantError("404, Not Found"), "404"),
        ("sensor.temperature", None, "Not a camera or image entity"),
        (SOURCE, Exception("unexpected"), None),
    ],
)
async def test_image_overlay_failure_leaves_it_out(
    hass: HomeAssistant,
    hass_client_no_auth,
    loaded_entry,
    photo_path,
    *,
    freezer,
    pictures,
    caplog,
    image,
    result,
    error,
) -> None:
    if result is not None:
        pictures[SOURCE] = result if error else b"not an image"
    await _add_image_overlay(hass, loaded_entry, photo_path, image=image)
    client = await hass_client_no_auth()
    response = await _wake(client, freezer)
    assert response.status == 200
    text, last_error = (await _texts(hass, loaded_entry))["Camera"]
    assert text == image and last_error
    if error:
        assert error in last_error
    assert "left out" in caplog.text
    assert not loaded_entry.runtime_data.state.overlay_images


async def test_image_overlay_times_out(
    hass: HomeAssistant, loaded_entry, photo_path, monkeypatch
) -> None:
    async def hang(hass, source):
        await asyncio.sleep(3600)

    monkeypatch.setattr(overlay_images, "async_download", hang)
    overlay_id = await _add_image_overlay(hass, loaded_entry, photo_path)
    manager = loaded_entry.runtime_data
    overlay = manager.require_overlay(overlay_id)
    images, errors = await manager._async_snapshots([overlay], {overlay_id: SOURCE}, 0.05)
    assert images == {}
    assert errors == {overlay_id: "No picture within 0.05 s"}


async def test_image_overlay_photo_policy_keeps_snapshot(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, *, freezer, pictures
) -> None:
    await _add_image_overlay(hass, loaded_entry, photo_path, redraw="photo")
    client = await hass_client_no_auth()
    first = await _wake(client, freezer)
    kept = dict(loaded_entry.runtime_data.state.overlay_images)
    pictures[SOURCE] = make_jpeg((250, 250, 0))
    again = await _wake(client, freezer)  # same single photo: picture kept
    assert again.headers["Last-Modified"] == first.headers["Last-Modified"]
    assert loaded_entry.runtime_data.state.overlay_images == kept


async def test_image_overlay_actions(
    hass: HomeAssistant, loaded_entry, photo_path, pictures
) -> None:
    overlay_id = await _add_image_overlay(hass, loaded_entry, photo_path)
    listed = (await _call(hass, "list_overlays", config_entry_id=loaded_entry.entry_id))["overlays"]
    assert listed[0]["kind"] == "image" and listed[0]["image"] == SOURCE
    with pytest.raises(ServiceValidationError, match="kind"):
        await _call(
            hass,
            "update_overlay",
            config_entry_id=loaded_entry.entry_id,
            overlay_id=overlay_id,
            kind="text",
        )
    with pytest.raises(ServiceValidationError, match="picture source"):
        await _call(
            hass, "add_overlay", config_entry_id=loaded_entry.entry_id, name="X", kind="image"
        )
    with pytest.raises(ServiceValidationError, match="needs a text"):
        await _call(hass, "add_overlay", config_entry_id=loaded_entry.entry_id, name="X")


async def test_image_overlay_previews(
    hass: HomeAssistant, loaded_entry, photo_path, pictures
) -> None:
    await _add_image_overlay(hass, loaded_entry, photo_path)
    manager = loaded_entry.runtime_data
    bare = await manager.async_photo_preview(manager.photos[0].id)
    assert await manager.async_preview("up_next") != bare
    # Housekeeping knows what "Up next" rendered to.
    assert manager._up_next_keys() == await manager._async_render_up_next()

    png, results = await manager.async_overlay_preview(manager.photos[0].id)
    assert png != bare
    assert next(iter(results.values())) == {"text": SOURCE, "error": None}

    pictures[SOURCE] = HomeAssistantError("offline")
    png, results = await manager.async_overlay_preview(manager.photos[0].id)
    assert png == bare
    assert next(iter(results.values()))["error"] == "offline"


async def test_image_overlay_on_card_thumbnail(hass: HomeAssistant, loaded_entry, pictures) -> None:
    card = await _call(hass, "add_card", config_entry_id=loaded_entry.entry_id, name="Door")
    plain = await loaded_entry.runtime_data.async_photo_preview(card["photo_id"])
    await _call(
        hass,
        "add_overlay",
        config_entry_id=loaded_entry.entry_id,
        photo_id=card["photo_id"],
        name="Camera",
        kind="image",
        image=SOURCE,
    )
    assert await loaded_entry.runtime_data.async_photo_preview(card["photo_id"]) != plain


async def test_unused_snapshots_are_deleted(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_path, *, freezer, pictures
) -> None:
    await _add_image_overlay(hass, loaded_entry, photo_path)
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    used = manager.snapshots.path(next(iter(manager.state.overlay_images.values())))
    stale = manager.snapshots.path("stale")
    stale.write_bytes(b"x")
    old = time.time() - cache.GRACE_SECONDS - 10
    for path in (used, stale):
        os.utime(path, (old, old))
    await manager.async_housekeeping()
    assert used.is_file()
    assert not stale.exists()


async def test_fetch_refuses_frame_previews(hass: HomeAssistant, loaded_entry) -> None:
    with pytest.raises(HomeAssistantError, match="own preview"):
        await overlay_images.async_fetch(hass, "image.kitchen_up_next")


async def test_fetch_refuses_other_sources(hass: HomeAssistant) -> None:
    with pytest.raises(HomeAssistantError, match="Not a camera"):
        await overlay_images.async_fetch(hass, "/local/door.jpg")
    # Without the integration, its module (and its requirements) isn't imported.
    with pytest.raises(HomeAssistantError, match="camera integration is not set up"):
        await overlay_images.async_fetch(hass, "camera.missing")
    with pytest.raises(HomeAssistantError, match="image integration is not set up"):
        await overlay_images.async_fetch(hass, "image.missing")


async def test_up_next_entity_follows_overlays(
    hass: HomeAssistant, loaded_entry, photo_path, pictures
) -> None:
    """The panel shows "Up next" by the entity's picture URL, which changes with its state."""
    await _add_image_overlay(hass, loaded_entry, photo_path)
    await hass.async_block_till_done()
    before = hass.states.get("image.kitchen_up_next").state

    await _call(
        hass, "add_overlay", config_entry_id=loaded_entry.entry_id, name="Label", template="Hi"
    )
    await hass.async_block_till_done()
    after_add = hass.states.get("image.kitchen_up_next").state
    assert after_add != before

    # A new picture from the same source doesn't refresh it: that would fetch again and again.
    pictures[SOURCE] = make_jpeg((250, 250, 0))
    await loaded_entry.runtime_data.async_preview("up_next")
    loaded_entry.runtime_data._changed(prerender=False)
    await hass.async_block_till_done()
    assert hass.states.get("image.kitchen_up_next").state == after_add
