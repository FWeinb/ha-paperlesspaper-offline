"""Cache eviction and cleanup of files that are no longer needed."""

from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import time
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
import pytest

from custom_components.paperlessoffline import cache, housekeeping
from custom_components.paperlessoffline.cache import RenderCache
from custom_components.paperlessoffline.diagnostics import async_get_config_entry_diagnostics
from custom_components.paperlessoffline.store import OverlayDef

from .conftest import TOKEN, make_jpeg

IMAGE_URL = f"/api/paperlessoffline/{TOKEN}/image.bmp"
SETTINGS_URL = f"/api/paperlessoffline/{TOKEN}/settings.json"
ULID = "01J0000000000000000000000A"
OTHER_ULID = "01J0000000000000000000000B"


def _age(path: Path, seconds: float) -> None:
    """Pretend a file was last used ``seconds`` ago."""
    then = time.time() - seconds
    os.utime(path, (then, then))


def _keys(directory: Path) -> set[str]:
    return {p.name.split(".", 1)[0] for p in directory.iterdir()}


async def _wake(client, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(minutes=61))
    await client.get(SETTINGS_URL)
    assert (await client.get(IMAGE_URL)).status == 200


def test_evict_keeps_needed_and_recent(tmp_path: Path) -> None:
    rc = RenderCache(tmp_path)
    for key in ("needed", "old", "recent"):
        rc.put(key, b"bmp", b"png")
    (tmp_path / "crashed.bmp.tmp").write_bytes(b"x")
    for path in tmp_path.iterdir():
        if not path.name.startswith("recent"):
            _age(path, cache.GRACE_SECONDS + 1)
    assert rc.evict(["needed", None]) == 2
    assert _keys(tmp_path) == {"needed", "recent"}


def test_reads_count_as_use(tmp_path: Path) -> None:
    """A hit or read touches the files, so a used entry survives the grace period."""
    rc = RenderCache(tmp_path)
    rc.put("a", b"bmp", b"png")
    rc.put("b", b"bmp", b"png")
    for path in tmp_path.iterdir():
        _age(path, cache.GRACE_SECONDS + 1)
    assert rc.read_png("a") == b"png"
    assert rc.has("b")
    assert rc.evict([]) == 0
    _age(rc.bmp_path("a"), cache.GRACE_SECONDS + 1)
    assert rc.evict([]) == 0  # the png was used recently, so the entry stays whole
    assert rc.has("a")


async def test_cache_holds_only_needed_set(
    hass: HomeAssistant, hass_client_no_auth, loaded_entry, freezer, monkeypatch
) -> None:
    """After wakes with changing overlay values, only the needed renders remain."""
    manager = loaded_entry.runtime_data
    await manager.async_add_photo(make_jpeg((200, 30, 30)), "red")
    await manager.async_add_photo(make_jpeg((30, 30, 200)), "blue")
    manager.async_save_overlay(
        OverlayDef(id="t", name="Temp", template="{{ states('sensor.temp') }} °C")
    )
    client = await hass_client_no_auth()
    for value in range(4):
        hass.states.async_set("sensor.temp", str(20 + value))
        await _wake(client, freezer)
        await manager.async_overlay_preview(None)  # editor previews land in the cache too
    await hass.async_block_till_done()
    assert len(_keys(manager.cache.directory)) > 4  # within the grace period, all stay

    monkeypatch.setattr(cache, "GRACE_SECONDS", 0)
    await manager.async_housekeeping()
    base, final = await manager._async_render_up_next()
    st = manager.state
    needed = {st.served_key, st.served_base_key, base, final}
    assert st.served_key != st.served_base_key  # the frame shows a composite
    assert _keys(manager.cache.directory) == needed


async def test_thumbs_cleanup(hass: HomeAssistant, loaded_entry, monkeypatch) -> None:
    manager = loaded_entry.runtime_data
    photo = await manager.async_add_photo(make_jpeg(), "red")
    thumbs = manager.directory / "thumbs"
    for size, rotation in ((320, 0), (320, 90), (1280, 0), (1280, 90)):
        await manager.async_thumbnail(photo.id, size, rotation)
    (thumbs / "gone_320_0.jpg").write_bytes(b"x")  # photo no longer in the library
    (thumbs / "new_320_0.jpg").write_bytes(b"x")  # photo added after the snapshot
    _age(thumbs / "gone_320_0.jpg", cache.GRACE_SECONDS + 1)
    await manager.async_housekeeping()
    assert {p.name for p in thumbs.iterdir()} == {
        "new_320_0.jpg",
        f"{photo.id}_320_0.jpg",
        f"{photo.id}_320_90.jpg",
        f"{photo.id}_1280_0.jpg",
        f"{photo.id}_1280_90.jpg",
    }

    for path in thumbs.iterdir():
        _age(path, housekeeping.THUMB_GRACE_SECONDS + 1)
    await manager.async_thumbnail(photo.id, 1280, 90)  # used again: kept a day longer
    await manager.async_housekeeping()
    assert {p.name for p in thumbs.iterdir()} == {
        f"{photo.id}_320_0.jpg",
        f"{photo.id}_1280_90.jpg",
    }


async def test_unreferenced_originals_and_override(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    photo = await manager.async_add_photo(make_jpeg(), "red")
    kept = manager.originals / photo.filename
    stray = manager.originals / "crashed.jpg"
    fresh = manager.originals / "being_added.jpg"
    old_override = manager.directory / "override.png"
    for path in (stray, fresh, old_override):
        path.write_bytes(make_jpeg())
    for path in (kept, stray, old_override):
        _age(path, cache.GRACE_SECONDS + 1)
    await manager.async_housekeeping()
    assert kept.exists()
    assert fresh.exists()  # within the grace period
    assert not stray.exists()
    assert not old_override.exists()

    await manager.async_set_override(make_jpeg(), "notice", None, 1)
    current = manager.directory / manager.state.override.filename
    _age(current, cache.GRACE_SECONDS + 1)
    await manager.async_housekeeping()
    assert current.exists()


def test_remove_orphan_entries(tmp_path: Path) -> None:
    root = tmp_path / "paperlessoffline"
    storage = tmp_path / ".storage"
    for path in (root / ULID / "cache", root / OTHER_ULID, root / "not-an-entry", storage):
        path.mkdir(parents=True)
    for name in (
        f"paperlessoffline.{ULID}",
        f"paperlessoffline.{OTHER_ULID}",
        "paperlessoffline.global",
    ):
        (storage / name).write_text("{}")
    for path in [*root.iterdir(), *storage.iterdir()]:
        _age(path, cache.GRACE_SECONDS + 1)
    (storage / "paperlessoffline.01J0000000000000000000000C").write_text("{}")  # just created

    assert housekeeping.remove_orphan_entries(root, storage, "paperlessoffline", {ULID}) == [
        OTHER_ULID
    ]
    assert {p.name for p in root.iterdir()} == {ULID, "not-an-entry"}
    assert {p.name for p in storage.iterdir()} == {
        f"paperlessoffline.{ULID}",
        "paperlessoffline.global",
        "paperlessoffline.01J0000000000000000000000C",
    }


async def test_orphan_cleanup_at_setup(
    hass: HomeAssistant, config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Setting up the integration looks for orphans with the existing entry ids."""
    calls = []

    def fake(root: Path, storage: Path, domain: str, entry_ids: set[str]) -> list[str]:
        calls.append((root, storage, domain, entry_ids))
        return []

    monkeypatch.setattr(housekeeping, "remove_orphan_entries", fake)
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert calls == [
        (
            Path(hass.config.path("paperlessoffline")),
            Path(hass.config.path(".storage")),
            "paperlessoffline",
            {config_entry.entry_id},
        )
    ]


async def test_diagnostics_storage(hass: HomeAssistant, loaded_entry) -> None:
    manager = loaded_entry.runtime_data
    photo = await manager.async_add_photo(make_jpeg(), "red")
    await manager.async_thumbnail(photo.id)
    diag = await async_get_config_entry_diagnostics(hass, loaded_entry)
    assert diag["storage"]["originals"]["files"] == 1
    assert diag["storage"]["originals"]["bytes"] == len(make_jpeg())
    assert diag["storage"]["thumbs"]["files"] == 1
    assert set(diag["storage"]) == {"cache", "thumbs", "originals", "snapshots"}


async def test_up_next_keys_match_render(hass: HomeAssistant, loaded_entry) -> None:
    """Housekeeping knows the up-next keys without rendering them."""
    manager = loaded_entry.runtime_data
    assert manager._up_next_keys() == await manager._async_render_up_next()  # placeholder
    await manager.async_add_photo(make_jpeg(), "red")
    manager.async_save_overlay(OverlayDef(id="t", name="T", template="Hello"))
    keys = manager._up_next_keys()
    assert keys[0] != keys[1]
    assert keys == await manager._async_render_up_next()
    await manager.async_set_override(make_jpeg((0, 0, 200)), "notice", None, 1)
    assert manager._up_next_keys() == await manager._async_render_up_next()


async def test_cleanup_runs_when_prerender_fails(
    hass: HomeAssistant, loaded_entry, monkeypatch, caplog
) -> None:
    manager = loaded_entry.runtime_data
    stale = manager.cache.directory / "stale.png"
    stale.write_bytes(b"x")
    _age(stale, cache.GRACE_SECONDS + 1)

    async def broken() -> tuple[str, str]:
        raise OSError("original unreadable")

    monkeypatch.setattr(manager, "_async_render_up_next", broken)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    await manager._async_prerender()
    assert "Pre-rendering" in caplog.text
    assert not stale.exists()
