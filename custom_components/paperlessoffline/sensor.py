"""Frame status sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PaperlessConfigEntry
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0

# Entity key -> key in the BLE status
BLE_VALUES = {"battery_voltage": "voltage", "wifi_signal": "rssi"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    manager = entry.runtime_data
    async_add_entities(
        [
            LastSeenSensor(manager, "last_seen"),
            CurrentPhotoSensor(manager, "current_photo"),
            PendingSensor(manager, "pending_changes"),
            PhotoCountSensor(manager, "photos"),
            BleValueSensor(manager, "battery_voltage"),
            BleValueSensor(manager, "wifi_signal"),
        ]
    )


class LastSeenSensor(PaperlessEntity, SensorEntity):
    """When the frame last made a request."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def _update_from_manager(self) -> None:
        st = self.manager.state
        self._attr_native_value = (
            dt_util.utc_from_timestamp(st.last_request) if st.last_request else None
        )
        self._attr_extra_state_attributes = {
            "last_wake": dt_util.utc_from_timestamp(st.last_wake).isoformat()
            if st.last_wake
            else None,
            "wake_count": st.wake_count,
            **({"telemetry": dict(st.telemetry)} if st.telemetry else {}),
        }


class CurrentPhotoSensor(PaperlessEntity, SensorEntity):
    """What the frame was last served."""

    @callback
    def _update_from_manager(self) -> None:
        st = self.manager.state
        self._attr_native_value = st.served_name
        self._attr_extra_state_attributes = {
            "kind": st.current_kind,
            "photo_id": st.current_id if st.current_kind == "photo" else None,
        }


class PendingSensor(PaperlessEntity, SensorEntity):
    """Number of changes waiting for the next wake."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def _update_from_manager(self) -> None:
        pending = self.manager.pending_changes()
        self._attr_native_value = len(pending)
        self._attr_extra_state_attributes = {"pending": pending}


class PhotoCountSensor(PaperlessEntity, SensorEntity):
    """Photos in the library and in the rotation."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @callback
    def _update_from_manager(self) -> None:
        self._attr_native_value = len(self.manager.enabled_ids())
        self._attr_extra_state_attributes = {"library": len(self.manager.photos)}


class BleValueSensor(PaperlessEntity, SensorEntity):
    """A value read over Bluetooth when the frame was last in setup mode."""

    def __init__(self, manager: FrameManager, key: str) -> None:
        """Initialise."""
        self._status_key = BLE_VALUES[key]
        if key == "battery_voltage":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
            self._attr_suggested_unit_of_measurement = UnitOfElectricPotential.VOLT
            self._attr_suggested_display_precision = 2
        else:
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
        self._attr_state_class = SensorStateClass.MEASUREMENT
        super().__init__(manager, key)

    @callback
    def _update_from_manager(self) -> None:
        st = self.manager.state
        self._attr_native_value = st.ble_status.get(self._status_key)
        self._attr_extra_state_attributes = {
            "last_read": dt_util.utc_from_timestamp(st.ble_read_at).isoformat()
            if st.ble_read_at
            else None,
        }
