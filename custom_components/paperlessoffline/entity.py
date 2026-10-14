"""Base entity for paperlessoffline frames."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .frame import FrameManager, signal_update


class PaperlessEntity(Entity):
    """An entity belonging to one frame, updated via dispatcher."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: FrameManager, key: str) -> None:
        """Initialise."""
        self.manager = manager
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.client_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, manager.client_id)})
        self._update_from_manager()

    async def async_added_to_hass(self) -> None:
        """Subscribe to frame updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_update(self.manager.entry.entry_id), self._handle_update
            )
        )
        self._handle_update()

    @callback
    def _handle_update(self) -> None:
        self._update_from_manager()
        if self.hass is not None and self.entity_id:
            self.async_write_ha_state()

    @callback
    def _update_from_manager(self) -> None:
        """Refresh cached attributes; override in subclasses."""

    async def _async_set_option(self, key: str, value: Any) -> None:
        entry = self.manager.entry
        self.hass.config_entries.async_update_entry(entry, options={**entry.options, key: value})
