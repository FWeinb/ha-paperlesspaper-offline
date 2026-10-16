"""Fixtures."""

from __future__ import annotations

import io
from pathlib import Path

from homeassistant.core import HomeAssistant
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.paperlessoffline.const import (
    CONF_CLIENT_ID,
    CONF_INTERVAL,
    CONF_MOUNTING,
    CONF_ORDER,
    CONF_PANEL,
    CONF_TOKEN,
    DOMAIN,
)

CLIENT_ID = "epd7-3485188f1dc8"
TOKEN = "test-token-abcdefghijklmnop"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


def make_jpeg(color: tuple[int, int, int] = (200, 30, 30), size=(320, 200)) -> bytes:
    """Return JPEG bytes of a solid image."""
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A 7" frame entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen",
        unique_id=CLIENT_ID,
        data={CONF_CLIENT_ID: CLIENT_ID, CONF_PANEL: "epd7", CONF_TOKEN: TOKEN},
        options={CONF_INTERVAL: 3600, CONF_ORDER: "sequential", CONF_MOUNTING: "landscape"},
    )


@pytest.fixture
async def loaded_entry(hass: HomeAssistant, config_entry: MockConfigEntry) -> MockConfigEntry:
    """Set up the integration with one frame."""
    hass.config.internal_url = "http://192.168.1.10:8123"
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def config_entry_factory(hass: HomeAssistant):
    """Create and load additional frames."""

    async def _create(client_id: str, title: str) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=title,
            unique_id=client_id,
            data={
                CONF_CLIENT_ID: client_id,
                CONF_PANEL: client_id.split("-", maxsplit=1)[0],
                CONF_TOKEN: f"token-{client_id}",
            },
            options={CONF_INTERVAL: 3600},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _create


@pytest.fixture
def photo_path(hass: HomeAssistant, tmp_path: Path) -> Path:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    path = tmp_path / "a.jpg"
    path.write_bytes(make_jpeg((60, 120, 200)))
    return path
