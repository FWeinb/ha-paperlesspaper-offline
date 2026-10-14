"""Refresh interval."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PaperlessConfigEntry
from .const import CONF_INTERVAL, MAX_INTERVAL, MIN_INTERVAL
from .entity import PaperlessEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up numbers."""
    async_add_entities([IntervalNumber(entry.runtime_data, "interval")])


class IntervalNumber(PaperlessEntity, NumberEntity):
    """How long the frame sleeps between wakes (outside quiet hours)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = MIN_INTERVAL // 60
    _attr_native_max_value = MAX_INTERVAL // 60
    _attr_native_step = 1

    @callback
    def _update_from_manager(self) -> None:
        self._attr_native_value = self.manager.interval // 60

    async def async_set_native_value(self, value: float) -> None:
        """Set the interval."""
        await self._async_set_option(CONF_INTERVAL, int(value) * 60)
