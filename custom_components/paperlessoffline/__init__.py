"""paperlesspaper offline-firmware frames for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
import logging
from pathlib import Path
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_CLIENT_ID,
    CONF_PROVISIONED_BASE,
    CONF_PROVISIONED_TOKEN,
    CONF_TOKEN,
    DOMAIN,
    STORAGE_DIR,
    STORAGE_VERSION,
    mac_from_client_id,
)
from .data import DATA_KEY, DomainData
from .frame import FrameManager
from .frontend import async_register_frontend
from .issues import async_delete_issues
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
ISSUE_CHECK_INTERVAL = timedelta(minutes=5)

_LOGGER = logging.getLogger(__name__)

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
    _async_setup_bluetooth(hass, entry, manager)

    async def _check(_now: object = None) -> None:
        await manager.async_refresh_base_url()

    entry.async_on_unload(async_track_time_interval(hass, _check, ISSUE_CHECK_INTERVAL))

    @callback
    def _device_updated(event: Event[dr.EventDeviceRegistryUpdatedData]) -> None:
        # A device rename changes the frame's name (placeholder, templates, panel).
        if event.data["action"] == "update" and event.data["device_id"] == manager.device_id:
            manager.async_options_updated()
            async_dispatcher_send(hass, SIGNAL_FRAMES_CHANGED)

    entry.async_on_unload(hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, _device_updated))

    @callback
    def _core_config_updated(_event: Event) -> None:
        entry.async_create_background_task(hass, _check(), f"{DOMAIN} url check")

    entry.async_on_unload(hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _core_config_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    manager.async_options_updated()
    manager.async_update_issues()
    async_dispatcher_send(hass, SIGNAL_FRAMES_CHANGED)
    return True


@callback
def _async_setup_bluetooth(
    hass: HomeAssistant, entry: PaperlessConfigEntry, manager: FrameManager
) -> None:
    """Watch for the frame advertising, which it only does in setup mode."""
    if "bluetooth" not in hass.config.components:
        return
    # Imported lazily so the integration works on systems without Bluetooth.
    from homeassistant.components import bluetooth  # noqa: PLC0415

    @callback
    def _seen(
        service_info: bluetooth.BluetoothServiceInfoBleak, _change: bluetooth.BluetoothChange
    ) -> None:
        manager.async_ble_seen(service_info.address)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _seen,
            bluetooth.BluetoothCallbackMatcher(local_name=manager.client_id, connectable=True),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older entries."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        # Assume the frame was set up with the URLs it has now.
        data = {**entry.data}
        data.setdefault(CONF_PROVISIONED_TOKEN, data[CONF_TOKEN])
        data.setdefault(CONF_PROVISIONED_BASE, None)
        hass.config_entries.async_update_entry(entry, data=data, minor_version=2)
        _LOGGER.debug("Migrated %s to version 1.2", entry.title)
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: PaperlessConfigEntry) -> None:
    """Apply changed options/data without reloading."""
    data = hass.data[DATA_KEY]
    manager = entry.runtime_data
    for token, known in list(data.tokens.items()):
        if known is manager and token != manager.token:
            del data.tokens[token]
    data.tokens[manager.token] = manager
    # Keep the device's own name in step with a renamed entry (a user-set
    # device name still wins, see FrameManager.display_name).
    registry = dr.async_get(hass)
    device = registry.async_get(manager.device_id) if manager.device_id else None
    if device is not None and device.name != entry.title:
        registry.async_update_device(device.id, name=entry.title)
    manager.async_options_updated()
    # The chosen URL host may have changed.
    entry.async_create_background_task(
        hass, manager.async_refresh_base_url(), f"{DOMAIN} url check"
    )


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
    """Delete a removed frame's library, state and repair issues."""
    async_delete_issues(hass, entry.entry_id)
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
    directory = Path(hass.config.path(STORAGE_DIR, entry.entry_id))
    await hass.async_add_executor_job(shutil.rmtree, directory, True)
