"""In-sync status."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PaperlessConfigEntry
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0

# Entity key -> key in the BLE system info
BLE_FLAGS = {"charging": "charging", "usb_power": "usb"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    manager = entry.runtime_data
    async_add_entities(
        [
            InSyncSensor(manager, "in_sync"),
            BleFlagSensor(manager, "charging"),
            BleFlagSensor(manager, "usb_power"),
        ]
    )


class InSyncSensor(PaperlessEntity, BinarySensorEntity):
    """On when the frame has picked up every change."""

    @callback
    def _update_from_manager(self) -> None:
        pending = self.manager.pending_changes()
        self._attr_is_on = not pending
        self._attr_extra_state_attributes = {"pending": pending}


class BleFlagSensor(PaperlessEntity, BinarySensorEntity):
    """Charging / USB power, read over Bluetooth in setup mode."""

    def __init__(self, manager: FrameManager, key: str) -> None:
        """Initialise."""
        self._status_key = BLE_FLAGS[key]
        self._attr_device_class = (
            BinarySensorDeviceClass.BATTERY_CHARGING
            if key == "charging"
            else BinarySensorDeviceClass.PLUG
        )
        super().__init__(manager, key)

    @callback
    def _update_from_manager(self) -> None:
        st = self.manager.state
        self._attr_is_on = st.ble_status.get(self._status_key)
        self._attr_extra_state_attributes = {
            "last_read": dt_util.utc_from_timestamp(st.ble_read_at).isoformat()
            if st.ble_read_at
            else None,
        }
