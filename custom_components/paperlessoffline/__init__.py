"""paperlesspaper offline-firmware frames for Home Assistant."""

from __future__ import annotations

from pathlib import Path
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import CONF_CLIENT_ID, DOMAIN, STORAGE_DIR, STORAGE_VERSION, mac_from_client_id
from .data import DATA_KEY, DomainData
from .frame import FrameManager
from .frontend import async_register_frontend
from .services import async_setup_services
from .store import GlobalStore
from .views import (
    FrameImageView,
    FrameSettingsView,
    PhotoPreviewView,
    PhotoThumbView,
    PhotoUploadView,
)
from .websocket import SIGNAL_FRAMES_CHANGED, async_setup_websocket

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.IMAGE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type PaperlessConfigEntry = ConfigEntry[FrameManager]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide pieces."""
    global_store = GlobalStore(hass)
    await global_store.async_load()
    hass.data[DATA_KEY] = DomainData(global_store)
    hass.http.register_view(FrameImageView())
    hass.http.register_view(FrameSettingsView())
    hass.http.register_view(PhotoPreviewView())
    hass.http.register_view(PhotoThumbView())
    hass.http.register_view(PhotoUploadView())
    async_setup_services(hass)
    async_setup_websocket(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PaperlessConfigEntry) -> bool:
    """Set up one frame."""
    data = hass.data[DATA_KEY]
    manager = FrameManager(hass, entry, data.global_store)
    await manager.async_setup()
    entry.runtime_data = manager
    data.entries[entry.entry_id] = manager
    data.tokens[manager.token] = manager

    connections = set()
    if mac := mac_from_client_id(entry.data[CONF_CLIENT_ID]):
        connections.add((dr.CONNECTION_NETWORK_MAC, dr.format_mac(mac)))
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, manager.client_id)},
        connections=connections,
        manufacturer="paperlesspaper",
        model=manager.panel.model,
        name=entry.title,
        serial_number=manager.client_id,
        sw_version="offline firmware",
    )

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.async_options_updated()
    async_dispatcher_send(hass, SIGNAL_FRAMES_CHANGED)
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: PaperlessConfigEntry) -> None:
    """Apply changed options/data without reloading."""
    data = hass.data[DATA_KEY]
    manager = entry.runtime_data
    for token, known in list(data.tokens.items()):
        if known is manager and token != manager.token:
            del data.tokens[token]
    data.tokens[manager.token] = manager
    manager.async_options_updated()


async def async_unload_entry(hass: HomeAssistant, entry: PaperlessConfigEntry) -> bool:
    """Unload a frame."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        manager = entry.runtime_data
        await manager.async_unload()
        data = hass.data[DATA_KEY]
        data.entries.pop(entry.entry_id, None)
        data.tokens.pop(manager.token, None)
        async_dispatcher_send(hass, SIGNAL_FRAMES_CHANGED)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: PaperlessConfigEntry) -> None:
    """Delete a removed frame's library and state."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
    directory = Path(hass.config.path(STORAGE_DIR, entry.entry_id))
    await hass.async_add_executor_job(shutil.rmtree, directory, True)
