"""show_text: a one-off card with one text overlay, in the frame's override slot."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
import probatio as vol
import pytest

from custom_components.paperlessoffline.store import FrameState

from .conftest import make_jpeg
from .test_cards import _add_photo, _colors, _run, _wake
from .test_photo_overlays import _add


async def _show_text(hass: HomeAssistant, entry, text: str, **data) -> None:
    await _run(hass, "show_text", config_entry_id=entry.entry_id, text=text, **data)


@pytest.fixture
def photo_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    (tmp_path / "red.jpg").write_bytes(make_jpeg((255, 0, 0), size=(800, 480)))
    (tmp_path / "blue.jpg").write_bytes(make_jpeg((0, 0, 255), size=(800, 480)))
    return tmp_path


def test_older_overrides_load_without_text() -> None:
    state = FrameState.from_dict(
        {"override": {"filename": "override.jpg", "name": "A", "sha256": "x"}}
    )
    assert state.override is not None
    assert state.override.text is None


async def test_show_text_draws_crisp_text_on_a_plain_background(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    await _show_text(hass, loaded_entry, "Dinner is ready", background="blue")
    assert "image" in manager.pending_changes()
    client = await hass_client_no_auth()
    img = await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    assert list(manager.state.overlay_texts.values()) == ["Dinner is ready"]
    assert manager.state.served_name == "Dinner is ready"
    # White text on blue, nothing dithered.
    assert _colors(img) == {(0, 0, 255), (255, 255, 255)}


async def test_show_text_defaults_and_photo_is_none(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    await _show_text(hass, loaded_entry, "# {{ photo is none }}")
    ov = manager.state.override
    assert ov is not None and ov.text is not None
    assert ov.text == {
        "template": "# {{ photo is none }}",
        "background": "white",
        "size": "xxl",
        "anchor": "center",
        "align": "center",
    }
    assert ov.name == "{{ photo is none }}"
    client = await hass_client_no_auth()
    img = await _wake(client, freezer)
    assert list(manager.state.overlay_texts.values()) == ["# True"]
    assert _colors(img) == {(255, 255, 255), (0, 0, 0)}


async def test_show_text_counts_down_wakes(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", dither="none")
    await _show_text(hass, loaded_entry, "Hi", wakes=2)
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    assert manager.state.override.wakes_remaining == 1
    await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    img = await _wake(client, freezer)
    assert manager.state.current_kind == "photo"
    assert _colors(img) == {(255, 0, 0)}


async def test_show_text_re_evaluates_each_wake(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    hass.states.async_set("sensor.washer", "running")
    await _show_text(hass, loaded_entry, "Washer: {{ states('sensor.washer') }}")
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert list(manager.state.overlay_texts.values()) == ["Washer: running"]
    hass.states.async_set("sensor.washer", "done")
    await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    assert list(manager.state.overlay_texts.values()) == ["Washer: done"]


async def test_show_text_and_show_image_replace_each_other(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    client = await hass_client_no_auth()
    await _run(
        hass,
        "show_image",
        config_entry_id=loaded_entry.entry_id,
        file_path=str(photo_dir / "red.jpg"),
        dither="none",
    )
    await _wake(client, freezer)
    assert list(manager.directory.glob("override.*"))

    await _show_text(hass, loaded_entry, "Text", background="yellow")
    assert manager.state.override.text is not None
    # The image file goes, the slot holds only the text.
    assert not list(manager.directory.glob("override.*"))
    img = await _wake(client, freezer)
    assert _colors(img) == {(255, 255, 0), (0, 0, 0)}

    await _run(
        hass,
        "show_image",
        config_entry_id=loaded_entry.entry_id,
        file_path=str(photo_dir / "blue.jpg"),
        dither="none",
    )
    assert manager.state.override.text is None
    img = await _wake(client, freezer)
    assert _colors(img) == {(0, 0, 255)}


async def test_clear_image_clears_text(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, photo_dir, freezer
) -> None:
    manager = loaded_entry.runtime_data
    await _add_photo(hass, loaded_entry, photo_dir / "red.jpg", dither="none")
    await _show_text(hass, loaded_entry, "Hi")
    client = await hass_client_no_auth()
    await _wake(client, freezer)
    assert manager.state.current_kind == "override"
    await _run(hass, "clear_image", config_entry_id=loaded_entry.entry_id)
    assert manager.state.override is None
    await _wake(client, freezer)
    assert manager.state.current_kind == "photo"


async def test_show_text_overlays_switch(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer
) -> None:
    manager = loaded_entry.runtime_data
    await _add(hass, loaded_entry, "Global", "g")
    client = await hass_client_no_auth()
    for overlays, expected in ((True, ["Hi", "g"]), (False, ["Hi"])):
        await _show_text(hass, loaded_entry, "Hi", wakes=1, overlays=overlays)
        await _wake(client, freezer)
        assert manager.state.current_kind == "override"
        assert list(manager.state.overlay_texts.values()) == expected


async def test_show_text_up_next_preview(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    await _show_text(hass, loaded_entry, "Soon", background="green")
    assert manager.up_next() == ("override", None)
    assert await manager.async_preview("up_next")


@pytest.mark.parametrize("background", ["photo", "purple"])
async def test_show_text_refuses_other_backgrounds(
    hass: HomeAssistant, loaded_entry, background: str
) -> None:
    with pytest.raises(vol.Invalid):
        await _show_text(hass, loaded_entry, "x", background=background)


async def test_frames_list_tells_text_from_image(
    hass: HomeAssistant, hass_ws_client, loaded_entry, photo_dir: Path
) -> None:
    ws = await hass_ws_client(hass)

    async def override() -> dict:
        await ws.send_json({"id": next(ids), "type": "paperlessoffline/frames"})
        return (await ws.receive_json())["result"]["frames"][0]["override"]

    ids = iter(range(1, 10))
    await _show_text(hass, loaded_entry, "## Hello\nworld", wakes=3)
    assert await override() == {"kind": "text", "name": "Hello", "wakes_remaining": 3}
    await _run(
        hass,
        "show_image",
        config_entry_id=loaded_entry.entry_id,
        file_path=str(photo_dir / "red.jpg"),
        name="Red",
    )
    assert await override() == {"kind": "image", "name": "Red", "wakes_remaining": None}
