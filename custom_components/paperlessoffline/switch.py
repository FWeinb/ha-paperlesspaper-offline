"""Device feature switches, delivered via the settings JSON."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PaperlessConfigEntry
from .const import CONF_AUTO_ROTATION, CONF_CHARGER_MODE, CONF_MOTION_WAKEUP
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0

SWITCHES = (CONF_MOTION_WAKEUP, CONF_AUTO_ROTATION, CONF_CHARGER_MODE)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    async_add_entities(OptionSwitch(entry.runtime_data, key) for key in SWITCHES)


class OptionSwitch(PaperlessEntity, SwitchEntity):
    """A boolean frame setting."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: FrameManager, key: str) -> None:
        """Initialise."""
        self._key = key
        super().__init__(manager, key)

    @callback
    def _update_from_manager(self) -> None:
        self._attr_is_on = bool(self.manager.options.get(self._key, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable."""
        await self._async_set_option(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable."""
        await self._async_set_option(self._key, False)
