"""Device trigger, media source and diagnostics."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import automation, media_source
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_get_device_automations
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.paperlessoffline.const import DOMAIN

from .conftest import CLIENT_ID, TOKEN, make_jpeg


async def test_device_trigger(hass: HomeAssistant, hass_client_no_auth, loaded_entry) -> None:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, CLIENT_ID), loaded_entry.entry_id
    )
    assert device is not None
    triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device.id)
    assert any(t["type"] == "wake" and t["domain"] == DOMAIN for t in triggers)

    calls: list[ServiceCall] = []
    hass.services.async_register("test", "automation", calls.append)
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "device",
                    "domain": DOMAIN,
                    "device_id": device.id,
                    "type": "wake",
                },
                "action": {"service": "test.automation"},
            }
        },
    )
    client = await hass_client_no_auth()
    await client.get(f"/api/paperlessoffline/{TOKEN}/image.bmp")
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_media_source(hass: HomeAssistant, loaded_entry, tmp_path: Path) -> None:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    (tmp_path / "beach.jpg").write_bytes(make_jpeg())
    await hass.services.async_call(
        DOMAIN,
        "add_photo",
        {"config_entry_id": loaded_entry.entry_id, "file_path": str(tmp_path / "beach.jpg")},
        blocking=True,
    )
    root = await media_source.async_browse_media(hass, f"media-source://{DOMAIN}")
    assert [c.title for c in root.children] == ["Kitchen"]
    frame = await media_source.async_browse_media(
        hass, f"media-source://{DOMAIN}/{loaded_entry.entry_id}"
    )
    assert [c.title for c in frame.children] == ["beach"]
    resolved = await media_source.async_resolve_media(
        hass, frame.children[0].media_content_id, None
    )
    assert resolved.mime_type == "image/png"
    assert "/api/paperlessoffline/preview/" in resolved.url


async def test_diagnostics(hass: HomeAssistant, hass_client, loaded_entry) -> None:
    diag = await get_diagnostics_for_config_entry(hass, hass_client, loaded_entry)
    assert diag["data"]["token"] == "**REDACTED**"
    assert diag["panel"]["width"] == 800


async def test_remove_entry_deletes_files(hass: HomeAssistant, loaded_entry) -> None:
    directory = Path(hass.config.path(DOMAIN, loaded_entry.entry_id))
    assert directory.is_dir()
    await hass.config_entries.async_remove(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert not directory.exists()
