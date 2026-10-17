"""Device feature switches, delivered via the settings JSON."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PaperlessConfigEntry
from .const import CONF_AUTO_ROTATION, CONF_CHARGER_MODE, CONF_MOTION_WAKEUP, CONF_TELEMETRY
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0

SWITCHES = (CONF_MOTION_WAKEUP, CONF_AUTO_ROTATION, CONF_CHARGER_MODE, CONF_TELEMETRY)
# Switches that are on until the user turns them off
DEFAULT_ON = {CONF_TELEMETRY}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""
    async_add_entities(
        (MotionWakeupSwitch if key == CONF_MOTION_WAKEUP else OptionSwitch)(entry.runtime_data, key)
        for key in SWITCHES
    )


class OptionSwitch(PaperlessEntity, SwitchEntity):
    """A boolean frame setting."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: FrameManager, key: str) -> None:
        """Initialise."""
        self._key = key
        super().__init__(manager, key)

    @callback
    def _update_from_manager(self) -> None:
        self._attr_is_on = bool(self.manager.options.get(self._key, self._key in DEFAULT_ON))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable."""
        await self._async_set_option(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable."""
        await self._async_set_option(self._key, False)


class MotionWakeupSwitch(OptionSwitch):
    """Motion wake-up, which quiet hours can turn off for a while.

    ``suppressed_until`` says when quiet hours stop sending ``motionWakeup:
    false`` while the switch is on, so the switch and settings JSON agree. The
    manager sends an update when quiet hours start or end.
    """

    @callback
    def _update_from_manager(self) -> None:
        super()._update_from_manager()
        until = self.manager.motion_suppressed_until(dt_util.utcnow())
        self._attr_extra_state_attributes = {"suppressed_until": until}
