"""In-sync status."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PaperlessConfigEntry
from .entity import PaperlessEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    async_add_entities([InSyncSensor(entry.runtime_data, "in_sync")])


class InSyncSensor(PaperlessEntity, BinarySensorEntity):
    """On when the frame has picked up every change."""

    @callback
    def _update_from_manager(self) -> None:
        pending = self.manager.pending_changes()
        self._attr_is_on = not pending
        self._attr_extra_state_attributes = {"pending": pending}
